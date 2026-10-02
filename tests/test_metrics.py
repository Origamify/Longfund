"""Risk-math tests: hand-computed goldens over the buy-and-hold family."""

import statistics

import numpy as np
import pytest

from src.metrics import (
    annualized_vol,
    cdar,
    daily_returns,
    drawdown_series,
    expected_shortfall,
    historical_var,
    longest_underwater,
    regression_stats,
    residual_momentum,
    risk_snapshot,
    skewness,
    sue,
    ulcer_index,
)

# --- risk math (analysis page) ---


def test_daily_returns():
    assert daily_returns([100, 110, 99]) == pytest.approx([0.1, -0.1])


def test_annualized_vol_golden_and_window():
    # std of [0.1, -0.1, 0.060606] = 0.105945 → ×√252 = 1.6818
    assert annualized_vol([100, 110, 99, 105], 3) == pytest.approx(1.681826, abs=1e-4)
    assert annualized_vol([100, 110, 99, 105], 4) is None  # not enough returns


def test_drawdown_series():
    dd = drawdown_series([100, 110, 99, 105])
    assert dd[0] == 0.0
    assert dd == pytest.approx([0.0, 0.0, -0.1, -0.045455], abs=1e-6)


def test_ulcer_index_golden():
    # sqrt(mean([0, 0, 0.01, 0.002066])) = 0.054923 → 5.49%
    assert ulcer_index([100, 110, 99, 105]) == pytest.approx(5.4923, abs=1e-3)
    assert ulcer_index([1.0]) is None


def test_cdar_goldens_and_limits():
    dds = [0.0, 0.0, -0.1, -0.045455]
    assert cdar(dds) == pytest.approx(0.1)  # α=0.8: worst 1 of 4
    # 10 uniform −0.1 dds: any tail averages to 0.1; α=0 → mean dd, α=1 → max
    assert cdar([-0.1] * 10) == pytest.approx(0.1)
    assert cdar(dds, alpha=0.0) == pytest.approx(0.036364, abs=1e-6)
    assert cdar(dds, alpha=1.0) == pytest.approx(0.1)
    assert cdar([0.0, -0.1]) == pytest.approx(0.1)
    assert cdar([0.0]) is None  # < 2 observations
    # monotone up-curve: zero drawdowns everywhere
    assert cdar(drawdown_series([1, 2, 3])) == pytest.approx(0.0)


def test_expected_shortfall_golden_and_vs_var():
    rets = [-0.05 + 0.01 * i for i in range(20)]  # −5%..+14%
    # worst 1 of 20 (k = int(0.05·20)) = the −5% day
    assert expected_shortfall(rets) == pytest.approx(0.05)
    assert expected_shortfall([0.01] * 19) is None  # < 20 observations
    # ES ≥ VaR on the same sample (tail average vs quantile)
    closes = [100.0]
    for r in rets:
        closes.append(closes[-1] * (1 + r))
    assert expected_shortfall(rets) >= historical_var(closes)
    # wider tail: worst 5 of 100 (k = int(0.05·100)) → mean of that decile
    rets100 = [0.001 * i - 0.05 for i in range(100)]
    tail = rets100[:5]
    assert expected_shortfall(rets100) == pytest.approx(-sum(tail) / 5)


def test_historical_var():
    rets = [-0.05 + 0.01 * i for i in range(20)]  # distinct, ascending −5%..+14%
    closes = [100.0]
    for r in rets:
        closes.append(closes[-1] * (1 + r))
    # 5th pct of 20 obs: idx 0.95 → −0.05 + 0.95×0.01 = −0.0405 loss
    assert historical_var(closes) == pytest.approx(0.0405, abs=1e-6)
    assert historical_var([100, 110, 99, 105]) is None  # < 20 observations


