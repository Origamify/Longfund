# Metric review — valuation group

Reviewed against: Fama–French (HML/SMB), Novy-Marx 2013 (gross
profitability), Harvey–Liu–Zhu (factor-zoo critique).

Group context: the research library's value evidence is built on **book-to-market**
(HML, 0.40%/mo 1963–2010, t = 3.25; one of the few factors — with MOM — that
clears Harvey–Liu–Zhu's multiple-testing adjustments). Earnings-based and
cash-flow ratios rank below it: Novy-Marx finds GP/A "roughly the same power
as book-to-market" while "earnings and free-cash-flow measures carry much
less." So the honest ordering of this panel is: B/M first, everything else
context.

### `marketCap` — market cap
- what: price × shares; the size of the company.
- research: size is a **grouping variable, not a signal** — J&T find momentum
  spreads survive within all size subsamples; HML/SMB construction neutralizes
  size to isolate value. Its practical use: know when a value tilt is
  silently a small-cap bet.
- reference: n/a (grouping); mega > $200B, large $10–200B, small < $2B
- hover: "Total market value of all shares (price × shares). Size is a grouping variable in the factor research more than a signal — but know it: value tilts can silently become small-cap bets"

### `trailingPE` — P/E (ttm)
- what: price ÷ trailing 12-month EPS.
- research: familiar but low-ranking: value premia are measured on
  book/market; E/P carries little beyond profitability (Novy-Marx).
- reference: market median ≈ 16× (long-run; bull markets run 20×+)
- hover: "Price ÷ trailing 12-month EPS. Familiar but low-ranked in the research: value premia are measured on book/market, and earnings ratios add little beyond profitability"

### `forwardPE` — P/E (fwd)
- what: price ÷ consensus next-year EPS.
- research: not a research factor; the estimate is the weak leg (analyst
  forecasts, revisions).
- reference: ≈ 16×, usually below trailing P/E
- hover: "Price ÷ estimated next-12-months EPS — consensus-dependent; the estimate is the weak leg"

### `priceToSalesTrailing12Months` — P/S
- what: market cap ÷ trailing revenue.
- research: sales enter the research only inside gross profitability
  (turnover × margin); as a price ratio it is a weak value proxy. One
  legitimate use: the fallback ratio when there are no earnings to divide by.
- reference: ≈ 2× median; > 10× = priced for perfection
- hover: "Market cap ÷ trailing 12-month revenue. Sales matter to the research only inside gross profitability (turnover × margin) — as a price ratio this is a weak value proxy, useful mainly when there are no earnings to divide by"

### `priceToBook` — P/B
- what: price ÷ book value per share.
- research: the reciprocal of the actual sort variable (B/M). Showing both
  directions is redundant; the research direction is book/market.
- reference: ≈ 2.5× median
- hover: "Price ÷ book value per share — the value ratio, inverted. The research sorts on its reciprocal, book/market, shown below"

### `bookToMarket` — book/market
- what: 1 ÷ P/B — the value factor's sort variable.
- research: **the** value metric. HML 0.40%/mo (t = 3.25) 1963–2010;
  survives Harvey–Liu–Zhu's Bonferroni/Holm/BHY adjustments (HML and MOM are
  the named survivors). Conditioned on profitability it improves to
  0.54%/mo (t = 5.01). Drives the scorecard's value factor.
- reference: market median ≈ 0.4×; top-30% B/M (NYSE breakpoint) = the value leg
- hover: "1 ÷ P/B — the value factor's actual sort variable (HML: high minus low book-to-market, ≈0.40%/month since 1963; one of the few factors that survives the multiple-testing critiques)"

### `earningsYield` — earnings yield
- what: 1 ÷ P/E — earnings bought per dollar per year.
- research: comparable to interest rates (useful real-world context), but as
  a value signal it is subsumed by book/market + profitability (Novy-Marx:
  E/P carries little incremental power; GP/A explains the E/P anomaly).
- reference: ≈ 6% median; compare vs the 10-y Treasury
- hover: "1 ÷ P/E (ttm) — earnings bought per dollar per year. Comparable to rates; as a value signal the research finds it subsumed by profitability"

### `fcfYield` — FCF yield
- what: free cash flow ÷ market cap.
- research: cash-flow *levels* matter inside the accruals split (Sloan 1996),
  but the FCF **price ratio** carries little predictive power beyond
  book/market and profitability (Novy-Marx).
- reference: ≈ 4% median
- hover: "Free cash flow ÷ market cap. Cash yield of the business — context mostly: cash-flow value measures carry little predictive power beyond book/market and profitability"

### `enterpriseToEbitda` — EV/EBITDA
- what: enterprise value ÷ EBITDA.
- research: not a ranked factor, but it embodies the research library's favorite
  design choice — leverage-neutral scaling, the same property Novy-Marx
  builds into GP/A (scale by assets, not equity).
- reference: ≈ 10× median
- hover: "Enterprise value ÷ EBITDA — comparable across debt levels, the same leverage-neutrality the research builds into its profitability measure"

### `enterpriseToRevenue` — EV/rev
- what: EV ÷ trailing revenue.
- research: leverage-neutral scale read; no independent evidence.
- reference: ≈ 2× median
- hover: "Enterprise value ÷ trailing 12-month revenue — leverage-neutral scale read"

### `trailingEps` — EPS (ttm)
- what: trailing 12-month earnings per share.
- research: the input series SUE is computed on (quarterly version). Pure
  plumbing.
- reference: n/a
- hover: "Trailing 12-month earnings per share — the series the earnings-momentum metrics (SUE, surprise) are computed on"

### `trailingAnnualDividendYield` — div yield
- what: trailing dividends ÷ price.
- research: income context; the research library has no dividend-yield factor evidence.
- reference: ≈ 1.5% median (S&P)
- hover: "Trailing 12-month dividends ÷ current price — income context"

### `payoutRatio` — payout
- what: share of earnings paid out as dividends.
- research: sustainability screen for the income read; no factor evidence.
- reference: ≈ 35% median; 100%+ rarely lasts
- hover: "Share of earnings paid out as dividends; 100%+ rarely lasts"

## MARKET_REF column review

The ≈ values are approximate US large-cap medians (static, Yahoo-universe
era), **not** from the research library — it carries factor *returns*, not
ratio medians. Keep the column but keep the header caveat ("context, not a
verdict"). One correction: P/B ≈ 2.5× and B/M ≈ 0.4× are consistent
reciprocals — fine. No changes recommended beyond flagging staleness
(verify medians against the live universe occasionally).
