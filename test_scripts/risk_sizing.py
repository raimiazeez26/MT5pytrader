"""Estimate lot size, stop-loss amount, and margin without submitting a trade."""

from _common import main, parser


def build_parser():
    p = parser(__doc__)
    p.add_argument("--side", choices=("buy", "sell"), default="buy")
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--risk", type=float, default=25, help="Budget in account currency")
    return p


def example(args, trader):
    estimate = trader.calculate_volume(args.symbol, args.side, args.entry, args.stop, args.risk)
    print("Lots:", estimate.volume)
    print("Estimated stop loss:", estimate.estimated_loss, estimate.currency)
    print(
        "Estimated margin:",
        trader.margin_required(args.symbol, args.side, estimate.volume, args.entry),
    )
    print("These estimates exclude slippage, gaps, commission, and swap. No trade submitted.")


if __name__ == "__main__":
    main(build_parser(), example)
