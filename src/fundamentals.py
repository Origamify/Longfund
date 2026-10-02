"""Fundamentals & fund-profile tables and row builders.

STAT_GROUPS / ETF_GROUPS curate the Yahoo `info` keys shown on the
symbol page (those keys curated by STAT_KEYS in src/market.py);
MARKET_REF holds the broad-market reference column. Pure formatting,
no I/O — rows are (label, gloss, value, market, desc) 5-tuples.
"""

from datetime import datetime
from itertools import pairwise

from src.metrics import sue

# fundamentals panel: (heading, [(load_stats key, label, inline gloss,
# _fmt_stat kind, hover description)]); keys are Yahoo `info` names
# curated by STAT_KEYS in src/market.py
STAT_GROUPS = [
    (
        "valuation",
        [
            (
                "marketCap",
                "market cap",
                "total value of all shares",
                "usd_big",
                "Total market value of all shares (price × shares). Size is a grouping variable in the research more than a signal — but know it: value tilts silently become small-cap bets",
            ),
            (
                "trailingPE",
                "P/E (ttm)",
                "price / last year's earnings",
                "x",
                "Price ÷ trailing 12-month EPS. Familiar but low-ranking in the research: value premia are measured on book/market, and earnings ratios add little beyond profitability",
            ),
            (
                "forwardPE",
                "P/E (fwd)",
                "price / expected next-year earnings",
                "x",
                "Price ÷ estimated next-12-months EPS — consensus-dependent; the estimate is the weak leg",
            ),
            (
                "priceToSalesTrailing12Months",
                "P/S",
                "price / last year's sales",
                "x",
                "Market cap ÷ trailing 12-month revenue. Sales matter to the research only inside gross profitability (turnover × margin) — as a price ratio this is a weak value proxy, useful mainly when there are no earnings to divide by",
            ),
            (
                "priceToBook",
                "P/B",
                "price / accounting book value",
                "x",
                "Price ÷ book value per share — the value ratio, inverted. The research sorts on its reciprocal, book/market, shown below",
            ),
            (
                "bookToMarket",
                "book/market",
                "book value / price",
                "x",
                (
                    "1 ÷ P/B — the value factor's actual sort variable (HML: high "
                    "minus low book-to-market, ≈0.40%/month since 1963; one of the "
                    "few factors that survives the multiple-testing critiques)"
                ),
            ),
            (
                "earningsYield",
                "earnings yield",
                "earnings per dollar invested",
                "pct",
                "1 ÷ P/E (ttm) — earnings bought per dollar per year. Comparable to rates; as a value signal the research finds it subsumed by profitability",
            ),
            (
                "fcfYield",
                "FCF yield",
                "free cash flow / price",
                "pct",
                "Free cash flow ÷ market cap. Cash yield of the business — context mostly: cash-flow value measures carry little predictive power beyond book/market and profitability",
            ),
            (
                "enterpriseToEbitda",
                "EV/EBITDA",
                "firm value / cash earnings",
                "x",
                "Enterprise value ÷ EBITDA — comparable across debt levels, the same leverage-neutrality the research builds into its profitability measure",
            ),
            (
                "enterpriseToRevenue",
                "EV/rev",
                "firm value / sales",
                "x",
                "Enterprise value ÷ trailing 12-month revenue — leverage-neutral scale read",
            ),
            (
                "trailingEps",
                "EPS (ttm)",
                "last year's profit per share",
                "usd",
                "Trailing 12-month earnings per share — the series the earnings-momentum metrics (SUE, surprise) are computed on",
            ),
            (
                "trailingAnnualDividendYield",
                "div yield",
                "dividends per dollar of price",
                "pct",
                "Trailing 12-month dividends ÷ current price — income context",
            ),
            (
                "payoutRatio",
                "payout",
                "share of earnings paid out",
                "pct",
                "Share of earnings paid out as dividends; 100%+ rarely lasts",
            ),
        ],
    ),
    (
        "profitability · growth",
        [
            (
                "grossMargins",
                "gross margin",
                "profit after production costs",
                "pct",
                "Gross profit ÷ revenue. The top line is where the research measures quality: gross profitability (gross profits ÷ assets = this × asset turnover) has value-like predictive power (0.52%/mo FF3 alpha since 1963) and explains most earnings-based anomalies",
            ),
            (
                "operatingMargins",
                "operating margin",
                "profit from core operations",
                "pct",
                "Operating income ÷ revenue. Below the gross line, expensed investments (R&D, ads) that raise future profits cut current margins — read with suspicion",
            ),
            (
                "profitMargins",
                "net margin",
                "bottom-line profit / sales",
                "pct",
                "Net income ÷ revenue — same caveat as operating margin, one step further down the statement",
            ),
            (
                "returnOnEquity",
                "ROE",
                "profit per dollar of equity",
                "pct",
                "Net income ÷ shareholder equity. The research's profitability measure (gross profits ÷ assets) explains most of what this says, without the leverage",
            ),
            (
                "returnOnAssets",
                "ROA",
                "profit per dollar of assets",
                "pct",
                "Net income ÷ total assets — efficiency read; largely subsumed by gross profitability",
            ),
            (
                "revenueGrowth",
                "revenue growth",
                "sales change vs last year",
                "pct",
                "Year-over-year revenue change. Growth is the other side of the valuation identity — context, not a ranked signal",
            ),
            (
                "earningsGrowth",
                "earnings growth",
                "profit change vs last year",
                "pct",
                "Year-over-year earnings change — context for P/E; the standardized version (SUE) is what predicts returns",
            ),
        ],
    ),
    (
        "balance · cash flow",
        [
            (
                "totalRevenue",
                "revenue (ttm)",
                "last year's total sales",
                "usd_big",
                "Trailing 12-month revenue",
            ),
            (
                "netIncomeToCommon",
                "net income",
                "last year's profit to shareholders",
                "usd_big",
                "Trailing 12-month net income to common — watch it against operating cash flow: earnings split into persistent cash flow and fast-reverting accruals",
            ),
            (
                "freeCashflow",
                "free cash flow",
                "cash flow left after capex",
                "usd_big",
                "Operating cash flow − capex; cash the business frees up",
            ),
            (
                "operatingCashflow",
                "op. cash flow",
                "cash generated by operations",
                "usd_big",
                "Cash generated by operations — the persistent leg of the earnings-quality split: cash-backed earnings persist (persistence ≈0.86), accrual-backed earnings mostly vanish within 1–3 years",
            ),
            (
                "totalCash",
                "total cash",
                "cash and near-cash held",
                "usd_big",
                "Cash and short-term investments on the balance sheet",
            ),
            (
                "totalDebt",
                "total debt",
                "short- and long-term debt",
                "usd_big",
                "Short- plus long-term debt — the leverage that amplifies everything else on this page",
            ),
            (
                "netDebt",
                "net debt",
                "debt minus cash on hand",
                "usd_big",
                "Total debt − total cash; what is owed beyond the cash pile",
            ),
            (
                "currentRatio",
                "current ratio",
                "near-term assets vs bills",
                "num",
                "Current assets ÷ current liabilities. When receivables and inventory grow without matching liabilities, earnings are accrual-heavy — the earnings-quality anomaly's signature (the accrual hedge returned +10.4% in its first year, positive 28 of 30 years)",
            ),
            (
                "debtToEquity",
                "debt / equity",
                "debt per dollar of equity",
                "dex",
                "Total debt ÷ shareholder equity — leverage context",
            ),
        ],
    ),
    (
        "size",
        [
            (
                "sharesOutstanding",
                "shares out",
                "shares issued",
                "cnt",
                "Common shares issued and outstanding",
            ),
            (
                "fullTimeEmployees",
                "employees",
                "full-time headcount",
                "int",
                "Company-reported full-time headcount",
            ),
            (
                "averageVolume",
                "avg volume",
                "shares traded per day",
                "cnt",
                (
                    "Average daily shares traded (3 months) — liquidity is a "
                    "style factor and trading costs scale inversely with it"
                ),
            ),
            (
                "revenuePerEmployee",
                "revenue / employee",
                "sales per employee",
                "usd_big",
                "Trailing 12-month revenue ÷ headcount; derived, not reported",
            ),
        ],
    ),
]

