"""Buy-and-hold analytics: the risk/drawdown/tail family, market-relative
regression math, and earnings-momentum helpers for the research pages.
No I/O.

Strategy backtesting, walk-forward, and cost models do not live here —
this product researches instruments, not trades.

References: Chan (drawdowns/VaR/ES), Chekhlov–Uryasev–Zabarankin (CDaR),
Blitz–van Vliet (low volatility), Blitz–Huij–Martens (residual momentum),
Amihud–Goyenko (R² selectivity), Livnat–Mendenhall (SUE).
"""

import math

TRADING_DAYS = 252


# --- risk math for the research page ---


def daily_returns(closes: list[float]) -> list[float]:
    """Bar-over-bar returns; len = len(closes) − 1."""
    return [closes[t] / closes[t - 1] - 1 for t in range(1, len(closes))]


def annualized_vol(closes: list[float], window: int) -> float | None:
    """Std of the last `window` daily returns × √252; None if too short."""
    rets = daily_returns(closes)[-window:]
    if len(rets) < window:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var * TRADING_DAYS)


def drawdown_series(closes: list[float]) -> list[float]:
    """Underwater curve: close ÷ running peak − 1 (≤ 0), bar 0 = 0."""
    out, peak = [], -math.inf
    for close in closes:
        peak = max(peak, close)
        out.append(close / peak - 1)
    return out


def ulcer_index(closes: list[float]) -> float | None:
    """RMS of drawdowns in percent — depth *and* duration of pain."""
    dds = drawdown_series(closes)
    if len(dds) < 2:
        return None
    return math.sqrt(sum(d * d for d in dds) / len(dds)) * 100


def cdar(drawdowns: list[float], alpha: float = 0.8) -> float | None:
    """Conditional drawdown at risk: mean of the worst (1−α)·100% of
    drawdown observations along the equity path (Chekhlov–Uryasev–
    Zabarankin) — the tail-average cousin of
    max drawdown (α = 1 → MDD, α = 0 → average drawdown). Positive
    magnitude; None under 2 observations."""
    n = len(drawdowns)
    if n < 2:
        return None
    k = max(1, round((1 - alpha) * n))
    worst = sorted(drawdowns)[:k]
    return -sum(worst) / k


def expected_shortfall(rets: list[float], level: float = 0.05) -> float | None:
    """Mean of the worst `level`·100% of daily returns, as a positive loss
    magnitude (ES sizes the losses VaR only counts). None under 20
    observations."""
    n = len(rets)
    if n < 20:
        return None
    k = max(1, int(level * n))
    tail = sorted(rets)[:k]
    return -sum(tail) / k


def skewness(rets: list[float]) -> float | None:
    """Adjusted Fisher-Pearson skewness of daily returns; None under 20
    observations. Negative = crashes are the tail (winner-decile −0.82,
    WML −4.70 monthly — the number Sharpe ignores)."""
    n = len(rets)
    if n < 20:
        return None
    mean = sum(rets) / n
    m2 = sum((r - mean) ** 2 for r in rets) / n
    m3 = sum((r - mean) ** 3 for r in rets) / n
    if m2 <= 0:
        return None
    return (m3 / m2**1.5) * math.sqrt(n * (n - 1)) / (n - 2)


def longest_underwater(closes: list[float]) -> int | None:
    """Longest run of bars strictly below the running peak, in trading days
    — drawdown duration (Ulcer covers depth, this covers time)."""
    if len(closes) < 2:
        return None
    peak, run, worst = -math.inf, 0, 0
    for close in closes:
        if close >= peak:  # at a fresh (or equal) high: out of the water
            peak, run = close, 0
        else:
            run += 1
            worst = max(worst, run)
    return worst


def sue(eps: list[float]) -> float | None:
    """Standardized unexpected earnings from quarterly EPS in
    chronological order: SUE = (E − E 4 quarters ago) ÷ σ of the last ≤8
    quarterly YoY differences. Needs ≥5 differences and σ > 0."""
    diffs = [eps[i] - eps[i - 4] for i in range(4, len(eps))]
    if len(diffs) < 5:
        return None
    sample = diffs[-8:]
    mean = sum(sample) / len(sample)
    var = sum((d - mean) ** 2 for d in sample) / (len(sample) - 1)
    std = math.sqrt(var)
    return diffs[-1] / std if std > 0 else None


