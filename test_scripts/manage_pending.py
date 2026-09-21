"""Inspect, modify, or cancel one pending ORDER ticket."""

from _common import main, parser, show_result


def build_parser():
    p = parser(__doc__, execution=True)
    p.add_argument("--ticket", type=int, required=True)
    p.add_argument("--cancel", action="store_true")
    p.add_argument("--price", type=float)
    p.add_argument("--sl", type=float)
    p.add_argument("--tp", type=float)
    return p


def example(args, trader):
    orders = trader.get_orders(ticket=args.ticket, symbol=args.symbol, magic=args.magic)
    if not orders:
        raise ValueError("Pending order does not match ticket/symbol/magic")
    changes = {
        name: getattr(args, name)
        for name in ("price", "sl", "tp")
        if getattr(args, name) is not None
    }
    if args.cancel and changes:
        raise ValueError("Choose cancellation or modification, not both")
    print("Current order:", orders[0])
    print("Requested:", "cancel" if args.cancel else changes or "inspect only")
    if not args.execute or (not args.cancel and not changes):
        print("No order change submitted.")
        return
    result = (
        trader.cancel_order(args.ticket)
        if args.cancel
        else trader.modify_order(args.ticket, **changes)
    )
    show_result(result)


if __name__ == "__main__":
    main(build_parser(), example)
