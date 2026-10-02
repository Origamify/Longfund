# Longfund

A local research and analysis tool for stocks, ETFs, and fund
strategies. Watch a handful of instruments, open their research
pages, and read honest long-horizon numbers: total-return chart,
trailing returns, fundamentals or fund profile, risk, vs-S&P panels,
earnings momentum.

Longfund's aspiration is to grow into a workbench that assists in
**managing and backtesting fund strategies** and in **risk and
exposure management**. The research layer you see today — drawdown
and CDaR risk measures, β/α regression, residual momentum, factor
scorecard — is the foundation that work is built on; strategy
backtesting and portfolio-level exposure tracking are the roadmap,
not yet shipped. For investors who hold for quarters to years — no
intraday data, no trading.

## What it does

- **Watchlist landing** — one row per symbol with sparklines, add/remove
  symbols (verified on Yahoo), links into research pages
- **Research pages** (`/symbol/{TICKER}`) — total-return chart (SMA,
  volume, drawdown, RS vs S&P), trailing-return strip, fundamentals or
  ETF fund profile, earnings momentum (SUE + surprise), vs-S&P
  regression panel (β/α/R², residual momentum, LETF decay readout),
  buy-and-hold risk card, watchlist factor scorecard,
  payment-aligned distributions
- **Risk & exposure analytics** — the research panels double as the
  risk/exposure building blocks: drawdown profiles, volatility and
  tail-risk reads, benchmark β/α, factor ranks across the watchlist —
  designed to later feed portfolio-level exposure management
- **Daily data sweep** — launch fetches the benchmark + whole watchlist
  once per calendar day per symbol (Yahoo, via yfinance), cached on
  disk; every page read is then offline
- **Export** — any research page as one self-contained HTML snapshot
  to share (see [Exporting a page](#exporting-a-page))
- **JSON API** — `/api/bars`, `/api/stats`, `/api/eps` (see
  [interface.md](interface.md))
- **GitHub Actions export** — run the `Export analysis` workflow with a
  ticker; the HTML snapshot comes back as a run artifact, no local
  setup needed

## Requirements

- **Python** ≥ 3.10
- **Internet** — for the daily Yahoo fetch (cached after; pages render
  fully offline with a warm cache)

## Setup

```bash
# 1. Clone and install:
git clone <repo-url> longfund && cd longfund
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run:
./launch.sh                        # sweep today's data, serve http://127.0.0.1:3042
./launch.sh --offline              # skip the sweep, serve the cache as-is
./test.sh                          # offline test suite (network stubbed)
```

Then open **http://127.0.0.1:3042**, add a symbol on the landing page,
and read its research page. Data lives in gitignored `data/` — a warm
cache means zero network on later runs.

## Exporting a page

`utils/export_html_analysis.py` turns a research page into one HTML
file you can send to someone — it opens offline in any phone or
desktop browser, no server behind it.

```bash
python utils/export_html_analysis.py AAPL
# → exports/AAPL_snapshot.html (~440 KB)

python utils/export_html_analysis.py AAPL -o report.html   # custom path
python utils/export_html_analysis.py AAPL --range ytd       # initial chart window
```

How it works:

- **Cold-start capable** — an off-watchlist symbol is added through the
  same verified path as the web form first (added to your watchlist,
  verified on Yahoo), so an empty cache + empty watchlist still works.
- **Fresh by itself** — a warm-up pass fetches the symbol and the
  benchmark fetch-if-stale before rendering (same freshness semantics
  as the app: at most one fetch per symbol per day). No launch needed.
- **Exact page** — it renders `/symbol/{TICKER}` through the real
  web-app code path, then inlines theme.css, the vendored Chart.js
  bundle, and the chart payload; internal app links drop out or become
  plain spans — the file contains no anchors.
- **Mobile-first overlay** — desktop styling unchanged; an export-only
  stylesheet reflows the snapshot for ≤700px screens.

Exit codes: `0` file written · `1` bad ticker or no data after the
warm pass · `2` bad usage. Details: [interface.md](interface.md).

The same export runs on GitHub Actions — dispatch the `Export
analysis` workflow with a ticker and download the snapshot from the
run's artifacts, no local setup needed.

## Utilities

- **CI sweep warm-up** — `python longfund.py --sweep-only` — run the
  fetch sweep, then exit without serving (same flags as `launch.sh`).

## Docs

- `about.md` — short "what is this" page
- `interface.md` — CLI flags, exit codes, HTTP API, data formats
  (authoritative)
- `project.md` — maintainer's map: architecture, file map, conventions,
  settings
- `docs/` — per-metric review notes behind the panel math

## Notes

- **Dev server**: Flask's built-in server, bound to `127.0.0.1` only —
  single-user by design, not for production or shared hosting.
- `static/chart.umd.min.js` is a vendored copy of
  [Chart.js](https://github.com/chartjs/Chart.js) 4.4.9 (MIT), kept so
  pages and snapshots render fully offline.
- Long-horizon numbers read the total-return series (adjusted close);
  raw close serves the price header and day change — what the ticker
  shows.
- Free-data caveat: results are indicative, not
  survivorship-bias-free; total return is the adjusted-close
  approximation (dividends reinvested, withholding not modeled).
