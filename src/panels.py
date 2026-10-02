"""Computed research panels: chart payload helpers, trailing-return
strip, buy-and-hold risk card, vs-S&P regression panel (β/α/R²,
residual momentum, LETF decay readout), watchlist factor ranks, and
the landing sparkline. Disk reads via src/market; math via
src/metrics.
"""

from src.market import cached_bars, read_eps, read_stats, symbols
from src.metrics import (
    annualized_vol,
    daily_returns,
    regression_stats,
    residual_momentum,
    sue,
)

# chart overlays + the scorecard's momentum factor (classic 12-1, in
# trading days: lookback ~1y, skip the most recent month)
SMA_SHORT = 50
SMA_LONG = 200
MOM_LOOKBACK = 252
MOM_SKIP = 21


def sma(values, window):
    """Simple moving average of a pandas Series (chart overlays)."""
    return values.rolling(window).mean()


def _tr_column(bars) -> str:
    """Total-return column: Adj Close when cached (dividends and
    distributions reinvested, Yahoo's adjustment), else Close."""
    return "Adj Close" if "Adj Close" in bars.columns else "Close"


def _tr_closes(bars) -> list[float]:
    """Total-return closes for long-horizon numbers (strip, risk card,
    drawdown, scorecard momentum). Raw Close stays for the price header,
    day change, and the /api/bars rows — what the ticker shows."""
    return [float(c) for c in bars[_tr_column(bars)]]


CHART_BARS = 504  # default timescale (bars ≈ 2 trading years) on the symbol pages
MAX_CHART_BARS = 5040  # chart payload cap (~20y); timescale buttons slice in-browser
BETA_WINDOW = 252  # daily returns in the vs-S&P regression (~1y)
# LETF readout: flag effective leverage when the regression beta says
# leveraged (|β| ≥ 1.5) or inverse (β ≤ −1)
LETF_BETA = 1.5


# trailing-return strip windows in trading days, with the hover text each
# chip carries (12-1 skips the last month; 1m is the reversal zone the
# research skips; the rest are plain)
STRIP_WINDOWS = (
    (
        "1m",
        21,
        (
            "Total return over the last month — the zone momentum "
            "constructions deliberately skip (short-term reversal noise "
            "lives here)"
        ),
    ),
    (
        "3m",
        63,
        (
            "Total return over the last 3 months — a momentum formation "
            "length the research tests (J ∈ {3,6,9,12})"
        ),
    ),
    (
        "6m",
        126,
        (
            "Total return over the last 6 months — a momentum formation "
            "length the research tests (6-month formation earned "
            "0.95–1.10%/mo winner−loser)"
        ),
    ),
    (
        "ytd",
        0,
        ("Total return since January 1 — calendar convenience, not a research window"),
    ),
    (
        "1y",
        252,
        "Trailing 1-year total return — the canonical momentum formation window",
    ),
)

STRIP_REL_DESC = (
    "Total return ÷ the S&P 500's total return over the last year, minus 1 — "
    "the relative-momentum read rotation strategies rank on"
)


def _mom_12_1(closes: list[float]) -> float | None:
    """Classic 12-1 momentum return, magnitude not just sign: close 1 month
    ago ÷ close 12 months ago — the scorecard's momentum factor."""
    if len(closes) <= MOM_LOOKBACK:
        return None
    return closes[-1 - MOM_SKIP] / closes[-1 - MOM_LOOKBACK] - 1


def _perf_strip(
    closes: list[float],
    dates: list[str],
    rel_1y: float | None = None,
    high: float | None = None,
    low: float | None = None,
) -> list[tuple[str, float | tuple[float, float] | None, str, str]]:
    """Trailing-return chips: 1m/3m/6m/ytd/1y on the total-return series,
    plus (when the benchmark is available) the 1y relative return vs the
    S&P 500, and 52w high/low distance chips when the stats carry them;
    `kind` picks the strip's format, `desc` the hover text."""
    rows = []
    for label, n, desc in STRIP_WINDOWS:
        if label == "ytd":
            year = dates[-1][:4]
            first = next((i for i, d in enumerate(dates) if d[:4] == year), None)
            value = (
                closes[-1] / closes[first] - 1
                if first is not None and first < len(closes) - 1
                else None
            )
        else:
            value = closes[-1] / closes[-1 - n] - 1 if len(closes) > n else None
        rows.append((label, value, "pct", desc))
    if rel_1y is not None:
        rows.append(("vs S&P 1y", rel_1y, "pct", STRIP_REL_DESC))
    if isinstance(high, (int, float)) and high > 0:
        rows.append(
            (
                "52w high",
                (high, closes[-1] / high - 1),
                "px_pct",
                "52-week high · how far the last close sits below it — location context, not a ranked factor",
            )
        )
    if isinstance(low, (int, float)) and low > 0:
        rows.append(
            (
                "52w low",
                (low, closes[-1] / low - 1),
                "px_pct",
                "52-week low · how far the last close sits above it — location context, not a ranked factor",
            )
        )
    return rows


