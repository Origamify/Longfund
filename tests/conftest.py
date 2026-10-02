"""Pytest config: root on sys.path; shared offline fixtures."""

import sys
from pathlib import Path

import pandas as pd
import pytest

from src import market

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def scratch_data(tmp_path, monkeypatch):
    """Dummy data dir per test: every path the app persists to is redirected
    to pytest scratch space, so tests can never read or write real data/."""
    monkeypatch.setattr(market, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(market, "WATCHLIST_PATH", tmp_path / "watchlist.json")


@pytest.fixture
def frame() -> pd.DataFrame:
    """Minimal OHLCV frame a stubbed download returns."""
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-02-20", "2026-02-23"]),
            "Open": [1.0, 1.5],
            "High": [2.0, 3.0],
            "Low": [0.5, 1.0],
            "Close": [1.5, 2.5],
            "Adj Close": [1.4, 2.4],
            "Volume": [100, 200],
        }
    )


@pytest.fixture
def cache() -> Path:
    """The scratch cache dir (set by scratch_data)."""
    return market.CACHE_DIR


@pytest.fixture
def watchlist() -> Path:
    """The scratch watchlist file (set by scratch_data)."""
    return market.WATCHLIST_PATH


@pytest.fixture
def stub_download(monkeypatch, frame):
    """Replace the network call; counts how many times it runs."""
    calls = []

    def fake(symbol):
        calls.append(symbol)
        return frame.copy()

    monkeypatch.setattr(market, "download_bars", fake)
    return calls


@pytest.fixture
def stub_stats(monkeypatch):
    """Deterministic fundamentals; stats tests never touch network."""
    monkeypatch.setattr(
        market,
        "download_stats",
        lambda symbol: {
            "shortName": f"{symbol} Inc.",
            "sector": "Technology",
            "industry": "Gadgets",
            "trailingPE": 39.5,
            "fullTimeEmployees": 1000,
            "totalRevenue": 5_000_000_000,
            "revenuePerEmployee": 5_000_000.0,
        },
    )


# 9 quarters ascending: SUE = 0.20 / stdev([0.1, 0.1, 0.1, 0.1, 0.2]) ≈ +4.47
STUB_EPS_DATES = [
    "2024-04-30",
    "2024-07-31",
    "2024-10-31",
    "2025-01-30",
    "2025-04-30",
    "2025-07-31",
    "2025-10-30",
    "2026-01-29",
    "2026-04-30",
]
STUB_EPS_VALUES = [1.00, 1.02, 1.04, 1.06, 1.10, 1.12, 1.14, 1.16, 1.30]


@pytest.fixture
def stub_eps(monkeypatch):
    """Deterministic quarterly EPS; eps tests never touch network."""
    rows = [
        [date, value, 1.25 if i == len(STUB_EPS_DATES) - 1 else None]
        for i, (date, value) in enumerate(zip(STUB_EPS_DATES, STUB_EPS_VALUES))
    ]
    monkeypatch.setattr(market, "download_eps", lambda symbol: rows)
    return rows
