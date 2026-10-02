"""Yahoo Finance daily bars + fundamentals: fetch at most once per day per
symbol, cache to disk.

The only network call site in the codebase — swap providers here and
nowhere else. Fetching happens in `refresh_all` (launch-time sweep and
`--sweep-only`), `add_symbol`'s verification, and the exporter's warm
pass (`refresh_symbol`); every request path reads the disk-only twins
(`cached_bars`/`read_stats`/`read_eps`/`read_divs`/
`cached_benchmark`). This product computes no signals.
"""

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # project root, not src/
CACHE_DIR = DATA_DIR / "cache"

# First-run seed: 12 mega-caps across sectors and geographies (US,
# Europe, Asia); written to watchlist.json when that file doesn't exist yet
DEFAULT_WATCHLIST = [
    "AAPL",  # US · consumer tech
    "JPM",  # US · banking
    "CAT",  # US · industrials
    "SHEL",  # UK/NL · energy
    "SAP",  # DE · software
    "NVO",  # DK · pharma
    "ASML",  # NL · semiconductors
    "NSRGY",  # CH · staples (Nestlé, ADR)
    "ZURVY",  # CH · insurance (Zurich, ADR)
    "TSM",  # TW · semiconductors (ADR)
    "TM",  # JP · autos (ADR)
    "INFY",  # IN · IT services (ADR)
]
WATCHLIST_PATH = DATA_DIR / "watchlist.json"  # the whole watchlist, persisted

# Market-relative context only: S&P 500 bars for beta/R²/relative-strength,
# never a watchlist member or analysis subject
BENCHMARK = "^GSPC"

_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-^]{1,8}$")

_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]

# fundamentals snapshot: the Yahoo `info` keys kept (labels/formatting live
# in the tools); anything not listed here is dropped at the cache boundary
STAT_KEYS = (
    "shortName",
    "sector",
    "industry",
    # valuation
    "marketCap",
    "trailingPE",
    "forwardPE",
    "priceToSalesTrailing12Months",
    "priceToBook",
    "enterpriseToEbitda",
    "enterpriseToRevenue",
    "trailingEps",
    "payoutRatio",
    # profitability & growth
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "returnOnEquity",
    "returnOnAssets",
    "revenueGrowth",
    "earningsGrowth",
    # balance sheet & cash flow
    "totalRevenue",
    "netIncomeToCommon",
    "totalCash",
    "totalDebt",
    "freeCashflow",
    "operatingCashflow",
    "currentRatio",
    "debtToEquity",
    # price context
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    # size
    "sharesOutstanding",
    "fullTimeEmployees",
    "averageVolume",
    # ETF lens: classification + fund profile; absent keys drop
    # per-symbol, so stocks are untouched
    "quoteType",
    "category",
    "fundFamily",
    "annualExpenseRatio",
    "totalAssets",
    "navPrice",
    "yield",
)


def symbols() -> list[str]:
    """Effective watchlist: symbols persisted in watchlist.json, ordered,
    deduplicated; a missing file is seeded with DEFAULT_WATCHLIST."""
    return list(dict.fromkeys(_read_watchlist()))


def add_symbol(raw: str, verify: bool = True) -> str:
    """Validate a ticker, optionally verify it on Yahoo, persist it.
    Returns the upper symbol. ValueError on bad format or duplicate,
    OSError when `verify` and Yahoo has no data for it (also warms the
    bars cache on success). `verify=False` (the `--offline` path)
    persists on format + duplicate checks alone — unverified."""
    symbol = raw.strip().upper()
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ValueError(f"not a ticker: {raw!r}")
    if symbol in symbols():
        raise ValueError(f"already watchlisted: {symbol}")
    if verify:
        load_bars(symbol)
    listed = _read_watchlist()
    listed.append(symbol)
    _save_json(WATCHLIST_PATH, listed)
    return symbol


