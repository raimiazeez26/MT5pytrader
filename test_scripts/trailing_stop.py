"""Run a bounded client-side trailing stop on a selected ticket."""

from _common import main, parser, show_result


def build_parser():
    p = parser(__doc__, execution=True)
    p.add_argument("--ticket", type=int, required=True)
    p.add_argument("--distance-points", type=float, default=200)
    p.add_argument("--interval", type=float, default=2)
    p.add_argument("--polls", type=int, default=1, help="1 for one update; larger values repeat")
    return p


def example(args, trader):
    positions = trader.positions(ticket=args.ticket, symbol=args.symbol, magic=args.magic)
    if not positions:
        raise ValueError("Position does not match ticket/symbol/magic")
    print("Current position:", positions[0])
    if not args.execute:
        print("No stop changed. Add --execute to run trailing protection.")
        return
    if args.polls == 1:
        show_result(trader.trail_stop(args.ticket, args.distance_points))
    else:
        trader.run_trailing_stop(
            args.ticket,
            args.distance_points,
            interval=args.interval,
            max_polls=args.polls,
            callback=show_result,
        )


if __name__ == "__main__":
    main(build_parser(), example)
