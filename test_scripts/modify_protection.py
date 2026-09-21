"""Modify absolute SL/TP prices or move a selected position to break-even."""

from _common import main, parser, show_result


def build_parser():
    p = parser(__doc__, execution=True)
    p.add_argument("--ticket", type=int, required=True)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--sl", type=float, help="Absolute price; 0 removes stop loss")
    action.add_argument("--tp", type=float, help="Absolute price; 0 removes take profit")
    action.add_argument("--break-even", action="store_true")
    p.add_argument("--offset-points", type=float, default=0)
    return p


def example(args, trader):
    positions = trader.positions(ticket=args.ticket, symbol=args.symbol, magic=args.magic)
    if not positions:
        raise ValueError("Position does not match ticket/symbol/magic")
    print("Current protection:", positions[0].sl, positions[0].tp)
    print("Requested:", "SL", args.sl, "TP", args.tp, "break-even", args.break_even)
    if not args.execute:
        print("No modification submitted. Broker validation happens when executing.")
        return
    selection = dict(ticket_id=args.ticket, symbol=args.symbol, magic=args.magic)
    if args.sl is not None:
        result = trader.modify_sl(sl=args.sl, **selection)
    elif args.tp is not None:
        result = trader.modify_tp(tp=args.tp, **selection)
    else:
        result = trader.break_even(offset_points=args.offset_points, **selection)
    show_result(result)


if __name__ == "__main__":
    main(build_parser(), example)
