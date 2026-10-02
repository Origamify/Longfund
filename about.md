# Longfund

A local research and analysis tool for stocks, ETFs, and fund
strategies. Watch instruments for quarters to years with honest
total-return math — fundamentals, risk, market-relative panels —
with the aspiration of growing into a workbench for managing and
backtesting fund strategies and their risk and exposure.

Today it is the research layer of that ambition: watchlist,
per-symbol research pages, risk and factor analytics you read and
trust. Strategy backtesting and exposure management are the
direction, built on this foundation. For investors who hold, not
day-traders — no intraday data, no trading, no signals pushed at you.

Install (once, Python 3.10+):

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt        # run the app
    .venv/bin/pip install -r requirements-dev.txt    # tests + lint (optional)

Start it:

    ./launch.sh          # fetch today's data once, then serve the app
    # → http://127.0.0.1:3042

Browse: the watchlist landing (sparklines) links into per-symbol
research pages (total-return chart, trailing returns, fundamentals or
fund profile, vs-S&P panel, risk card, scorecard).

Typical flow: launch once (data caches on disk), read the pages, export
one page as a static HTML snapshot to share:

    python utils/export_html_analysis.py AAPL

Tests: `./test.sh`. Lint: `ruff check . && ruff format --check .`
(run from the venv: `.venv/bin/ruff ...`).

Flags, exit codes, HTTP API, data formats: `interface.md`.
Free-data caveat: results are indicative, not survivorship-bias-free;
total return is the adjusted-close approximation (dividends
reinvested, withholding not modeled).
