"""Apply local execution limits and check a sample request without sending it."""

from MT5pytrader import ExecutionLimits
from _common import main, parser


def build_parser():
    p = parser(__doc__)
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--max-spread", type=float, default=30)
    p.add_argument("--max-exposure", type=float, default=1.0)
    p.add_argument("--max-daily-loss", type=float, default=100)
    return p


def example(args, trader):
    # You can also pass limits=ExecutionLimits(...) to Trader's constructor.
    trader.limits = ExecutionLimits(
        allowed_symbols=frozenset({args.symbol}),
        max_spread_points=args.max_spread,
        max_exposure_lots=args.max_exposure,
        max_daily_loss=args.max_daily_loss,
    )
    print(trader.check_order(args.symbol, "buy", lot=args.lot))
    print("No order sent. Limits are local snapshot checks, not broker-enforced controls.")


if __name__ == "__main__":
    main(build_parser(), example)
