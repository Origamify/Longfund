# Metric review — ETF fund profile group

Reviewed against: K&S ch. 4 (ETF strategies), the equity-factors research
(momentum/rotation parameter conventions).

Group context: the research library's ETF chapter premise is the ETF as the *cheap
vehicle* — rotation exposure "without having to buy or sell a large number
of underlying stocks." Costs (expense ratio) are the one number the fund
fully controls; everything else (reported returns, reported yield) is
marketing or accounting until independently computed. The rotation
strategies (sector momentum T = 6–12 mo, MA filter T′ = 100–200 days, dual
momentum, alpha rotation, selectivity) define what the fund profile is
*for*: identifying rotation candidates and their costs.

### `category` — category
- what: Yahoo's fund category.
- research: names the rotation bucket (sector/asset class) this ETF is a
  candidate for.
- reference: n/a
- hover: "Yahoo's fund category — which sector/asset-class rotation bucket this ETF is a candidate for"

### `fundFamily` — family
- what: issuer.
- research: none (provenance).
- reference: n/a
- hover: "Fund family / issuer"

### `totalAssets` — AUM
- what: net assets in the fund.
- research: viability and liquidity glance; closure risk when tiny.
- reference: n/a; <$50M = closure-risk zone (rule of thumb)
- hover: "Total net assets in the fund — viability and liquidity at a glance"

### `navPrice` — NAV
- what: per-share value of the underlying basket.
- research: premium/discount context vs market price.
- reference: n/a
- hover: "Net asset value per share — what the underlying basket is worth"

### `averageVolume` — avg volume
- same as the stock-side row.
- reference: n/a
- hover: "Average daily shares traded (3 months) — liquidity is a style factor and trading costs scale inversely with it"

### `annualExpenseRatio` — expense ratio
- what: annual fee as a share of assets.
- research: the research library's core ETF fact — the vehicle's whole pitch is being
  cheap; the fee is a guaranteed drag compounding like negative alpha.
- reference: ≈ 0.4% median; broad-index funds ≤ 0.10%; anything ≥ 0.75%
  needs a story
- hover: "Annual fee as a share of assets — the one guaranteed drag on fund returns, compounding like negative alpha. The ETF's whole pitch is being cheap; verify it here"

### `yield` — dist. yield (reported)
- what: fund's self-reported distribution yield.
- research: unverified until computed — trust the cash-yield row when they
  disagree (return-of-capital, uneven timing).
- reference: n/a
- hover: "The fund's reported distribution yield (trailing) — trust the computed cash yield below when they disagree"

### `trailingAnnualDividendYield` — cash yield (ttm, computed)
- what: actual TTM distributions ÷ price, from the payment series.
- research: the honest version of the yield above.
- reference: n/a
- hover: "Trailing 12-month cash distributions ÷ current price, computed from the actual payment series"

## LETF readout (conditional rows)

The `bench^β path` + `decay gap` rows appear when |β| ≥ 1.5 or β ≤ −1 — see
market-relative.md for their review (K&S §4.5 short-pair / volatility-drag
mechanism).
