from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class OHLCV:
    ticker: str
    df: pd.DataFrame  # columns: open high low close volume; DatetimeIndex


@dataclass
class Fundamentals:
    ticker: str
    bvps: Optional[float]       # Book Value Per Share
    pbv_ttm: Optional[float]    # Price/Book (trailing)
    extra: dict = field(default_factory=dict)


@dataclass
class UMAEntry:
    ticker: str        # normalised, e.g. TLKM.JK
    date_listed: str   # ISO date
    reason: str


class PriceDataProvider(ABC):
    @abstractmethod
    def fetch(self, ticker: str, days: int = 90) -> OHLCV:
        """Fetch OHLCV history for the last `days` calendar days."""
        ...


class FundamentalsProvider(ABC):
    @abstractmethod
    def fetch(self, ticker: str) -> Fundamentals:
        ...


class UMAProvider(ABC):
    @abstractmethod
    def fetch(self) -> list[UMAEntry]:
        """Return all currently UMA-listed tickers."""
        ...
