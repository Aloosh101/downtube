from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess

from PySide6.QtCore import QObject, QSettings, QTimer
from PySide6.QtWidgets import (
    QFileDialog, QListWidgetItem, QMenu, QMessageBox, QTableWidgetItem
)

from views.main_window import (
    AddChannelDialog, AddSingleVideoDialog, EditChannelDialog, ChannelCardWidget, MainWindow,
)
from models.db_manager import DBManager
from core.engine import DownloadEngine
from core.workers import (
    ConvertWorker, DownloadWorker, ExtractionWorker, SingleVideoWorker,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# status → colour
STATUS_COLORS = {
    "completed":  "#a6e3a1",
    "error":      "#f38ba8",
    "downloading":"#89b4fa",
    "pending":    "",
}


class MainController(QObject):

    def __init__(self, main_window: MainWindow):
        super().__init__()
        self.view     = main_window
        self.settings = QSettings("Downtube", "ArchiverSettings")

        self._load_app_settings()
        self._init_backend()
        self._setup_connections()
        self._load_settings_to_ui()
        self._refresh_channels_list()
        self._run_auto_convert()
        self._setup_auto_refresh_timer()

    # ═══════════════════════════════════════════
    #  Init helpers
    # ═══════════════════════════════════════════

    def _load_app_settings(self):
        s = self.settings
        self.cfg: dict = {
            "base_path":      s.value("base_path",      os.path.expanduser("~/Downloads/Downtube")),
            "max_res":        s.value("max_res",         "720"),
            "jellyfin":       self._bool_val(s.value("jellyfin",        "False")),
            "download_shorts":self._bool_val(s.value("download_shorts", "False")),
            "delay_min":      int(s.value("delay_min",   3)),
            "delay_max":      int(s.value("delay_max",   7)),
            "retries":        int(s.value("retries",     10)),
            "ratelimit":      s.value("ratelimit",       ""),
            "max_filesize":   s.value("max_filesize",    ""),
            "proxy":          s.value("proxy",           ""),
            "cookies_file":   s.value("cookies_file",   ""),
            "user_agent":     s.value("user_agent",      ""),
            "file_template":  s.value("file_template",  "%(title)s.%(ext)s"),
            "audio_format":   s.value("audio_format",   "m4a (native, fastest)"),
            "audio_bitrate":  s.value("audio_bitrate",  "best (default)"),
            "parallel_limit": int(s.value("parallel_limit", 3)),
            "auto_convert":   self._bool_val(s.value("auto_convert",   "True")),
            "auto_refresh":   self._bool_val(s.value("auto_refresh",   "False")),
            "auto_refresh_h": int(s.value("auto_refresh_h", 24)),
            "minimize_tray":  self._bool_val(s.value("minimize_tray",  "False")),
            "start_minimized":self._bool_val(s.value("start_minimized","False")),
        }

    @staticmethod
    def _bool_val(v) -> bool:
        if isinstance(v, bool):
            return v
        return str(v).lower() == "true"

    def _init_backend(self):
        base = self.cfg["base_path"]
        os.makedirs(base, exist_ok=True)
        self.db     = DBManager(base)
        self.engine = DownloadEngine(self.cfg)

        # worker tracking
        self.workers: list        = []
        self.active_downloads: dict[int, DownloadWorker] = {}   # channel_id → worker
        self.current_channel_id: int | None = None
        self._all_videos_cache: list[dict]  = []
        self._filtered_videos_cache: list[dict] = []
        self._current_page: int = 0

    # ═══════════════════════════════════════════
    #  Connections
    # ═══════════════════════════════════════════

    def _setup_connections(self):
        v = self.view

        # Settings
        v.btn_browse.clicked.connect(self._browse_path)
        v.btn_browse_cookies.clicked.connect(self._browse_cookies)
        v.btn_save_settings.clicked.connect(self._save_settings)
        v.btn_export_channels.clicked.connect(self._export_channels)
        v.btn_import_channels.clicked.connect(self._import_channels)
        v.btn_clear_log.clicked.connect(v.log_text.clear)

        # Add
        v.btn_add_channel.clicked.connect(self._show_add_channel_dialog)
        v.btn_add_single.clicked.connect(self._show_add_single_dialog)

        # Channel list
        v.channels_list.itemClicked.connect(self._on_channel_selected)
        v.channels_list.customContextMenuRequested.connect(self._channels_context_menu)

        # Search / filter
        v.search_input.textChanged.connect(self._filter_channels_list)
        v.video_search.textChanged.connect(self._filter_videos_table)
        v.status_filter.currentTextChanged.connect(self._filter_videos_table)

        # Pagination
        v.btn_first_page.clicked.connect(lambda: self._go_to_page(0))
        v.btn_prev_page.clicked.connect(lambda: self._go_to_page(self._current_page - 1))
        v.btn_next_page.clicked.connect(lambda: self._go_to_page(self._current_page + 1))
        v.btn_last_page.clicked.connect(lambda: self._go_to_page(self._total_pages() - 1))
        v.page_size_combo.currentTextChanged.connect(lambda _: self._go_to_page(0))

        # Channel actions
        v.btn_download_channel.clicked.connect(self._download_current_channel)
        v.btn_stop_channel.clicked.connect(self._stop_current_channel)
        v.btn_refresh_channel.clicked.connect(self._refresh_current_channel)
        v.btn_edit_channel.clicked.connect(self._edit_current_channel)
        v.btn_retry_errors.clicked.connect(self._retry_errors)
        v.btn_open_folder.clicked.connect(self._open_channel_folder)
        v.btn_delete_channel.clicked.connect(self._delete_current_channel)

        # Table context menu
        v.videos_table.customContextMenuRequested.connect(self._videos_context_menu)

        # Window
        v.window_closed.connect(self._on_window_closed)

    # ═══════════════════════════════════════════
    #  Settings
    # ═══════════════════════════════════════════

    def _load_settings_to_ui(self):
        c  = self.cfg
        v  = self.view
        v.path_input.setText(c["base_path"])
        v.file_template_input.setText(c["file_template"])
        v.res_combo.setCurrentText(c["max_res"])
        v.jellyfin_check.setChecked(c["jellyfin"])
        v.download_shorts_check.setChecked(c["download_shorts"])
        v.delay_min_spin.setValue(c["delay_min"])
        v.delay_max_spin.setValue(c["delay_max"])
        v.retries_spin.setValue(c["retries"])
        v.ratelimit_input.setText(c["ratelimit"])
        v.max_filesize_input.setText(c["max_filesize"])
        v.proxy_input.setText(c["proxy"])
        v.cookies_input.setText(c["cookies_file"])
        v.useragent_input.setText(c["user_agent"])
        v.audio_format_combo.setCurrentText(c["audio_format"])
        v.audio_bitrate_combo.setCurrentText(c["audio_bitrate"])
        v.parallel_spin.setValue(c["parallel_limit"])
        v.auto_convert_check.setChecked(c["auto_convert"])
        v.auto_refresh_check.setChecked(c["auto_refresh"])
        v.auto_refresh_hours_spin.setValue(c["auto_refresh_h"])
        v.minimize_to_tray_check.setChecked(c["minimize_tray"])
        v.start_minimized_check.setChecked(c["start_minimized"])

    def _save_settings(self):
        v  = self.view
        s  = self.settings

        new_path = v.path_input.text().strip()
        if new_path != self.cfg["base_path"]:
            os.makedirs(new_path, exist_ok=True)
            self.db = DBManager(new_path)

        dmin = v.delay_min_spin.value()
        dmax = v.delay_max_spin.value()
        if dmin > dmax:
            dmax = dmin
            v.delay_max_spin.setValue(dmax)

        self.cfg.update({
            "base_path":      new_path,
            "max_res":        v.res_combo.currentText(),
            "jellyfin":       v.jellyfin_check.isChecked(),
            "download_shorts":v.download_shorts_check.isChecked(),
            "delay_min":      dmin,
            "delay_max":      dmax,
            "retries":        v.retries_spin.value(),
            "ratelimit":      v.ratelimit_input.text().strip(),
            "max_filesize":   v.max_filesize_input.text().strip(),
            "proxy":          v.proxy_input.text().strip(),
            "cookies_file":   v.cookies_input.text().strip(),
            "user_agent":     v.useragent_input.text().strip(),
            "file_template":  v.file_template_input.text().strip() or "%(title)s.%(ext)s",
            "audio_format":   v.audio_format_combo.currentText(),
            "audio_bitrate":  v.audio_bitrate_combo.currentText(),
            "parallel_limit": v.parallel_spin.value(),
            "auto_convert":   v.auto_convert_check.isChecked(),
            "auto_refresh":   v.auto_refresh_check.isChecked(),
            "auto_refresh_h": v.auto_refresh_hours_spin.value(),
            "minimize_tray":  v.minimize_to_tray_check.isChecked(),
            "start_minimized":v.start_minimized_check.isChecked(),
        })

        for k, val in self.cfg.items():
            s.setValue(k, val)

        self.engine.update_settings(self.cfg)
        self._setup_auto_refresh_timer()

        self.view.statusBar().showMessage("Settings saved.", 4000)
        self._log("Settings saved.", "success")

    def _browse_path(self):
        d = QFileDialog.getExistingDirectory(self.view, "Select Base Download Directory")
        if d:
            self.view.path_input.setText(d)

    def _browse_cookies(self):
        f, _ = QFileDialog.getOpenFileName(self.view, "Select cookies.txt", filter="Text (*.txt);;All (*)")
        if f:
            self.view.cookies_input.setText(f)

    # ═══════════════════════════════════════════
    #  Channel list
    # ═══════════════════════════════════════════

    def _refresh_channels_list(self):
        self.view.channels_list.clear()
        channels = self.db.get_all_channels()
        for ch in channels:
            stats   = self.db.get_channel_stats(ch["id"])
            is_dl   = ch["id"] in self.active_downloads
            card    = ChannelCardWidget(
                ch["name"], stats,
                is_downloading=is_dl,
                audio_only=ch.get("audio_only", 0) == 1,
            )
            item = QListWidgetItem()
            item.setData(1000, ch["id"])
            item.setSizeHint(card.sizeHint())
            self.view.channels_list.addItem(item)
            self.view.channels_list.setItemWidget(item, card)

        self.view.set_active_downloads_label(len(self.active_downloads))

    def _filter_channels_list(self, query: str):
        q = query.lower()
        for i in range(self.view.channels_list.count()):
            item   = self.view.channels_list.item(i)
            widget = self.view.channels_list.itemWidget(item)
            name   = widget.lbl_name.text().lower() if widget else ""
            item.setHidden(q not in name if q else False)

    def _channels_context_menu(self, pos):
        item = self.view.channels_list.itemAt(pos)
        if not item:
            return
        channel_id = item.data(1000)
        menu = QMenu(self.view)
        menu.addAction("⬇  Download",       lambda: self._download_channel(channel_id))
        menu.addAction("🔄  Refresh",        lambda: self._refresh_channel(channel_id))
        menu.addAction("✏  Edit Channel",   lambda: self._edit_channel_by_id(channel_id))
        menu.addAction("↩  Retry Errors",   lambda: self._retry_errors_by_id(channel_id))
        menu.addAction("📁  Open Folder",    lambda: self._open_folder_by_id(channel_id))
        menu.addSeparator()
        menu.addAction("🗑  Delete Channel", lambda: self._delete_channel(channel_id))
        menu.exec(self.view.channels_list.viewport().mapToGlobal(pos))

    # ═══════════════════════════════════════════
    #  Channel selection / detail
    # ═══════════════════════════════════════════

    def _on_channel_selected(self, item: QListWidgetItem):
        self.current_channel_id = item.data(1000)
        self._reload_channel_detail()

    def _reload_channel_detail(self):
        cid = self.current_channel_id
        if cid is None:
            return
        ch = self.db.get_channel_by_id(cid)
        if not ch:
            return
        stats = self.db.get_channel_stats(cid)
        is_audio = ch.get("audio_only", 0) == 1
        is_dl    = cid in self.active_downloads

        mode_badge = "🎵 Audio" if is_audio else "🎬 Video"
        self.view.lbl_channel_name.setText(f"<b>{ch['name']}</b>  {mode_badge}")
        self.view.lbl_stats.setText(
            f"📥 {stats['completed']}  ⏳ {stats['pending']}  ❌ {stats['error']}  📊 {stats['total']}"
        )
        total = max(stats["total"], 1)
        self.view.channel_progress.setRange(0, total)
        self.view.channel_progress.setValue(stats["completed"])

        # Toggle download / stop buttons
        self.view.btn_download_channel.setVisible(not is_dl)
        self.view.btn_stop_channel.setVisible(is_dl)

        self._all_videos_cache = self.db.get_videos_for_channel(cid)
        self._filter_videos_table()

    def _filter_videos_table(self):
        """Apply search/status filter and reset to page 0."""
        query      = self.view.video_search.text().lower()
        status_flt = self.view.status_filter.currentText()

        self._filtered_videos_cache = [
            v for v in self._all_videos_cache
            if (not query or query in v["title"].lower())
            and (status_flt == "All" or v["status"] == status_flt)
        ]
        self._current_page = 0
        self._render_table_page()

    def _total_pages(self) -> int:
        page_size = int(self.view.page_size_combo.currentText())
        total     = len(self._filtered_videos_cache)
        return max(1, (total + page_size - 1) // page_size)

    def _go_to_page(self, page: int):
        total = self._total_pages()
        self._current_page = max(0, min(page, total - 1))
        self._render_table_page()

    def _render_table_page(self):
        """Render only the current page slice into the table — O(page_size) not O(total)."""
        from PySide6.QtGui import QColor

        page_size = int(self.view.page_size_combo.currentText())
        total     = len(self._filtered_videos_cache)
        start     = self._current_page * page_size
        end       = min(start + page_size, total)
        page      = self._filtered_videos_cache[start:end]
        n_pages   = self._total_pages()

        # Update pagination controls
        self.view.lbl_page_info.setText(f"Page {self._current_page + 1} / {n_pages}")
        self.view.lbl_total_videos.setText(
            f"{total} video{'s' if total != 1 else ''}  (showing {start+1}–{end})"
            if total else "0 videos"
        )
        self.view.btn_first_page.setEnabled(self._current_page > 0)
        self.view.btn_prev_page.setEnabled(self._current_page > 0)
        self.view.btn_next_page.setEnabled(self._current_page < n_pages - 1)
        self.view.btn_last_page.setEnabled(self._current_page < n_pages - 1)

        # Fill the table with only the visible slice
        tbl = self.view.videos_table
        tbl.setUpdatesEnabled(False)          # batch paint
        tbl.setRowCount(len(page))
        for row, vid in enumerate(page):
            tbl.setItem(row, 0, QTableWidgetItem(vid["video_id"]))
            tbl.setItem(row, 1, QTableWidgetItem(vid["title"]))
            tbl.setItem(row, 2, QTableWidgetItem(vid["url"]))
            status_item = QTableWidgetItem(vid["status"])
            colour = STATUS_COLORS.get(vid["status"], "")
            if colour:
                status_item.setForeground(QColor(colour))
            tbl.setItem(row, 3, status_item)
        tbl.setUpdatesEnabled(True)

    def _videos_context_menu(self, pos):
        row = self.view.videos_table.rowAt(pos.y())
        if row < 0:
            return
        vid_id = self.view.videos_table.item(row, 0).text()
        url    = self.view.videos_table.item(row, 2).text()
        menu = QMenu(self.view)
        menu.addAction("↩  Mark as Pending", lambda: self._mark_video_pending(vid_id))
        menu.addAction("🌐  Open in Browser", lambda: __import__("webbrowser").open(url))
        menu.exec(self.view.videos_table.viewport().mapToGlobal(pos))

    def _mark_video_pending(self, vid_id: str):
        self.db.update_video_status(vid_id, "pending")
        self._reload_channel_detail()

    # ═══════════════════════════════════════════
    #  Add channel
    # ═══════════════════════════════════════════

    def _show_add_channel_dialog(self):
        dlg = AddChannelDialog(self.view)
        if dlg.exec():
            url, audio_only, custom_path = dlg.get_data()
            if url:
                self._start_extraction(url, audio_only=audio_only, custom_path=custom_path)

    def _start_extraction(self, url: str, audio_only=False, custom_path=None):
        self.view.statusBar().showMessage("Adding channel …")
        worker = ExtractionWorker(
            self.db, self.engine, url,
            skip_shorts=not self.cfg.get("download_shorts", False),
            just_info=True,
            audio_only=audio_only,
            custom_path=custom_path,
        )
        worker.progress.connect(self.view.statusBar().showMessage)
        worker.progress.connect(lambda m: self._log(m))
        worker.error.connect(lambda e: (
            QMessageBox.critical(self.view, "Extraction Error", e),
            self._log(e, "error"),
        ))
        worker.finished.connect(self._on_extraction_finished)
        self.workers.append(worker)
        worker.start()

    def _on_extraction_finished(self, channel_id: int):
        self._log(f"Channel added (id={channel_id}).", "success")
        self._refresh_channels_list()
        self._select_channel_by_id(channel_id)
        self._cleanup_workers()

    # ═══════════════════════════════════════════
    #  Refresh channel
    # ═══════════════════════════════════════════

    def _refresh_current_channel(self):
        if self.current_channel_id is not None:
            self._refresh_channel(self.current_channel_id)

    def _refresh_channel(self, channel_id: int):
        ch = self.db.get_channel_by_id(channel_id)
        if not ch:
            return
        self.view.btn_refresh_channel.setEnabled(False)
        self.view.statusBar().showMessage(f"Refreshing '{ch['name']}' …")
        self._log(f"Refreshing channel: {ch['name']}")
        worker = ExtractionWorker(
            self.db, self.engine, ch["url"],
            skip_shorts=not self.cfg.get("download_shorts", False),
            break_on_existing=50,
        )
        worker.progress.connect(self.view.statusBar().showMessage)
        worker.progress.connect(lambda m: self._log(m))
        worker.error.connect(lambda e: (
            QMessageBox.critical(self.view, "Refresh Error", e),
            self._log(e, "error"),
        ))
        worker.finished.connect(self._on_refresh_finished)
        self.workers.append(worker)
        worker.start()

    def _on_refresh_finished(self, channel_id: int):
        self.view.btn_refresh_channel.setEnabled(True)
        self._log("Refresh complete.", "success")
        self._refresh_channels_list()
        if self.current_channel_id == channel_id:
            self._reload_channel_detail()
        self._cleanup_workers()

    # ═══════════════════════════════════════════
    #  Download channel
    # ═══════════════════════════════════════════

    def _download_current_channel(self):
        if self.current_channel_id is not None:
            self._download_channel(self.current_channel_id)

    def _stop_current_channel(self):
        """Stop the currently downloading channel."""
        cid = self.current_channel_id
        if cid is None or cid not in self.active_downloads:
            return
        worker = self.active_downloads[cid]
        worker.stop()
        self._log(f"Stopping download for channel id={cid}…", "warning")
        self.view.statusBar().showMessage("Stopping download…")

    def _edit_current_channel(self):
        """Open the edit dialog to modify channel settings."""
        cid = self.current_channel_id
        if cid is None:
            return
        ch = self.db.get_channel_by_id(cid)
        if not ch:
            return
        dlg = EditChannelDialog(ch, parent=self.view)
        if dlg.exec():
            data = dlg.get_data()
            self.db.update_channel_settings(
                cid,
                audio_only=data["audio_only"],
                custom_path=data["custom_path"],
                video_quality=data["video_quality"],
                audio_bitrate=data["audio_bitrate"],
            )
            self._log(f"Updated settings for '{ch['name']}'.", "success")
            self.view.statusBar().showMessage("Channel settings saved.", 4000)
            self._refresh_channels_list()
            self._reload_channel_detail()

    def _edit_channel_by_id(self, channel_id: int):
        """Open edit dialog for a specific channel (used from context menu)."""
        ch = self.db.get_channel_by_id(channel_id)
        if not ch:
            return
        dlg = EditChannelDialog(ch, parent=self.view)
        if dlg.exec():
            data = dlg.get_data()
            self.db.update_channel_settings(
                channel_id,
                audio_only=data["audio_only"],
                custom_path=data["custom_path"],
                video_quality=data["video_quality"],
                audio_bitrate=data["audio_bitrate"],
            )
            self._log(f"Updated settings for '{ch['name']}'.", "success")
            self._refresh_channels_list()
            if self.current_channel_id == channel_id:
                self._reload_channel_detail()

    def _download_channel(self, channel_id: int):
        if channel_id in self.active_downloads:
            self.view.statusBar().showMessage("This channel is already downloading.")
            return

        ch = self.db.get_channel_by_id(channel_id)
        if not ch:
            return

        worker = DownloadWorker(self.db, self.engine, channel_id)
        self.active_downloads[channel_id] = worker

        worker.progress.connect(self.view.statusBar().showMessage)
        worker.progress.connect(lambda m: self._log(m))
        worker.error.connect(lambda e: self._log(e, "error"))
        worker.video_started.connect(lambda vid: self._on_video_started(channel_id, vid))
        worker.video_finished.connect(lambda vid: self._on_video_downloaded(channel_id, vid))
        worker.finished.connect(self._on_download_finished)

        self.workers.append(worker)
        worker.start()

        self._log(f"Started download for '{ch['name']}'.")
        self._refresh_channels_list()
        if self.current_channel_id == channel_id:
            self.view.btn_download_channel.setVisible(False)
            self.view.btn_stop_channel.setVisible(True)

    def _on_video_started(self, channel_id: int, video_id: str):
        self._update_video_status_in_cache(video_id, "downloading")
        if self.current_channel_id == channel_id:
            self.view.lbl_current_video.setText(f"⬇ Downloading: {video_id}")
            self._update_visible_table_row(video_id, "downloading")

    def _on_video_downloaded(self, channel_id: int, video_id: str):
        self._update_video_status_in_cache(video_id, "completed")
        if self.current_channel_id == channel_id:
            self._update_visible_table_row(video_id, "completed")
            
            # Update stats label and progress
            stats = self.db.get_channel_stats(channel_id)
            self.view.lbl_stats.setText(
                f"📥 {stats['completed']}  ⏳ {stats['pending']}  ❌ {stats['error']}  📊 {stats['total']}"
            )
            self.view.channel_progress.setValue(stats["completed"])
            self.view.lbl_current_video.setText("")

    def _update_video_status_in_cache(self, video_id: str, status: str):
        """Update status in all cache lists so pagination stays in sync."""
        for v in self._all_videos_cache:
            if v["video_id"] == video_id:
                v["status"] = status
        for v in self._filtered_videos_cache:
            if v["video_id"] == video_id:
                v["status"] = status

    def _update_visible_table_row(self, video_id: str, status: str):
        """Update the row only if it's currently visible on the active page."""
        tbl = self.view.videos_table
        from PySide6.QtGui import QColor
        for row in range(tbl.rowCount()):
            item0 = tbl.item(row, 0)
            if item0 and item0.text() == video_id:
                status_item = QTableWidgetItem(status)
                colour = STATUS_COLORS.get(status, "")
                if colour:
                    status_item.setForeground(QColor(colour))
                tbl.setItem(row, 3, status_item)
                break
            self.view.lbl_current_video.setText("")

    def _on_download_finished(self, channel_id: int):
        ch   = self.db.get_channel_by_id(channel_id)
        name = ch["name"] if ch else str(channel_id)
        self._log(f"Download complete: '{name}'.", "success")
        self.view.notify("Downtube", f"Download finished: {name}")

        self.active_downloads.pop(channel_id, None)
        self._refresh_channels_list()

        if self.current_channel_id == channel_id:
            self.view.btn_download_channel.setVisible(True)
            self.view.btn_stop_channel.setVisible(False)
            self.view.lbl_current_video.setText("")
            self._reload_channel_detail()

        self._cleanup_workers()
        if self.cfg.get("auto_convert"):
            self._run_auto_convert()

    # ═══════════════════════════════════════════
    #  Single video
    # ═══════════════════════════════════════════

    def _show_add_single_dialog(self):
        dlg = AddSingleVideoDialog(self.view)
        if dlg.exec():
            url, audio_only = dlg.get_data()
            if url:
                self._start_single_download(url, audio_only)

    def _start_single_download(self, url: str, audio_only: bool = False):
        self.view.statusBar().showMessage("Starting single video download …")
        worker = SingleVideoWorker(self.engine, url, audio_only=audio_only)
        worker.progress.connect(self.view.statusBar().showMessage)
        worker.progress.connect(lambda m: self._log(m))
        worker.error.connect(lambda e: (
            QMessageBox.warning(self.view, "Download Error", e),
            self._log(e, "error"),
        ))
        worker.finished.connect(self._on_single_finished)
        self.workers.append(worker)
        worker.start()

    def _on_single_finished(self):
        self._log("Single video downloaded.", "success")
        self.view.notify("Downtube", "Single video download complete!")
        self.view.statusBar().showMessage("Done.", 4000)
        self._cleanup_workers()

    # ═══════════════════════════════════════════
    #  Error retry
    # ═══════════════════════════════════════════

    def _retry_errors(self):
        if self.current_channel_id is not None:
            self._retry_errors_by_id(self.current_channel_id)

    def _retry_errors_by_id(self, channel_id: int):
        self.db.retry_errors(channel_id)
        self._log("Errors reset to pending.", "info")
        if self.current_channel_id == channel_id:
            self._reload_channel_detail()

    # ═══════════════════════════════════════════
    #  Open folder
    # ═══════════════════════════════════════════

    def _open_channel_folder(self):
        if self.current_channel_id is not None:
            self._open_folder_by_id(self.current_channel_id)

    def _open_folder_by_id(self, channel_id: int):
        ch = self.db.get_channel_by_id(channel_id)
        if not ch:
            return
        custom  = ch.get("custom_path") or None
        base    = custom if custom else self.cfg["base_path"]
        folder  = os.path.join(base, ch["name"])
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        import subprocess as sp, sys
        if sys.platform == "linux":
            sp.Popen(["xdg-open", folder])
        elif sys.platform == "darwin":
            sp.Popen(["open", folder])
        else:
            sp.Popen(["explorer", folder])

    # ═══════════════════════════════════════════
    #  Delete channel
    # ═══════════════════════════════════════════

    def _delete_current_channel(self):
        if self.current_channel_id is not None:
            self._delete_channel(self.current_channel_id)

    def _delete_channel(self, channel_id: int):
        ch = self.db.get_channel_by_id(channel_id)
        if not ch:
            return
        reply = QMessageBox.question(
            self.view,
            "Delete Channel",
            f"Delete channel <b>{ch['name']}</b> from the database?<br><br>"
            "Downloaded files on disk will <b>NOT</b> be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if channel_id in self.active_downloads:
            self.active_downloads[channel_id].stop()
            self.active_downloads.pop(channel_id, None)

        self.db.delete_channel(channel_id)
        self._log(f"Deleted channel '{ch['name']}'.", "warning")

        if self.current_channel_id == channel_id:
            self.current_channel_id = None
            self.view.lbl_channel_name.setText("Select a channel →")
            self.view.lbl_stats.setText("")
            self.view.videos_table.setRowCount(0)
            self._all_videos_cache = []

        self._refresh_channels_list()

    # ═══════════════════════════════════════════
    #  Export / Import
    # ═══════════════════════════════════════════

    def _export_channels(self):
        path, _ = QFileDialog.getSaveFileName(
            self.view, "Export Channels", "downtube_channels.json",
            "JSON (*.json);;All (*)"
        )
        if path:
            self.db.export_channels(path)
            self._log(f"Exported channels to {path}", "success")
            self.view.statusBar().showMessage(f"Exported to {path}", 4000)

    def _import_channels(self):
        path, _ = QFileDialog.getOpenFileName(
            self.view, "Import Channels", filter="JSON (*.json);;All (*)"
        )
        if not path:
            return
        try:
            added = self.db.import_channels(path)
            self._log(f"Imported {added} channel(s) from {path}", "success")
            self.view.statusBar().showMessage(f"Imported {added} channel(s).", 5000)
            self._refresh_channels_list()
        except Exception as e:
            QMessageBox.critical(self.view, "Import Error", str(e))
            self._log(str(e), "error")

    # ═══════════════════════════════════════════
    #  Auto convert
    # ═══════════════════════════════════════════

    def _run_auto_convert(self):
        if not self.cfg.get("auto_convert", True):
            return
        worker = ConvertWorker(self.db, self.engine)
        worker.progress.connect(lambda m: self._log(m))
        worker.error.connect(lambda e: self._log(e, "error"))
        worker.finished.connect(lambda: self._remove_worker(worker))
        self.workers.append(worker)
        worker.start()

    # ═══════════════════════════════════════════
    #  Auto refresh timer
    # ═══════════════════════════════════════════

    def _setup_auto_refresh_timer(self):
        if hasattr(self, "_auto_refresh_timer"):
            self._auto_refresh_timer.stop()
        if self.cfg.get("auto_refresh", False):
            hours_ms = self.cfg.get("auto_refresh_h", 24) * 3600 * 1000
            self._auto_refresh_timer = QTimer(self)
            self._auto_refresh_timer.timeout.connect(self._auto_refresh_all)
            self._auto_refresh_timer.start(hours_ms)
            self._log(f"Auto-refresh every {self.cfg['auto_refresh_h']}h enabled.")

    def _auto_refresh_all(self):
        self._log("Auto-refresh: checking all channels for new videos …")
        for ch in self.db.get_all_channels():
            self._refresh_channel(ch["id"])

    # ═══════════════════════════════════════════
    #  Helpers
    # ═══════════════════════════════════════════

    def _select_channel_by_id(self, channel_id: int):
        lst = self.view.channels_list
        for i in range(lst.count()):
            item = lst.item(i)
            if item.data(1000) == channel_id:
                lst.setCurrentItem(item)
                self._on_channel_selected(item)
                break

    def _remove_worker(self, w):
        if w in self.workers:
            self.workers.remove(w)

    def _cleanup_workers(self):
        self.workers = [w for w in self.workers if w.isRunning()]

    def _log(self, msg: str, level: str = "info"):
        logger.info(msg)
        self.view.append_log(msg, level)

    def _on_window_closed(self):
        for w in list(self.workers):
            if w.isRunning():
                w.stop()
                w.wait(2000)
