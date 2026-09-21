"""Read recent deals and a deal-level profit/cost summary in UTC."""

from datetime import datetime, timedelta, timezone
from _common import main, parser


def build_parser():
    p = parser(__doc__)
    p.add_argument("--days", type=int, default=7)
    return p


def example(args, trader):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    print(trader.history_deals(start, end, symbol=args.symbol, magic=args.magic))
    print(trader.performance_report(start, end, symbol=args.symbol, magic=args.magic))


if __name__ == "__main__":
    main(build_parser(), example)
