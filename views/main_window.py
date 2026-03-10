import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QCheckBox, QFileDialog,
    QSpinBox, QProgressBar, QSplitter, QTextEdit, QMenu,
    QSystemTrayIcon, QApplication, QMessageBox, QSizePolicy,
    QScrollArea, QGroupBox, QDoubleSpinBox, QToolButton, QFrame,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont, QAction, QColor, QPalette, QPixmap, QFontDatabase


# ─────────────────────────────────────────────
#  Theme helpers
# ─────────────────────────────────────────────
DARK_PALETTE = {
    "bg":        "#1e1e2e",
    "surface":   "#2a2a3d",
    "border":    "#3a3a55",
    "accent":    "#7c6af7",
    "accent2":   "#5cb85c",
    "danger":    "#e06c75",
    "text":      "#cdd6f4",
    "text_dim":  "#6c7086",
    "sidebar_bg":"#16161f",
}

LIGHT_PALETTE = {
    "bg":        "#f5f5f7",
    "surface":   "#ffffff",
    "border":    "#d1d1d6",
    "accent":    "#5856d6",
    "accent2":   "#34c759",
    "danger":    "#ff3b30",
    "text":      "#1c1c1e",
    "text_dim":  "#8e8e93",
    "sidebar_bg":"#e8e8ed",
}


def build_stylesheet(p: dict) -> str:
    return f"""
    /* ── Global ── */
    QMainWindow, QDialog, QWidget {{
        background-color: {p['bg']};
        color: {p['text']};
        font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        font-size: 13px;
    }}

    /* ── Sidebar ── */
    #sidebar {{
        background-color: {p['sidebar_bg']};
        border-right: 1px solid {p['border']};
    }}
    #sidebar QPushButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        color: {p['text']};
        font-size: 13px;
        font-weight: 500;
    }}
    #sidebar QPushButton:hover {{
        background-color: {p['border']};
    }}
    #sidebar QPushButton:checked {{
        background-color: {p['accent']};
        color: white;
    }}
    #sidebar_logo {{
        font-size: 20px;
        font-weight: 700;
        color: {p['accent']};
        padding: 8px 14px 4px 14px;
    }}
    #sidebar_version {{
        font-size: 11px;
        color: {p['text_dim']};
        padding: 0px 14px 12px 14px;
    }}

    /* ── Buttons ── */
    QPushButton {{
        background-color: {p['surface']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 7px;
        padding: 7px 14px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {p['border']};
    }}
    QPushButton:pressed {{
        background-color: {p['accent']};
        color: white;
        border-color: {p['accent']};
    }}
    QPushButton:disabled {{
        color: {p['text_dim']};
        border-color: {p['border']};
    }}
    QPushButton#btn_primary {{
        background-color: {p['accent']};
        color: white;
        border: none;
        font-weight: 600;
    }}
    QPushButton#btn_primary:hover {{
        background-color: {p['accent']};
        opacity: 0.9;
    }}
    QPushButton#btn_success {{
        background-color: {p['accent2']};
        color: white;
        border: none;
        font-weight: 600;
    }}
    QPushButton#btn_danger {{
        background-color: {p['danger']};
        color: white;
        border: none;
        font-weight: 600;
    }}

    /* ── Input fields ── */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
        background-color: {p['surface']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 7px;
        padding: 6px 10px;
        selection-background-color: {p['accent']};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
        border-color: {p['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        selection-background-color: {p['accent']};
        color: {p['text']};
    }}

    /* ── List ── */
    QListWidget {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        outline: none;
    }}
    QListWidget::item {{
        border-radius: 6px;
        padding: 10px 12px;
        margin: 2px 4px;
        color: {p['text']};
    }}
    QListWidget::item:hover {{
        background-color: {p['border']};
    }}
    QListWidget::item:selected {{
        background-color: {p['accent']};
        color: white;
    }}

    /* ── Table ── */
    QTableWidget {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        gridline-color: {p['border']};
        outline: none;
    }}
    QTableWidget::item {{
        padding: 8px 10px;
        color: {p['text']};
        border-bottom: 1px solid {p['border']};
    }}
    QTableWidget::item:selected {{
        background-color: {p['accent']};
        color: white;
    }}
    QHeaderView::section {{
        background-color: {p['sidebar_bg']};
        color: {p['text_dim']};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        padding: 8px 10px;
        border: none;
        border-bottom: 1px solid {p['border']};
    }}

    /* ── Progress bars ── */
    QProgressBar {{
        background-color: {p['border']};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {p['accent']};
        border-radius: 4px;
    }}

    /* ── GroupBox ── */
    QGroupBox {{
        border: 1px solid {p['border']};
        border-radius: 8px;
        margin-top: 12px;
        font-weight: 600;
        color: {p['text']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {p['text_dim']};
        font-size: 11px;
        text-transform: uppercase;
    }}

    /* ── Scrollbar ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p['text_dim']};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p['border']};
        border-radius: 4px;
        min-width: 30px;
    }}

    /* ── StatusBar ── */
    QStatusBar {{
        background-color: {p['sidebar_bg']};
        color: {p['text_dim']};
        border-top: 1px solid {p['border']};
        font-size: 12px;
        padding: 2px 8px;
    }}

    /* ── Splitter ── */
    QSplitter::handle {{
        background-color: {p['border']};
    }}

    /* ── Tooltip ── */
    QToolTip {{
        background-color: {p['surface']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 4px 8px;
    }}

    /* ── Checkboxes ── */
    QCheckBox {{
        color: {p['text']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {p['border']};
        background: {p['surface']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p['accent']};
        border-color: {p['accent']};
    }}

    /* ── Label ── */
    QLabel#section_title {{
        font-size: 18px;
        font-weight: 700;
        color: {p['text']};
        padding-bottom: 4px;
    }}
    QLabel#stat_badge {{
        background-color: {p['border']};
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 12px;
        color: {p['text_dim']};
    }}
    QFrame#divider {{
        background-color: {p['border']};
        max-height: 1px;
    }}

    /* ── Log panel ── */
    QTextEdit#log_panel {{
        background-color: {p['sidebar_bg']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        color: {p['text_dim']};
        font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
        font-size: 12px;
    }}

    /* ── Tray menu ── */
    QMenu {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        color: {p['text']};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background-color: {p['accent']};
        color: white;
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {p['border']};
        margin: 4px 8px;
    }}
    """


