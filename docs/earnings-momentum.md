# Metric review — earnings momentum (SUE, surprise)

Reviewed against: the earnings-momentum construction (Latane–Jegadeesh
SUE), Sloan-era earnings-quality research (announcement timing), and the
momentum family's evidence standards (Jegadeesh–Titman).

Group context: K&S's earnings-momentum construction is **exactly** the SUE
longfund computes: latest quarterly EPS vs four quarters ago, ÷ σ of the
unexpected earnings over the last 8 quarters; decile long-short; holding
period "typically 6 months, with diminishing returns beyond." The library
carries no fresh return table for SUE specifically (the K&S catalog is
descriptive), so hovers should claim the construction, not invent
magnitudes. The accruals article supplies the timing fact: earnings-based
corrections cluster around subsequent announcements (40% of the Sloan hedge
in the 12 days around the next four announcements).

### `SUE` — standardized unexpected earnings
- what: (E − E₍₋₄₎) ÷ σ of the last ≤8 quarterly YoY differences; needs ≥5
  differences and σ > 0.
- research: the earnings-momentum criterion — same formula as K&S's §3.2;
  ranking variable for a ~6-month-horizon decile trade. Distinct signal
  family from price momentum (slower information diffusion through
  earnings). Drives the scorecard's SUE factor.
- reference: decile rank vs the universe is what trades; |SUE| ≳ 2 is a
  clean surprise by construction
- hover: "Standardized unexpected earnings: latest quarter vs 4 quarters ago, ÷ σ of the last 8 quarterly surprises. The earnings-momentum criterion — the market digests earnings news slowly and the effect persists on a ~6-month horizon; decile ranks are what the research trades"

### `last surprise` — actual vs estimate
- what: (reported − estimate) ÷ |estimate| at the latest announcement.
- research: the event-level sibling of SUE (announcement vs consensus).
  The research library's timing evidence (Sloan) says the payoff of
  earnings-quality corrections clusters in the ~12 days around
  announcements — so the number matters most *at* the event, then decays.
- reference: ±5% vs estimate = a normal beat/miss; ±20%+ = a big surprise
- hover: "Reported vs estimated EPS at the latest announcement — the event-level sibling of SUE. The research's timing evidence says earnings-news corrections concentrate in the days around announcements, then fade — context, not a standing signal"

## Data note

Both rows need quarterly EPS history with estimates (`.eps.json`); they
degrade to placeholders when short — correct behavior, keep. SUE's σ window
(≤8 quarters, min 5 differences) matches K&S's "last 8 quarters" exactly.
