# Metric review — buy-and-hold risk card

Reviewed against: Chan's performance-metric list (Sharpe #2, max drawdown
#4, max drawdown duration #5; Calmar bar ≥ 1; VaR/ES as non-Gaussian
stand-ins), Bailey–López de Prado 2014 (deflated Sharpe), Harvey–Liu–Zhu
2016 (multiple testing), Kelly-sizing risk management, and long-horizon
trend-following evidence.

Group context: the research library judges risk metrics by one question — *do they
capture tail risk without a Gaussian assumption?* Chan's verdict: Sharpe
implicitly assumes Gaussian returns; max drawdown does not, hence his bar
"backtest Calmar ≥ 1" and his prescription to size leverage so drawdown is
tolerable "over a period containing several financial crises" (his worked
counterexample: SPY-like stats imply Kelly leverage 5, but one −20% Black
Monday wipes the account — the Gaussian assumption is the failure point).
The DSR article adds the estimation critique: short samples and
skewed/kurtotic returns *inflate* any Sharpe you compute.

### `vol_63` — ann. vol 63d
- what: annualized std of the last 63 daily returns (3-month read).
- research: freshness read on the anomaly's sort variable (which uses 6–12
  months); mostly a "what changed lately" number.
- reference: S&P 500 long-run ≈ 15–20% (approximation, not from the
  research library);
  single stocks 25–60%
- hover: "Annualized std of the last 63 daily returns — a 3-month read. The low-volatility anomaly sorts on the 6–12 month version"

### `vol_252` — ann. vol 252d
- what: annualized std of the last 252 daily returns.
- research: the low-volatility anomaly's exact sort variable — long bottom
  decile by historical σ (6–12 mo, 126–252 days), short top decile;
  previously-low-vol portfolios beat high-vol ones risk-adjusted. Also the
  scorecard's low-vol factor.
- reference: formation window 126–252 days per the strategy catalog; lower is the
  anomaly's long side
- hover: "Annualized std of the last 252 daily returns. The low-volatility anomaly sorts on exactly this: previously low-vol stocks beat high-vol ones risk-adjusted — volatility is not paid for here"

### `sharpe` — sharpe (hold)
- what: annualized mean ÷ vol of daily returns, buy-and-hold.
- research: the research library's most-cited and most-criticized statistic. It
  assumes Gaussian returns; fat tails and skew inflate the estimate (DSR
  corrects with skewness and kurtosis). Anchors from the research library: market
  Sharpe ≈ 0.34 (Novy-Marx sample); a *truly significant* factor averages
  ≈ 0.44 (Harvey–Liu–Zhu structural estimate); diversified multi-asset
  trend following > 1.
- reference: single-instrument buy-and-hold of 0.3–0.5 is normal market
  exposure; > 1 for one instrument over a window usually means the sample
  is kind, not that it will persist
- hover: "Annualized mean ÷ volatility of daily returns, for simply holding. Read with skewness: Sharpe treats both tails the same and non-normal returns inflate it (the deflated-Sharpe critique). For scale: the whole market ran ≈0.34 over 1963–2010"

### `sortino` — sortino (hold)
- what: like Sharpe but only downside days count as risk.
- research: half-way correction toward the asymmetry the research library keeps
  flagging; not separately evidenced in the research library.
- reference: ≈ 1.5–2× the Sharpe for equity-like series
- hover: "Like Sharpe but only downside days count as risk — the pain an investor actually experiences"

