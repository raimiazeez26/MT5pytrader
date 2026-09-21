"""Preview/check a buy or sell; add --execute to submit it once."""

from _common import main, parser, show_result


def build_parser():
    p = parser(__doc__, execution=True)
    p.add_argument("--side", choices=("buy", "sell"), default="buy")
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--stop-loss", type=float, default=200, help="Distance in points")
    p.add_argument("--take-profit", type=float, default=400, help="Distance in points")
    return p


def example(args, trader):
    options = dict(lot=args.lot, stop_loss=args.stop_loss, take_profit=args.take_profit)
    print("Request:", trader.preview_order(args.symbol, args.side, **options))
    check = trader.check_order(args.symbol, args.side, **options)
    print("Preflight:", check.valid, check.retcode, check.message)
    if not args.execute or not check.valid:
        print("No order submitted.")
        return
    # Each execution method performs its own fresh validation and preflight.
    if args.side == "buy":
        result = trader.open_buy(args.symbol, **options)
    else:
        result = trader.open_sell(args.symbol, **options)
    show_result(result)


if __name__ == "__main__":
    main(build_parser(), example)
