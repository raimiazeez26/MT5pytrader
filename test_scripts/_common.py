"""Shared setup for usage examples; feature calls live in the individual scripts."""

import argparse
from contextlib import contextmanager
import os

from MT5pytrader import Trader, TradeError


def parser(description, *, execution=False):
    result = argparse.ArgumentParser(description=description)
    result.add_argument("--symbol", default="EURUSD", help="Exact broker symbol, including suffix")
    result.add_argument(
        "--magic", type=int, default=260001, help="Strategy ID used by these examples"
    )
    if execution:
        result.add_argument(
            "--execute", action="store_true", help="Actually submit the selected operation"
        )
    return result


@contextmanager
def connect(args):
    required = ("MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError("Set these environment variables first: " + ", ".join(missing))
    # Construction is delayed; entering the context initializes the terminal.
    # Context exit calls disconnect()/mt5.shutdown(), including on exceptions.
    with Trader(
        path=os.environ.get("MT5_PATH") or None,
        magic=args.magic,
        comment="package-example",
        auto_initialize=False,
    ) as trader:
        trader.connect(
            int(os.environ["MT5_LOGIN"]),
            os.environ["MT5_PASSWORD"],
            os.environ["MT5_SERVER"],
        )
        yield trader


def main(argument_parser, example):
    args = argument_parser.parse_args()
    try:
        with connect(args) as trader:
            example(args, trader)
    except (TradeError, ValueError) as exc:
        argument_parser.exit(1, f"{type(exc).__name__}: {exc}\n")
    except KeyboardInterrupt:
        print("Stopped; terminal connection closed.")


def show_result(result):
    print(
        f"status={result.status}, retcode={result.retcode}, order={result.order}, deal={result.deal}"
    )
    print(f"requested={result.requested_volume}, executed={result.executed_volume}")
    if result.message:
        print(result.message)
    if result.status == "unknown":
        print("Inspect orders, positions, and deal history before any retry.")
