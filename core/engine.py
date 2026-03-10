import yt_dlp
import os
import random
import time
import logging


class DownloadEngine:
    """
    Central engine that produces yt-dlp option-dicts for every download
    scenario.  All tunables come from a single settings dict so the
    controller only needs to call `update_settings(...)` once after a
    save.
    """

    def __init__(self, settings: dict):
        self.logger = logging.getLogger(__name__)
        self.update_settings(settings)

    # ─────────────────────────────────────────────
    #  Settings
    # ─────────────────────────────────────────────

    def update_settings(self, settings: dict):
        self.base_path          = settings.get("base_path", os.path.expanduser("~/Downloads/Downtube"))
        self.max_resolution     = settings.get("max_res", "720").split()[0]   # strip "(4K)" labels
        self.jellyfin_compat    = settings.get("jellyfin", False)
        self.delay_min          = int(settings.get("delay_min", 3))
        self.delay_max          = int(settings.get("delay_max", 7))
        self.retries            = int(settings.get("retries", 10))
        self.ratelimit          = settings.get("ratelimit", "").strip() or None
        self.max_filesize       = settings.get("max_filesize", "").strip() or None
        self.proxy              = settings.get("proxy", "").strip() or None
        self.cookies_file       = settings.get("cookies_file", "").strip() or None
        self.user_agent         = settings.get("user_agent", "").strip() or None
        self.file_template      = settings.get("file_template", "").strip() or "%(title)s.%(ext)s"
        self.audio_format       = settings.get("audio_format", "m4a")     # m4a | mp3 | opus | flac
        self.audio_bitrate      = settings.get("audio_bitrate", "best")   # best | 320k | 256k …
        self.parallel_limit     = int(settings.get("parallel_limit", 3))

    # ─────────────────────────────────────────────
    #  Output template helpers
    # ─────────────────────────────────────────────

    def _outtmpl(self, channel_name: str, custom_path: str | None = None) -> str:
        base = custom_path if custom_path else self.base_path
        if self.jellyfin_compat:
            return os.path.join(base, "%(uploader)s", self.file_template)
        return os.path.join(base, channel_name, self.file_template)

    # ─────────────────────────────────────────────
    #  Download options
    # ─────────────────────────────────────────────

    def get_download_options(
        self,
        channel_name: str,
        audio_only: bool = False,
        custom_path: str | None = None,
    ) -> dict:
        outtmpl = self._outtmpl(channel_name, custom_path)

        if audio_only:
            fmt = self._audio_format_str()
            postprocessors = self._audio_postprocessors(audio_only=True)
            merge_opts: dict = {}
        else:
            fmt = (
                f"bestvideo[ext=mp4][height<={self.max_resolution}]"
                f"+bestaudio[ext=m4a]"
                f"/bestvideo[height<={self.max_resolution}]+bestaudio"
                f"/best[height<={self.max_resolution}]"
            )
            postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
            merge_opts = {"merge_output_format": "mp4"}

        opts: dict = {
            "format": fmt,
            "outtmpl": outtmpl,
            "writethumbnail": False,
            "postprocessors": postprocessors,
            "clean_infojson": True,
            "retries": self.retries,
            "fragment_retries": self.retries,
            "sleep_interval_requests": 1,
            "sleep_interval_subtitles": 1,
            "sleep_interval": self.delay_min,
            "max_sleep_interval": self.delay_max,
            "quiet": False,
            "noprogress": True,
            "ignoreerrors": True,
        }

        opts.update(merge_opts)

        if self.ratelimit:
            opts["ratelimit"] = self._parse_size(self.ratelimit)
        if self.max_filesize:
            opts["max_filesize"] = self._parse_size(self.max_filesize)
        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookies_file and os.path.exists(self.cookies_file):
            opts["cookiefile"] = self.cookies_file
        if self.user_agent:
            opts["http_headers"] = {"User-Agent": self.user_agent}

        return opts

    def get_extraction_options(self) -> dict:
        """Flat metadata-only extraction (no download)."""
        opts: dict = {
            "extract_flat": True,
            "quiet": True,
            "ignoreerrors": True,
            "lazy_playlist": True,
        }
        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookies_file and os.path.exists(self.cookies_file):
            opts["cookiefile"] = self.cookies_file
        if self.user_agent:
            opts["http_headers"] = {"User-Agent": self.user_agent}
        return opts

    # ─────────────────────────────────────────────
    #  Audio helpers
    # ─────────────────────────────────────────────

    def _audio_format_str(self) -> str:
        fmt = self.audio_format.split()[0].lower()   # strip label suffix
        if fmt == "m4a":
            return "bestaudio[ext=m4a]/bestaudio/best"
        if fmt == "mp3":
            return "bestaudio/best"
        if fmt == "opus":
            return "bestaudio[ext=webm]/bestaudio/best"
        if fmt == "flac":
            return "bestaudio/best"
        return "bestaudio[ext=m4a]/bestaudio/best"

    def _audio_postprocessors(self, audio_only: bool = False) -> list:
        fmt = self.audio_format.split()[0].lower()
        if fmt == "m4a":
            return []           # native m4a — no conversion needed
        bitrate = self.audio_bitrate if self.audio_bitrate != "best" else "0"
        codec_map = {"mp3": "mp3", "opus": "opus", "flac": "flac"}
        codec = codec_map.get(fmt, "mp3")
        return [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": codec,
            "preferredquality": bitrate.replace("k", ""),
        }]

    # ─────────────────────────────────────────────
    #  Utilities
    # ─────────────────────────────────────────────

    def sleep_randomly(self):
        t = random.uniform(float(self.delay_min), float(self.delay_max))
        self.logger.debug(f"Sleeping {t:.1f}s between downloads")
        time.sleep(t)

    @staticmethod
    def _parse_size(s: str) -> int:
        """Convert '5M' → 5_000_000, '500K' → 500_000, etc."""
        s = s.strip().upper()
        mult = {"K": 1_000, "M": 1_000_000, "G": 1_000_000_000}
        if s and s[-1] in mult:
            return int(float(s[:-1]) * mult[s[-1]])
        return int(s) if s.isdigit() else 0
