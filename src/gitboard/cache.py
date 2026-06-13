import json
import sqlite3
import time
import logging
from pathlib import Path
from typing import Any, Optional

from gitboard.config import CACHE_DB_PATH

logger = logging.getLogger(__name__)


class DiskCache:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or CACHE_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                "  key TEXT PRIMARY KEY,"
                "  value TEXT NOT NULL,"
                "  expires_at REAL NOT NULL"
                ")"
            )
            self._conn.commit()
        return self._conn

    def get(self, key: str) -> Optional[Any]:
        cursor = self.conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        value_json, expires_at = row
        if time.time() > expires_at:
            self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self.conn.commit()
            return None
        return json.loads(value_json)

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time() + ttl),
        )
        self.conn.commit()

    def clear(self) -> None:
        self.conn.execute("DELETE FROM cache")
        self.conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