# risk card: (risk_snapshot key, label, inline gloss, format, hover description)
RISK_ROWS = [
    (
        "vol_63",
        "ann. vol 63d",
        "3-month price swings",
        "pct",
        (
            "Annualized std of the last 63 daily returns — a 3-month read. "
            "The low-volatility anomaly sorts on the 6–12 month version"
        ),
    ),
    (
        "vol_252",
        "ann. vol 252d",
        "1-year price swings",
        "pct",
        (
            "Annualized std of the last 252 daily returns. The low-"
            "volatility anomaly sorts on exactly this: previously low-vol "
            "stocks beat high-vol ones risk-adjusted — volatility is not "
            "paid for here"
        ),
    ),
    (
        "sharpe",
        "sharpe (hold)",
        "return per unit of risk",
        "num",
        (
            "Annualized mean ÷ volatility of daily returns, for simply "
            "holding. Read with skewness: Sharpe treats both tails the same, "
            "and non-normal returns inflate it (the deflated-Sharpe "
            "critique). For scale: the whole market ran ≈0.34 over 1963–2010"
        ),
    ),
    (
        "sortino",
        "sortino (hold)",
        "return per downside risk",
        "num",
        "Like Sharpe but only downside days count as risk — the pain an investor actually experiences",
    ),
    (
        "max_dd",
        "max drawdown",
        "worst peak-to-trough fall",
        "pct",
        (
            "Worst peak-to-trough decline over the window — the risk number "
            "that ends strategies and the one leverage gets sized against. "
            "Chan's bar: keep |CAGR ÷ max drawdown| ≥ 1"
        ),
    ),
    (
        "current_dd",
        "vs peak",
        "how far below the peak",
        "pct_signed",
        "How far the last close sits below the window's peak — how underwater a buyer today starts",
    ),
    (
        "var_95",
        "VaR 1d 95%",
        "loss exceeded 1 day in 20",
        "pct",
        (
            "5th percentile of daily losses (historical simulation): exceeded "
            "~1 day in 20. A threshold, not a tail measure — pair with ES for "
            "how bad breaches get"
        ),
    ),
    (
        "es_95",
        "ES 1d 95%",
        "average loss beyond VaR",
        "pct",
        (
            "Mean of the worst 5% of daily returns — how bad the breaches "
            "are, which VaR's threshold doesn't say. The non-Gaussian tail "
            "measure the research prefers for equalizing risk"
        ),
    ),
    (
        "ulcer",
        "ulcer index",
        "depth-weighted drawdown pain",
        "pct",
        "RMS of drawdowns — penalizes deep, long-lived pain, unlike volatility, which treats a quick dip and a long grind the same",
    ),
    (
        "cdar",
        "CDaR 80%",
        "tail-average drawdown",
        "pct",
        (
            "Mean of the worst 20% of drawdown observations — max drawdown "
            "is one sample; this averages the bad tail of the underwater curve"
        ),
    ),
    (
        "skew",
        "skewness",
        "tail asymmetry of returns",
        "num_signed",
        (
            "Skewness of daily returns; negative means the tail is the "
            "downside — the crash risk Sharpe ignores and the term the "
            "deflated-Sharpe correction uses"
        ),
    ),
    (
        "best_day",
        "best day",
        "biggest daily gain",
        "pct_signed",
        "Best single-day return in the window — the right tail's observed edge",
    ),
    (
        "worst_day",
        "worst day",
        "biggest daily loss",
        "pct_signed",
        "Worst single-day return in the window — the observed left tail behind the VaR/ES numbers; one such bar is what breaks Gaussian leverage math",
    ),
    (
        "uw_max",
        "longest underwater",
        "longest run below a peak",
        "bars",
        (
            "Most consecutive bars below a fresh peak — drawdown duration; "
            "Ulcer covers depth, this covers time"
        ),
    ),
]


