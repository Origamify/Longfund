"""Longfund web app: entry point — argparse + configuration only.

All app logic (routes, JSON API, formatting) lives in src/web.py. Run via
./launch.sh or directly. Long-horizon stock & ETF research: watchlist +
per-symbol research pages. No strategies, no backtests.

Usage: python longfund.py [--port PORT] [--offline] [--sweep-only]

Launching fetches: the benchmark + whole watchlist sweep synchronously
before the server comes up (progress in the terminal). --offline skips
it all and serves whatever cache is on disk. --sweep-only runs the
sweep and exits — no server (CI warm-up).
"""

import argparse

from src import market
from src.web import app

DEFAULT_PORT = 3042


def _progress(symbol: str, i: int, total: int, error: str | None) -> None:
    """One terminal line per sweep step; failures noted, never fatal."""
    line = f"[{i}/{total}] {symbol}"
    print(f"{line} — {error}" if error else line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        metavar="N",
        help=f"port to serve on (default {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the launch-time fetch sweep; serve the cache as-is",
    )
    parser.add_argument(
        "--sweep-only",
        action="store_true",
        help="run the fetch sweep, then exit without serving (CI warm-up)",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.sweep_only:
        market.refresh_all(progress=_progress)
        return 0  # no server: warm the cache and leave
    app.config["OFFLINE"] = args.offline  # landing note + unverified adds
    if not args.offline:
        market.refresh_all(progress=_progress)
    app.run(host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
