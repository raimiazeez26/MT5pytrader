"""Print opened/updated/closed events from bounded, read-only polling."""

from _common import main, parser


def build_parser():
    p = parser(__doc__)
    p.add_argument("--interval", type=float, default=2)
    p.add_argument("--polls", type=int, default=30)
    return p


def example(args, trader):
    def on_change(event):
        print(event.kind, event.ticket, "before:", event.before, "after:", event.after)

    count = trader.watch_positions(
        on_change,
        symbol=args.symbol,
        magic=args.magic,
        interval=args.interval,
        max_polls=args.polls,
    )
    print("Events:", count)


if __name__ == "__main__":
    main(build_parser(), example)
