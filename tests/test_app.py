"""Offline tests: stubbed download, fixture frames, Flask test client."""

import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import longfund
from src import fundamentals, market, panels, web


def _age(path, days: int) -> None:
    """Backdate a cache file's mtime so it counts as stale."""
    old = pd.Timestamp.today().timestamp() - days * 86400
    os.utime(path, (old, old))


# --- market: cache behavior ---


def test_load_bars_fetches_and_caches(cache, stub_download):
    bars = market.load_bars("AAPL")
    assert stub_download == ["AAPL"]
    assert (cache / "AAPL.csv").exists()
    assert len(bars) == 2
    assert list(bars.columns) == market._COLUMNS


def test_fresh_cache_means_no_fetch(cache, stub_download):
    market.load_bars("AAPL")
    market.load_bars("AAPL")
    assert stub_download == ["AAPL"]  # second load hit the cache


def test_stale_cache_refetches(cache, stub_download):
    market.load_bars("AAPL")
    _age(cache / "AAPL.csv", days=1)
    market.load_bars("AAPL")
    assert stub_download == ["AAPL", "AAPL"]


def test_corrupt_cache_refetches(cache, stub_download):
    cache.mkdir(parents=True)
    (cache / "AAPL.csv").write_text("garbage,not,a,frame\n")
    bars = market.load_bars("AAPL")
    assert stub_download == ["AAPL"]
    assert len(bars) == 2


def test_failed_fetch_with_no_cache_raises(cache, monkeypatch):
    def boom(symbol):
        raise OSError("offline")

    monkeypatch.setattr(market, "download_bars", boom)
    with pytest.raises(OSError):
        market.load_bars("AAPL")


def test_failed_fetch_serves_stale_cache(cache, stub_download, monkeypatch):
    market.load_bars("AAPL")
    _age(cache / "AAPL.csv", days=2)

    def boom(symbol):
        raise OSError("offline")

    monkeypatch.setattr(market, "download_bars", boom)
    assert len(market.load_bars("AAPL")) == 2  # stale beats nothing


def test_provider_error_wrapped_serves_stale_cache(cache, stub_download, monkeypatch):
    market.load_bars("AAPL")
    _age(cache / "AAPL.csv", days=2)

    def boom(*args, **kwargs):  # e.g. YFRateLimitError — not an OSError
        raise RuntimeError("too many requests")

    monkeypatch.setattr(market.yf, "download", boom)
    assert len(market.load_bars("AAPL")) == 2  # wrapped → stale still served


def test_provider_error_without_cache_raises_osperror(cache, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("too many requests")

    monkeypatch.setattr(market.yf, "download", boom)
    with pytest.raises(OSError):
        market.load_bars("AAPL")


# --- market: fundamentals cache ---


class _FakeTicker:
    """Stands in for yfinance.Ticker in stats tests."""

    def __init__(self, symbol):
        self.symbol = symbol

    def get_info(self):
        return {
            "shortName": "Apple Inc.",
            "sector": "Technology",
            "trailingPE": 12.5,
            "priceToBook": 4.0,
            "marketCap": 8_000_000_000.0,
            "freeCashflow": 400_000_000.0,
            "totalDebt": 3_000_000.0,
            "totalCash": 1_000_000.0,
            "fiftyTwoWeekHigh": 200.0,
            "fiftyTwoWeekLow": 100.0,
            "totalRevenue": 4_000_000.0,
            "fullTimeEmployees": 2000,
            "currentPrice": 40.0,
            "trailingAnnualDividendYield": 9.9,  # bogus on purpose
            "pegRatio": None,
            "junk": "x",
        }

    @property
    def dividends(self):
        now = pd.Timestamp.now()
        return pd.Series(
            [5.0, 1.0, 2.0],  # only the last two fall inside TTM
            index=pd.DatetimeIndex(
                [
                    now - pd.Timedelta(days=400),
                    now - pd.Timedelta(days=200),
                    now - pd.Timedelta(days=10),
                ],
                tz="America/New_York",  # ex-dates come tz-aware from Yahoo
            ),
        )


def _fake_yf(ticker_cls):
    """yfinance module stand-in whose .Ticker(symbol).get_info() hits a stub."""
    return SimpleNamespace(Ticker=ticker_cls)


def test_stats_curates_and_caches(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_FakeTicker))
    stats = market.load_stats("AAPL")
    assert stats["trailingPE"] == 12.5
    assert stats["revenuePerEmployee"] == 2000.0  # derived
    for junk in ("pegRatio", "junk"):  # dropped: None/NaN/unlisted
        assert junk not in stats
    assert (cache / "AAPL.stats.json").exists()


def test_stats_derive_value_lens(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_FakeTicker))
    stats = market.load_stats("AAPL")
    assert stats["earningsYield"] == pytest.approx(0.08)  # 1/12.5
    assert stats["bookToMarket"] == pytest.approx(0.25)  # 1/4
    assert stats["fcfYield"] == pytest.approx(0.05)  # 4e8/8e9
    assert stats["netDebt"] == pytest.approx(2_000_000.0)  # debt − cash


