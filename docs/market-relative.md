# Metric review — market-relative panel (β / α / R² / residual momentum)

Reviewed against: K&S ch. 4 (alpha rotation, R² selectivity, LETF short
pair), the residual-momentum construction (Blitz–Huij–Martens), Chan
(factor models — dumb vs smart beta), and the quant-evaluation research
(beta is cheap, alpha is the scarce thing).

Group context: this is the panel where the research library's ETF chapter puts its
research weight. **Alpha rotation** ranks ETFs on Jensen's α (regression
intercept, estimation typically 1 year of daily/weekly returns).
**Selectivity = 1 − R²** (Amihud–Goyenko 2013; Garyn-Tal 2014): overweight
funds whose returns the factors *don't* explain — the worked scheme sorts
into R² quintiles, then α sub-quintiles, buying lowest-R²/highest-α and
selling the mirror. **Residual momentum** runs 12-1 momentum on FF3-regression
residuals (36-month estimation, α dropped over the formation window,
εmean/σ risk-adjusted). Longfund's versions are honest single-factor
proxies: β/α/R² on the S&P 500 only, residual momentum purged by that β
alone, 252-day estimation window.

### `beta` — beta
- what: OLS slope of daily returns on the S&P 500 (252d window).
- research: the "dumb beta" — cheaply available via index instruments,
  what risk management hedges away, not what you research. Needed as the
  purge input for residual momentum and the LETF trigger.
- reference: 1.0 = market; |β| ≥ 1.5 or β ≤ −1 triggers the LETF readout
- hover: "OLS slope of the stock's daily returns on the S&P 500's over the regression window — the unforecast market exposure risk management would hedge away, not the thing you're researching"

### `alpha` — α (ann.)
- what: regression intercept × 252 — annualized return beyond the market's
  contribution.
- research: the scarce commodity — alpha rotation strategies rank on
  exactly this quantity (Jensen's α). Caveats to keep in the hover:
  single-factor here (not FF3 as in the research), and Chan's warning that
  incidental alpha decays; also the base the residual purge builds on.
- reference: persistently positive α over 1y+ is rare; the research library's
  rotation schemes trade the cross-section of it
- hover: "Regression intercept × 252: annualized return left over after the market's contribution. Alpha rotation strategies rank on exactly this; single-factor here, not the Fama–French alpha of the research — and the base the residual purge builds on"

### `r2` → selectivity (1−R²)
- what: 1 − R² of the regression — share of returns the market doesn't
  explain.
- research: Amihud–Goyenko / Garyn-Tal **selectivity** — the prized pair
  is low R² *with* positive α (idiosyncratic skill); high R² = buying the
  index with extra steps. The research library's own ranking scheme quintile-sorts on
  R² then α.
- reference: 0 = pure index clone; higher = more idiosyncratic
- hover: "1 − R² of the regression: the share of returns the market does not explain. Research calls this selectivity (Amihud–Goyenko, Garyn-Tal) and overweights it — low R² with positive α is the prized pair; high R² = buying the index with extra steps"

### `resid` — resid. momentum
- what: risk-adjusted 12-1 momentum on market-purged residuals (daily
  mean/σ units).
- research: the strategy catalog's residual momentum — momentum on the
  stock-specific component, constructed to dodge the factor exposures raw
  momentum carries. Research version purges FF3 over 36 months; ours purges
  the market factor alone over 3y estimation, same 12-1 formation and skip.
  `resid. momentum` (the 12-1 detail lives in the hover)
- reference: sign and magnitude vs the watchlist; daily mean/σ units (not
  annualized)
- hover: "Risk-adjusted 12-1 momentum on market-purged residuals — the stock-specific part of momentum, with the market factor's contribution removed (single-factor purge, a proxy for the research's Fama–French version). In daily mean/σ units"

### RS ratio chart + `vs S&P 1y`
- what: relative-strength line (stock ÷ benchmark, rebased) and the 1-year
  relative return chip.
- research: the visual form of relative momentum — sector/ETF rotation
  ranks on cumulative relative performance over 6–12 months.
- reference: rising RS line = the rotation candidate
- hover (chip): "Total return ÷ the S&P 500's total return over the last year, minus 1 — the relative-momentum read rotation strategies rank on"

## LETF readout (conditional)

`bench^β path` and `decay gap` rows appear when the regression smells
leverage (|β| ≥ 1.5, or β ≤ −1):

- what: compounded benchmark^β target vs the fund's realized return over
  the window; gap = decay.
- research: K&S §4.5 — LETFs rebalance daily to constant leverage, which
  "can result in a negative drift in the long term" (volatility drag). The
  book's exploit — short both leveraged legs, park proceeds in Treasuries —
  carries "significant downside risk in the short term if one of the short
  ETF legs has a sizable positive return"; Chan's Kelly side-note makes the
  same point (Russell 3× funds vs Kelly leverage ≈ 1.8).
- reference: negative gap = decay, as expected for daily-rebalanced LETFs
- hover (bench^β path): "Compounded benchmark return raised to the effective leverage β over the regression window — the path a perfect daily-rebalanced leveraged fund would track"
- hover (decay gap): "Leveraged (inverse) ETFs rebalance daily and drift below their leverage target as volatility compounds — negative gap = decay. The research's exploit (short both leveraged legs, park in Treasuries) is portfolio-level — out of single-symbol scope"

## Note on window conventions

The research library's estimation convention is "typically 1 year, daily or weekly
returns" (alpha rotation / selectivity) — our 252d window matches. The
residual-momentum construction wants a 36-month β estimation (our
`est_window = 756` in `residual_momentum` matches); both conventions are
already right. Longer R² windows "worth considering for monthly returns"
do not bind for daily data.
