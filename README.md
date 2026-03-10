# ⬇ Downtube

## Why Downtube?

Most existing YouTube archivers and GUIs (like Tartube) are often overly complex, cluttered, or prone to frequent crashes and bugs. Downtube was created to provide a **simple, stable, and professional** alternative—focusing on ease of use without sacrificing powerful features like parallel downloads and automatic channel updates.

- 📥 Download entire YouTube channels in video or audio-only (M4A) mode
- 🔄 Parallel multi-channel downloading
- 🔍 Smart refresh — only fetches new videos
- ⚙️ Rich settings: proxy, cookies, rate limit, custom path per channel, file naming templates
- 🌙 Dark / Light theme
- 📋 Live activity log
- 🔔 System tray with notifications
- 💾 SQLite database with automatic backup & integrity check
- 📤 Export / Import channels as JSON
- ↩ Retry failed downloads
- 🗑 Delete channels from the database
- 🤖 Auto-refresh channels on a schedule

## Requirements

- Python 3.11+
- `ffmpeg` installed and available in your PATH

## Installation

```bash
pip install downtube
```

Then launch with:
**soon**
```bash
downtube
```

Or:
**soon**
```bash
python -m downtube
```

## Development Setup

```bash
git clone https://github.com/aloosh101/downtube
cd downtube
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e ".[dev]"
python main.py
```

## Build & Publish to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

## License

MIT