def _risk_rows(snapshot: dict) -> tuple[list[tuple[str, str, str]], str]:
    """Risk snapshot → (label, gloss, formatted value, tooltip) rows + head note."""
    rows = []
    for key, label, gloss, kind, desc in RISK_ROWS:
        value = snapshot.get(key)
        if value is None:
            shown = "—"
        elif kind == "num":
            shown = f"{value:.2f}"
        elif kind == "num_signed":
            shown = f"{value:+.2f}"
        elif kind == "pct_signed":
            shown = f"{value:+.1%}"
        elif kind == "bars":
            shown = f"{value} bars"
        else:
            shown = f"{value:.1%}"
        rows.append((label, gloss, shown, desc))
    bars = snapshot.get("bars", 0)
    meta = f"{bars} bars ≈ {bars / 252:.0f}y" if bars else "—"
    return rows, meta


# market-relative panel rows: (key into _bench_context values, label,
# inline gloss, hover description) — the regression read out for one stock
BENCH_ROWS = [
    (
        "beta",
        "beta",
        "market sensitivity",
        (
            "OLS slope of the stock's daily returns on the S&P 500's over "
            "the regression window — the unforecast market exposure risk "
            "management would hedge away, not the thing you're researching"
        ),
    ),
    (
        "alpha",
        "α (ann.)",
        "return beyond the market",
        (
            "Regression intercept × 252: annualized return left over after "
            "the market's contribution. Alpha rotation strategies rank on "
            "exactly this; single-factor here, not the Fama–French alpha of "
            "the research — and the base the residual purge builds on"
        ),
    ),
    (
        "r2",
        "selectivity (1−R²)",
        "returns the market doesn't explain",
        (
            "1 − R² of the regression: the share of returns the market does "
            "not explain. Research calls this selectivity (Amihud–"
            "Goyenko / Garyn-Tal) and overweights it — low R² with positive "
            "α is the prized pair; high R² = buying the index with extra steps"
        ),
    ),
    (
        "resid",
        "resid. momentum",
        "stock-specific momentum",
        (
            "Risk-adjusted 12-1 momentum on market-purged residuals — the "
            "stock-specific part of momentum, with the market factor's "
            "contribution removed (single-factor purge, a proxy for the "
            "research's Fama–French version). In daily mean/σ units"
        ),
    ),
]


def _bench_context(bars, bench, column: str = "Close") -> dict:
    """Market-relative context vs the benchmark: 1y daily β/α/R², residual
    12-1 momentum, 1y relative return, and an RS ratio series (stock ÷
    benchmark, 1.0 at the first charted bar) aligned to the page's chart
    dates — all on the `column` series (total-return when adjusted closes
    are cached). Degrades to empty rows when benchmark/overlap is missing."""
    empty = {"rows": [], "meta": "benchmark unavailable", "rs": [], "rel_1y": None}
    if bench is None:
        return empty
    bench_col = column if column in bench.columns else "Close"
    keyed = {
        d.strftime("%Y-%m-%d"): float(c)
        for d, c in zip(bench["Date"], bench[bench_col])
    }
    pairs = [
        (d.strftime("%Y-%m-%d"), float(c), keyed[d.strftime("%Y-%m-%d")])
        for d, c in zip(bars["Date"], bars[column])
        if d.strftime("%Y-%m-%d") in keyed
    ]
    if len(pairs) < 30:
        return {**empty, "meta": "benchmark overlap too short"}
    rets = daily_returns([p[1] for p in pairs])
    bench_rets = daily_returns([p[2] for p in pairs])
    reg = regression_stats(rets[-BETA_WINDOW:], bench_rets[-BETA_WINDOW:])
    values = {**(reg or {}), "resid": residual_momentum(rets, bench_rets)}
    rows = []
    for key, label, gloss, desc in BENCH_ROWS:
        value = values.get(key)
        if value is None:
            shown = "—"
        elif key == "alpha":
            shown = f"{value:+.1%}"
        elif key == "r2":
            shown = f"{1 - value:.2f}"
        elif key == "resid":
            shown = f"{value:+.2f}"
        else:
            shown = f"{value:.2f}"
        rows.append((label, gloss, shown, desc))
    rows.extend(_letf_rows(values.get("beta"), pairs))

    rel_1y = None
    if len(pairs) > 252:  # relative (1+r_stock)/(1+r_bench) − 1 over 1y
        rel_1y = (pairs[-1][1] / pairs[-253][1]) / (pairs[-1][2] / pairs[-253][2]) - 1
    chart = pairs[-MAX_CHART_BARS:]
    base_s, base_b = chart[0][1], chart[0][2]
    ratio = {d: (s / base_s) / (b / base_b) for d, s, b in chart}
    page_dates = [
        d.strftime("%Y-%m-%d")
        for d in bars["Date"].iloc[max(0, len(bars) - MAX_CHART_BARS) :]
    ]
    rs = [ratio.get(d) for d in page_dates]
    return {
        "rows": rows,
        "meta": (f"{min(BETA_WINDOW, len(rets))}d regression · {len(pairs)}d aligned"),
        "rs": rs,
        "rel_1y": rel_1y,
    }


