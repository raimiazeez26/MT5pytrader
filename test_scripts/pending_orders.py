"""Create one limit, stop, or stop-limit order with an optional expiry."""

from datetime import datetime, timedelta, timezone

from _common import main, parser, show_result


def build_parser():
    p = parser(__doc__, execution=True)
    p.add_argument("--side", choices=("buy", "sell"), default="buy")
    p.add_argument("--kind", choices=("limit", "stop", "stop_limit"), default="limit")
    p.add_argument("--price", type=float, required=True, help="Absolute entry/trigger price")
    p.add_argument("--stoplimit", type=float, help="Absolute limit entry for stop_limit")
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--stop-loss", type=float, default=200)
    p.add_argument("--take-profit", type=float, default=400)
    p.add_argument("--expires-minutes", type=int, help="Future expiry, in minutes from now")
    return p


def example(args, trader):
    options = dict(lot=args.lot, stop_loss=args.stop_loss, take_profit=args.take_profit)
    if args.expires_minutes is not None:
        options.update(
            type_time=trader.mt5.ORDER_TIME_SPECIFIED,
            expiration=datetime.now(timezone.utc) + timedelta(minutes=args.expires_minutes),
        )
    print(
        trader.preview_order(
            args.symbol,
            args.side,
            kind=args.kind,
            price=args.price,
            stoplimit=args.stoplimit,
            **options,
        )
    )
    if not args.execute:
        print("Preview only; no pending order submitted.")
        return
    # Select one API; do not run all six in sequence.
    methods = {
        ("buy", "limit"): trader.open_buy_limit,
        ("sell", "limit"): trader.open_sell_limit,
        ("buy", "stop"): trader.open_buy_stop,
        ("sell", "stop"): trader.open_sell_stop,
        ("buy", "stop_limit"): trader.open_buy_stop_limit,
        ("sell", "stop_limit"): trader.open_sell_stop_limit,
    }
    if args.kind == "stop_limit":
        options["stoplimit"] = args.stoplimit
    show_result(methods[args.side, args.kind](args.symbol, args.price, **options))


if __name__ == "__main__":
    main(build_parser(), example)