### `max_dd` — max drawdown
- what: worst peak-to-trough decline over the cached window.
- research: Chan's non-Gaussian tail number — one of his five headline
  metrics, the denominator of his Calmar bar (CAGR/|MDD| ≥ 1 over 3 years),
  and the constraint he sizes leverage against ("over a period containing
  several financial crises"). Trend followers' own drawdowns ran to ~25%
  even for the good strategies (HOP).
- reference: ≤ CAGR keeps Calmar ≥ 1; bear-market magnitudes: −30–55% for
  equities is historically ordinary
- hover: "Worst peak-to-trough decline over the window — the risk number that ends strategies and the one leverage gets sized against. Chan's bar: keep |CAGR ÷ max drawdown| ≥ 1"

### `current_dd` — vs peak
- what: distance below the running peak.
- research: entry-point context — how underwater a buyer today starts.
- reference: n/a
- hover: "How far the last close sits below the window's peak — how underwater a buyer today starts"

### `var_95` — VaR 1d 95%
- what: 5th-percentile daily loss (historical simulation).
- research: Chan's list of non-Gaussian risk stand-ins (with ES) for
  equalizing tail risk across portfolio components. A threshold, not a
  tail measure.
- reference: exceeded ~1 day in 20 by construction
- hover: "5th percentile of daily losses (historical simulation): exceeded ~1 day in 20. A threshold, not a tail measure — pair with ES for how bad breaches get"

### `es_95` — ES 1d 95%
- what: mean of the worst 5% of daily returns.
- research: "ES sizes the losses VaR only counts" — Chan's preferred
  non-Gaussian stand-in for targeting equal tail risk per component.
- reference: typically 1.2–1.5× the 95% VaR for equity-like tails
- hover: "Mean of the worst 5% of daily returns — how bad the breaches are, which VaR's threshold doesn't say. The non-Gaussian tail measure the research prefers for equalizing risk"

### `ulcer` — ulcer index
- what: RMS of drawdowns (depth × duration of pain).
- research: not in the research library; consistent with its drawdown-over-
  variance stance.
- reference: single-digit % = calm; > 20% = a war story
- hover: "RMS of drawdowns — penalizes deep, long-lived pain, unlike volatility, which treats a quick dip and a long grind the same"

### `cdar` — CDaR 80%
- what: mean of the worst 20% of drawdown observations.
- research: Chekhlov–Uryasev–Zabarankin directly; same family as
  Chan's drawdown preference — averages the tail of the underwater curve
  instead of one sample.
- reference: between average drawdown and MDD, closer to MDD at 80%
- hover: "Mean of the worst 20% of drawdown observations — max drawdown is one sample; this averages the bad tail of the underwater curve"

### `skew` — skewness
- what: adjusted Fisher–Pearson skewness of daily returns.
- research: the correction term in the DSR formula (with kurtosis) — the
  quantity that makes naive Sharpe estimates lie. Negative skew = crashes
  are the tail; equity momentum's crash risk lives here.
- reference: single stocks typically slightly negative; more negative =
  worse Sharpe inflation
- hover: "Skewness of daily returns; negative means the tail is the downside — the crash risk Sharpe ignores and the term the deflated-Sharpe correction uses"

### `best_day` / `worst_day`
- what: observed one-day extremes.
- research: the realized tails behind VaR/ES; Chan's Black-Monday point —
  a single −20% bar is what breaks Gaussian-derived leverage.
- reference: worst_day ≈ −2 to −3× vol_63's daily σ is ordinary
- hover (best): "Best single-day return in the window — the right tail's observed edge"
- hover (worst): "Worst single-day return in the window — the observed left tail behind the VaR/ES numbers; one such bar is what breaks Gaussian leverage math"

### `uw_max` — longest underwater
- what: most consecutive bars below a fresh peak.
- research: max-drawdown-**duration** — #5 on Chan's five-metric list;
  drawdown depth and time are separate risks.
- reference: years, not months, for buy-and-hold equity after big tops
- hover: "Most consecutive bars below a fresh peak — drawdown duration; Ulcer covers depth, this covers time"

## Candidate add (not in product): Calmar

CAGR ÷ |max drawdown| over the most recent 3 years — Chan's recommended
Sharpe replacement precisely because it carries no Gaussian assumption, with
his explicit bar: ≥ 1. Would slot naturally next to `sharpe`. (MAR — same
ratio over full history — is ill-defined: drawdowns grow mechanically with
track-record length.)
