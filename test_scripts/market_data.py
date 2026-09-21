"""Fetch five-minute bars and recent ticks using timezone-aware datetimes."""

from datetime import datetime, timedelta, timezone
from _common import main, parser


def build_parser():
    return parser(__doc__)


def example(args, trader):
    end = datetime.now(timezone.utc)
    bars = trader.get_rates(args.symbol, trader.mt5.TIMEFRAME_M5, end - timedelta(days=1), end)
    ticks = trader.get_ticks(args.symbol, end - timedelta(minutes=5), end)
    print("Bars:", bars.tail(), sep="\n")
    print("Ticks:", ticks.tail(), sep="\n")


if __name__ == "__main__":
    main(build_parser(), example)
