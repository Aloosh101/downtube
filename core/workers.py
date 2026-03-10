from __future__ import annotations

import os
import subprocess
import threading
import traceback
import logging

import yt_dlp
from PySide6.QtCore import QThread, Signal

from models.db_manager import DBManager
from core.engine import DownloadEngine


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  ExtractionWorker  —  fast flat-crawl of a channel / playlist
# ═══════════════════════════════════════════════════════════════

class ExtractionWorker(QThread):
    progress = Signal(str)
    finished = Signal(int)   # channel_id
    error    = Signal(str)

    def __init__(
        self,
        db_manager: DBManager,
        engine: DownloadEngine,
        url: str,
        skip_shorts: bool = True,
        skip_live: bool = True,
        break_on_existing: int = 0,
        just_info: bool = False,
        audio_only: bool = False,
        custom_path: str | None = None,
    ):
        super().__init__()
        self.db                = db_manager
        self.engine            = engine
        self.url               = url
        self.skip_shorts       = skip_shorts
        self.skip_live         = skip_live
        self.break_on_existing = break_on_existing
        self.just_info         = just_info
        self.audio_only        = audio_only
        self.custom_path       = custom_path
        self.is_running        = True

    def run(self):
        try:
            self.progress.emit(f"Extracting info from {self.url} …")

            ydl_opts = self.engine.get_extraction_options()
            if self.just_info:
                ydl_opts["playlistend"] = 1

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            if not info:
                self.error.emit("Could not extract channel information.")
                return

            channel_name = info.get("uploader") or info.get("title") or "Unknown Channel"
            channel_id   = self.db.add_channel(
                channel_name, self.url,
                audio_only=self.audio_only,
                custom_path=self.custom_path,
            )

            if self.just_info:
                self.progress.emit(f"Channel '{channel_name}' added.")
                self.finished.emit(channel_id)
                return

            entries = info.get("entries", [])
            if not entries:
                self.progress.emit("No videos found.")
                self.finished.emit(channel_id)
                return

            # Check prior extraction state
            conn   = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT is_fully_extracted FROM Channels WHERE id = ?", (channel_id,))
            row = cursor.fetchone()
            fully_extracted = row[0] == 1 if row else False
            conn.close()

            count                = 0
            consecutive_existing = 0
            completed_naturally  = True
            existing_ids         = self.db.get_existing_video_ids(channel_id)
            batch                = []

            def process_video(entry) -> str | bool:
                nonlocal count, consecutive_existing, completed_naturally
                if self.skip_live and entry.get("is_live", False):
                    return False
                url_     = entry.get("url", "")
                title    = entry.get("title", "Unknown Title")
                video_id = entry.get("id", "")
                if self.skip_shorts and "/shorts/" in url_:
                    return False
                if not url_.startswith("http") and video_id:
                    url_ = f"https://www.youtube.com/watch?v={video_id}"
                if video_id and url_:
                    if video_id in existing_ids:
                        consecutive_existing += 1
                        if (self.break_on_existing > 0
                                and consecutive_existing >= self.break_on_existing
                                and fully_extracted):
                            return "break_tab"
                        return False
                    batch.append((video_id, title, url_, channel_id))
                    existing_ids.add(video_id)
                    count += 1
                    consecutive_existing = 0
                    if len(batch) >= 100:
                        self.db.add_videos_batch(batch)
                        batch.clear()
                        self.progress.emit(f"Extracted {count} new videos …")
                return True

            def process_entries(ents):
                nonlocal completed_naturally
                if ents is None:
                    return
                for e in ents:
                    if not self.is_running:
                        completed_naturally = False
                        break
                    if not e:
                        continue
                    if e.get("_type") in ("playlist", "multi_video"):
                        process_entries(e.get("entries", []))
                    else:
                        res = process_video(e)
                        if res == "break_tab":
                            self.progress.emit(f"Up to date  ({consecutive_existing} existing seen). Skipping rest.")
                            break

            process_entries(entries)

            if batch:
                self.db.add_videos_batch(batch)

            if completed_naturally:
                self.db.set_channel_fully_extracted(channel_id)

            self.db.update_channel_extracted_count(channel_id)

            msg = (f"Extracted {count} new videos for '{channel_name}'."
                   if count else f"No new videos for '{channel_name}'.")
            self.progress.emit(msg)
            self.finished.emit(channel_id)

        except Exception as e:
            self.error.emit(f"Extraction failed: {e}\n{traceback.format_exc()}")

    def stop(self):
        self.is_running = False


