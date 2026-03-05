"""SQLite persistence for anomaly snapshots."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from ..utils.logging import get_logger

logger = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS anomaly_snapshots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date   TEXT NOT NULL,
    ticker     TEXT NOT NULL,
    score      REAL,
    severity   TEXT,
    is_uma     INTEGER DEFAULT 0,
    payload    TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_date, ticker)
);
CREATE INDEX IF NOT EXISTS idx_snap_ticker   ON anomaly_snapshots(ticker);
CREATE INDEX IF NOT EXISTS idx_snap_run_date ON anomaly_snapshots(run_date);
CREATE INDEX IF NOT EXISTS idx_snap_score    ON anomaly_snapshots(score);
"""


class SQLiteRepo:
    def __init__(self, db_path: str = "data/anomaly.db") -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def upsert(
        self,
        run_date: str,
        ticker: str,
        score: float,
        severity: str,
        is_uma: bool,
        payload: dict,
    ) -> None:
        sql = """
        INSERT INTO anomaly_snapshots (run_date, ticker, score, severity, is_uma, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date, ticker) DO UPDATE SET
            score=excluded.score,
            severity=excluded.severity,
            is_uma=excluded.is_uma,
            payload=excluded.payload
        """
        with self._connect() as conn:
            conn.execute(
                sql, (run_date, ticker, score, severity, int(is_uma), json.dumps(payload))
            )
        logger.debug("upserted %s/%s score=%.1f", run_date, ticker, score)

    def query_alerts(self, run_date: str | None = None, min_score: float = 0) -> list[dict]:
        where = "WHERE score >= ?"
        params: list = [min_score]
        if run_date:
            where += " AND run_date = ?"
            params.append(run_date)
        sql = f"SELECT * FROM anomaly_snapshots {where} ORDER BY score DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
