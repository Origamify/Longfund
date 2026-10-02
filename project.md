# Longfund — Project Map

## Goal

A research and analysis tool for long-horizon investors — and the
foundation for a fund-strategy workbench.

The core today: you watch a handful of instruments, open their
research pages, and read honest long-horizon numbers — total-return
chart, trailing returns, fundamentals or fund profile, risk, vs-S&P
panels, earnings momentum. It is a reading tool for investors who
hold for quarters to years.

The aspiration: assist in managing and backtesting fund strategies
and in risk and exposure management. The analytics already in place
(total-return math, drawdown and CDaR risk measures, β/α regression,
residual momentum, factor scorecard) are the building blocks —
strategy backtesting and portfolio-level exposure tracking are the
planned direction, not yet shipped features. Every panel added should
either show better research on an instrument or move toward that
strategy-management goal.

Still out of scope: day-trading concerns — no intraday or live data,
no signals pushed at users, no trading execution, no screeners, no
multi-user serving.

## Status

Active, working product. Pages, JSON API, and the HTML exporter all
function; the test suite (117 tests) and ruff pass. Strategy
backtesting and portfolio-level exposure management are aspirational
— the research and risk-analysis layer they will build on is live.

## Scope

- Does: launch-time daily-data sweep (Yahoo) with disk cache;
  per-symbol research pages — total-return chart (SMA, volume,
  drawdown, RS vs S&P), trailing-return strip, fundamentals or ETF
  fund profile, earnings momentum (SUE + surprise), vs-S&P regression
  panel (β/α/R², residual momentum, LETF decay readout), buy-and-hold
  risk card, watchlist factor scorecard, payment-aligned
  distributions group; offline HTML snapshot export; JSON API
  (bars/stats/eps).
- Doesn't yet (aspiration): strategy definition or backtesting;
  portfolio-level exposure and risk aggregation; position tracking.
  These are the roadmap, not the current surface.
- Doesn't by design: intraday or live data (daily cache, refreshed
  once per calendar day); multi-user serving or auth (localhost,
  single user); trading or order execution; screeners (removed —
  watchlist + research pages are the product).

## Run & setup

- Run: `./launch.sh` (or `python longfund.py`) — sweeps the benchmark +
  watchlist (fetch-if-stale), then serves on 127.0.0.1:3042.
- Install: `python3 -m venv .venv` then `pip install -r requirements.txt`
  (flask, yfinance); `requirements-dev.txt` adds pytest + ruff.
  `launch.sh`/`test.sh` prefer `.venv/bin/python`, falling back to
  `python3`.
- Tests: `./test.sh` (pytest). Lint: `ruff check . && ruff format --check .`

## File map

- `longfund.py` — entry point: argparse + config only.
- `src/` — all app logic.
  - `market.py` — Yahoo fetch + disk cache; the **only network call site**.
  - `web.py` — Flask routes, JSON API, request handling (the HTTP layer).
  - `panels.py` — computed research panels: chart payload helpers,
    trailing-return strip, risk card, vs-S&P regression panel, watchlist
    factor ranks, landing sparkline.
  - `fundamentals.py` — fundamentals/fund-profile metric tables
    (STAT_GROUPS, ETF_GROUPS, MARKET_REF) and their row builders.
  - `metrics.py` — risk/drawdown/regression/earnings-momentum math; pure.
    The natural home for future backtest and exposure math.
  - `__init__.py` — BLAS thread pinning (see Settings).
- `templates/`, `static/` — Jinja pages; `theme.css`, vendored chart.js.
- `tests/` — pytest suite; conftest redirects all data paths to scratch.
- `utils/export_html_analysis.py` — offline HTML snapshot exporter.
- `data/` — persisted state: `watchlist.json`,
  `cache/` (bars `.csv` + `.stats.json` / `.eps.json` / `.divs.json`
  twins).
- `interface.md` — CLI flags, HTTP API, data formats (authoritative).
- To change fetching/caching → `src/market.py`; routes/API behavior →
  `src/web.py`; panel math (risk, vs-S&P, strip, scorecard) →
  `src/panels.py`; fundamentals tables → `src/fundamentals.py`; analytics
  math (incl. future backtest/exposure math) → `src/metrics.py`; UI →
  `templates/` + `static/theme.css`.

## Conventions

- `src/market.py` is the only network call site — swap providers there
  and nowhere else.
- Request paths are disk-only (`cached_bars`/`read_stats`/`read_eps`/
  `read_divs`/`cached_benchmark`); fetching happens in the launch sweep
  (`--sweep-only` shares it), `add_symbol` verification, and the
  exporter's fetch-if-stale warm pass (`refresh_symbol`).
- Long-horizon numbers read the total-return series (Adj Close when
  cached); raw Close serves the price header, day change, and
  `/api/bars` — what the ticker shows.
- Optional data (stats, EPS, dividends, benchmark) degrades silently to
  placeholders; bars failures are the only hard errors.
- Comments cite the research papers behind the math (Chan, Novy-Marx,
  Jegadeesh–Titman, Chekhlov–Uryasev–Zabarankin, ...) — keep the
  citations when editing that math. This matters double as the tool
  grows toward strategy backtesting: the math must stay anchored to
  literature. `docs/` holds the per-metric review.

## Settings

- `--port N` — port to serve on; default 3042.
- `--offline` — skip the fetch sweep, serve the cache as-is (watchlist
  adds then persist unverified); default off.
- `--sweep-only` — run the fetch sweep, then exit without serving (CI
  cache warm-up); default off.
- `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` —
  pinned to 1 by `src/__init__.py` via `setdefault` before numpy loads
  (BLAS thread pools slow tiny-array ops); explicit env wins.
- Cache freshness — files refetch at most once per calendar day per
  symbol (mtime check).
