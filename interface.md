# Longfund — Interface

A nice research tool for stocks and ETFs — and nothing else. No
strategies, no signals, no backtests, no trading — see `project.md`
for scope. This file: flags, exit codes, HTTP API, data formats.

## CLI: `longfund.py`

```
python longfund.py [--port N] [--offline] [--sweep-only]
./launch.sh ...        # same args, forwarded
```

- `--port N` — serve on N (default 3042; 1–65535, invalid → exit 2,
  argparse).
- `--offline` — skip the launch-time fetch sweep; serve the cache as-is
  (the watchlist add form then persists symbols unverified).
- `--sweep-only` — run the fetch sweep, print progress, exit 0 without
  serving. For CI: warm `data/cache/`, then run the exporter offline.

Launching fetches: the benchmark + whole watchlist sweep synchronously
**before** the server comes up (one terminal progress line per symbol;
per-symbol failures noted, never fatal). The dev server binds
`127.0.0.1` only.

Exit codes: `0` clean shutdown · `2` bad usage.

## CLI: `utils/export_html_analysis.py`

```
python utils/export_html_analysis.py {TICKER} [-o out.html] [--range N|ytd|max]
```

Exports the `/symbol/{TICKER}` research page as one self-contained HTML
file (no server needed — CSS, the vendored Chart.js bundle and the
chart payload are all inlined; ~440 KB). Before rendering it warms the
cache fetch-if-stale (`refresh_symbol`: the symbol + the benchmark),
so a stale or empty cache still yields a fresh snapshot without
launching the app. Same freshness semantics as the web app (at most
one fetch per symbol per day).

- `symbol` (required, positional) — ticker, case-insensitive; added to
  the watchlist first if missing (verified on Yahoo).
- `-o/--out` — output path; default `exports/{SYMBOL}_snapshot.html`
  (`exports/` is gitignored).
- `--range N|ytd|max` — initial chart window, like the page's `?range=`
  (bar count, `ytd`, or `max` = full cached history; default 504 ≈ 2y).
  Buttons still re-slice in-browser.

The snapshot keeps desktop styling and layers mobile-first rules on top
(≤700px). Internal app links are removed or converted to plain styled
spans at export time — the file contains no anchors. It opens offline
in any phone or desktop browser.

Exit codes: `0` file written · `1` no page for the symbol (bad ticker,
or no data after the warm pass — fetch failed and nothing cached) ·
`2` bad usage.

## HTTP API (dev server on `127.0.0.1`, default port 3042)

JSON under `/api/*`; errors there are `{"error": "..."}` with the status
code. Pages keep Flask's default error pages. All reads are disk-only
(the launch sweep warmed them).

- `GET /api/bars/<symbol>?tail=N` — last N daily `[date, close]` rows
  (raw close, not adjusted; default 10, must be a positive integer).
  404 unknown symbol / no cached data; 400 bad tail.
- `GET /api/stats/<symbol>` — curated fundamentals snapshot (`info` keys
  + derived value-lens/ETF keys); `{}` = unavailable.
- `GET /api/eps/<symbol>` — quarterly EPS rows `[date, reported,
  estimate]` ascending + derived `sue`; `[]` / `null` = unavailable.

## Pages

- `GET /` — watchlist landing (rows, sparklines, add-symbol form).
- `GET /symbol/<symbol>[?range=N|ytd|max]` — research page.
- `POST /watchlist` — form field `symbol`; verified on Yahoo unless the
  server runs `--offline`; 400 on bad/duplicate.

## Data formats

Cached data (all under gitignored `data/`):

- `cache/{TICKER}.csv` — `Date,Open,High,Low,Close,Adj Close,Volume`,
  oldest first; `Adj Close` is the total-return basis the pages prefer.
- `cache/{TICKER}.stats.json` — curated `info` keys + derived keys
  (`earningsYield`, `bookToMarket`, `fcfYield`, `netDebt`,
  `revenuePerEmployee`, `trailingAnnualDividendYield`, ETF lens keys).
- `cache/{TICKER}.eps.json` — rows `[date, reported, estimate]`.
- `cache/{TICKER}.divs.json` — rows `[ex-date, cash per share]`.
- `cache/^GSPC.csv` — benchmark bars.
- `watchlist.json` — symbol list.
