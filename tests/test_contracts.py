"""Compatibility and edge cases, including an optional native import-only check."""

import ast
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from MT5pytrader import Trader, TradeError
from MT5pytrader.pytrader import Trader as LegacyTrader
from MT5pytrader.validation import integer
from fake_mt5 import FakeMT5, order, position


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.m = FakeMT5()
        self.t = Trader(adapter=self.m)

    def test_historical_import_and_large_tickets(self):
        self.assertIs(LegacyTrader, Trader)
        ticket = 9007199254740993
        self.assertEqual(integer(ticket, "ticket"), ticket)
        self.m.position_rows = [position(ticket=ticket)]
        self.assertEqual(self.t.close_position(ticket).request["position"], ticket)

    def test_partial_decimal_arithmetic_does_not_drop_extra_step(self):
        # Binary 0.1 * 0.7 is 0.06999999999999999, which must close 0.07.
        self.assertEqual(self.t.close_partial_buy(0.7, ticket_id=101).request["volume"], 0.07)

    def test_invalid_remaining_volume(self):
        self.m.info.volume_min = 0.1
        self.m.position_rows = [position(volume=0.15)]
        with self.assertRaises(TradeError):
            self.t.close_position(101, 0.1)
        self.m.order_send.assert_not_called()

    def test_direction_is_rechecked_after_selection(self):
        self.m.positions_get.side_effect = [(position(),), (position(side=1),)]
        with self.assertRaises(TradeError):
            self.t.close_buy(ticket_id=101)
        self.m.order_send.assert_not_called()

    def test_native_all_ticks_flag_can_be_passed_explicitly(self):
        start = datetime.now(timezone.utc) - timedelta(minutes=1)
        end = datetime.now(timezone.utc)
        self.t.get_ticks("EURUSD", start, end, flags=self.m.COPY_TICKS_ALL)
        self.assertEqual(self.m.copy_ticks_range.call_args.args[-1], -1)
        with self.assertRaises(TradeError):
            self.t.get_ticks("EURUSD", start, end, flags=True)

    def test_pending_expiry_and_stoplimit_preserved(self):
        expiry = int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp())
        self.m.order_rows = [
            order(
                type=6,
                price_open=1.12,
                price_stoplimit=1.11,
                sl=1.1,
                tp=1.13,
                type_time=2,
                time_expiration=expiry,
            )
        ]
        result = self.t.modify_order(201, price=1.121)
        self.assertEqual(result.request["stoplimit"], 1.11)
        self.assertEqual(result.request["expiration"], expiry)
        result = self.t.modify_order(201, type_time=0)
        self.assertEqual(result.request["expiration"], 0)

    def test_pending_freeze_and_missing_order(self):
        self.m.order_rows = [order(price_open=1.1021)]
        self.m.info.trade_freeze_level = 20
        with self.assertRaises(TradeError):
            self.t.cancel_order(201)
        with self.assertRaises(TradeError):
            self.t.modify_order(404, price=1.09)

    def test_pending_modify_rejects_nonfinite_stops(self):
        self.m.order_rows = [order()]
        for value in (float("nan"), -1, False):
            with self.assertRaises(TradeError):
                self.t.modify_order(201, sl=value)

    def test_none_preflight_and_calc_failures_raise(self):
        self.m.order_check.return_value = None
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")
        self.m.order_send.assert_not_called()
        self.m.order_calc_margin.side_effect = None
        self.m.order_calc_margin.return_value = None
        with self.assertRaises(TradeError):
            self.t.margin_required("EURUSD", "buy", 0.1)
        self.m.order_calc_profit.side_effect = None
        self.m.order_calc_profit.return_value = None
        with self.assertRaises(TradeError):
            self.t.calculate_volume("EURUSD", "buy", 1.1, 1.09, 100)

    def test_no_changes_and_preflight_opt_out(self):
        self.m.order_send.side_effect = None
        self.m.order_send.return_value = SimpleNamespace(retcode=10025, comment="No changes")
        self.t.preflight = False
        result = self.t.modify_tp(ticket_id=101, tp=1.13)
        self.assertEqual(result.status, "unchanged")
        self.assertTrue(result.accepted)
        self.m.order_check.assert_not_called()

    def test_delayed_initialization_and_missing_account(self):
        self.m.initialize.reset_mock()
        t = Trader(adapter=self.m, auto_initialize=False)
        self.m.initialize.assert_not_called()
        t.connect(123, "password", "Demo")
        self.m.initialize.assert_called_once()
        self.m.account = None
        with self.assertRaises(TradeError):
            t.positions()

    def test_login_verifies_account_and_server(self):
        with self.assertRaises(TradeError):
            self.t.connect(456, "password", "Other")
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")

    @unittest.skipUnless(importlib.util.find_spec("MetaTrader5"), "Native MT5 wheel not installed")
    def test_native_constant_contract_without_connection(self):
        import MetaTrader5 as native

        # Do not initialize, login, query terminal/account, or send any request.
        for filename in ("core.py", "data.py"):
            tree = ast.parse((Path(__file__).parents[1] / "MT5pytrader" / filename).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr.isupper():
                    self.assertTrue(hasattr(native, node.attr), node.attr)
                    if hasattr(self.m, node.attr):
                        self.assertEqual(getattr(self.m, node.attr), getattr(native, node.attr))


if __name__ == "__main__":
    unittest.main()