# ETF fund-profile groups: swapped in for STAT_GROUPS when the
# stats say quoteType == ETF — funds have no earnings, only costs, size,
# distributions, and pricing vs the basket
ETF_GROUPS = [
    (
        "fund",
        [
            (
                "category",
                "category",
                "what the fund holds",
                "str",
                "Yahoo's fund category — which sector/asset-class rotation bucket this ETF is a candidate for",
            ),
            (
                "fundFamily",
                "family",
                "issuer",
                "str",
                "Fund family / issuer",
            ),
            (
                "totalAssets",
                "AUM",
                "assets under management",
                "usd_big",
                "Total net assets in the fund — viability and liquidity at a glance",
            ),
            (
                "navPrice",
                "NAV",
                "value of the underlying basket",
                "usd",
                "Net asset value per share — what the underlying basket is worth",
            ),
            (
                "averageVolume",
                "avg volume",
                "shares traded per day",
                "cnt",
                (
                    "Average daily shares traded (3 months) — liquidity is a "
                    "style factor and trading costs scale inversely with it"
                ),
            ),
        ],
    ),
    (
        "costs · income",
        [
            (
                "annualExpenseRatio",
                "expense ratio",
                "annual fee share",
                "pct",
                (
                    "Annual fee as a share of assets — the one guaranteed drag "
                    "on fund returns, compounding like negative alpha. The ETF's "
                    "whole pitch is being cheap; verify it here"
                ),
            ),
            (
                "yield",
                "dist. yield",
                "distributions per dollar",
                "pct",
                "The fund's reported distribution yield (trailing) — trust the computed cash yield below when they disagree",
            ),
            (
                "trailingAnnualDividendYield",
                "cash yield (ttm)",
                "cash distributions / price",
                "pct",
                (
                    "Trailing 12-month cash distributions ÷ current price, "
                    "computed from the actual payment series"
                ),
            ),
        ],
    ),
]