def test_stats_negative_multiples_derive_nothing(cache, monkeypatch):
    class Loser(_FakeTicker):
        def get_info(self):
            info = super().get_info()
            info.update(trailingPE=-12.5, priceToBook=0.0, totalCash=None)
            return info

    monkeypatch.setattr(market, "yf", _fake_yf(Loser))
    stats = market.load_stats("AAPL")
    for absent in ("earningsYield", "bookToMarket", "netDebt"):
        assert absent not in stats


def test_stats_dividend_yield_derived_from_series(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_FakeTicker))
    stats = market.load_stats("AAPL")
    # (1.0 + 2.0) / 40 — the bogus info value (9.9) never passes through
    assert stats["trailingAnnualDividendYield"] == pytest.approx(0.075)


def test_stats_dividend_series_cached_for_page(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_FakeTicker))
    market.load_stats("AAPL")
    today = datetime.now(tz=timezone.utc).date()
    rows = market.read_divs("AAPL")
    assert rows == [
        [(today - timedelta(days=400)).strftime("%Y-%m-%d"), 5.0],
        [(today - timedelta(days=200)).strftime("%Y-%m-%d"), 1.0],
        [(today - timedelta(days=10)).strftime("%Y-%m-%d"), 2.0],
    ]


def test_read_divs_empty_when_never_cached(cache):
    assert market.read_divs("AAPL") == []


def test_stats_dividend_yield_absent_without_history(cache, monkeypatch):
    class Bare(_FakeTicker):  # no dividends attr, no currentPrice in info
        @property
        def dividends(self):
            raise RuntimeError("offline")

    monkeypatch.setattr(market, "yf", _fake_yf(Bare))
    stats = market.load_stats("AAPL")
    assert "trailingAnnualDividendYield" not in stats


def test_stats_provider_error_wrapped_and_empty(cache, monkeypatch):
    class Boom:
        def __init__(self, symbol):
            pass

        def get_info(self):
            raise RuntimeError("too many requests")

    monkeypatch.setattr(market, "yf", _fake_yf(Boom))
    with pytest.raises(OSError):
        market.download_stats("AAPL")
    assert market.load_stats("AAPL") == {}  # never raises, nothing cached


def test_stats_stale_cache_beats_failed_fetch(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_FakeTicker))
    assert market.load_stats("AAPL")["trailingPE"] == 12.5
    _age(cache / "AAPL.stats.json", days=2)

    class Boom:
        def __init__(self, symbol):
            pass

        def get_info(self):
            raise RuntimeError("offline")

    monkeypatch.setattr(market, "yf", _fake_yf(Boom))
    assert market.load_stats("AAPL")["trailingPE"] == 12.5


# --- market: quarterly EPS cache (SUE source) ---


class _EpsTicker:
    """yfinance.Ticker stand-in: 3 rows, one future/NaN, unsorted dates."""

    def __init__(self, symbol):
        self.symbol = symbol

    def get_earnings_dates(self, limit=12):
        return pd.DataFrame(
            {
                "EPS Estimate": [1.77, 1.98, None],
                "Reported EPS": [1.85, float("nan"), 2.0],
            },
            index=pd.DatetimeIndex(["2025-10-30", "2026-10-29", "2026-07-30"]),
        )


def test_download_eps_keeps_reported_sorts_ascending(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_EpsTicker))
    rows = market.download_eps("AAPL")
    assert rows == [["2025-10-30", 1.85, 1.77], ["2026-07-30", 2.0, None]]


def test_eps_provider_error_wrapped_and_empty(cache, monkeypatch):
    class Boom:
        def __init__(self, symbol):
            pass

        def get_earnings_dates(self, limit=12):
            raise RuntimeError("too many requests")

    monkeypatch.setattr(market, "yf", _fake_yf(Boom))
    with pytest.raises(OSError):
        market.download_eps("AAPL")
    assert market.load_eps("AAPL") == []  # never raises, nothing cached


def test_eps_empty_payload_is_error(cache, monkeypatch):
    class Empty:
        def __init__(self, symbol):
            pass

        def get_earnings_dates(self, limit=12):
            return None

    monkeypatch.setattr(market, "yf", _fake_yf(Empty))
    with pytest.raises(OSError):
        market.download_eps("AAPL")


def test_eps_stale_cache_beats_failed_fetch(cache, monkeypatch):
    monkeypatch.setattr(market, "download_eps", lambda s: [["2026-01-30", 2.0, 1.9]])
    assert market.load_eps("AAPL") == [["2026-01-30", 2.0, 1.9]]
    assert (cache / "AAPL.eps.json").exists()
    _age(cache / "AAPL.eps.json", days=2)
    monkeypatch.setattr(
        market,
        "download_eps",
        lambda s: (_ for _ in ()).throw(OSError("offline")),
    )
    assert market.load_eps("AAPL") == [["2026-01-30", 2.0, 1.9]]


