"""Exercise actual sample feature calls with the fake adapter, never a terminal."""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest

from MT5pytrader import Trader
from fake_mt5 import FakeMT5, order

EXAMPLES = Path(__file__).resolve().parents[1] / "test_scripts"


def load_example(name):
    sys.path.insert(0, str(EXAMPLES))
    try:
        spec = importlib.util.spec_from_file_location("sample_" + name, EXAMPLES / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(EXAMPLES))


class ExampleTests(unittest.TestCase):
    def run_example(self, name, argv):
        module = load_example(name)
        args = module.build_parser().parse_args(["--magic", "42", *argv])
        adapter = FakeMT5()
        adapter.order_rows = [order()]
        # This public MT5 constant is only used in the market-data example.
        adapter.TIMEFRAME_M5 = 5
        with contextlib.redirect_stdout(io.StringIO()):
            module.example(args, Trader(adapter=adapter, magic=42))
        return adapter

    def test_examples_do_not_send_without_execute(self):
        cases = {
            "connection": [],
            "positions": [],
            "market_orders": [],
            "pending_orders": ["--price", "1.09"],
            "close_position": ["--ticket", "101", "--percent", "0.5"],
            "modify_protection": ["--ticket", "101", "--sl", "1.1"],
            "manage_pending": ["--ticket", "201", "--cancel"],
            "risk_sizing": ["--entry", "1.1", "--stop", "1.09"],
            "execution_limits": [],
            "history": [],
            "market_data": [],
            "watch_positions": ["--polls", "1"],
            "trailing_stop": ["--ticket", "101"],
        }
        for name, argv in cases.items():
            with self.subTest(example=name):
                self.run_example(name, argv).order_send.assert_not_called()

    def test_selected_execute_examples_send_once(self):
        cases = [
            ("market_orders", ["--side", "buy"]),
            ("market_orders", ["--side", "sell"]),
            ("close_position", ["--ticket", "101"]),
            ("close_position", ["--ticket", "101", "--percent", "0.5"]),
            ("modify_protection", ["--ticket", "101", "--sl", "1.1"]),
            ("modify_protection", ["--ticket", "101", "--tp", "1.13"]),
            ("modify_protection", ["--ticket", "101", "--break-even"]),
            ("manage_pending", ["--ticket", "201", "--cancel"]),
            ("manage_pending", ["--ticket", "201", "--price", "1.091"]),
            ("trailing_stop", ["--ticket", "101"]),
        ]
        for name, argv in cases:
            with self.subTest(example=name, args=argv):
                self.run_example(name, [*argv, "--execute"]).order_send.assert_called_once()

    def test_all_pending_placement_samples(self):
        for side in ("buy", "sell"):
            for kind in ("limit", "stop", "stop_limit"):
                with self.subTest(side=side, kind=kind):
                    price = "1.09" if (side == "buy") == (kind == "limit") else "1.12"
                    argv = ["--side", side, "--kind", kind, "--price", price, "--execute"]
                    if kind == "stop_limit":
                        argv += ["--stoplimit", "1.11" if side == "buy" else "1.10"]
                    self.run_example("pending_orders", argv).order_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
