"""Longfund web app: Flask routes and the JSON API.

Entry point is the thin `longfund.py` at the repo root (config +
launch); this module is the HTTP layer only — page math lives in
src/panels.py (risk, vs-S&P, strip, scorecard) and src/fundamentals.py
(fundamentals tables). Research only — no strategies, no backtests, no
signal computation anywhere. Long-horizon numbers read
total-return series (adjusted closes) via `panels._tr_closes`.
"""

import math
from pathlib import Path

import pandas as pd
from flask import Flask, abort, jsonify, redirect, render_template, request
from werkzeug.exceptions import HTTPException

from src.fundamentals import _distribution_rows, _eps_rows, _stat_groups
from src.market import (
    add_symbol,
    cached_bars,
    cached_benchmark,
    read_divs,
    read_eps,
    read_stats,
    sweep_freshness,
    symbols,
)
from src.metrics import drawdown_series, risk_snapshot, sue
from src.panels import (
    CHART_BARS,
    MAX_CHART_BARS,
    SMA_LONG,
    SMA_SHORT,
    SPARK_WINDOW,
    _bench_context,
    _perf_strip,
    _risk_rows,
    _sparkline,
    _tr_closes,
    _tr_column,
    _watchlist_ranks,
    sma,
)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
    static_folder=str(Path(__file__).resolve().parent.parent / "static"),
)


@app.get("/")
def index():
    """Landing: one row per watchlist symbol, linking into /symbol/{TICKER}.
    Reads disk only (launch warmed it); no strategy runs, no fetching."""
    rows = []
    for symbol in symbols():
        try:
            bars = cached_bars(symbol)
        except OSError:
            rows.append({"symbol": symbol, "ok": False})
            continue
        closes = [float(c) for c in bars["Close"]]
        stats = read_stats(symbol)
        last = closes[-1]
        prev = closes[-2] if len(closes) > 1 else last
        rows.append(
            {
                "symbol": symbol,
                "ok": True,
                "company": stats.get("shortName"),
                "sector": stats.get("sector") or stats.get("category"),
                "last": last,
                "change": last / prev - 1,
                "spark": _sparkline(_tr_closes(bars)),
            }
        )
    fresh, as_of = sweep_freshness()
    note = (
        None
        if fresh and not app.config.get("OFFLINE")
        else f"data as of {as_of or '—'} — restart to refresh"
    )
    return render_template(
        "index.html",
        rows=rows,
        spark_days=SPARK_WINDOW,
        data_note=note,
    )


@app.get("/symbol/<symbol>")
def symbol_page(symbol):
    """Research page: total-return chart with volume + drawdown, trailing
    strip, fundamentals (or fund profile), vs-S&P panel, risk card.
    Disk-only reads, zero computation beyond pandas rolling — and every
    long-horizon number reads the total-return series (`_tr_closes`)."""
    symbol, bars = _page_bars(symbol)
    range_arg, _ = _page_range(bars)
    dates = [d.strftime("%Y-%m-%d") for d in bars["Date"]]
    raw = [float(c) for c in bars["Close"]]
    closes = _tr_closes(bars)  # total return: chart, strip, risk, drawdown, SMA
    tr = pd.Series(closes)
    start = max(0, len(dates) - MAX_CHART_BARS)
    window = closes[start:]

    bench_frame = cached_benchmark()
    bench = _bench_context(bars, bench_frame, _tr_column(bars))
    payload = {
        "dates": dates[start:],
        "closes": [round(c, 4) for c in window],
        # SMA on the same TR series it overlays: raw-Close SMAs drift above
        # the adjusted price line wherever dividend history accumulates
        "sma_short": _clean(sma(tr, SMA_SHORT))[start:],
        "sma_long": _clean(sma(tr, SMA_LONG))[start:],
        "volume": [int(v) for v in bars["Volume"].iloc[start:]],
        "drawdown": [round(d * 100, 2) for d in drawdown_series(window)],
        # relative strength vs ^GSPC (stock/bench ratio, 1.0 at window start)
        "rs": [round(r, 4) if r is not None else None for r in bench["rs"]],
    }

    stats = read_stats(symbol)
    is_etf = stats.get("quoteType") == "ETF"
    company = stats.get("shortName")
    stat_groups = _stat_groups(stats, is_etf=is_etf)
    eps_rows = [] if is_etf else _eps_rows(read_eps(symbol))
    if eps_rows:
        stat_groups.append(("earnings momentum", eps_rows))
    divs = read_divs(symbol)
    dist_groups = [("distributions", _distribution_rows(divs))] if divs else []
    risk_rows, risk_meta = _risk_rows(risk_snapshot(window))
    return render_template(
        "symbol.html",
        symbol=symbol,
        company=company,
        last_price=raw[-1],
        day_change=raw[-1] / raw[-2] - 1 if len(raw) > 1 else None,
        total_return="Adj Close" in bars.columns,
        range_arg=range_arg,
        payload=payload,
        perf_strip=_perf_strip(
            closes,
            dates,
            bench["rel_1y"],
            stats.get("fiftyTwoWeekHigh"),
            stats.get("fiftyTwoWeekLow"),
        ),
        risk_rows=risk_rows,
        risk_meta=risk_meta,
        bench_rows=bench["rows"],
        bench_meta=bench["meta"],
        rank_line=_watchlist_ranks(symbol),
        stat_groups=stat_groups,
        dist_groups=dist_groups,
        stat_title="fund profile" if is_etf else None,
        stat_meta=(
            " · ".join(filter(None, (stats.get("sector"), stats.get("industry"))))
            or " · ".join(
                filter(None, (stats.get("category"), stats.get("fundFamily")))
            )
        ),
    )


