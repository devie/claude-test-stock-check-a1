"""Parquet persistence for anomaly snapshots (alternative to SQLite)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ParquetRepo:
    def __init__(self, base_dir: str = "data/parquet") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path_for(self, run_date: str) -> Path:
        return self._base / f"anomaly_{run_date}.parquet"

    def upsert(
        self,
        run_date: str,
        ticker: str,
        score: float,
        severity: str,
        is_uma: bool,
        payload: dict,
    ) -> None:
        path = self._path_for(run_date)
        flat = {
            k: v
            for k, v in payload.items()
            if not isinstance(v, (dict, list))
        }
        row = pd.DataFrame([{
            "run_date": run_date,
            "ticker": ticker,
            "score": score,
            "severity": severity,
            "is_uma": is_uma,
            **flat,
        }])
        if path.exists():
            existing = pd.read_parquet(path)
            existing = existing[existing["ticker"] != ticker]
            row = pd.concat([existing, row], ignore_index=True)
        row.to_parquet(path, index=False)
        logger.debug("parquet upsert %s/%s score=%.1f", run_date, ticker, score)

    def query_alerts(self, run_date: str | None = None, min_score: float = 0) -> list[dict]:
        paths = [self._path_for(run_date)] if run_date else sorted(self._base.glob("anomaly_*.parquet"))
        frames = [pd.read_parquet(p) for p in paths if p.exists()]
        if not frames:
            return []
        df = pd.concat(frames, ignore_index=True)
        df = df[df["score"] >= min_score].sort_values("score", ascending=False)
        return df.to_dict(orient="records")