def test_risk_snapshot_assembles_and_degrades():
    snap = risk_snapshot([100, 110, 99, 105])
    assert snap["bars"] == 4
    assert snap["max_dd"] == pytest.approx(-0.1)
    assert snap["current_dd"] == pytest.approx(-0.045455, abs=1e-6)
    assert snap["ulcer"] == pytest.approx(5.4923, abs=1e-3)
    assert snap["sharpe"] == pytest.approx(3.027012, abs=1e-4)  # buy & hold
    assert snap["sortino"] == pytest.approx(5.554637, abs=1e-4)
    assert snap["vol_63"] is None and snap["vol_252"] is None  # window too short
    assert snap["var_95"] is None
    # tail-shape keys: present, None until enough observations
    assert snap["best_day"] == pytest.approx(0.1)
    assert snap["worst_day"] == pytest.approx(-0.1)
    assert snap["skew"] is None  # < 20 returns
    assert snap["uw_max"] == 2  # 99 and 105 both sit under the 110 peak
    assert snap["es_95"] is None  # < 20 returns
    assert snap["cdar"] == pytest.approx(0.1)  # worst 1 of 4 dds
    # degenerate windows: no values, never raises
    empty = risk_snapshot([1.0])
    assert empty == {k: None for k in empty} | {"bars": 1}


# --- market-relative & tail-shape math ---


def test_regression_stats_perfect_fit():
    bench = [0.01, -0.02, 0.005, 0.015, -0.01, 0.02] * 5  # 30 pairs
    rets = [2 * m + 0.001 for m in bench]
    stats = regression_stats(rets, bench)
    assert stats["beta"] == pytest.approx(2.0)
    assert stats["alpha"] == pytest.approx(0.001 * 252)  # annualized
    assert stats["r2"] == pytest.approx(1.0)


def test_regression_stats_degenerate():
    assert regression_stats([0.01] * 30, [0.02] * 30) is None  # no bench var
    assert regression_stats([0.01] * 19, [0.02] * 19) is None  # < 20 pairs
    # period-4 returns vs period-2 bench: orthogonal → slope 0, R² 0
    bench = [0.01, -0.01] * 16
    rets = [0.01, 0.01, -0.01, -0.01] * 8
    stats = regression_stats(rets, bench)
    assert stats["beta"] == pytest.approx(0.0)
    assert stats["r2"] == pytest.approx(0.0)


def test_residual_momentum_matches_direct_ols():
    rng = np.random.default_rng(7)
    n = 1100
    bench = rng.normal(0.0005, 0.01, n).tolist()
    drift = rng.normal(0.001, 0.002, n).tolist()
    rets = [1.5 * b + e for b, e in zip(bench, drift)]
    out = residual_momentum(rets, bench, est_window=800)
    # independent computation: same-window OLS β, then formation residuals
    est = slice(n - (252 + 21 + 800), n - (252 + 21))
    beta = np.polyfit(bench[est], rets[est], 1)[0]
    form = slice(n - (252 + 21), n - 21)
    res = np.array(rets[form]) - beta * np.array(bench[form])
    assert out == pytest.approx(res.mean() / res.std(ddof=1))


def test_residual_momentum_needs_history_and_spread():
    bench = [0.01, -0.01] * 100
    rets = [1.5 * m for m in bench]
    assert residual_momentum(rets, bench) is None  # < est+formation+skip
    # dyadic floats keep the arithmetic exact: stock ≡ market scaled →
    # residuals are exactly zero → σ = 0 → None
    bench = [0.125, -0.0625] * 600
    rets = [1.5 * m for m in bench]
    assert residual_momentum(rets, bench) is None


def test_skewness_sign_and_degrades():
    assert skewness([0.01, -0.01] * 15) == pytest.approx(0.0, abs=1e-9)  # symmetric
    assert skewness([0.01] * 19 + [0.5]) > 0  # right tail
    assert skewness([-0.01] * 19 + [-0.5]) < 0  # left (crash) tail
    assert skewness([0.01] * 10) is None  # < 20 observations


def test_longest_underwater_runs():
    # runs below peak: bars 1-3 (under 100), then 5-8 (under 130)
    assert longest_underwater([100, 90, 80, 100, 99, 98, 97, 96, 120]) == 4
    assert longest_underwater([1, 2, 3, 4]) == 0  # never underwater
    assert longest_underwater([100.0]) is None


def test_sue_golden_and_degrades():
    # 9 quarters → YoY diffs [0.1, 0.1, 0.1, 0.1, 0.2]; SUE = 0.2/stdev
    eps = [1.00, 1.02, 1.04, 1.06, 1.10, 1.12, 1.14, 1.16, 1.30]
    assert sue(eps) == pytest.approx(0.20 / statistics.stdev([0.1] * 4 + [0.2]))
    assert sue([1, 2, 3]) is None  # < 5 diffs
    assert sue([1, 1, 1, 1, 1, 1, 1, 1, 1]) is None  # σ = 0
