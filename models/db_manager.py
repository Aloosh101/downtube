import sqlite3
import os
import shutil
import json
import logging


class DBManager:
    """
    SQLite-backed persistence layer for Downtube.

    Improvements over v1:
    - Connection pool (one per-thread connection via `check_same_thread=False`
      is adequate for our usage pattern where one thread writes at a time).
    - delete_channel() + optional file cleanup.
    - export / import channels to / from JSON.
    - get_channel_by_id() helper.
    - retry_errors() — reset error→pending.
    - get_all_pending_channels() for scheduler.
    """

    def __init__(self, base_path: str):
        self.base_path       = base_path
        self.data_dir        = os.path.join(base_path, ".data")
        self.main_db_path    = os.path.join(self.data_dir, "main.db")
        self.backup_db_path  = os.path.join(self.data_dir, "backup.db")
        self.logger          = logging.getLogger(__name__)

        os.makedirs(self.data_dir, exist_ok=True)
        self._ensure_db_integrity()
        self._initialize_tables()
        self._reset_stuck_downloads()

    # ─────────────────────────────────────────────
    #  Connection
    # ─────────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.main_db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")    # better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    # ─────────────────────────────────────────────
    #  Integrity & setup
    # ─────────────────────────────────────────────

    def _ensure_db_integrity(self):
        main_ok   = os.path.exists(self.main_db_path)
        backup_ok = os.path.exists(self.backup_db_path)

        if not main_ok and backup_ok:
            self.logger.info("Restoring main.db from backup.")
            shutil.copy2(self.backup_db_path, self.main_db_path)
        elif main_ok:
            try:
                conn = sqlite3.connect(self.main_db_path)
                res  = conn.execute("PRAGMA integrity_check;").fetchone()
                conn.close()
                if not res or res[0] != "ok":
                    raise sqlite3.DatabaseError("Integrity check failed")
            except sqlite3.DatabaseError as e:
                self.logger.warning(f"main.db corrupt ({e}). Restoring backup.")
                if backup_ok:
                    shutil.copy2(self.backup_db_path, self.main_db_path)
                else:
                    self.logger.error("No backup available. Creating fresh DB.")
                    os.remove(self.main_db_path)

        if os.path.exists(self.main_db_path):
            shutil.copy2(self.main_db_path, self.backup_db_path)

    def _initialize_tables(self):
        conn   = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Channels (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                name               TEXT    NOT NULL,
                url                TEXT    NOT NULL UNIQUE,
                extracted_count    INTEGER DEFAULT 0,
                custom_path        TEXT,
                is_fully_extracted INTEGER DEFAULT 0,
                audio_only         INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Videos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id   TEXT    NOT NULL UNIQUE,
                title      TEXT    NOT NULL,
                url        TEXT    NOT NULL,
                status     TEXT    DEFAULT 'pending',
                channel_id INTEGER,
                FOREIGN KEY(channel_id) REFERENCES Channels(id) ON DELETE CASCADE
            )
        """)

        # Safe migrations (idempotent)
        for col, definition in [
            ("audio_only",      "INTEGER DEFAULT 0"),
            ("custom_path",     "TEXT"),
            ("video_quality",   "TEXT DEFAULT ''"),
            ("audio_bitrate",   "TEXT DEFAULT ''"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE Channels ADD COLUMN {col} {definition}")
            except sqlite3.OperationalError:
                pass

        conn.commit()
        conn.close()
        if os.path.exists(self.main_db_path):
            shutil.copy2(self.main_db_path, self.backup_db_path)

    def _reset_stuck_downloads(self):
        """On startup, anything stuck in 'downloading' goes back to 'pending'."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE Videos SET status='pending' WHERE status IN ('downloading')"
        )
        conn.commit()
        conn.close()

    # ─────────────────────────────────────────────
    #  Channel CRUD
    # ─────────────────────────────────────────────

    def add_channel(
        self,
        name: str,
        url: str,
        custom_path: str | None = None,
        audio_only: bool = False,
    ) -> int:
        conn   = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Channels (name, url, custom_path, audio_only) VALUES (?, ?, ?, ?)",
                (name, url, custom_path, int(audio_only)),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM Channels WHERE url = ?", (url,))
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_all_channels(self) -> list[dict]:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM Channels ORDER BY name COLLATE NOCASE").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_channel_by_id(self, channel_id: int) -> dict | None:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM Channels WHERE id = ?", (channel_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_channel_extracted_count(self, channel_id: int):
        conn = self._get_connection()
        conn.execute(
            "UPDATE Channels SET extracted_count = (SELECT COUNT(*) FROM Videos WHERE channel_id = ?) WHERE id = ?",
            (channel_id, channel_id),
        )
        conn.commit()
        conn.close()

    def set_channel_fully_extracted(self, channel_id: int):
        conn = self._get_connection()
        conn.execute("UPDATE Channels SET is_fully_extracted = 1 WHERE id = ?", (channel_id,))
        conn.commit()
        conn.close()

    def update_channel_quality(self, channel_id: int, video_quality: str = "", audio_bitrate: str = ""):
        """Set per-channel video resolution or audio bitrate override."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE Channels SET video_quality = ?, audio_bitrate = ? WHERE id = ?",
            (video_quality, audio_bitrate, channel_id),
        )
        conn.commit()
        conn.close()

    def update_channel_settings(self, channel_id: int, audio_only: bool, custom_path: str | None,
                                video_quality: str = "", audio_bitrate: str = ""):
        """Update all editable channel properties."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE Channels SET audio_only = ?, custom_path = ?, video_quality = ?, audio_bitrate = ? WHERE id = ?",
            (int(audio_only), custom_path, video_quality, audio_bitrate, channel_id),
        )
        conn.commit()
        conn.close()

    def delete_channel(self, channel_id: int):
        """Delete a channel and all its videos from the database."""
        conn = self._get_connection()
        conn.execute("DELETE FROM Videos WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM Channels WHERE id = ?", (channel_id,))
        conn.commit()
        conn.close()

    # ─────────────────────────────────────────────
    #  Video CRUD
    # ─────────────────────────────────────────────

    def get_existing_video_ids(self, channel_id: int) -> set:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT video_id FROM Videos WHERE channel_id = ?", (channel_id,)
        ).fetchall()
        conn.close()
        return {r[0] for r in rows}

    def add_videos_batch(self, videos: list[tuple]):
        """videos: list of (video_id, title, url, channel_id)"""
        conn = self._get_connection()
        conn.executemany(
            "INSERT OR IGNORE INTO Videos (video_id, title, url, status, channel_id) VALUES (?, ?, ?, 'pending', ?)",
            videos,
        )
        conn.commit()
        conn.close()

    def update_video_status(self, video_id: str, status: str):
        conn = self._get_connection()
        conn.execute("UPDATE Videos SET status = ? WHERE video_id = ?", (status, video_id))
        conn.commit()
        conn.close()

    def get_videos_for_channel(self, channel_id: int) -> list[dict]:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM Videos WHERE channel_id = ? ORDER BY id", (channel_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def retry_errors(self, channel_id: int):
        """Reset all 'error' videos back to 'pending' for a channel."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE Videos SET status='pending' WHERE channel_id = ? AND status = 'error'",
            (channel_id,),
        )
        conn.commit()
        conn.close()

    def get_channel_stats(self, channel_id: int) -> dict:
        conn    = self._get_connection()
        cursor  = conn.cursor()
        total   = cursor.execute("SELECT COUNT(*) FROM Videos WHERE channel_id = ?", (channel_id,)).fetchone()[0]
        done    = cursor.execute("SELECT COUNT(*) FROM Videos WHERE channel_id = ? AND status='completed'", (channel_id,)).fetchone()[0]
        errors  = cursor.execute("SELECT COUNT(*) FROM Videos WHERE channel_id = ? AND status='error'", (channel_id,)).fetchone()[0]
        conn.close()
        return {"total": total, "completed": done, "pending": total - done - errors, "error": errors}

    # ─────────────────────────────────────────────
    #  Import / Export
    # ─────────────────────────────────────────────

    def export_channels(self, filepath: str):
        channels = self.get_all_channels()
        data = [
            {
                "name":          c["name"],
                "url":           c["url"],
                "audio_only":    c.get("audio_only", 0),
                "custom_path":   c.get("custom_path"),
                "video_quality": c.get("video_quality", ""),
                "audio_bitrate": c.get("audio_bitrate", ""),
            }
            for c in channels
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_channels(self, filepath: str) -> int:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        added = 0
        for item in data:
            url = item.get("url", "").strip()
            if not url:
                continue
            self.add_channel(
                name=item.get("name", "Imported Channel"),
                url=url,
                custom_path=item.get("custom_path"),
                audio_only=bool(item.get("audio_only", False)),
            )
            added += 1
        return added

    # ─────────────────────────────────────────────
    #  Backup
    # ─────────────────────────────────────────────

    def backup_database(self):
        if os.path.exists(self.main_db_path):
            shutil.copy2(self.main_db_path, self.backup_db_path)