def historical_var(closes: list[float], level: float = 0.05) -> float | None:
    """Historical-simulation VaR: interpolated `level` quantile of daily
    returns, as a positive loss magnitude. None under 20 observations."""
    rets = sorted(daily_returns(closes))
    if len(rets) < 20:
        return None
    idx = level * (len(rets) - 1)
    lo, hi = math.floor(idx), math.ceil(idx)
    quantile = rets[lo] + (rets[hi] - rets[lo]) * (idx - lo)
    return -quantile


def risk_snapshot(closes: list[float]) -> dict:
    """Buy-and-hold risk card for a close series: vol (63d/252d), Sharpe,
    Sortino, max/current drawdown, 1-day 95% VaR, Ulcer Index, tail shape
    (skew, best/worst day, longest underwater run). Values the window is
    too short for are None — pages render them as placeholders. Pass a
    total-return series (adjusted closes) for long-horizon honesty."""
    snapshot = {
        "vol_63": annualized_vol(closes, 63),
        "vol_252": annualized_vol(closes, 252),
        "max_dd": None,
        "current_dd": None,
        "var_95": historical_var(closes),
        "es_95": None,
        "ulcer": ulcer_index(closes),
        "cdar": None,
        "sharpe": None,
        "sortino": None,
        "skew": None,
        "best_day": None,
        "worst_day": None,
        "uw_max": longest_underwater(closes),
        "bars": len(closes),
    }
    if len(closes) > 2:
        rets = daily_returns(closes)
        n = len(rets)
        mean = sum(rets) / n
        var = sum((r - mean) ** 2 for r in rets) / (n - 1)
        std = math.sqrt(var)
        downside = math.sqrt(sum(min(r, 0.0) ** 2 for r in rets) / n)
        dds = drawdown_series(closes)
        snapshot["max_dd"] = min(dds)
        snapshot["current_dd"] = dds[-1]
        snapshot["sharpe"] = mean / std * math.sqrt(TRADING_DAYS) if std else 0.0
        snapshot["sortino"] = (
            mean / downside * math.sqrt(TRADING_DAYS) if downside else 0.0
        )
        snapshot["best_day"] = max(rets)
        snapshot["worst_day"] = min(rets)
        snapshot["skew"] = skewness(rets)
        snapshot["es_95"] = expected_shortfall(rets)
        snapshot["cdar"] = cdar(dds)
    return snapshot


# --- market-relative math (regression per Amihud–Goyenko / Blitz–Huij–
# Martens; skew is why Sharpe understates pain) ---


def regression_stats(rets: list[float], bench_rets: list[float]) -> dict | None:
    """Single-factor OLS r = α + β·r_M over aligned daily returns: {"beta",
    "alpha" (annualized), "r2"}. None under 20 pairs or when either side has
    no variance."""
    pairs = list(zip(rets, bench_rets))
    n = len(pairs)
    if n < 20:
        return None
    mean_r = sum(r for r, _ in pairs) / n
    mean_m = sum(m for _, m in pairs) / n
    cov = sum((r - mean_r) * (m - mean_m) for r, m in pairs)
    var_r = sum((r - mean_r) ** 2 for r, _ in pairs)
    var_m = sum((m - mean_m) ** 2 for _, m in pairs)
    if var_r <= 0 or var_m <= 0:
        return None
    beta = cov / var_m
    return {
        "beta": beta,
        "alpha": (mean_r - beta * mean_m) * TRADING_DAYS,
        "r2": cov * cov / (var_r * var_m),
    }


def residual_momentum(
    rets: list[float],
    bench_rets: list[float],
    est_window: int = 756,  # β estimation: 3y (36 months, as in the research)
    formation: int = 252,  # classic 12-1 formation, trading days
    skip: int = 21,  # skip the most recent month
) -> float | None:
    """Risk-adjusted 12-1 momentum on market-purged residuals (single-
    factor purge, not FF3). β is estimated on the `est_window` bars
    before the formation window; residuals ε = r − β·r_M over months
    t−12..t−1 (α dropped); returns εmean/σ in daily units —
    risk-adjusted (daily mean/σ), not annualized."""
    if len(rets) != len(bench_rets) or len(rets) < est_window + formation + skip:
        return None
    cut = -(formation + skip)
    est = regression_stats(
        rets[cut - est_window : cut], bench_rets[cut - est_window : cut]
    )
    if est is None:
        return None
    form_r = rets[cut:-skip]
    form_m = bench_rets[cut:-skip]
    eps = [r - est["beta"] * m for r, m in zip(form_r, form_m)]
    mean = sum(eps) / len(eps)
    var = sum((e - mean) ** 2 for e in eps) / (len(eps) - 1)
    std = math.sqrt(var)
    return mean / std if std else None
