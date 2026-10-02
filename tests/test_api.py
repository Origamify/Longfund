"""API contract tests: shapes, status codes, offline via stubbed download."""

import numpy as np
import pandas as pd
import pytest

from src import market, web


def long_frame(adj=None) -> pd.DataFrame:
    """300 rising bars: every rolling window is warm, values rise."""
    closes = np.linspace(100, 200, 300)
    data = {
        "Date": pd.bdate_range("2020-01-01", periods=300),
        "Open": 1.0,
        "High": 1.0,
        "Low": 1.0,
        "Close": closes,
        "Volume": 0,
    }
    if adj is not None:
        data["Adj Close"] = adj
    return pd.DataFrame(data)


@pytest.fixture
def client(cache, watchlist, stub_stats, stub_eps, monkeypatch):
    """Test client with a warm cache — the launch sweep's equivalent
    (stubbed downloads); API reads are disk-only after it."""
    monkeypatch.setattr(market, "download_bars", lambda s: long_frame())
    market.refresh_all()
    web.app.config["TESTING"] = True
    return web.app.test_client()


# --- GET /api/bars/<symbol> ---


def test_bars_defaults_to_tail(client):
    body = client.get("/api/bars/AAPL").get_json()
    assert body["symbol"] == "AAPL"
    rows = body["bars"]
    assert len(rows) == 10  # documented default
    assert len(rows[0]) == 2  # [date, close]


def test_bars_tail_query(client):
    assert len(client.get("/api/bars/AAPL?tail=1").get_json()["bars"]) == 1
    assert len(client.get("/api/bars/AAPL?tail=10000").get_json()["bars"]) == 300


@pytest.mark.parametrize("query", ["tail=abc", "tail=0", "tail=-5", "tail=2.5"])
def test_bars_bad_tail_400(client, query):
    resp = client.get(f"/api/bars/AAPL?{query}")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_bars_unknown_symbol_404(client):
    resp = client.get("/api/bars/NOPE")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# --- GET /api/stats/<symbol> ---


def test_stats_shape(client):
    body = client.get("/api/stats/AAPL").get_json()
    assert body["symbol"] == "AAPL"
    assert body["stats"]["sector"] == "Technology"
    assert body["stats"]["trailingPE"] == 39.5
    assert set(body) == {"symbol", "stats"}


def test_stats_unavailable_is_empty_not_error(client, cache):
    (cache / "AAPL.stats.json").unlink()
    assert client.get("/api/stats/AAPL").get_json() == {
        "symbol": "AAPL",
        "stats": {},
    }


def test_stats_unknown_symbol_404(client):
    resp = client.get("/api/stats/NOPE")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# --- GET /api/eps/<symbol> ---


def test_eps_shape_and_sue(client):
    body = client.get("/api/eps/AAPL").get_json()
    assert set(body) == {"symbol", "eps", "sue"}
    rows = body["eps"]
    assert len(rows) == 9 and len(rows[0]) == 3  # [date, reported, estimate]
    assert rows[0][0] < rows[-1][0]  # ascending
    # stub_eps: SUE = 0.2 / stdev([0.1, 0.1, 0.1, 0.1, 0.2])
    assert body["sue"] == pytest.approx(0.2 / np.std([0.1] * 4 + [0.2], ddof=1))


def test_eps_unavailable_empty_not_error(client, cache):
    (cache / "AAPL.eps.json").unlink()
    assert client.get("/api/eps/AAPL").get_json() == {
        "symbol": "AAPL",
        "eps": [],
        "sue": None,
    }


def test_eps_unknown_symbol_404(client):
    resp = client.get("/api/eps/NOPE")
    assert resp.status_code == 404
    assert "error" in resp.get_json()