# market-reference column: approximate broad-market value per Yahoo
# stat key (US large-cap norms — medians of the ~S&P 500 universe, not
# sector medians). Context for reading a stock's number, not a verdict;
# keys without a useful market norm (EPS, AUM, headcount, absolute
# balance-sheet totals) show an em dash
MARKET_REF = {
    "trailingPE": "≈ 16×",
    "forwardPE": "≈ 16×",
    "priceToSalesTrailing12Months": "≈ 2×",
    "priceToBook": "≈ 2.5×",
    "bookToMarket": "≈ 0.4×",
    "earningsYield": "≈ 6%",
    "fcfYield": "≈ 4%",
    "enterpriseToEbitda": "≈ 10×",
    "enterpriseToRevenue": "≈ 2×",
    "trailingAnnualDividendYield": "≈ 1.5%",
    "payoutRatio": "≈ 35%",
    "grossMargins": "≈ 38%",
    "operatingMargins": "≈ 12%",
    "profitMargins": "≈ 9%",
    "returnOnEquity": "≈ 17%",
    "returnOnAssets": "≈ 6%",
    "revenueGrowth": "≈ 5%",
    "earningsGrowth": "≈ 8%",
    "currentRatio": "≈ 1.6",
    "debtToEquity": "≈ 0.8×",
    "annualExpenseRatio": "≈ 0.4%",
}


def _fmt_stat(value, kind: str) -> str:
    """One fundamentals value → display string; missing → em dash."""
    if value is None:
        return "—"
    if kind == "pct":
        return f"{value:.2%}"
    if kind == "pct_signed":
        return f"{value:+.2%}"
    if kind == "x":
        return f"{value:.1f}×"
    if kind == "x2":
        return f"{value:.2f}×"
    if kind == "num_signed":
        return f"{value:+.2f}"
    if kind == "dex":  # Yahoo reports debt/equity as a percentage
        return f"{value / 100:.2f}×"
    if kind == "usd":
        return f"${value:,.2f}"
    if kind in {"usd_big", "cnt"}:  # compact T/B/M, with/without $
        prefix = "$" if kind == "usd_big" else ""
        for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
            if abs(value) >= div:
                return f"{prefix}{value / div:,.2f}{unit}"
        return f"{prefix}{value:,.0f}"
    if kind == "int":
        return f"{value:,.0f}"
    return str(value)  # strings: sector, industry, name


