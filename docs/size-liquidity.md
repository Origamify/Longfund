# Metric review — size & liquidity group (+ price context)

Reviewed against: Fama–French (size factor), the equity-factors research
(momentum × size interaction).

Group context: size and liquidity are style/grouping variables in the
research, not return signals in the research library. J&T: momentum
survives within
all size subsamples and size adds nothing once controlled for — "size is a
grouping variable more than a standalone signal." Liquidity enters only via
costs (turnover × cost killed or survived strategies in every backtesting
article) and as a listed style factor in the loadings-matrix taxonomy.

### `sharesOutstanding` — shares out
- what: common shares issued and outstanding.
- research: plumbing (market cap ÷ price); dilution watch.
- reference: n/a
- hover: "Common shares issued and outstanding"

### `fullTimeEmployees` — employees
- what: company-reported headcount.
- research: none — exists to denominate revenue per employee.
- reference: n/a
- hover: "Company-reported full-time headcount"

### `averageVolume` — avg volume
- what: 3-month average daily shares traded.
- research: liquidity is a style factor; trading costs scale inversely with
  it (J&T's cost discipline: 0.5% one-way; TSMOM: liquid contracts if
  anything *better* for the signal).
- reference: n/a; small caps < $1M dollar-volume/day get expensive fast
- hover: "Average daily shares traded (3 months) — liquidity is a style factor and trading costs scale inversely with it"

### `revenuePerEmployee` — revenue / employee
- what: TTM revenue ÷ headcount.
- research: none in the research library — a qualitative efficiency/intensity read.
  **Kept on owner preference.**
- reference: no research-library anchor; ~$200k–$2M/employee spans services →
  software (rule-of-thumb, not research)
- hover: "Trailing 12-month revenue ÷ headcount; derived, not reported — a rough labor-intensity read"

## Price context rows (`52w high` / `52w low`)

Rendered ahead of the valuation group from `fiftyTwoWeekHigh/Low` plus the
last close.

- what: trailing-year extreme prices and the close's distance from them.
- research: the 52-week-high *proximity* signal itself is not in this
  research library — treat as location context, not a factor.
- reference: n/a
- hover (high): "52-week high price · how far the last close sits below it — location context, not a ranked factor"
- hover (low): "52-week low price · how far the last close sits above it — location context, not a ranked factor"
