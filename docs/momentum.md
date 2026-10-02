# Metric review — price momentum (strip, 12-1, chart overlays)

Reviewed against: Jegadeesh–Titman 1993 (price momentum), the
equity-factors research (MA signals), K&S ch. 4 (MA filter, dual
momentum).

Group context: the strongest cross-sectional evidence in the research library.
J&T 1965–89: winner−loser decile spread **1.49%/mo (t = 4.28)** for 12-3
with skip-week — surviving a Bonferroni correction across all 32 J/K
configurations; profits come from delayed reaction to *firm-specific*
information (zero-cost beta ≈ −0.08), not risk. Caveats the hovers should
carry: profits **peak at month 12 and partially reverse by month 36**;
January loses ~7% on average; and in mean-reverting regimes (1927–40) the
36-month cumulative was **−40.8%** — momentum is conditional on the market
not strongly reversing.

### trailing strip — `1m`
- what: last-month total return.
- research: this is the *skip* zone — momentum constructions deliberately
  skip the most recent month (short-term reversal / liquidity effects).
  Keep it as a reversal context chip, not a momentum read.
- reference: short-horizon mean reversion lives here — don't extrapolate
- hover: "Total return over the last month — the zone momentum constructions deliberately skip (short-term reversal noise lives here)"

### trailing strip — `3m` / `6m`
- what: 3- and 6-month total returns.
- research: valid formation lengths (J ∈ {3, 6, 9, 12}; 6/6 earned
  0.95%/mo, 1.10%/mo with skip-week).
- reference: formation horizons the research actually tests
- hover (3m): "Total return over the last 3 months — a momentum formation length the research tests (J ∈ {3,6,9,12})"
- hover (6m): "Total return over the last 6 months — a momentum formation length the research tests (6-month formation earned 0.95–1.10%/mo winner−loser)"

### trailing strip — `ytd` / `1y`
- what: calendar-year and trailing-1-year total returns.
- research: 1y is the canonical formation; ytd is convenience.
- reference: 12-month formation is the strongest J&T configuration
- hover (ytd): "Total return since January 1 — calendar convenience, not a research window"
- hover (1y): "Trailing 1-year total return — the canonical momentum formation window"

### 12-1 momentum (scorecard factor + `_mom_12_1`)
- what: close 1 month ago ÷ close 12 months ago − 1 (total-return series).
- research: the canonical sort variable — formation 12, skip 1; the 12/3
  skip-week spread is the research library's headline (1.49%/mo, t = 4.28). Drives
  the scorecard's momentum factor.
- reference: winner decile = top 10% of the ranked universe; reversal risk
  in years 2–3 after formation
- hover: "Classic 12-1 momentum: return from 12 months ago to 1 month ago, skipping the reversal-prone recent month. The research's strongest cross-sectional signal (winners−losers ≈1.5%/mo since 1965) — but it reverses in years 2–3 and dies in sharp mean-reverting regimes"

### SMA 50 / SMA 200 (chart overlays)
- what: 50- and 200-day simple moving averages on the chart.
- research: the MA filter of the rotation strategies — buy top-decile only
  if price > MA(T′), T′ typically **100–200 days**; the dual-momentum gate
  (broad index above its MA, else park in an uncorrelated ETF). The book's
  own commentary: single-stock MA crossovers are "deemed unscientific" —
  their footing comes from large cross-sections, so read these as regime
  filters, not signals.
- reference: price > SMA200 = the long-only gate convention
- hover (overlay legend): "50/200-day moving averages — the trend filter of the rotation research: entries gated on price above a 100–200 day MA (dual momentum parks in an uncorrelated asset when the broad index is below it)"

### drawdown + RS overlays (chart)
- what: underwater curve and relative-strength line vs the S&P.
- research: visual counterparts of the risk card's dd family and the
  relative-momentum read (see risk.md / market-relative.md).
- reference: —
- hover: covered by their panels' rows

### landing sparkline
- what: 60-bar inline SVG on the watchlist.
- research: none — pure UI.
- reference: —
