# Metric review — watchlist factor scorecard

Reviewed against: the multifactor rank-level combination research
(K&S approach 2), Fama–French (HML), Jegadeesh–Titman (momentum),
Novy-Marx 2013 (combination evidence), Harvey–Liu–Zhu (survivor list).

Group context: the scorecard implements K&S's **rank-level multifactor
combination** exactly: demeaned ranks s_Ai = rank − (N+1)/2, averaged
across factors. The research library's stated reason: value and momentum
are usually
*negatively correlated*, so combining "can add value." The factor choices
all trace to research-library evidence:

| factor | sort variable | research-library evidence |
|---|---|---|
| value | book/market (1/P/B) | HML 0.40%/mo, t = 3.25; HLZ survivor |
| 12-1 mom | formation 12m, skip 1m | 1.49%/mo spread, t = 4.28; HLZ survivor (MOM) |
| low-vol | inverse 252d vol | bottom-decile σ sort, 126–252d formation |
| SUE | standardized unexpected earnings | K&S earnings-momentum criterion |

This is the product's research core, and it is the most research-faithful
object on the site.

### per-factor ranks (`value 3/7 · 12-1 mom 2/7 · …`)
- what: watchlist-internal rank per factor.
- research: ranks, not z-scores, are the trading objects in every
  cross-sectional construction in the strategy catalog (deciles = ranks).
- reference: top/bottom decile of the ranked universe is what the research
  longs/shorts — with a small watchlist read top-2/bottom-2 as the tails
- hover: "Watchlist rank on this factor — cross-sectional rank is what the factor research trades (long top decile, short bottom)"

### composite (`composite 1/7 (+1.8)`)
- what: mean demeaned rank across available factors.
- research: K&S approach 2 (demeaned ranks averaged); value×momentum
  negative correlation is the canonical reason. Novy-Marx's version of the
  same logic: value (corr −0.57 with profitability) blended 50/50 earned
  both spreads at Sharpe 0.85 vs 0.34, with no losing 5-year window —
  combination is where the risk-adjusted gains live, not in any single
  factor.
- reference: with N symbols the composite spans ±(N−1)/2; persistently
  top-ranked across *different* factors is the robust read
- hover: "Mean of demeaned factor ranks (value, 12-1 momentum, low-vol, SUE) — the research's rank-blending recipe. Factors are combined because they are weakly or negatively correlated: blends earn the same spreads at lower risk than any single factor"

### noted limitations (documentation, not defects)
- **Universe = the watchlist.** All factor evidence is cross-sectional over
  a broad universe; ranks over 5–15 symbols are indicative, not deciles.
  The hover above already frames ranks as watchlist-internal.
- **Missing quality leg.** The research library's other headline blend is
  value + GP/A (Novy-Marx). GP/A can't be computed from Yahoo `info`
  (no COGS/assets — see profitability.md); gross margin is the visible
  proxy today.
- **Single-factor purge.** Residual momentum here purges the market only;
  the construction in the strategy catalog purges FF3 (see market-relative.md).
- **Survivor discipline.** HML and MOM are the two factors Harvey–Liu–Zhu
  name as clearing all multiple-testing adjustments — the scorecard's four
  factors are all defensible members of that short list's neighborhood
  (low-vol and SUE are strategy-catalog strategies without fresh t-stats; treat
  them as diversifiers, not headline premia).
