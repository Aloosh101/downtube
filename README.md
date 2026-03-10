# ⬇ Downtube

**A simple, stable, and professional YouTube channel archiver** — built with Python, PySide6, and yt-dlp.

## Why Downtube?

Most existing YouTube archiver GUIs (like Tartube) are overly complex, cluttered, or constantly broken. Downtube was built to be the opposite: clean, simple, and reliable — without sacrificing the features that matter.

## Features

- 📥 Download entire YouTube channels in video or audio-only (M4A) mode
- 🔄 Parallel multi-channel downloading
- 🔍 Smart refresh — only fetches new videos since last check
- ⚙️ Rich settings: proxy, cookies, rate limit, per-channel custom path, file naming templates
- 🌙 Dark / Light theme
- 📋 Live activity log
- 🔔 System tray notifications
- 💾 SQLite database with automatic backup & integrity check
- 📤 Export / Import channel lists as JSON
- ↩ Retry failed downloads
- 🗑 Remove channels from the database
- 🤖 Auto-refresh channels on a configurable schedule

## Requirements

- Python 3.11+
- `ffmpeg` in your PATH (required for audio conversion)

## Installation

### Option 1 — via pip *(Coming Soon)*

The package will be published to PyPI shortly. Once available:

```bash
pip install downtube
downtube
```

### Option 2 — from source *(Available Now)*

```bash
git clone https://github.com/aloosh101/downtube
cd downtube
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e .
python main.py
```

## License

MIT