# --- market: benchmark ---


def test_cached_benchmark_reads_bar_cache(cache, stub_download):
    market.load_bars(market.BENCHMARK)  # what refresh_all does at launch
    calls = len(stub_download)
    frame = market.cached_benchmark()
    assert list(frame["Close"]) == [1.5, 2.5]
    assert len(stub_download) == calls  # the read itself never fetched


def test_cached_benchmark_missing_is_none(cache, monkeypatch):
    def boom(symbol):
        raise AssertionError("must not fetch")

    monkeypatch.setattr(market, "download_bars", boom)
    assert market.cached_benchmark() is None


# --- market: launch-time sweep + disk-only reads ---


def test_refresh_all_sweeps_benchmark_first_and_warms(cache, watchlist, monkeypatch):
    order = []

    def fake_download(symbol):
        order.append(symbol)
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(["2026-02-20", "2026-02-23"]),
                "Open": [1.0, 1.0],
                "High": [1.0, 1.0],
                "Low": [1.0, 1.0],
                "Close": [1.0, 2.0],
                "Adj Close": [1.0, 2.0],
                "Volume": [0, 0],
            }
        )

    monkeypatch.setattr(market, "download_bars", fake_download)
    monkeypatch.setattr(market, "download_stats", lambda s: {"shortName": f"{s} Inc."})
    monkeypatch.setattr(market, "download_eps", lambda s: [["2026-01-30", 2.0, 1.9]])
    lines = []
    market.refresh_all(progress=lambda s, i, n, e: lines.append((s, i, n, e)))
    expected = [market.BENCHMARK, *market.DEFAULT_WATCHLIST]
    assert order == expected  # benchmark first, every symbol once
    assert len(lines) == len(expected) and all(line[3] is None for line in lines)
    for symbol in expected:
        assert (cache / f"{symbol}.csv").exists()
    assert (cache / "AAPL.stats.json").exists() and (cache / "AAPL.eps.json").exists()
    assert not (cache / f"{market.BENCHMARK}.stats.json").exists()  # bars only


def test_refresh_all_fresh_files_untouched(cache, watchlist, monkeypatch):
    monkeypatch.setattr(
        market,
        "download_bars",
        lambda s: (_ for _ in ()).throw(AssertionError("must not refetch")),
    )
    for symbol in [market.BENCHMARK, *market.symbols()]:
        market._save(
            cache / f"{symbol}.csv",
            pd.DataFrame({"Date": [pd.Timestamp("2026-02-20")], "Close": [1.0]}),
        )
    market.refresh_all()  # everything fresh: not one fetch, no crash


def test_refresh_all_contains_per_symbol_failure(cache, watchlist, monkeypatch):
    def flaky(symbol):
        if symbol == market.DEFAULT_WATCHLIST[0]:
            raise OSError("no data")
        return pd.DataFrame({"Date": [pd.Timestamp("2026-02-20")], "Close": [1.0]})

    monkeypatch.setattr(market, "download_bars", flaky)
    lines = []
    market.refresh_all(progress=lambda s, i, n, e: lines.append((s, i, n, e)))
    failed = next(line for line in lines if line[3])
    assert failed[0] == market.DEFAULT_WATCHLIST[0] and "no data" in failed[3]
    assert (cache / f"{market.DEFAULT_WATCHLIST[1]}.csv").exists()  # sweep moved on


def test_disk_only_reads_never_fetch(cache, monkeypatch, stub_download):
    market.load_bars("AAPL")  # warm one bars cache
    market.load_bars(market.BENCHMARK)  # ...and the benchmark
    (cache / "AAPL.stats.json").write_text('{"shortName": "AAPL Inc."}')
    (cache / "AAPL.eps.json").write_text('[["2026-01-30", 2.0, 1.9]]')
    calls = len(stub_download)

    def boom(*args, **kwargs):
        raise AssertionError("disk-only reads must not fetch")

    monkeypatch.setattr(market, "download_stats", boom)
    monkeypatch.setattr(market, "download_eps", boom)
    assert market.read_stats("AAPL")["shortName"] == "AAPL Inc."
    assert market.read_eps("AAPL") == [["2026-01-30", 2.0, 1.9]]
    assert list(market.cached_benchmark()["Close"]) == [1.5, 2.5]
    assert len(stub_download) == calls  # bars reads stayed disk-only too
    assert market.read_stats("NOPE") == {} and market.read_eps("NOPE") == []
    assert market.cached_benchmark() is not None


def test_sweep_freshness(cache, watchlist, stub_download):
    market.load_bars(market.DEFAULT_WATCHLIST[0])
    fresh, as_of = market.sweep_freshness()
    assert not fresh  # the rest of the watchlist has no cache yet
    assert as_of is not None  # newest mtime's date, from the one warm file
    for symbol in market.symbols():
        market.load_bars(symbol)
    fresh, _ = market.sweep_freshness()
    assert fresh  # everything warmed today
    _age(cache / f"{market.DEFAULT_WATCHLIST[0]}.csv", days=1)
    assert market.sweep_freshness()[0] is False  # one stale file spoils it