def refresh_symbol(symbol: str) -> str | None:
    """Fetch-if-stale warm-up for one symbol: bars always, stats + EPS
    unless it's the benchmark or an ETF. The shared body of
    `refresh_all` and the exporter's warm pass. Returns an error string
    or None; never raises — a warm-enough cache makes even a failed
    fetch survivable (`load_bars` only fails with nothing on disk)."""
    try:
        load_bars(symbol)
        if symbol != BENCHMARK:  # stats/eps never raise, garnish anyway
            stats = load_stats(symbol)
            if stats.get("quoteType") != "ETF":  # ETFs have no EPS
                load_eps(symbol)
    except OSError as err:
        return str(err)
    return None


def refresh_all(progress=None) -> None:
    """Sweep the benchmark + watchlist once via `refresh_symbol`, so
    every later read in the process is disk-only (launch-time warm-up).
    One bad ticker or Yahoo hiccup costs one progress line, never the
    launch. `progress(symbol, i, total, error)` fires per symbol,
    `error` a str or None."""
    queue = list(dict.fromkeys([BENCHMARK, *symbols()]))
    for i, symbol in enumerate(queue, 1):
        error = refresh_symbol(symbol)
        if progress:
            progress(symbol, i, len(queue), error)


def _read_watchlist() -> list:
    """Watchlist from disk; a missing or corrupt file is (re)seeded."""
    try:
        listed = json.loads(WATCHLIST_PATH.read_text())
    except (OSError, ValueError):
        listed = None
    if not isinstance(listed, list):
        listed = list(DEFAULT_WATCHLIST)
        _save_json(WATCHLIST_PATH, listed)
    return listed


