# Metric review — longfund metrics vs the research literature

Longfund is a nice research tool for stocks and ETFs — and nothing
else. These files document the metrics its research pages show.

Fine-grained review of every metric shown on the site against the reference
literature (papers and books listed under Research anchors below), with
the changes below applied to the code. Per metric: what it is, its
standing in the research, a reference range or median, and the hover text
users see (the `title=` copy in `STAT_GROUPS` / `ETF_GROUPS` / `RISK_ROWS` /
`BENCH_ROWS` in `src/`).

## Files

| file | covers |
|---|---|
| [valuation.md](valuation.md) | valuation ratios + MARKET_REF column |
| [profitability.md](profitability.md) | margins, ROE/ROA, growth (GP/A evidence) |
| [balance-cashflow.md](balance-cashflow.md) | balance sheet, cash flow, accruals read |
| [size-liquidity.md](size-liquidity.md) | size, headcount, volume, revenue/employee, 52w price context |
| [etf-profile.md](etf-profile.md) | fund profile, expense ratio, yields, reported returns |
| [risk.md](risk.md) | vol, Sharpe/Sortino, drawdown family, VaR/ES, skew |
| [market-relative.md](market-relative.md) | β, α, selectivity, residual momentum, LETF readout, RS |
| [momentum.md](momentum.md) | trailing strip, 12-1 momentum, SMA overlays |
| [earnings-momentum.md](earnings-momentum.md) | SUE, analyst surprise |
| [scorecard.md](scorecard.md) | watchlist factor ranks + composite |
| [distributions.md](distributions.md) | dividend cadence, TTM cash, history |

## Applied changes

The review's decisions are already in the code (docs now serve as the
metric reference):

- **Deleted:** PEG, fund-reported 3y/5y returns — gone from the tables,
  `MARKET_REF`, and the stats fetch list.
- **Renamed:** `resid. 12-1 mom` → `resid. momentum`.
- **Hovers refreshed** to the reviewed copy in each file; trailing-strip
  chips and the scorecard rank line gained tooltips.
- **Kept on owner preference:** `revenue / employee`.

**Candidate adds (documented, not built):** Calmar ratio (CAGR/|MDD| 3y,
Chan's bar ≥ 1) in risk.md; true GP/A blocked by missing COGS/total-assets
in Yahoo `info` (profitability.md).

## Research anchors used throughout

- Novy-Marx 2013 (GP/A): 0.52%/mo FF3 alpha (t = 4.49); value/profitability
  correlation −0.57; 50/50 blend Sharpe 0.85 vs market 0.34.
- Jegadeesh–Titman 1993 (momentum): 12/3 skip-week 1.49%/mo (t = 4.28);
  reversal by month 36; −40.8% in 1927–40 regimes.
- Fama–French HML: 0.40%/mo (t = 3.25); HML + MOM survive Harvey–Liu–Zhu's
  multiple-testing adjustments (recommended t-hurdle > 3.0, not 2.0).
- Sloan 1996 (accruals): +10.4% yr-1 hedge (t = 4.71), positive 28/30
  years; persistence 0.855 (cash) vs 0.765 (accruals).
- Chan (Machine Trading 2017): Calmar ≥ 1; Sharpe's Gaussian blind spot;
  VaR/ES as non-Gaussian tail stand-ins; MDD-duration as a headline metric.
- Bailey–López de Prado 2014 (DSR): skew/kurtosis inflate Sharpe; trial
  count inflates the best backtest.
- K&S 151 Strategies: SUE formula (8-quarter σ), 12-1 formation with skip,
  low-vol decile sort (126–252d), rank-level multifactor blend, alpha
  rotation + R² selectivity (1y estimation), MA filter 100–200d, LETF
  daily-rebalance drift.

## In the research library but deliberately out of product scope

The research library also covers order-flow imbalance (seconds–minutes),
option positioning / put-call ratios (days–weeks), and the variance risk
premium (VIX² − realized, peaking at a quarterly horizon). All are
short-horizon or derivatives-data signals — wrong regime for a daily-data,
long-horizon research workbench; DSR itself is a backtest-meta-metric
(a backtest concern, not a research-page one). Correctly absent;
recorded here so the omission reads as a decision, not an oversight.
