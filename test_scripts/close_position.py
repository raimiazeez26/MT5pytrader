"""Close a selected position fully, by explicit volume, or by fraction."""

from _common import main, parser, show_result


def build_parser():
    p = parser(__doc__, execution=True)
    p.add_argument("--ticket", type=int, required=True)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--volume", type=float, help="Lots to close; omitted means full position")
    group.add_argument("--percent", type=float, help="Fraction, e.g. 0.5 for half")
    return p


def example(args, trader):
    positions = trader.positions(ticket=args.ticket, symbol=args.symbol, magic=args.magic)
    if not positions:
        raise ValueError("Ticket must match --symbol and --magic; use positions.py to inspect it")
    position = positions[0]
    print("Selected position:", position)
    print("Requested close:", args.percent if args.percent is not None else args.volume or "all")
    if not args.execute:
        print("No close submitted. Volume validation happens when executing.")
        return
    if args.percent is None:
        result = trader.close_position(
            args.ticket, volume=args.volume, symbol=args.symbol, magic=args.magic
        )
    elif position.type == trader.mt5.ORDER_TYPE_BUY:
        result = trader.close_partial_buy(
            args.percent, ticket_id=args.ticket, symbol=args.symbol, magic=args.magic
        )
    else:
        result = trader.close_partial_sell(
            args.percent, ticket_id=args.ticket, symbol=args.symbol, magic=args.magic
        )
    show_result(result)


if __name__ == "__main__":
    main(build_parser(), example)