@app.post("/watchlist")
def watchlist_add():
    """Add a symbol to the watchlist: form field `symbol`, redirected to /.
    The one in-request fetch left (Yahoo verification); under --offline
    it is skipped — format + duplicate check only, persisted unverified."""
    try:
        add_symbol(
            request.form.get("symbol") or "", verify=not app.config.get("OFFLINE")
        )
    except (ValueError, OSError) as err:
        abort(400, description=str(err))
    return redirect("/")


# --- JSON API ---


@app.errorhandler(HTTPException)
def _json_api_errors(err):
    """API paths get JSON errors; pages keep Flask's default pages."""
    if request.path.startswith("/api/"):
        return jsonify({"error": err.description or err.name}), err.code
    return err


def _bars_or_abort(symbol: str):
    """Bars for a watchlist symbol, or abort(404) on unknown/no-cache."""
    if symbol.upper() not in symbols():
        abort(404, description=f"unknown symbol: {symbol}")
    try:
        return cached_bars(symbol)
    except OSError:
        abort(404, description=f"no cached data for {symbol}")


def _page_bars(symbol: str):
    """Uppercased watchlist symbol + its bars, or abort(404)."""
    if symbol.upper() not in symbols():
        abort(404)
    try:
        bars = cached_bars(symbol)
    except OSError:
        abort(404, description=f"no cached data for {symbol}")
    return symbol.upper(), bars


def _page_range(bars) -> tuple[str, int]:
    """`range` query param for the timescale row: int ≥ 2, `ytd`, or `max`
    (full cached history) → (echoed value, bar count it stands for).

    Validated only, not capped — the browser slices to what exists. The
    echoed value drives the initially-selected button ("ytd" | "max" |
    str(n)); the count is the server-side window.
    """
    raw = request.args.get("range", default=str(CHART_BARS))
    if raw == "ytd":
        year = bars["Date"].iloc[-1].year
        window = int((bars["Date"].dt.year == year).sum())
    elif raw == "max":
        window = len(bars)
    else:
        try:
            window = int(raw)
        except ValueError:
            window = 0
    if window < 2:
        abort(
            400, description=f"range must be ytd, max, or an integer ≥ 2, got {raw!r}"
        )
    return raw, window


def _jsonable(value):
    """Non-finite floats → None; JSON-strict (NaN/inf break parsers)."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _clean(series) -> list:
    """Rounded floats, NaN (SMA warmup) → None for JSON."""
    return [None if math.isnan(float(v)) else round(float(v), 4) for v in series]


@app.get("/api/bars/<symbol>")
def api_bars(symbol):
    bars = _bars_or_abort(symbol)
    raw = request.args.get("tail", default="10")
    try:
        tail = int(raw)
        if tail < 1:
            raise ValueError(raw)
    except ValueError:
        abort(400, description=f"tail must be a positive integer, got {raw!r}")
    rows = [
        (d.strftime("%Y-%m-%d"), round(float(c), 4))
        for d, c in zip(bars["Date"][-tail:], bars["Close"][-tail:])
    ]
    return jsonify({"symbol": symbol.upper(), "bars": rows})


@app.get("/api/stats/<symbol>")
def api_stats(symbol):
    """Curated fundamentals for a watchlist symbol; {} = unavailable."""
    if symbol.upper() not in symbols():
        abort(404, description=f"unknown symbol: {symbol}")
    return jsonify({"symbol": symbol.upper(), "stats": read_stats(symbol)})


@app.get("/api/eps/<symbol>")
def api_eps(symbol):
    """Quarterly EPS history + derived SUE; [] / null = unavailable."""
    if symbol.upper() not in symbols():
        abort(404, description=f"unknown symbol: {symbol}")
    eps = read_eps(symbol)
    return jsonify(
        {
            "symbol": symbol.upper(),
            "eps": eps,
            "sue": _jsonable(sue([row[1] for row in eps])),
        }
    )