def download_bars(symbol: str) -> pd.DataFrame:
    """Full daily history from Yahoo, oldest first. Raises OSError on any
    failure (empty payload or a provider error, e.g. rate limiting)."""
    try:
        df = yf.download(
            symbol, period="max", interval="1d", auto_adjust=False, progress=False
        )
    except Exception as err:  # yfinance raises provider-specific errors
        raise OSError(f"fetch failed for {symbol}: {err}") from err
    if df is None or df.empty:
        raise OSError(f"no data for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.reset_index()[_COLUMNS]


def load_bars(symbol: str) -> pd.DataFrame:
    """Cached daily bars for symbol; refreshes once per calendar day."""
    path = CACHE_DIR / f"{symbol.upper()}.csv"
    if not _fresh_today(path):
        try:
            _save(path, download_bars(symbol))
        except OSError:
            if not path.exists():
                raise  # nothing cached and nothing fetched: caller shows failure
    try:
        return _read_cache(path)
    except (OSError, ValueError):
        # corrupt cache: refetch once, then fail for real if still unreadable
        _save(path, download_bars(symbol))
        return _read_cache(path)


def cached_bars(symbol: str) -> pd.DataFrame:
    """Bars straight from disk, freshness irrelevant — pages and the
    exporter read this (the launch sweep warms them).

    Raises FileNotFoundError when no cache exists — callers hint at warming it.
    """
    return _read_cache(CACHE_DIR / f"{symbol.upper()}.csv")


def download_stats(symbol: str) -> dict:
    """Curated fundamentals snapshot (PE, margins, headcount, ...).

    Keeps STAT_KEYS only: finite numbers and non-empty strings; derives
    revenuePerEmployee and the TTM dividend yield from the dividend history
    (the info field's ADR rate is not per-ADR cash — e.g. ZURVY reported
    108% against a true ~5%). Raises OSError on any failure, like
    download_bars.
    """
    ticker = yf.Ticker(symbol)
    try:
        info = ticker.get_info()
    except Exception as err:  # yfinance raises provider-specific errors
        raise OSError(f"stats fetch failed for {symbol}: {err}") from err
    stats = {}
    for key in STAT_KEYS:
        value = info.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            if math.isfinite(value):
                stats[key] = value
        elif isinstance(value, str) and value:
            stats[key] = value
    if not stats:
        raise OSError(f"no stats for {symbol}")
    employees = stats.get("fullTimeEmployees")
    if employees and isinstance(stats.get("totalRevenue"), (int, float)):
        stats["revenuePerEmployee"] = stats["totalRevenue"] / employees
    _derive_value_stats(stats)
    if stats.get("quoteType") == "ETF" and "annualExpenseRatio" not in stats:
        try:  # yfinance's info omits it for ETFs; the scrape has it
            ratio = _fetch_expense_ratio(ticker)
        except OSError:
            ratio = None  # garnish: the panel shows its placeholder
        if ratio is not None:
            stats["annualExpenseRatio"] = ratio
    try:
        _derive_dividend_yield(stats, ticker, info, symbol)
    except OSError:
        pass  # dividends are garnish: stats survive without them
    return stats


def _derive_dividend_yield(stats: dict, ticker, info: dict, symbol: str) -> None:
    """TTM dividend yield in place from the dividend series, not the info
    field: Yahoo's trailingAnnualDividendYield mis-scales ADRs (an
    ordinary-share rate against the ADR price). Cash dividends with ex-dates
    in the last 365 days ÷ the current price; missing history or price
    leaves the key absent — the panel shows its placeholder."""
    try:
        dividends = ticker.dividends
    except Exception as err:  # yfinance raises provider-specific errors
        raise OSError(f"dividends fetch failed for {symbol}: {err}") from err
    if not isinstance(dividends, pd.Series) or dividends.empty:
        return
    # the series itself is page data (distributions panel): persist it
    # alongside the stats — ex-date rows ["YYYY-MM-DD", cash per share]
    _save_json(
        CACHE_DIR / f"{symbol.upper()}.divs.json",
        [
            [stamp.strftime("%Y-%m-%d"), round(float(amount), 6)]
            for stamp, amount in dividends.items()
        ],
    )
    price = _info_price(info)
    if not isinstance(price, (int, float)) or not price > 0:
        return
    now = pd.Timestamp.now(dividends.index.tz)
    recent = dividends[dividends.index > now - pd.Timedelta(days=365)]
    if not recent.empty:
        stats["trailingAnnualDividendYield"] = float(recent.sum()) / price


def _info_price(info: dict) -> int | float | None:
    """Last price from the info payload (fetch-time only; page paths read
    the bars cache). None when Yahoo reports no finite number."""
    return next(
        (
            info[key]
            for key in ("currentPrice", "regularMarketPrice")
            if isinstance(info.get(key), (int, float))
            and not isinstance(info.get(key), bool)
            and math.isfinite(info[key])
        ),
        None,
    )


def _fetch_expense_ratio(ticker) -> float | None:
    """Annual expense ratio from the fund-operations table — yfinance's
    info payload omits `annualExpenseRatio` for ETFs (verified 1.7.0),
    the funds_data scrape carries it ("Annual Report Expense Ratio",
    first column = the fund itself). Raises OSError on any fetch/shape
    failure (contained by the caller); None when the value is unusable."""
    try:
        row = ticker.funds_data.fund_operations.loc["Annual Report Expense Ratio"]
        value = row.iloc[0]
    except Exception as err:  # yfinance raises provider-specific errors
        raise OSError(f"fund operations failed: {err}") from err
    if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
        return float(value)
    return None


def _derive_value_stats(stats: dict) -> None:
    """Value-lens ratios added in place (value reads as book-to-market /
    yields, not raw price multiples). Only derived from valid inputs;
    negative PE/P/B yield nothing."""
    pe = stats.get("trailingPE")
    if isinstance(pe, (int, float)) and pe > 0:
        stats["earningsYield"] = 1 / pe
    pb = stats.get("priceToBook")
    if isinstance(pb, (int, float)) and pb > 0:
        stats["bookToMarket"] = 1 / pb
    cap = stats.get("marketCap")
    fcf = stats.get("freeCashflow")
    if isinstance(cap, (int, float)) and cap > 0 and isinstance(fcf, (int, float)):
        stats["fcfYield"] = fcf / cap
    debt, cash = stats.get("totalDebt"), stats.get("totalCash")
    if isinstance(debt, (int, float)) and isinstance(cash, (int, float)):
        stats["netDebt"] = debt - cash


def load_stats(symbol: str) -> dict:
    """Cached fundamentals for symbol; refreshes once per calendar day.

    Unlike load_bars this never raises: stats are garnish, not a gate —
    {} means "nothing available, show placeholders".
    """
    path = CACHE_DIR / f"{symbol.upper()}.stats.json"
    if not _fresh_today(path):
        try:
            _save_json(path, download_stats(symbol))
        except OSError:
            pass  # stale cache (or none at all) is fine for optional data
    return read_stats(symbol)


def read_stats(symbol: str) -> dict:
    """Stats straight from disk (load_stats minus the fetch); {} when
    absent or corrupt — request paths read this, refresh_all fetches."""
    try:
        return json.loads((CACHE_DIR / f"{symbol.upper()}.stats.json").read_text())
    except (OSError, ValueError):
        return {}


def read_divs(symbol: str) -> list:
    """Dividend rows straight from disk, written during the stats sweep;
    [] when absent or corrupt — request paths read this, never fetch."""
    try:
        payload = json.loads((CACHE_DIR / f"{symbol.upper()}.divs.json").read_text())
    except (OSError, ValueError):
        return []
    return payload if isinstance(payload, list) else []


def cached_benchmark() -> pd.DataFrame | None:
    """S&P 500 daily bars for market-relative context (beta/R², relative
    strength, residual purge) — straight from disk, because launch
    already warmed it; None when never cached, market-relative panels
    degrade as ever."""
    try:
        return cached_bars(BENCHMARK)
    except OSError:
        return None


def sweep_freshness() -> tuple[bool, str | None]:
    """(fresh, as_of) over the watchlist's bar caches for the landing
    staleness note: fresh when every cache was written today; as_of is
    the newest cache mtime's date — fetch date, close enough to last-bar
    date for a muted one-liner. (False, None) when nothing is cached."""
    fresh, newest = True, None
    for symbol in symbols():
        path = CACHE_DIR / f"{symbol.upper()}.csv"
        if not path.exists():
            fresh = False
            continue
        stamp = path.stat().st_mtime
        newest = stamp if newest is None else max(newest, stamp)
        fresh = fresh and _fresh_today(path)
    as_of = (
        datetime.fromtimestamp(newest, tz=timezone.utc).strftime("%Y-%m-%d")
        if newest is not None
        else None
    )
    return fresh, as_of


def download_eps(symbol: str) -> list:
    """Quarterly EPS history for the SUE metric: rows [date "YYYY-MM-DD",
    reported, estimate] ascending by earnings date, estimates optional
    (None when Yahoo has none). Raises OSError on any failure."""
    try:
        df = yf.Ticker(symbol).get_earnings_dates(limit=12)
    except Exception as err:  # yfinance raises provider-specific errors
        raise OSError(f"eps fetch failed for {symbol}: {err}") from err
    rows = []
    if df is not None and "Reported EPS" in getattr(df, "columns", []):
        for date, rec in df.iterrows():
            reported, estimate = rec.get("Reported EPS"), rec.get("EPS Estimate")
            if isinstance(reported, (int, float)) and math.isfinite(reported):
                rows.append(
                    [
                        pd.Timestamp(date).strftime("%Y-%m-%d"),
                        float(reported),
                        float(estimate)
                        if isinstance(estimate, (int, float))
                        and math.isfinite(estimate)
                        else None,
                    ]
                )
    rows.sort()
    if not rows:
        raise OSError(f"no eps for {symbol}")
    return rows


def load_eps(symbol: str) -> list:
    """Cached quarterly EPS rows; refreshes once per calendar day. Like
    load_stats it never raises: [] means "no earnings history available"."""
    path = CACHE_DIR / f"{symbol.upper()}.eps.json"
    if not _fresh_today(path):
        try:
            _save_json(path, download_eps(symbol))
        except OSError:
            pass
    return read_eps(symbol)


def read_eps(symbol: str) -> list:
    """EPS rows straight from disk (load_eps minus the fetch); [] when
    absent or corrupt — request paths read this, refresh_all fetches."""
    try:
        payload = json.loads((CACHE_DIR / f"{symbol.upper()}.eps.json").read_text())
    except (OSError, ValueError):
        return []
    return payload if isinstance(payload, list) else []


def _fresh_today(path: Path) -> bool:
    if not path.exists():
        return False
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return modified.date() == datetime.now(tz=timezone.utc).date()


def _read_cache(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"])


def _save(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _save_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1))
