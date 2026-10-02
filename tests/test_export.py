"""Snapshot exporter tests: offline render → one self-contained HTML file."""

import numpy as np
import pandas as pd
import pytest

from src import market, web
from utils.export_html_analysis import build_html


@pytest.fixture
def export_env(monkeypatch, cache):
    """Offline page render: 300 rising bars served straight from the
    scratch cache. Fetches are stubbed to fail like a network outage:
    fresh files never fetch, and optional data degrades silently."""
    closes = np.linspace(100, 200, 300)
    frame = pd.DataFrame(
        {
            "Date": pd.bdate_range("2020-01-01", periods=300),
            "Open": 1.0,
            "High": 1.0,
            "Low": 1.0,
            "Close": closes,
            "Volume": 0,
        }
    )
    monkeypatch.setattr(
        market,
        "download_bars",
        lambda symbol: (_ for _ in ()).throw(OSError("offline")),
    )
    monkeypatch.setattr(
        market,
        "download_stats",
        lambda symbol: (_ for _ in ()).throw(OSError("offline")),
    )
    monkeypatch.setattr(
        market,
        "download_eps",
        lambda symbol: (_ for _ in ()).throw(OSError("offline")),
    )
    cache.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache / "AAPL.csv", index=False)
    web.app.config["TESTING"] = True


def test_snapshot_is_self_contained(export_env):
    html = build_html("aapl")
    assert "<script src=" not in html  # Chart.js inlined, not referenced
    assert '<link rel="stylesheet"' not in html  # CSS inlined too
    assert "Chart.defaults.color" in html  # chart wiring made it through
    assert "replaceState" not in html  # file:// URL must stay intact
    assert "<a " not in html and "</a>" not in html  # zero anchors: no dead links
    assert 'href="/' not in html
    assert "data through" in html  # snapshot stamp
    assert "<title>AAPL" in html


def test_snapshot_has_no_strategies_leftovers(export_env):
    """The strategy product is gone; nothing references it."""
    html = build_html("aapl")
    assert "<h3>strategies" not in html and "/strategies" not in html


def test_snapshot_range_passthrough(export_env):
    html = build_html("AAPL", "21")
    assert '<button data-range="21" class="selected">1M</button>' in html


def test_snapshot_unknown_symbol_exits(export_env):
    with pytest.raises(SystemExit) as exc:
        build_html("NOPE")
    assert exc.value.code == 1
