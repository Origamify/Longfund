# Metric review — distributions group (payment-aligned)

Reviewed against: the fund-income research (K&S ch. 4) and the factor
literature generally — which carries **no dividend-strategy evidence**.

Group context: none of the research library's articles studies distribution income
as a signal; the distribution panel's research basis is methodological —
payment-aligned windows (cadence from the median ex-date gap, TTM = last N
payments) rather than calendar buckets, which is the same
look-ahead/alignment discipline the backtesting articles demand. The ETF
chapter's income note ("the fund's reported yield — trust the computed
cash yield when they disagree") is the one direct anchor.

### `cadence` — payments per year
- what: median gap between recent ex-dates, expressed as payments/year.
- research: none (mechanics). Needed to make TTM windows honest.
- reference: 1/2/4/12 = annual/semiannual/quarterly/monthly
- hover: "Median gap between recent ex-dates, as payments per year"

### `ttm cash/share` — last 12 months
- what: sum of the last N per-share distributions (N = cadence).
- research: the computed counterpart to the fund-reported yield row.
- reference: compare ÷ price vs the reported `dist. yield` row
- hover: "Sum of the last N per-share distributions (N = cadence)"

### `ttm growth` — vs prior 12 months
- what: last N payments ÷ the N before them − 1.
- research: none in the research library; income-growth context for long holders.
- reference: dividend growers vs cutters — no research-library anchor; sign is the
  coarse read
- hover: "Last N distributions vs the N before them — payment-aligned, so special dividends and timing shifts show up honestly"

### ex-date history rows
- what: recent ex-dates with per-share cash, newest first.
- research: none (record-keeping).
- reference: —
- hover: "Ex-dividend date and the per-share cash paid"