# --- watchlist ---


def test_symbols_reads_file_deduped(watchlist):
    watchlist.write_text('["GOOGL", "GOOGL", "AAPL"]')
    assert market.symbols() == ["GOOGL", "AAPL"]


def test_symbols_missing_file_seeded(watchlist):
    assert not watchlist.exists()
    assert market.symbols() == market.DEFAULT_WATCHLIST
    assert json.loads(watchlist.read_text()) == market.DEFAULT_WATCHLIST


def test_symbols_survives_corrupt_watchlist(watchlist):
    watchlist.write_text("not json")
    assert market.symbols() == market.DEFAULT_WATCHLIST


def test_add_symbol_verifies_and_persists(cache, watchlist, stub_download):
    assert market.add_symbol(" googl ") == "GOOGL"
    assert stub_download == ["GOOGL"]  # verified against the provider
    assert (cache / "GOOGL.csv").exists()  # cache warmed on add
    assert market.symbols() == [*market.DEFAULT_WATCHLIST, "GOOGL"]
    with pytest.raises(ValueError):  # duplicate
        market.add_symbol("GOOGL")
    with pytest.raises(ValueError):  # not a ticker
        market.add_symbol("nope!")


def test_add_symbol_unknown_ticker_not_persisted(cache, watchlist, monkeypatch):
    def boom(symbol):
        raise OSError("offline")

    monkeypatch.setattr(market, "download_bars", boom)
    with pytest.raises(OSError):
        market.add_symbol("ZZZZ")
    assert market.symbols() == market.DEFAULT_WATCHLIST


def test_add_symbol_unverified_skips_fetch(cache, watchlist, monkeypatch):
    """--offline adds: format + duplicate checks only, no verification."""
    monkeypatch.setattr(
        market,
        "download_bars",
        lambda s: (_ for _ in ()).throw(AssertionError("offline add must not fetch")),
    )
    assert market.add_symbol("googl", verify=False) == "GOOGL"
    assert market.symbols() == [*market.DEFAULT_WATCHLIST, "GOOGL"]
    assert not (cache / "GOOGL.csv").exists()  # nothing warmed, by design


# --- routes ---


def _long_frame():
    """Enough rising bars that every rolling window (200d SMA, 252d
    momentum/vol) is warm."""
    return pd.DataFrame(
        {
            "Date": pd.bdate_range("2020-01-01", periods=300),
            "Open": 1.0,
            "High": 1.0,
            "Low": 1.0,
            "Close": np.linspace(100, 200, 300),
            "Volume": 0,
        }
    )


@pytest.fixture
def client(cache, watchlist, stub_download, stub_stats, stub_eps, monkeypatch):
    """Test client with a warm cache — the launch-time sweep's equivalent:
    pages read disk only, so the fixture fetches (stubbed) up front."""
    monkeypatch.setattr(market, "download_bars", lambda s: _long_frame())
    market.refresh_all()  # stubbed downloads, per-test re-stubbable after
    web.app.config["TESTING"] = True
    web.app.config.pop("OFFLINE", None)
    return web.app.test_client()


# --- landing ---


def test_index_landing_rows_and_links(client):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/symbol/AAPL"' in html
    assert "day" in html
    assert "+" in html  # rising frame → positive day change
    assert "signals" not in html  # tally gone: zero computation on renders
    assert "no cached data" not in html
    assert html.count("<svg") == len(market.DEFAULT_WATCHLIST)  # one sparkline per row
    assert "polyline" in html and "60d" in html
    assert "AAPL Inc." in html  # company name under the symbol
    assert "Technology" in html  # ...and the sector


def test_index_sparkline_skips_uncached_rows(client, cache):
    (cache / f"{market.DEFAULT_WATCHLIST[0]}.csv").unlink()
    html = client.get("/").get_data(as_text=True)
    assert "no cached data" in html
    assert html.count("<svg") == len(market.DEFAULT_WATCHLIST) - 1


def test_index_survives_empty_cache(client, cache):
    for symbol in market.DEFAULT_WATCHLIST:
        (cache / f"{symbol}.csv").unlink(missing_ok=True)
    html = client.get("/").get_data(as_text=True)
    assert html.count("no cached data") == len(market.DEFAULT_WATCHLIST)


def test_index_no_note_when_fresh(client):
    assert "data as of" not in client.get("/").get_data(as_text=True)


def test_index_staleness_note_when_stale(client, cache):
    for symbol in market.DEFAULT_WATCHLIST:
        _age(cache / f"{symbol}.csv", days=1)
    html = client.get("/").get_data(as_text=True)
    assert "data as of" in html and "restart to refresh" in html


def test_index_offline_note_even_when_fresh(client):
    web.app.config["OFFLINE"] = True
    try:
        html = client.get("/").get_data(as_text=True)
    finally:
        web.app.config.pop("OFFLINE", None)
    assert "data as of" in html


# --- symbol overview page ---