# ═══════════════════════════════════════════════════════════════
#  DownloadWorker  —  sequential download of one channel queue
# ═══════════════════════════════════════════════════════════════

class DownloadWorker(QThread):
    progress        = Signal(str)
    video_started   = Signal(str)           # video_id
    video_finished  = Signal(str)           # video_id
    video_progress  = Signal(str, float)    # video_id, percent 0-100
    finished        = Signal(int)           # channel_id
    error           = Signal(str)

    def __init__(self, db_manager: DBManager, engine: DownloadEngine, channel_id: int):
        super().__init__()
        self.db         = db_manager
        self.engine     = engine
        self.channel_id = channel_id
        self.is_running = True

    def run(self):
        try:
            channels = self.db.get_all_channels()
            channel  = next((c for c in channels if c["id"] == self.channel_id), None)
            if not channel:
                self.error.emit("Channel not found.")
                return

            channel_name = channel["name"]
            audio_only   = channel.get("audio_only", 0) == 1
            custom_path  = channel.get("custom_path") or None
            # Per-channel quality overrides
            res_override     = channel.get("video_quality", "") or None
            bitrate_override = channel.get("audio_bitrate", "") or None
            if res_override == "channel default":
                res_override = None
            if bitrate_override == "channel default":
                bitrate_override = None

            pending = [v for v in self.db.get_videos_for_channel(self.channel_id)
                       if v["status"] == "pending"]

            if not pending:
                self.progress.emit("No pending videos.")
                self.finished.emit(self.channel_id)
                return

            self.progress.emit(f"Starting {len(pending)} videos for '{channel_name}' …")

            for video in pending:
                if not self.is_running:
                    self.progress.emit("Download paused.")
                    break

                vid_id = video["video_id"]
                self.video_started.emit(vid_id)
                self.progress.emit(f"Downloading: {video['title']}")
                self.db.update_video_status(vid_id, "downloading")

                opts = self.engine.get_download_options(
                    channel_name,
                    audio_only=audio_only,
                    custom_path=custom_path,
                    res_override=res_override,
                    bitrate_override=bitrate_override,
                )

                # ── progress hook ─────────────────────────────
                def _hook(d, _vid_id=vid_id):
                    if d["status"] == "downloading":
                        pct_str = d.get("_percent_str", "").strip()
                        try:
                            pct = float(pct_str.replace("%", ""))
                        except ValueError:
                            pct = 0.0
                        spd  = d.get("_speed_str", "")
                        eta  = d.get("_eta_str", "")
                        self.video_progress.emit(_vid_id, pct)
                        self.progress.emit(f"[{pct_str}]  {spd}  ETA {eta}  —  {video['title'][:60]}")

                opts["progress_hooks"] = [_hook]

                filepath = None
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info_dict = ydl.extract_info(video["url"], download=True)
                        if info_dict and "requested_downloads" in info_dict and info_dict["requested_downloads"]:
                            filepath = info_dict["requested_downloads"][0].get("filepath")
                        if not filepath and info_dict:
                            filepath = ydl.prepare_filename(info_dict)

                    self.db.update_video_status(vid_id, "completed")
                    self.video_finished.emit(vid_id)
                    logger.info(f"Downloaded: {video['title']}")

                    # Background conversion if it still came down as mp4 for audio channels
                    if audio_only and filepath and filepath.endswith(".mp4") and os.path.exists(filepath):
                        t = threading.Thread(target=self._background_convert, args=(filepath,), daemon=True)
                        t.start()

                    if self.is_running:
                        self.engine.sleep_randomly()

                except Exception as e:
                    self.db.update_video_status(vid_id, "error")
                    self.error.emit(f"Error on '{video['title']}': {e}")

            self.progress.emit(f"Finished batch for '{channel_name}'.")
            self.finished.emit(self.channel_id)

        except Exception as e:
            self.error.emit(f"Worker error: {e}\n{traceback.format_exc()}")

    def _background_convert(self, mp4_path: str):
        m4a_path = mp4_path[:-4] + ".m4a"
        cmd = ["ffmpeg", "-y", "-i", mp4_path, "-vn", "-c:a", "copy", m4a_path]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            fallback = ["ffmpeg", "-y", "-i", mp4_path, "-vn", "-c:a", "aac", "-b:a", "192k", m4a_path]
            subprocess.run(fallback, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(m4a_path) and os.path.getsize(m4a_path) > 1000:
            try:
                os.remove(mp4_path)
            except OSError:
                pass

    def stop(self):
        self.is_running = False


# ═══════════════════════════════════════════════════════════════
#  SingleVideoWorker
# ═══════════════════════════════════════════════════════════════

class SingleVideoWorker(QThread):
    progress = Signal(str)
    finished = Signal()
    error    = Signal(str)

    def __init__(self, engine: DownloadEngine, url: str, audio_only: bool = False):
        super().__init__()
        self.engine     = engine
        self.url        = url
        self.audio_only = audio_only
        self.is_running = True

    def run(self):
        try:
            self.progress.emit(f"Downloading: {self.url}")
            opts = self.engine.get_download_options(
                "Single Videos",
                audio_only=self.audio_only,
            )

            def _hook(d):
                if d["status"] == "downloading":
                    self.progress.emit(
                        f"[{d.get('_percent_str','').strip()}]  "
                        f"{d.get('_speed_str','')}  ETA {d.get('_eta_str','')}"
                    )

            opts["progress_hooks"] = [_hook]

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])

            self.progress.emit("Single video downloaded successfully.")
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Single video error: {e}")

    def stop(self):
        self.is_running = False


