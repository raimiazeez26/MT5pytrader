"""Connect using environment credentials and read account positions."""

from _common import main, parser


def build_parser():
    return parser(__doc__)


def example(args, trader):
    # _common.connect demonstrates Trader(...), connect(), and context cleanup.
    print("Connected:", trader)
    print(trader.get_open_positions(symbol=args.symbol))
    print("Floating profit:", trader.running_profit(symbol=args.symbol))


if __name__ == "__main__":
    main(build_parser(), example)
