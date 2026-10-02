"""Export a shareable, self-contained HTML snapshot of a stock's overview.

Usage: python utils/export_html_analysis.py AAPL [-o out.html] [--range N|ytd]

Renders the live /symbol/{TICKER} page through the exact web-app code path
(Flask test client), then post-processes it into one file that needs no
server: theme.css and the vendored Chart.js bundle are inlined next to
the already-inline chart payload. A warm-up pass fetches the symbol's
data (and the benchmark) if the disk cache is stale or missing, so the
snapshot is fresh without launching the app. A symbol that is not on
the watchlist is added through the same verified path as the web form
first, so the exporter also works on a cold cache with an empty
watchlist. Nav-only links drop out,
other internal links are neutralized at load time, and an export-only
stylesheet layers mobile-first responsive rules on top of the unchanged
desktop styles — the same file reads well on a phone and on a desktop.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # script lives in utils/, imports live in src/

STATIC_DIR = ROOT / "static"
EXPORTS_DIR = ROOT / "exports"
STAMP_FORMAT = "%Y-%m-%d %H:%M"

# export-only CSS: appended after the inlined theme.css. Desktop rendering is
# untouched; the media queries reflow the snapshot for phone screens
# (perf strip → value chips, glosses onto their own line, finger-sized
# timescale buttons, shorter chart)
SNAPSHOT_CSS = """
@media (hover: none) {
  body { -webkit-tap-highlight-color: transparent; }
  .shell { padding: 0 12px; }
  main.shell { padding-top: 14px; }

  .sym-head { flex-wrap: wrap; gap: 6px 10px; }
  .sym-price { font-size: 21px; }
  .sym-sub { margin-top: -8px; }

  .chart-tall { height: 300px; }

  .perf {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
    gap: 6px;
    font-size: 13px;
    margin-bottom: 12px;
  }
  .perf-item {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 6px;
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 9px;
  }
  .perf-item .muted { margin-right: 0; }

  .panel { padding: 12px; }
  .panel-head { flex-wrap: wrap; }

  table.data { font-size: 13px; }
  table.data td { padding: 7px 4px; }
  .gloss { display: block; font-size: 11px; line-height: 1.35; }

  .ranges a, .ranges button { padding: 7px 13px; }
  table.data tbody tr:hover { background: transparent; }
}
"""

# snapshot has no server behind it: every internal app link (brand,
# watchlist nav, symbol rows) is removed or converted to a plain styled
# span at export time — the file contains no anchors


def _swap(html: str, old: str, new: str) -> str:
    """Replace `old` once, loudly: template drift must fail, not ship."""
    if old not in html:
        raise RuntimeError(f"export target not found in rendered page: {old!r}")
    return html.replace(old, new, 1)


def build_html(symbol: str, range_arg: str | None = None) -> str:
    """Render /symbol/{SYMBOL} and fold every external reference inline."""
    from src import market, web  # after the sys.path bootstrap above

    symbol = symbol.upper()
    # cold-start export: an off-watchlist symbol is added through the same
    # verified path as the web form (fetches + persists), so no manual
    # watchlist seeding is needed before a snapshot
    if symbol not in market.symbols():
        try:
            market.add_symbol(symbol)
        except (OSError, ValueError) as err:
            print(f"no page for {symbol} — cannot watchlist it: {err}")
            raise SystemExit(1)
    # warm-up: fetch-if-stale for the symbol + benchmark; failures fall
    # through to the 404 path below (nothing cached, nothing fetched)
    market.refresh_symbol(symbol)
    market.refresh_symbol(market.BENCHMARK)
    client = web.app.test_client()
    query = {"range": range_arg} if range_arg else {}
    response = client.get(f"/symbol/{symbol}", query_string=query)
    if response.status_code != 200:
        print(
            f"no page for {symbol} (HTTP {response.status_code}) — the symbol "
            "has no data after the warm pass (fetch failed and nothing was "
            "cached)"
        )
        raise SystemExit(1)
    html = response.get_data(as_text=True)
    css = (STATIC_DIR / "theme.css").read_text()
    chart_js = (STATIC_DIR / "chart.umd.min.js").read_text()

    stamp = datetime.now().astimezone().strftime(STAMP_FORMAT)
    last_bar = market.cached_bars(symbol)["Date"].iloc[-1].strftime("%Y-%m-%d")

    html = _swap(
        html,
        '<link rel="stylesheet" href="/static/theme.css">',
        f"<style>\n{css}{SNAPSHOT_CSS}\n  </style>",
    )
    html = _swap(
        html,
        "<title>Longfund</title>",
        f"<title>{symbol} · Longfund snapshot</title>",
    )
    html = _swap(
        html,
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <meta name="theme-color" content="#0b0e14">',
    )
    # file:// pages must not rewrite their URL (the app's deep-link feature)
    html = _swap(
        html,
        'history.replaceState(null, "", `?${url}`);',
        "/* snapshot: keep the file:// URL intact */",
    )
    html = _swap(
        html,
        '<div class="crumb"><a href="/">&larr; watchlist</a></div>',
        f'<div class="crumb muted">snapshot {stamp} · data through {last_bar}</div>',
    )
    # links: nav-only anchors drop out (the theme toggle stays — it works
    # offline), the rest (brand, watchlist rows) become plain spans
    html = _swap(
        html, '<a href="/">watchlist</a>', '<span class="muted">watchlist</span>'
    )
    html = re.sub(r'<a([^>]*) href="[^"]*"', r"<span\1", html)
    html = html.replace("</a>", "</span>")
    if "<a " in html or 'href="/' in html:
        raise RuntimeError("snapshot still contains app links")
    # Chart.js goes in last: the anchor guard above must scan the page markup,
    # not the vendored bundle (whose minified code may embed '<a '-like text)
    html = _swap(
        html,
        '<script src="/static/chart.umd.min.js"></script>',
        f"<script>\n/* Chart.js 4.4.9, vendored — inlined for offline use */\n{chart_js}\n  </script>",
    )
    return html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("symbol", help="ticker to snapshot (e.g. AAPL)")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="output .html path (default: exports/{SYMBOL}_snapshot.html under the repo root)",
    )
    parser.add_argument(
        "--range",
        default=None,
        metavar="N|ytd|max",
        help="chart window, like the page's ?range= (bar count, ytd, or max; default 504)",
    )
    args = parser.parse_args(argv)

    symbol = args.symbol.upper()
    out = args.out or EXPORTS_DIR / f"{symbol}_snapshot.html"
    html = build_html(symbol, args.range)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(
        f"wrote {out} ({out.stat().st_size / 1024:.0f} KB) — send as a file; opens offline on phone and desktop"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