# ═══════════════════════════════════════════════════════════════
#  ConvertWorker  —  scan audio-only channel folders for MP4s
# ═══════════════════════════════════════════════════════════════

class ConvertWorker(QThread):
    progress = Signal(str)
    finished = Signal()
    error    = Signal(str)

    def __init__(self, db: DBManager, engine: DownloadEngine):
        super().__init__()
        self.db         = db
        self.engine     = engine
        self.is_running = True

    def run(self):
        try:
            mp4_files: list[str] = []
            for channel in self.db.get_all_channels():
                if channel.get("audio_only", 0) != 1:
                    continue
                custom_path  = channel.get("custom_path") or None
                opts         = self.engine.get_download_options(channel["name"], audio_only=True, custom_path=custom_path)
                channel_dir  = os.path.dirname(opts["outtmpl"])
                if not os.path.exists(channel_dir):
                    continue
                for root, _, files in os.walk(channel_dir):
                    for f in files:
                        if f.endswith(".mp4"):
                            mp4_files.append(os.path.join(root, f))

            if not mp4_files:
                self.progress.emit("No MP4 files found in audio-only channels.")
                self.finished.emit()
                return

            total = len(mp4_files)
            self.progress.emit(f"Found {total} MP4 file(s) to convert …")

            for i, mp4_file in enumerate(mp4_files):
                if not self.is_running:
                    self.progress.emit("Conversion stopped.")
                    break

                fname    = os.path.basename(mp4_file)
                m4a_path = mp4_file[:-4] + ".m4a"
                self.progress.emit(f"Converting ({i+1}/{total}): {fname}")

                cmd = ["ffmpeg", "-y", "-i", mp4_file, "-vn", "-c:a", "copy", m4a_path]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if res.returncode != 0:
                    fallback = ["ffmpeg", "-y", "-i", mp4_file, "-vn", "-c:a", "aac", "-b:a", "192k", m4a_path]
                    subprocess.run(fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if os.path.exists(m4a_path) and os.path.getsize(m4a_path) > 1000:
                    try:
                        os.remove(mp4_file)
                    except OSError:
                        pass

            if self.is_running:
                self.progress.emit("Conversion complete.")
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Conversion error: {e}")

    def stop(self):
        self.is_running = False
