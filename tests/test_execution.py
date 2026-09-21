import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from MT5pytrader import ExecutionLimits, TradeError, Trader
from fake_mt5 import FakeMT5, order, position


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.m = FakeMT5()
        self.t = Trader(adapter=self.m, magic=42, comment="configured")

    def request(self):
        return self.m.order_send.call_args.args[0]

    def test_correct_quotes_both_sides(self):
        self.t.open_buy("EURUSD", stop_loss=100, take_profit=200)
        self.assertEqual(self.request()["price"], 1.1022)
        self.assertAlmostEqual(self.request()["sl"], 1.1012)
        self.t.open_sell("EURUSD", stop_loss=100, take_profit=200)
        self.assertEqual(self.request()["price"], 1.102)
        self.assertAlmostEqual(self.request()["tp"], 1.1)

    def test_constructor_defaults_and_overrides(self):
        self.t.open_buy("EURUSD")
        self.assertEqual((self.request()["magic"], self.request()["comment"]), (42, "configured"))
        self.t.open_buy("EURUSD", magic=12, comment="override")
        self.assertEqual((self.request()["magic"], self.request()["comment"]), (12, "override"))
        self.t.open_buy("EURUSD")
        self.assertEqual(self.request()["magic"], 42)

    def test_preview_and_check_never_send(self):
        req = self.t.preview_order("EURUSD", "buy")
        self.assertEqual(req["type"], 0)
        self.m.order_check.assert_not_called()
        result = self.t.check_order("EURUSD", "buy")
        self.assertTrue(result.valid)
        self.m.order_send.assert_not_called()

    def test_market_execution_omits_price(self):
        self.m.info.trade_exemode = 2
        self.m.info.filling_mode = 2
        self.t.open_buy("EURUSD")
        self.assertNotIn("price", self.request())
        self.assertEqual(self.request()["type_filling"], 1)

    def test_filling_modes(self):
        for mode, flags, expected in [(0, 0, 0), (1, 0, 0), (2, 1, 0), (2, 2, 1), (3, 0, 2)]:
            with self.subTest(mode=mode, flags=flags):
                self.m.info.trade_exemode, self.m.info.filling_mode = mode, flags
                self.assertEqual(self.t.preview_order("EURUSD", "buy")["type_filling"], expected)
        self.m.info.trade_exemode, self.m.info.filling_mode = 2, 0
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")
        self.t.type_filling = 2
        self.m.info.filling_mode = 3
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")

    def test_pending_types_and_return_filling(self):
        for side in ("buy", "sell"):
            for kind in ("limit", "stop", "stop_limit"):
                with self.subTest(side=side, kind=kind):
                    price = 1.09 if (side == "buy") == (kind == "limit") else 1.12
                    args = {"kind": kind, "price": price, "stop_loss": 100, "take_profit": 200}
                    if kind == "stop_limit":
                        args["stoplimit"] = price - 0.001 if side == "buy" else price + 0.001
                    req = self.t.preview_order("EURUSD", side, **args)
                    self.assertEqual(
                        req["type"], getattr(self.m, f"ORDER_TYPE_{side.upper()}_{kind.upper()}")
                    )
                    self.assertEqual(req["type_filling"], 2)

    def test_pending_wrappers(self):
        for side, kind, price in [
            ("buy", "limit", 1.09),
            ("sell", "limit", 1.12),
            ("buy", "stop", 1.12),
            ("sell", "stop", 1.09),
            ("buy", "stop_limit", 1.12),
            ("sell", "stop_limit", 1.09),
        ]:
            with self.subTest(side=side, kind=kind):
                kwargs = (
                    {"stoplimit": 1.11 if side == "buy" else 1.10} if kind == "stop_limit" else {}
                )
                result = getattr(self.t, f"open_{side}_{kind}")("EURUSD", price, **kwargs)
                self.assertTrue(result.completed)

    def test_invalid_pending_prices_and_expiration(self):
        for kwargs in [
            dict(kind="limit", price=1.12),
            dict(kind="stop", price=1.09),
            dict(kind="stop_limit", price=1.12, stoplimit=1.13),
            dict(kind="limit", price=1.09, type_time=2),
            dict(kind="limit", price=1.09, expiration=datetime.now(timezone.utc)),
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(TradeError):
                self.t.preview_order("EURUSD", "buy", **kwargs)
        expiry = datetime.now(timezone.utc) + timedelta(days=1)
        req = self.t.preview_order(
            "EURUSD", "buy", kind="limit", price=1.09, type_time=2, expiration=expiry
        )
        self.assertEqual(req["expiration"], int(expiry.timestamp()))

    def test_invalid_numeric_inputs_never_send(self):
        for value in (float("nan"), float("inf"), -1, 0, True, "0.1", None, 0.015):
            with self.subTest(value=value), self.assertRaises(TradeError):
                self.t.open_buy("EURUSD", lot=value)
        self.m.order_send.assert_not_called()

    def test_bad_stop_and_price_rounding(self):
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD", stop_loss=5)
        self.assertEqual(
            self.t.preview_order("EURUSD", "buy", kind="limit", price=1.090004)["price"], 1.09
        )

    def test_missing_symbol_quote_and_select_failure(self):
        self.m.info.visible = False
        self.m.symbol_select.return_value = False
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")
        self.m.info.visible = True
        self.m.tick = None
        with self.assertRaises(TradeError) as ctx:
            self.t.open_buy("EURUSD")
        self.assertEqual(ctx.exception.last_error[0], -1)
        self.m.info = None
        with self.assertRaises(TradeError):
            self.t.open_buy("UNKNOWN")
        self.m.order_send.assert_not_called()

    def test_preflight_rejection_no_send(self):
        self.m.order_check.return_value = SimpleNamespace(retcode=10019, comment="No money")
        result = self.t.open_buy("EURUSD")
        self.assertEqual(result.status, "rejected")
        self.m.order_send.assert_not_called()

    def test_result_states_no_retry(self):
        for code, status in [
            (10009, "done"),
            (10008, "placed"),
            (10010, "partial"),
            (10012, "unknown"),
            (10031, "unknown"),
            (10019, "rejected"),
        ]:
            with self.subTest(code=code):
                self.m.order_send.side_effect = None
                self.m.order_send.return_value = SimpleNamespace(
                    retcode=code, volume=0.04, order=99, deal=88, comment="result"
                )
                self.m.order_send.reset_mock()
                result = self.t.open_buy("EURUSD")
                self.assertEqual(result.status, status)
                self.assertEqual(
                    result.executed_volume, 0.04 if status in ("done", "partial") else 0
                )
                self.assertEqual(result.requested_volume, 0.1)
                self.m.order_send.assert_called_once()
        self.m.order_send.return_value = None
        self.assertEqual(self.t.open_buy("EURUSD").status, "unknown")

    def test_ticket_only_close_and_correct_sides(self):
        for side, price, opposite in [(0, 1.102, 1), (1, 1.1022, 0)]:
            self.m.position_rows = [position(side=side)]
            result = self.t.close_position(101)
            self.assertTrue(result.completed)
            self.assertEqual(
                (self.request()["price"], self.request()["type"], self.request()["position"]),
                (price, opposite, 101),
            )

    def test_symbol_closing_filters_direction_magic_and_all_tickets(self):
        self.m.position_rows = [
            position(101),
            position(102),
            position(103, 1),
            position(104, magic=9),
        ]
        results = self.t.close_buy("EURUSD", magic=42)
        self.assertEqual([r.request["position"] for r in results], [101, 102])
        self.assertEqual(self.m.order_send.call_count, 2)
        with self.assertRaises(TradeError):
            self.t.close_buy(ticket_id=103)
        with self.assertRaises(TradeError):
            self.t.close_buy(symbol="OTHER", ticket_id=101)

    def test_missing_ticket_or_selection_raises(self):
        for operation in (
            lambda: self.t.close_buy(),
            lambda: self.t.modify_tp(ticket_id=404, tp=1.12),
        ):
            with self.assertRaises(TradeError):
                operation()
        self.m.order_send.assert_not_called()

    def test_partial_step_floor_and_remainder(self):
        self.m.info.volume_step = self.m.info.volume_min = 0.001
        self.m.position_rows = [position(volume=0.015)]
        result = self.t.close_partial_buy(0.5, ticket_id=101)
        self.assertEqual(result.request["volume"], 0.007)
        self.m.info.volume_step = self.m.info.volume_min = 0.01
        self.m.position_rows = [position(volume=0.01)]
        with self.assertRaises(TradeError):
            self.t.close_partial_buy(0.1, ticket_id=101)
        for percent in (float("nan"), 0, 2, -1):
            with self.assertRaises(TradeError):
                self.t.close_partial_buy(percent, ticket_id=101)
        with self.assertRaises(TradeError):
            self.t.close_position(101, 0.02)

    def test_batch_collects_per_ticket_errors(self):
        self.m.position_rows = [position(101, volume=0.01), position(102, volume=0.1)]
        results = self.t.close_partial_buy(0.1, symbol="EURUSD")
        self.assertEqual([r.status for r in results], ["error", "done"])

    def test_break_even_preserves_tp_both_sides(self):
        for side in (0, 1):
            self.m.position_rows = [position(side=side)]
            self.t.break_even(ticket_id=101, offset_points=10)
            self.assertEqual(self.request()["tp"], self.m.position_rows[0].tp)
            expected = self.m.position_rows[0].price_open + (0.0001 if side == 0 else -0.0001)
            self.assertAlmostEqual(self.request()["sl"], expected)

    def test_break_even_never_loosens_or_moves_losing_trade(self):
        for row in [position(sl=1.101), position(101, 1, sl=1.105), position(profit=-1)]:
            self.m.position_rows = [row]
            self.assertEqual(self.t.break_even(ticket_id=101).status, "unchanged")
        self.m.order_send.assert_not_called()

    def test_modify_preserves_other_stop_and_can_remove(self):
        self.t.modify_sl(ticket_id=101, sl=1.10)
        self.assertEqual(self.request()["tp"], 1.12)
        self.t.modify_tp(ticket_id=101, tp=0)
        self.assertEqual((self.request()["sl"], self.request()["tp"]), (1.09, 0))

    def test_freeze_and_minimum_distance(self):
        self.m.info.trade_freeze_level = 2000
        with self.assertRaises(TradeError):
            self.t.modify_sl(ticket_id=101, sl=1.101)

    def test_pending_modify_preserves_fields_and_cancel_uses_order(self):
        self.m.order_rows = [order()]
        self.t.modify_order(201, price=1.091)
        self.assertEqual(
            (self.request()["sl"], self.request()["tp"], self.request()["order"]), (1.08, 1.12, 201)
        )
        self.t.cancel_order(201)
        self.assertEqual(self.request(), {"action": 8, "order": 201})

    def test_limits_block_opening_but_allow_exit(self):
        for limits in [
            ExecutionLimits(allowed_symbols=frozenset({"GBPUSD"})),
            ExecutionLimits(max_spread_points=10),
            ExecutionLimits(max_exposure_lots=0.15),
        ]:
            self.t.limits = limits
            with self.assertRaises(TradeError):
                self.t.open_buy("EURUSD")
        self.t.close_position(101)
        self.m.order_send.assert_called_once()

    def test_exposure_includes_pending_orders(self):
        self.m.order_rows = [order(volume_current=0.5)]
        self.t.limits = ExecutionLimits(max_exposure_lots=0.6)
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")

    def test_risk_sizing_in_account_currency(self):
        result = self.t.calculate_volume("EURUSD", "buy", 1.10, 1.09, 105)
        self.assertEqual(result.volume, 0.10)
        self.assertLessEqual(result.estimated_loss, 105)
        self.assertEqual((result.margin, result.currency), (100, "USD"))
        with self.assertRaises(TradeError):
            self.t.calculate_volume("EURUSD", "buy", 1.1, 1.09, 1)
        with self.assertRaises(TradeError):
            self.t.calculate_volume("EURUSD", "sell", 1.1, 1.09, 100)

    def test_initialization_failure_and_login_fail_closed(self):
        self.m.initialize.return_value = False
        with self.assertRaises(TradeError):
            Trader(adapter=self.m)
        self.m.login.return_value = False
        with self.assertRaises(TradeError):
            self.t.connect(123, "secret", "Demo")
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")
        self.m.order_send.assert_not_called()

    def test_account_switch_and_trading_permission(self):
        self.m.terminal.tradeapi_disabled = True
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")
        self.m.account.login = 456
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")

    def test_context_shutdown_terminal_path_no_password_retention(self):
        with Trader(adapter=self.m, path="terminal.exe") as trader:
            trader.connect(123, "secret", "Demo")
            self.assertNotIn("secret", str(trader.__dict__))
        self.m.initialize.assert_called_with("terminal.exe")
        self.m.shutdown.assert_called_once()

    def test_audit_log_excludes_sensitive_comment(self):
        with self.assertLogs("MT5pytrader", level="INFO") as logs:
            self.t.open_buy("EURUSD", comment="private-comment")
        event = logs.records[0].mt5_event
        self.assertEqual(event["status"], "done")
        self.assertNotIn("private-comment", str(event))


if __name__ == "__main__":
    unittest.main()
