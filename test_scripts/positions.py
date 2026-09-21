"""Read positions, pending orders, and profit for one strategy."""

from _common import main, parser


def build_parser():
    p = parser(__doc__)
    p.add_argument("--side", choices=("buy", "sell"))
    return p


def example(args, trader):
    for position in trader.positions(symbol=args.symbol, magic=args.magic, side=args.side):
        print(position.ticket, position.symbol, position.type, position.volume, position.profit)
    print(trader.get_open_positions(symbol=args.symbol, magic=args.magic, side=args.side))
    print("Floating profit:", trader.running_profit(args.symbol, args.magic, args.side))
    print("Pending orders:", trader.get_orders(symbol=args.symbol, magic=args.magic))


if __name__ == "__main__":
    main(build_parser(), example)