@pytest.mark.parametrize("path", ["/symbol/NOPE"])
def test_symbol_page_unknown_symbol_404(client, path):
    assert client.get(path).status_code == 404


def test_symbol_page_renders(client, capsys):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert 'id="chart"' in html
    assert "SMA 50" in html and "SMA 200" in html
    assert "/strategies" not in html  # the lab is gone in this product
    assert "buy_hold" not in html


def test_symbol_page_timescale_buttons(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "data-ranges" in html  # button row under the chart
    assert '<button data-range="504" class="selected">2Y</button>' in html  # default


def test_symbol_page_range_ytd(client):
    html = client.get("/symbol/AAPL?range=ytd").get_data(as_text=True)
    assert '<button data-range="ytd" class="selected">YTD</button>' in html


def test_symbol_page_payload_capped_at_max(client, cache):
    n = panels.MAX_CHART_BARS + 80
    frame = pd.DataFrame(
        {
            "Date": pd.bdate_range("2010-01-01", periods=n),
            "Open": 1.0,
            "High": 1.0,
            "Low": 1.0,
            "Close": np.linspace(100, 200, n),
            "Volume": 0,
        }
    )
    frame.to_csv(cache / "AAPL.csv", index=False)  # cache is the only source
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    payload = _payload(html)
    assert len(payload["dates"]) == panels.MAX_CHART_BARS  # trimmed to the cap


def test_symbol_page_fundamentals_panel(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "fundamentals" in html
    assert "Technology · Gadgets" in html  # sector · industry in panel head
    assert "P/E (ttm)" in html and "39.5×" in html
    assert "$5.00B" in html  # revenue / market-cap style compaction
    assert "$5.00M" in html  # revenue per employee: 5e9 / 1000


def test_symbol_page_company_name_below_symbol(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert '<div class="sym-sub">AAPL Inc.</div>' in html  # stub shortName


def test_symbol_page_stat_tooltips(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    # every fundamentals row + risk row + market-relative row + the two
    # earnings-momentum rows (SUE, last surprise — from stub_eps) carry a
    # tooltip (price-context rows absent: stub stats carry no 52w keys)
    expected = (
        sum(len(rows) for _, rows in fundamentals.STAT_GROUPS)
        + len(panels.RISK_ROWS)
        + len(panels.BENCH_ROWS)
        + 2
    )
    assert html.count('<td title="') == expected
    assert 'title="Price ÷ trailing 12-month EPS' in html  # P/E (ttm)


def test_symbol_page_risk_card(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "ann. vol 63d" in html and "ann. vol 252d" in html
    assert "max drawdown" in html and "VaR 1d 95%" in html
    assert "ulcer index" in html
    # tail-shape rows: skew, best/worst day, longest underwater run
    assert "skewness" in html and "best day" in html and "worst day" in html
    assert "longest underwater" in html
    assert f"{len(_long_frame())} bars ≈" in html  # window note in panel head
    # factor scorecard across the (stubbed, identical) watchlist:
    # 12-1 mom + low-vol + SUE ranks + the composite (value absent:
    # no P/B in stub stats)
    assert "vs watchlist:" in html and "12-1 mom 1/12" in html
    assert "low-vol 1/12" in html and "SUE 1/12" in html
    assert "composite" in html


def test_symbol_page_bench_panel_and_rs(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "vs S&amp;P 500" in html and "252d regression" in html
    # stubbed benchmark equals the stock frame: β = 1, α = 0, R² = 1
    assert '<td class="num mono">1.00</td>' in html
    assert '<td class="num mono">+0.0%</td>' in html
    # residuals are exactly zero on identical frames → σ = 0 → placeholder
    assert '<td class="num mono">—</td>' in html
    # RS series in the payload, normalized to 1.0 at the window start
    payload = _payload(html)
    assert len(payload["rs"]) == len(payload["dates"])
    assert payload["rs"][0] == 1.0
    assert "RS vs S&P" in html  # legend entry for the toggle
    # relative chip in the perf strip: identical frames → exactly 0%
    assert "vs S&amp;P 1y" in html


def test_symbol_page_bench_unavailable_degrades(client, monkeypatch):
    monkeypatch.setattr(web, "cached_benchmark", lambda: None)
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "vs S&amp;P 500" not in html  # panel drops out entirely
    assert "vs S&amp;P 1y" not in html  # …and so does the strip chip


def test_symbol_page_earnings_momentum_group(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "earnings momentum" in html
    # stub_eps: SUE = 0.2/stdev([0.1,0.1,0.1,0.1,0.2]) ≈ +4.47
    assert "SUE" in html and "+4.47" in html
    # last surprise: (1.30 − 1.25)/1.25
    assert "last surprise (2026-04-30)" in html and "+4.0%" in html


def test_symbol_page_perf_strip(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    for label in ("1m", "3m", "6m", "ytd", "1y"):
        assert label in html
    # rising fixture → positive trailing returns colored green
    assert 'class="up">+' in html
    # the strategy-era chips are gone from this product
    assert "mom/σ" not in html  # (12-1 mom survives in the scorecard)
    assert 'href="/symbol/AAPL/strategies' not in html


def test_symbol_page_volume_and_drawdown_payload(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    payload = _payload(html)
    assert len(payload["volume"]) == len(payload["dates"])
    assert len(payload["drawdown"]) == len(payload["dates"])
    assert payload["volume"] == [0] * len(payload["dates"])  # fixture stub


def _payload(html):
    line = next(l for l in html.splitlines() if "const payload =" in l)
    return json.loads(line.split("= ", 1)[1].rstrip(";"))


def test_symbol_page_total_return_uses_adj_close(client, cache):
    """P1: with Adj Close cached, every long-horizon number reads the
    adjusted series; the price header + day change stay raw."""
    frame = _long_frame()
    frame["Adj Close"] = frame["Close"] * 0.5  # dividends-adjusted look
    frame.to_csv(cache / "AAPL.csv", index=False)
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    payload = _payload(html)
    assert payload["closes"][0] == 50.0  # adj, not 100
    # SMA overlay rides the same TR basis: 0.5 × raw-Close SMA, not raw
    expected_long = 0.5 * frame["Close"].rolling(panels.SMA_LONG).mean().iloc[-1]
    expected_short = 0.5 * frame["Close"].rolling(panels.SMA_SHORT).mean().iloc[-1]
    assert payload["sma_long"][-1] == pytest.approx(expected_long)
    assert payload["sma_short"][-1] == pytest.approx(expected_short)
    assert "total return" in html  # the chip that explains the basis
    assert "price · SMA overlay" not in html  # head says "total return ·"
    # header stays the ticker's raw price: $200.00, not $100.00
    assert 'class="sym-price mono">$200.00</span>' in html


def test_symbol_page_without_adj_close_falls_back(client, cache):
    frame = _long_frame()  # no Adj Close column at all
    frame.to_csv(cache / "AAPL.csv", index=False)
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    payload = _payload(html)
    assert payload["closes"][0] == 100.0  # raw close fallback
    assert "total return</span>" not in html  # no total-return chip
    assert "price · SMA overlay" in html


def test_symbol_page_range_max(client):
    html = client.get("/symbol/AAPL?range=max").get_data(as_text=True)
    assert '<button data-range="max" class="selected">MAX</button>' in html


def test_theme_foundation(client):
    """P2: light-first theme.css + toggle ship on every page."""
    for path in ("/", "/symbol/AAPL"):
        html = client.get(path).get_data(as_text=True)
        assert 'href="/static/theme.css"' in html
        assert 'id="theme-toggle"' in html
        assert "app.css" not in html
        assert 'localStorage.getItem("lf-theme")' in html  # no-FOUC boot


def test_symbol_page_chart_theme_wiring(client):
    """Chart colors read CSS vars; the toggle can restyle live."""
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "lfApplyChartTheme" in html
    assert 'cssVar("--chart-close")' in html
    assert "#58a6ff" not in html  # no hardcoded palette left


def test_symbol_page_price_header(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert 'class="sym-price mono">$200.00</span>' in html  # last close, big
    # linspace(100, 200, 300): +100/299 over 199.67 → +0.17% day change
    assert 'class="sym-change up">+0.17%' in html


def test_symbol_page_volume_toggle(client):
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert 'id="vol-toggle"' in html
    assert "volume: off</button>" in html  # starts hidden, click toggles
    assert '<div class="chart-foot">' in html  # right of the timescale row


def test_symbol_page_price_context_and_derived_rows(client, monkeypatch):
    monkeypatch.setattr(
        web,
        "read_stats",
        lambda s: {
            "shortName": f"{s} Inc.",
            "trailingPE": 12.5,
            "priceToBook": 4.0,
            "marketCap": 8e9,
            "totalDebt": 3e6,
            "fiftyTwoWeekHigh": 250.0,
            "fiftyTwoWeekLow": 100.0,
            # derived at the cache boundary by src/market.py
            "bookToMarket": 0.25,
            "earningsYield": 0.08,
            "fcfYield": 0.05,
            "netDebt": 2e6,
        },
    )
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "price context" not in html  # moved into the perf strip
    assert "52w high" in html and "$250.00 (-20.0%)" in html  # close 200 vs high 250
    assert "52w low" in html and "$100.00 (+100.0%)" in html  # ...vs low 100
    assert "book/market" in html and "0.2×" in html
    assert "earnings yield" in html and "8.00%" in html
    assert "FCF yield" in html and "5.00%" in html
    assert "net debt" in html and "$2.00M" in html


@pytest.mark.parametrize("path", ["/symbol/AAPL"])
@pytest.mark.parametrize("query", ["range=abc", "range=1", "range=0"])
def test_symbol_pages_bad_range_400(client, path, query):
    assert client.get(f"{path}?{query}").status_code == 400


@pytest.mark.parametrize("path", ["/symbol/AAPL"])
def test_symbol_pages_missing_cache_404(client, cache, path):
    (cache / "AAPL.csv").unlink()
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/", "/symbol/AAPL"])
def test_pages_never_fetch(client, monkeypatch, path):
    """Rule 1: with a warm cache, no page render touches the network."""

    def boom(*args, **kwargs):
        raise AssertionError("page render tried to fetch")

    monkeypatch.setattr(market, "download_bars", boom)
    monkeypatch.setattr(market, "download_stats", boom)
    monkeypatch.setattr(market, "download_eps", boom)
    assert client.get(path).status_code == 200


# --- stat formatting ---


def test_entry_default_and_custom_port(monkeypatch):
    ran = {}
    sweeps = []
    monkeypatch.setattr(web.app, "run", lambda **kw: ran.update(kw))
    monkeypatch.setattr(market, "refresh_all", lambda progress=None: sweeps.append(1))
    assert longfund.main([]) == 0
    assert ran == {"host": "127.0.0.1", "port": longfund.DEFAULT_PORT}
    assert sweeps == [1]  # default launch warms the cache first
    assert longfund.main(["--port", "9999"]) == 0
    assert ran == {"host": "127.0.0.1", "port": 9999}


def test_entry_offline_skips_sweep(monkeypatch):
    ran = {}
    monkeypatch.setattr(web.app, "run", lambda **kw: ran.update(kw))
    monkeypatch.setattr(
        market,
        "refresh_all",
        lambda progress=None: (_ for _ in ()).throw(AssertionError("no sweep offline")),
    )
    assert longfund.main(["--offline"]) == 0
    assert ran == {"host": "127.0.0.1", "port": longfund.DEFAULT_PORT}
    assert web.app.config["OFFLINE"] is True


def test_entry_sweep_only_runs_sweep_and_exits(monkeypatch):
    sweeps = []
    monkeypatch.setattr(market, "refresh_all", lambda progress=None: sweeps.append(1))
    monkeypatch.setattr(
        web.app,
        "run",
        lambda **kw: (_ for _ in ()).throw(AssertionError("no server in sweep-only")),
    )
    assert longfund.main(["--sweep-only"]) == 0
    assert sweeps == [1]  # swept once, never served


@pytest.mark.parametrize("port", ["0", "-1", "70000", "abc"])
def test_entry_rejects_bad_port(port):
    with pytest.raises(SystemExit) as err:
        longfund.main(["--port", port])
    assert err.value.code == 2  # argparse usage error


def test_entry_help_shows_port(capsys):
    with pytest.raises(SystemExit):
        longfund.main(["--help"])
    assert "--port" in capsys.readouterr().out


def test_fmt_stat_kinds():
    assert fundamentals._fmt_stat(0.2761, "pct") == "27.61%"
    assert fundamentals._fmt_stat(4_977_636_933_632, "usd_big") == "$4.98T"
    assert fundamentals._fmt_stat(892_000_000, "usd_big") == "$892.00M"
    assert fundamentals._fmt_stat(14_594_180_000, "cnt") == "14.59B"
    assert fundamentals._fmt_stat(78.445, "dex") == "0.78×"  # Yahoo pct → ratio
    assert fundamentals._fmt_stat(150_000, "int") == "150,000"
    assert fundamentals._fmt_stat(8.73, "usd") == "$8.73"
    assert fundamentals._fmt_stat(None, "x") == "—"
    assert fundamentals._fmt_stat("Technology", "str") == "Technology"


# --- ETF lens (quoteType classification, fund profile, LETF readout) ---


class _EtfTicker(_FakeTicker):
    """Stands in for an ETF's info payload."""

    def get_info(self):
        info = super().get_info()
        info.update(
            quoteType="ETF",
            category="Large Growth",
            fundFamily="Vanguard",
            annualExpenseRatio=0.0003,
            totalAssets=5e11,
            navPrice=499.0,
            currentPrice=505.0,
        )
        info["yield"] = 0.012
        return info


def test_stats_etf_keys(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_EtfTicker))
    stats = market.load_stats("SPY")
    assert stats["quoteType"] == "ETF"
    assert stats["category"] == "Large Growth"
    assert stats["annualExpenseRatio"] == pytest.approx(0.0003)
    assert "premiumDiscount" not in stats  # dropped: Yahoo's NAV lags, the
    # derived number was staleness artifact, not a real premium/discount


def test_stats_expense_ratio_from_fund_operations(cache, monkeypatch):
    """yfinance's info omits annualExpenseRatio for ETFs — the fund-
    operations scrape must backfill it (first column = the fund)."""

    class Scrape(_EtfTicker):
        def get_info(self):
            info = super().get_info()
            del info["annualExpenseRatio"]
            return info

        @property
        def funds_data(self):
            ops = pd.DataFrame(
                [[0.0004, 0.0072]],
                index=pd.Index(["Annual Report Expense Ratio"]),
                columns=["SPY", "Category Average"],
            )
            return SimpleNamespace(fund_operations=ops)

    monkeypatch.setattr(market, "yf", _fake_yf(Scrape))
    stats = market.load_stats("SPY")
    assert stats["annualExpenseRatio"] == pytest.approx(0.0004)


def test_stats_expense_ratio_scrape_failure_contained(cache, monkeypatch):
    class Broken(_EtfTicker):
        def get_info(self):
            info = super().get_info()
            del info["annualExpenseRatio"]
            return info

        @property
        def funds_data(self):
            raise RuntimeError("provider hiccup")

    monkeypatch.setattr(market, "yf", _fake_yf(Broken))
    stats = market.load_stats("SPY")
    assert "annualExpenseRatio" not in stats  # placeholder, not a crash


def test_stats_stock_gets_no_etf_keys(cache, monkeypatch):
    monkeypatch.setattr(market, "yf", _fake_yf(_FakeTicker))
    stats = market.load_stats("AAPL")
    assert "quoteType" not in stats  # absent keys drop per-symbol


def test_refresh_all_skips_eps_for_etf(cache, watchlist, monkeypatch):
    watchlist.write_text(json.dumps(["AAPL", "SPY"]))
    monkeypatch.setattr(market, "download_bars", lambda s: _long_frame())
    monkeypatch.setattr(
        market,
        "download_stats",
        lambda s: (
            {"shortName": s, "quoteType": "ETF"} if s == "SPY" else {"shortName": s}
        ),
    )
    fetched = []
    monkeypatch.setattr(market, "download_eps", lambda s: fetched.append(s) or [])
    market.refresh_all()
    assert "AAPL" in fetched  # stocks keep the EPS sweep
    assert "SPY" not in fetched  # ETFs skip it: no earnings to fetch


def test_index_sector_falls_back_to_category(client, cache):
    (cache / "AAPL.stats.json").write_text(
        json.dumps(
            {"shortName": "SPDR S&P 500", "quoteType": "ETF", "category": "Large Blend"}
        )
    )
    html = client.get("/").get_data(as_text=True)
    assert "Large Blend" in html


def test_symbol_page_etf_lens(client, cache):
    (cache / "AAPL.stats.json").write_text(
        json.dumps(
            {
                "shortName": "SPDR S&P 500 ETF",
                "quoteType": "ETF",
                "category": "Large Blend",
                "fundFamily": "State Street",
                "annualExpenseRatio": 0.0009,
                "navPrice": 500.0,
            }
        )
    )
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "fund profile" in html  # the stock fundamentals heading swapped
    assert "expense ratio" in html and "Large Blend" in html
    assert "gross margin" not in html  # stock profitability groups gone
    assert "earnings momentum" not in html  # no EPS lens for funds
    assert "premium" not in html  # the premium/discount row is gone


def test_symbol_page_distributions_group(client, cache):
    today = datetime.now(tz=timezone.utc).date()
    rows = [
        [(today - timedelta(days=d)).strftime("%Y-%m-%d"), amount]
        for d, amount in (
            (700, 0.24),
            (600, 0.25),
            (500, 0.25),
            (400, 0.25),  # prior-TTM bucket sums to 0.99
            (300, 0.26),
            (210, 0.26),
            (120, 0.27),
            (30, 0.28),  # TTM bucket sums to 1.07
        )
    ]
    (cache / "AAPL.stats.json").write_text(json.dumps({"shortName": "Apple Inc."}))
    (cache / "AAPL.divs.json").write_text(json.dumps(rows))
    html = client.get("/symbol/AAPL").get_data(as_text=True)
    assert "distributions" in html
    assert "quarterly" in html  # 4 ex-dates inside the TTM window
    assert "$1.07" in html  # TTM cash/share (≥ $1 → 2 decimals)
    assert "+8.1%" in html  # 1.07 / 0.99 − 1, vs the prior 12 months
    assert rows[-1][0] in html and "$0.2800" in html  # newest payment row


def test_bench_context_letf_rows():
    # a 2× daily-rebalanced subject: β = 2 exactly → LETF rows appear,
    # and compounding 2m falls below (compounding m)² → negative decay gap
    n = 400
    bench_closes = np.linspace(100, 200, n)
    bench_rets = np.diff(bench_closes) / bench_closes[:-1]
    subject = np.concatenate([[100.0], 100.0 * np.cumprod(1 + 2 * bench_rets)])
    dates = pd.bdate_range("2020-01-01", periods=n)
    bench = pd.DataFrame({"Date": dates, "Close": bench_closes})
    rows = panels._bench_context(
        pd.DataFrame({"Date": dates, "Close": subject}), bench
    )["rows"]
    labels = [row[0] for row in rows]
    assert "decay gap" in labels and any(l.startswith("bench^") for l in labels)
    gap = next(row for row in rows if row[0] == "decay gap")
    assert gap[2].startswith("-")  # variance drag
    # plain 1:1 subject: no leverage → no LETF rows
    plain = panels._bench_context(bench, bench)["rows"]
    assert "decay gap" not in [row[0] for row in plain]
