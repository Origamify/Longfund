# Metric review — profitability & growth group

Reviewed against: Novy-Marx 2013 (gross profitability), Fama–French
(factor construction).

Group context: this is the panel the research library cares most about on the
fundamentals side. **Gross profitability (GP/A = gross profits ÷ assets)**
earns 0.31%/mo raw (t = 2.49) but **0.52%/mo FF3 alpha (t = 4.49)** — it
has "roughly the same power as book-to-market" and *explains* most
earnings-based anomalies (ROA, E/P, asset turnover). Everything below the
gross line is progressively polluted by expensed investments (R&D, ads)
that raise future profits while cutting current margins. The DuPont split
matters: GP/A = (sales/assets) × (gross profits/sales) — turnover drives
the returns, margins identify "good growth."

### `grossMargins` — gross margin
- what: gross profit ÷ revenue.
- research: one of the two DuPont legs of GP/A (margin × turnover).
  GP/A works among large liquid stocks (top-quintile spread 26 bp/mo,
  beating value's 14 bp) and internationally. Yahoo gives no COGS or total
  assets, so the exact GP/A can't be computed here — gross margin is the
  closest observable leg.
- reference: ≈ 38% median (large-cap); top quintile ≈ 50%+
- hover: "Gross profit ÷ revenue. The top line is where the research measures quality: gross profitability (gross profits ÷ assets = this × asset turnover) has value-like predictive power (0.52%/mo FF3 alpha since 1963) and explains most earnings-based anomalies"

### `operatingMargins` — operating margin
- what: operating income ÷ revenue.
- research: below the gross line — expensed investments (R&D, advertising)
  that raise *future* profits cut current margins here, so it reads low
  exactly when the company is investing well.
- reference: ≈ 12% median
- hover: "Operating income ÷ revenue. Below the gross line, expensed investments (R&D, ads) that raise future profits cut current margins — read with suspicion"

### `profitMargins` — net margin
- what: net income ÷ revenue.
- research: same caveat one step further down the statement; also carries
  leverage and one-offs.
- reference: ≈ 9% median
- hover: "Net income ÷ revenue — same caveat as operating margin, one step further down the statement"

### `returnOnEquity` — ROE
- what: net income ÷ shareholder equity.
- research: subsumed: GP/A explains most of what ROE says *without the
  leverage distortion* (equity shrinks as debt grows, inflating ROE).
  Novy-Marx lists ROA-type anomalies among those GP/A absorbs.
- reference: ≈ 17% median
- hover: "Net income ÷ shareholder equity. The research's profitability measure (gross profits ÷ assets) explains most of what this says, without the leverage"

### `returnOnAssets` — ROA
- what: net income ÷ total assets.
- research: the closest *shape* to GP/A (assets-scaled) but built on
  bottom-line earnings; GP/A explains the ROA anomaly.
- reference: ≈ 6% median
- hover: "Net income ÷ total assets — efficiency read; largely subsumed by gross profitability"

### `revenueGrowth` — revenue growth
- what: YoY revenue change.
- research: growth is the other side of the valuation identity — context,
  not a ranked signal. (Valuation ratios already price it.)
- reference: ≈ 5% median nominal
- hover: "Year-over-year revenue change. Growth is the other side of the valuation identity — context, not a ranked signal"

### `earningsGrowth` — earnings growth
- what: YoY earnings change.
- research: context for P/E; no independent factor standing. The
  *standardized* version of earnings change (SUE) is what predicts — see
  earnings-momentum.md.
- reference: ≈ 8% median
- hover: "Year-over-year earnings change — context for P/E; the standardized version (SUE) is what predicts returns"

## Candidate add (not in product): GP/A

The research library's strongest fundamentals metric is computable only
with COGS and total assets, which Yahoo's `info` does not expose (balance-sheet fetch
would be needed). If ever added: quintile sorts, rebalanced on prior fiscal
year, non-financials; FF3 alpha 0.52%/mo (t = 4.49); correlation −0.57 with
value, so a 50/50 B/M + GP/A blend earned 0.71%/mo at Sharpe 0.85 vs the
market's 0.34, with no losing 5-year window 1963–2010 — the single best
"combine two panels" fact in the research library.