# ─────────────────────────────────────────────
#  Dialogs
# ─────────────────────────────────────────────

class AddChannelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Channel")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Add YouTube Channel")
        title.setObjectName("section_title")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/@channel  or  /c/channel")
        form.addRow("Channel URL:", self.url_input)

        self.custom_path_input = QLineEdit()
        self.custom_path_input.setPlaceholderText("Leave empty to use default path")
        path_row = QHBoxLayout()
        path_row.addWidget(self.custom_path_input)
        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(32)
        btn_browse.clicked.connect(self._browse)
        path_row.addWidget(btn_browse)
        form.addRow("Custom Save Path:", path_row)

        self.audio_only_check = QCheckBox("Audio Only  (downloads native M4A audio)")
        form.addRow("", self.audio_only_check)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Add & Extract")
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if d:
            self.custom_path_input.setText(d)

    def get_data(self):
        return (
            self.url_input.text().strip(),
            self.audio_only_check.isChecked(),
            self.custom_path_input.text().strip() or None,
        )


class AddSingleVideoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Single Video")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Download Single Video")
        title.setObjectName("section_title")
        layout.addWidget(title)

        form = QFormLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=...")
        form.addRow("Video URL:", self.url_input)
        self.audio_only_check = QCheckBox("Audio Only")
        form.addRow("", self.audio_only_check)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Download")
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def get_data(self):
        return self.url_input.text().strip(), self.audio_only_check.isChecked()


# ─────────────────────────────────────────────
#  Channel card widget (in the list)
# ─────────────────────────────────────────────