def _letf_rows(beta, pairs) -> list[tuple[str, str, str, str]]:
    """Leveraged-fund readout, appended when the regression smells leverage: effective
    leverage |β| ≥ 1.5, or inverse β ≤ −1. Rows compare what the ETF
    actually returned over the regression window against the compounded
    benchmark^β path — daily-rebalanced LETFs drift below that target as
    volatility compounds. The book's remedy (short both leveraged legs,
    park proceeds in a Treasury ETF) is a two-leg portfolio trade with
    short-leg rally risk — out of single-symbol scope; this reads the
    decay, it doesn't trade it."""
    if beta is None or not (abs(beta) >= LETF_BETA or beta <= -1):
        return []
    window = pairs[-BETA_WINDOW:]  # same window the β estimate reads
    realized = window[-1][1] / window[0][1] - 1
    levered = (window[-1][2] / window[0][2]) ** beta - 1
    return [
        (
            f"bench^{beta:.2g} path",
            "index leveraged by β",
            f"{levered:+.1%}",
            (
                "Compounded benchmark return raised to the effective leverage "
                f"β = {beta:.2f} over the regression window — the path a "
                "perfect daily-rebalanced leveraged fund would track"
            ),
        ),
        (
            "decay gap",
            "realized − bench^β",
            f"{realized - levered:+.1%}",
            (
                "Leveraged (inverse) ETFs rebalance daily and drift "
                "below their leverage target as volatility compounds — "
                "negative gap = decay. The research's exploit (short both "
                "leveraged legs, park in Treasuries) is portfolio-level — "
                "out of single-symbol scope"
            ),
        ),
    ]


def _watchlist_ranks(symbol: str) -> str:
    """Factor scorecard vs the watchlist: per-factor ranks plus the
    composite (demeaned ranks s_Ai = rank − (N+1)/2, averaged across
    factors; factors are value = book/market, momentum = 12-1, low-vol =
    inverse 252d vol, earnings momentum = SUE — value and momentum combine
    because they are negatively correlated). Symbols missing a factor
    average the rest."""
    factors = {"value": {}, "12-1 mom": {}, "low-vol": {}, "SUE": {}}
    for sym in symbols():
        try:
            bars = cached_bars(sym)
        except OSError:
            continue
        closes = _tr_closes(bars)
        pb = read_stats(sym).get("priceToBook")
        if isinstance(pb, (int, float)) and pb > 0:
            factors["value"][sym] = 1 / pb
        mom = _mom_12_1(closes)
        if mom is not None:
            factors["12-1 mom"][sym] = mom
        vol = annualized_vol(closes, 252)
        if vol:
            factors["low-vol"][sym] = 1 / vol
        score = sue([row[1] for row in read_eps(sym)])
        if score is not None:
            factors["SUE"][sym] = score

    parts, blended = [], {}
    for label, scores in factors.items():
        if not scores:
            continue
        ranked = sorted(scores, key=scores.get, reverse=True)
        for pos, sym in enumerate(ranked, 1):
            blended.setdefault(sym, []).append(pos - (len(ranked) + 1) / 2)
            if sym == symbol:
                parts.append(f"{label} {pos}/{len(ranked)}")
    if symbol in blended:
        scores = {sym: sum(v) / len(v) for sym, v in blended.items()}
        ranked = sorted(scores, key=scores.get, reverse=True)
        pos = next(i for i, s in enumerate(ranked, 1) if s == symbol)
        parts.append(f"composite {pos}/{len(ranked)} ({scores[symbol]:+.1f})")
    return " · ".join(parts)


SPARK_WINDOW = 60  # closes per landing sparkline
SPARK_W, SPARK_H = 120, 32


def _sparkline(closes: list[float]) -> str:
    """Inline SVG polyline of the last SPARK_WINDOW closes (no JS needed)."""
    values = closes[-SPARK_WINDOW:]
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    step = SPARK_W / (len(values) - 1)
    points = " ".join(
        f"{round(i * step, 1)},{round(SPARK_H - (v - lo) / span * SPARK_H, 1)}"
        for i, v in enumerate(values)
    )
    color = "#3fb950" if values[-1] >= values[0] else "#f85149"
    return (
        f'<svg width="{SPARK_W}" height="{SPARK_H}" '
        f'viewBox="0 0 {SPARK_W} {SPARK_H}">'
        f'<polyline fill="none" stroke="{color}" '
        f'stroke-width="1.5" points="{points}"/></svg>'
    )