def _eps_rows(eps: list) -> list[tuple[str, str, str]]:
    """Earnings-momentum readouts: SUE from quarterly EPS, plus the latest
    analyst surprise (the CJL sibling measure — announcement vs estimate).
    [] when history is too short for either."""
    rows = []
    score = sue([row[1] for row in eps])
    if score is not None:
        rows.append(
            (
                "SUE",
                "size of the earnings surprise",
                f"{score:+.2f}",
                "—",
                (
                    "Standardized unexpected earnings: latest quarter "
                    "vs 4 quarters ago, ÷ σ of the last 8 quarterly surprises. "
                    "The earnings-momentum criterion — the market digests "
                    "earnings news slowly and the effect persists on a "
                    "~6-month horizon; decile ranks are what the research "
                    "trades"
                ),
            )
        )
    if eps:
        date, reported, estimate = eps[-1]
        if isinstance(estimate, (int, float)) and estimate != 0:
            rows.append(
                (
                    f"last surprise ({date})",
                    "actual vs estimate",
                    f"{(reported - estimate) / abs(estimate):+.1%}",
                    "—",
                    (
                        "Reported vs estimated EPS at the latest announcement — "
                        "the event-level sibling of SUE. The research's timing "
                        "evidence says earnings-news corrections concentrate in "
                        "the days around announcements, then fade — context, "
                        "not a standing signal"
                    ),
                )
            )
    return rows


def _stat_groups(stats: dict, is_etf: bool = False) -> list[tuple[str, list]]:
    """Fundamentals groups: STAT_GROUPS, or the ETF fund-profile groups
    when quoteType says ETF."""
    groups = []
    base = ETF_GROUPS if is_etf else STAT_GROUPS
    groups.extend(
        (
            heading,
            [
                (
                    label,
                    gloss,
                    _fmt_stat(stats.get(key), kind),
                    MARKET_REF.get(key, "—"),
                    desc,
                )
                for key, label, gloss, kind, desc in rows
            ],
        )
        for heading, rows in base
    )
    return groups


_DIV_HISTORY_ROWS = 6  # recent ex-dates listed under the summaries

_DIV_GAP_WINDOW = 8  # last N+1 payments feed the median-gap cadence read

_DIV_CADENCE = {1: "annual", 2: "semiannual", 4: "quarterly", 12: "monthly"}


def _fmt_div_amount(value: float) -> str:
    """Per-share cash: 4 decimals under a dollar (quarterly drips),
    2 at/above it."""
    return f"${value:,.4f}" if value < 1 else f"${value:,.2f}"


def _distribution_rows(divs: list) -> list:
    """Distributions group rows from cached dividend history — rows are
    ["YYYY-MM-DD", cash per share] ascending (written by the stats sweep,
    read via `read_divs`). Windows are payment-aligned, not calendar-day
    buckets: a 365-day bucket on quarterly data catches 4 or 5 payments
    depending on today's date, so cadence comes from the median gap
    between recent ex-dates and TTM/prior are the last N / previous N
    payments for that N. Then the recent ex-date payments, newest first."""
    payments = [(datetime.fromisoformat(row[0]).date(), float(row[1])) for row in divs]
    recent = payments[-(_DIV_GAP_WINDOW + 1) :]
    gaps = sorted(later[0] - earlier[0] for earlier, later in pairwise(recent))
    median_gap = gaps[len(gaps) // 2].days if gaps else 0
    per_year = min(52, round(365 / median_gap)) if median_gap > 0 else 0
    rows = []
    if per_year:
        cadence = _DIV_CADENCE.get(per_year, f"{per_year}/yr")
        rows.append(
            (
                "cadence",
                "payments per year",
                cadence,
                "—",
                "Median gap between recent ex-dates, as payments per year",
            )
        )
        ttm = payments[-per_year:]
        rows.append(
            (
                "ttm cash/share",
                "last 12 months",
                _fmt_div_amount(sum(amount for _, amount in ttm)),
                "—",
                "Sum of the last N per-share distributions (N = cadence)",
            )
        )
        prior = payments[-2 * per_year : -per_year]
        if prior and sum(amount for _, amount in prior) > 0:
            growth = (
                sum(amount for _, amount in ttm) / sum(amount for _, amount in prior)
                - 1
            )
            rows.append(
                (
                    "ttm growth",
                    "vs prior 12 months",
                    f"{growth:+.1%}",
                    "—",
                    "Last N distributions vs the N before them — payment-aligned, so special dividends and timing shifts show up honestly",
                )
            )
    for ex_date, cash in payments[-_DIV_HISTORY_ROWS:][::-1]:
        rows.append(
            (
                ex_date.strftime("%Y-%m-%d"),
                "ex-date · cash/share",
                _fmt_div_amount(cash),
                "—",
                "Ex-dividend date and the per-share cash paid",
            )
        )
    return rows