class ChannelCardWidget(QWidget):
    """Rich card shown inside the channels list."""
    def __init__(self, name: str, stats: dict, is_downloading: bool = False, audio_only: bool = False):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        top = QHBoxLayout()
        self.lbl_name = QLabel(name)
        self.lbl_name.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        top.addWidget(self.lbl_name)
        top.addStretch()
        if audio_only:
            badge = QLabel("🎵 Audio")
            badge.setObjectName("stat_badge")
            top.addWidget(badge)
        if is_downloading:
            badge2 = QLabel("⬇ Downloading")
            badge2.setStyleSheet("color: #7c6af7; font-size: 11px; font-weight: 600;")
            top.addWidget(badge2)
        layout.addLayout(top)

        stats_lbl = QLabel(
            f"  {stats.get('completed', 0)} downloaded  ·  {stats.get('pending', 0)} pending  ·  {stats.get('total', 0)} total"
        )
        stats_lbl.setObjectName("stat_badge")
        layout.addWidget(stats_lbl)

        self.progress = QProgressBar()
        self.progress.setRange(0, max(stats.get('total', 1), 1))
        self.progress.setValue(stats.get('completed', 0))
        self.progress.setFixedHeight(5)
        layout.addWidget(self.progress)


# ─────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):
    window_closed = Signal()
    theme_changed = Signal(str)   # 'dark' or 'light'

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Downtube")
        self.resize(1100, 680)
        self._dark_mode = True

        self._build_ui()
        self._apply_theme()
        self._setup_tray()

    # ── Build ──────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ────────────────────────────────
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(210)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(8, 16, 8, 16)
        sb_layout.setSpacing(4)

        logo = QLabel("⬇ Downtube")
        logo.setObjectName("sidebar_logo")
        ver = QLabel("v2.0  ·  Professional")
        ver.setObjectName("sidebar_version")
        sb_layout.addWidget(logo)
        sb_layout.addWidget(ver)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        sb_layout.addWidget(div)
        sb_layout.addSpacing(8)

        self.btn_dashboard = QPushButton("  🏠  Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)
        self.btn_log = QPushButton("  📋  Activity Log")
        self.btn_log.setCheckable(True)
        self.btn_settings = QPushButton("  ⚙️  Settings")
        self.btn_settings.setCheckable(True)

        for btn in (self.btn_dashboard, self.btn_log, self.btn_settings):
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        self.btn_theme = QPushButton("  🌙  Dark Mode")
        self.btn_theme.setCheckable(True)
        self.btn_theme.setChecked(True)
        sb_layout.addWidget(self.btn_theme)

        div2 = QFrame()
        div2.setObjectName("divider")
        div2.setFixedHeight(1)
        sb_layout.addWidget(div2)
        sb_layout.addSpacing(4)

        self.btn_add_channel = QPushButton("  ＋  Add Channel")
        self.btn_add_channel.setObjectName("btn_primary")
        self.btn_add_single = QPushButton("  ＋  Single Video")
        sb_layout.addWidget(self.btn_add_channel)
        sb_layout.addWidget(self.btn_add_single)

        root.addWidget(self.sidebar)

        # ── Content area ───────────────────────────
        self.stacked_widget = QStackedWidget()
        root.addWidget(self.stacked_widget)

        self._build_dashboard()
        self._build_log_view()
        self._build_settings_view()

        # Navigation
        self.btn_dashboard.clicked.connect(lambda: self._nav(0, self.btn_dashboard))
        self.btn_log.clicked.connect(lambda: self._nav(1, self.btn_log))
        self.btn_settings.clicked.connect(lambda: self._nav(2, self.btn_settings))
        self.btn_theme.clicked.connect(self._toggle_theme)

        # Status bar
        self.statusBar().showMessage("Ready")
        self._lbl_active = QLabel("")
        self._lbl_active.setStyleSheet("color: #7c6af7; font-weight: 600; padding-right: 8px;")
        self.statusBar().addPermanentWidget(self._lbl_active)

    def _nav(self, idx: int, active_btn: QPushButton):
        self.stacked_widget.setCurrentIndex(idx)
        for btn in (self.btn_dashboard, self.btn_log, self.btn_settings):
            btn.setChecked(btn is active_btn)

    # ── Dashboard ──────────────────────────────────

    def _build_dashboard(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel("Channels")
        lbl.setObjectName("section_title")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self.lbl_active_downloads = QLabel("")
        self.lbl_active_downloads.setStyleSheet("color:#7c6af7; font-weight:600;")
        hdr.addWidget(self.lbl_active_downloads)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search channels...")
        self.search_input.setFixedWidth(220)
        hdr.addWidget(self.search_input)
        layout.addLayout(hdr)

        # Main splitter: list + detail
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left: channel list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        self.channels_list = QListWidget()
        self.channels_list.setSpacing(2)
        self.channels_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.channels_list.setMinimumWidth(240)
        self.channels_list.setMaximumWidth(340)
        left_layout.addWidget(self.channels_list)
        splitter.addWidget(left)

        # Right: channel detail
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(10)

        # Channel header
        ch_hdr = QHBoxLayout()
        self.lbl_channel_name = QLabel("Select a channel →")
        self.lbl_channel_name.setObjectName("section_title")
        ch_hdr.addWidget(self.lbl_channel_name)
        ch_hdr.addStretch()
        self.lbl_stats = QLabel("")
        self.lbl_stats.setObjectName("stat_badge")
        ch_hdr.addWidget(self.lbl_stats)
        right_layout.addLayout(ch_hdr)

        # Overall channel progress bar
        self.channel_progress = QProgressBar()
        self.channel_progress.setFixedHeight(6)
        self.channel_progress.setValue(0)
        right_layout.addWidget(self.channel_progress)

        # Action buttons
        btn_row = QHBoxLayout()
        self.btn_download_channel = QPushButton("⬇  Download Channel")
        self.btn_download_channel.setObjectName("btn_success")
        self.btn_refresh_channel = QPushButton("🔄  Refresh")
        self.btn_refresh_channel.setObjectName("btn_primary")
        self.btn_retry_errors = QPushButton("↩  Retry Errors")
        self.btn_open_folder = QPushButton("📁  Open Folder")
        self.btn_delete_channel = QPushButton("🗑  Delete")
        self.btn_delete_channel.setObjectName("btn_danger")

        for b in (self.btn_download_channel, self.btn_refresh_channel,
                  self.btn_retry_errors, self.btn_open_folder, self.btn_delete_channel):
            btn_row.addWidget(b)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        # Current video progress
        cur_prog_layout = QHBoxLayout()
        self.lbl_current_video = QLabel("")
        self.lbl_current_video.setStyleSheet("color:#7c6af7; font-size:12px;")
        cur_prog_layout.addWidget(self.lbl_current_video)
        cur_prog_layout.addStretch()
        right_layout.addLayout(cur_prog_layout)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.video_search = QLineEdit()
        self.video_search.setPlaceholderText("🔍  Search videos by title...")
        filter_row.addWidget(self.video_search)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "pending", "completed", "downloading", "error"])
        filter_row.addWidget(self.status_filter)
        right_layout.addLayout(filter_row)

        # Videos table
        self.videos_table = QTableWidget()
        self.videos_table.setColumnCount(4)
        self.videos_table.setHorizontalHeaderLabels(["Video ID", "Title", "URL", "Status"])
        self.videos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.videos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.videos_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.videos_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.videos_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.videos_table.setAlternatingRowColors(False)
        self.videos_table.verticalHeader().setVisible(False)
        self.videos_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        right_layout.addWidget(self.videos_table)

        splitter.addWidget(right)
        splitter.setSizes([280, 820])
        layout.addWidget(splitter)

        self.stacked_widget.addWidget(view)

    # ── Log View ───────────────────────────────────

    def _build_log_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        hdr = QHBoxLayout()
        lbl = QLabel("Activity Log")
        lbl.setObjectName("section_title")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self.btn_clear_log = QPushButton("Clear")
        hdr.addWidget(self.btn_clear_log)
        layout.addLayout(hdr)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("log_panel")
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.stacked_widget.addWidget(view)

    # ── Settings View ──────────────────────────────

    def _build_settings_view(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("section_title")
        layout.addWidget(title)

        # ── Group: Paths ──────────────────────────
        grp_paths = QGroupBox("Paths")
        g = QFormLayout(grp_paths)
        g.setSpacing(10)

        self.path_input = QLineEdit()
        self.btn_browse = QPushButton("Browse")
        p_row = QHBoxLayout()
        p_row.addWidget(self.path_input)
        p_row.addWidget(self.btn_browse)
        g.addRow("Base Download Path:", p_row)

        self.file_template_input = QLineEdit()
        self.file_template_input.setPlaceholderText("%(title)s.%(ext)s")
        self.file_template_input.setToolTip(
            "yt-dlp template variables:\n"
            "%(title)s  %(uploader)s  %(upload_date)s  %(id)s  %(ext)s\n"
            "Example: %(upload_date)s - %(title)s.%(ext)s"
        )
        g.addRow("File Name Template:", self.file_template_input)
        layout.addWidget(grp_paths)

        # ── Group: Video ──────────────────────────
        grp_video = QGroupBox("Video")
        g2 = QFormLayout(grp_video)
        g2.setSpacing(10)

        self.res_combo = QComboBox()
        self.res_combo.addItems(["2160 (4K)", "1440 (2K)", "1080", "720", "480", "360"])
        self.res_combo.setCurrentText("720")
        g2.addRow("Max Resolution:", self.res_combo)

        self.jellyfin_check = QCheckBox("Jellyfin / Plex Compatible Naming")
        self.download_shorts_check = QCheckBox("Download Shorts & Reels")
        g2.addRow("", self.jellyfin_check)
        g2.addRow("", self.download_shorts_check)
        layout.addWidget(grp_video)

        # ── Group: Audio ──────────────────────────
        grp_audio = QGroupBox("Audio")
        g3 = QFormLayout(grp_audio)
        g3.setSpacing(10)

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["m4a (native, fastest)", "mp3", "opus", "flac"])
        g3.addRow("Audio Format:", self.audio_format_combo)

        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["best (default)", "320k", "256k", "192k", "128k"])
        g3.addRow("Audio Bitrate:", self.audio_bitrate_combo)

        self.auto_convert_check = QCheckBox("Auto-convert MP4→M4A for audio-only channels")
        g3.addRow("", self.auto_convert_check)
        layout.addWidget(grp_audio)

        # ── Group: Download behaviour ─────────────
        grp_dl = QGroupBox("Download Behaviour")
        g4 = QFormLayout(grp_dl)
        g4.setSpacing(10)

        delay_row = QHBoxLayout()
        self.delay_min_spin = QSpinBox()
        self.delay_min_spin.setRange(0, 120)
        self.delay_min_spin.setValue(3)
        self.delay_max_spin = QSpinBox()
        self.delay_max_spin.setRange(0, 300)
        self.delay_max_spin.setValue(7)
        delay_row.addWidget(QLabel("Min:"))
        delay_row.addWidget(self.delay_min_spin)
        delay_row.addSpacing(8)
        delay_row.addWidget(QLabel("Max:"))
        delay_row.addWidget(self.delay_max_spin)
        delay_row.addStretch()
        g4.addRow("Delay Between Videos (s):", delay_row)

        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 8)
        self.parallel_spin.setValue(1)
        self.parallel_spin.setToolTip("How many channels can download simultaneously")
        g4.addRow("Max Parallel Channel Downloads:", self.parallel_spin)

        self.ratelimit_input = QLineEdit()
        self.ratelimit_input.setPlaceholderText("e.g. 5M  or  500K  (empty = unlimited)")
        g4.addRow("Download Rate Limit:", self.ratelimit_input)

        self.max_filesize_input = QLineEdit()
        self.max_filesize_input.setPlaceholderText("e.g. 2G  or  500M  (empty = unlimited)")
        g4.addRow("Skip Files Larger Than:", self.max_filesize_input)

        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(1, 50)
        self.retries_spin.setValue(10)
        g4.addRow("Retries on Failure:", self.retries_spin)

        layout.addWidget(grp_dl)

        # ── Group: Network ────────────────────────
        grp_net = QGroupBox("Network & Privacy")
        g5 = QFormLayout(grp_net)
        g5.setSpacing(10)

        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://user:pass@host:port  or  socks5://...")
        g5.addRow("Proxy:", self.proxy_input)

        self.cookies_input = QLineEdit()
        self.cookies_input.setPlaceholderText("Path to cookies.txt  (for age-restricted / private videos)")
        cookies_row = QHBoxLayout()
        cookies_row.addWidget(self.cookies_input)
        self.btn_browse_cookies = QPushButton("Browse")
        self.btn_browse_cookies.setFixedWidth(60)
        cookies_row.addWidget(self.btn_browse_cookies)
        g5.addRow("Cookies File:", cookies_row)

        self.useragent_input = QLineEdit()
        self.useragent_input.setPlaceholderText("Leave empty for default  (e.g. Mozilla/5.0 ...)")
        g5.addRow("User-Agent:", self.useragent_input)
        layout.addWidget(grp_net)

        # ── Group: Auto-update ────────────────────
        grp_auto = QGroupBox("Automation")
        g6 = QFormLayout(grp_auto)
        g6.setSpacing(10)

        self.auto_refresh_check = QCheckBox("Auto-refresh channels every")
        auto_refresh_row = QHBoxLayout()
        auto_refresh_row.addWidget(self.auto_refresh_check)
        self.auto_refresh_hours_spin = QSpinBox()
        self.auto_refresh_hours_spin.setRange(1, 168)
        self.auto_refresh_hours_spin.setValue(24)
        self.auto_refresh_hours_spin.setFixedWidth(60)
        auto_refresh_row.addWidget(self.auto_refresh_hours_spin)
        auto_refresh_row.addWidget(QLabel("hours"))
        auto_refresh_row.addStretch()
        g6.addRow("", auto_refresh_row)

        self.minimize_to_tray_check = QCheckBox("Minimize to system tray on close")
        self.start_minimized_check = QCheckBox("Start minimized to tray")
        g6.addRow("", self.minimize_to_tray_check)
        g6.addRow("", self.start_minimized_check)
        layout.addWidget(grp_auto)

        # ── Save ──────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_export_channels = QPushButton("📤  Export Channels")
        self.btn_import_channels = QPushButton("📥  Import Channels")
        self.btn_save_settings = QPushButton("💾  Save Settings")
        self.btn_save_settings.setObjectName("btn_primary")
        btn_row.addWidget(self.btn_export_channels)
        btn_row.addWidget(self.btn_import_channels)
        btn_row.addWidget(self.btn_save_settings)
        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(container)
        self.stacked_widget.addWidget(scroll)

    # ── System Tray ────────────────────────────────

    def _setup_tray(self):
        """Create a system-tray icon with a context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        # Use a blank pixmap as default icon (no file needed)
        px = QPixmap(16, 16)
        px.fill(QColor("#7c6af7"))
        self.tray_icon.setIcon(QIcon(px))
        self.tray_icon.setToolTip("Downtube")

        tray_menu = QMenu()
        act_show = QAction("Show / Hide", self)
        act_show.triggered.connect(self._toggle_visibility)
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.quit)
        tray_menu.addAction(act_show)
        tray_menu.addSeparator()
        tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def notify(self, title: str, message: str):
        """Send a system notification via the tray icon."""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)

    # ── Theme ──────────────────────────────────────

    def _toggle_theme(self, checked: bool):
        self._dark_mode = checked
        self.btn_theme.setText("  🌙  Dark Mode" if checked else "  ☀️  Light Mode")
        self._apply_theme()
        self.theme_changed.emit("dark" if checked else "light")

    def _apply_theme(self):
        p = DARK_PALETTE if self._dark_mode else LIGHT_PALETTE
        self.setStyleSheet(build_stylesheet(p))

    # ── Logging helpers ────────────────────────────

    def append_log(self, msg: str, level: str = "info"):
        """Append a line to the activity log panel."""
        from PySide6.QtCore import QDateTime
        ts = QDateTime.currentDateTime().toString("hh:mm:ss")
        colors = {"info": "#cdd6f4", "success": "#a6e3a1", "warning": "#f9e2af", "error": "#f38ba8"}
        c = colors.get(level, "#cdd6f4")
        self.log_text.append(f'<span style="color:{c};">[{ts}]  {msg}</span>')

    def set_active_downloads_label(self, n: int):
        if n == 0:
            self.lbl_active_downloads.setText("")
            self._lbl_active.setText("")
        else:
            t = f"⬇ {n} active download{'s' if n != 1 else ''}"
            self.lbl_active_downloads.setText(t)
            self._lbl_active.setText(t)

    # ── Window events ──────────────────────────────

    def closeEvent(self, event):
        if self.minimize_to_tray_check.isChecked():
            event.ignore()
            self.hide()
        else:
            self.window_closed.emit()
            self.tray_icon.hide()
            super().closeEvent(event)
