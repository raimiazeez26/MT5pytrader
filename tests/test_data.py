import unittest
from datetime import datetime, timedelta, timezone

from MT5pytrader import ExecutionLimits, TradeError, Trader
from fake_mt5 import Deal, FakeMT5, NoWait, position

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(days=1)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.m = FakeMT5()
        self.t = Trader(adapter=self.m)

    def test_empty_positions_schema_and_zero_profit(self):
        self.m.position_rows = []
        frame = self.t.get_open_positions()
        self.assertTrue(frame.empty)
        self.assertIn("magic", frame.columns)
        self.assertEqual(str(frame.time.dtype), "datetime64[ns, UTC]")
        self.assertEqual(self.t.running_profit(), 0.0)

    def test_query_failures_are_not_empty_or_zero(self):
        self.m.positions_get.side_effect = None
        self.m.positions_get.return_value = None
        for method in (self.t.get_open_positions, self.t.running_profit):
            with self.assertRaises(TradeError):
                method()
        self.m.orders_get.side_effect = None
        self.m.orders_get.return_value = None
        with self.assertRaises(TradeError):
            self.t.get_orders()

    def test_filters_and_profit_named_field(self):
        self.m.position_rows = [
            position(),
            position(102, side=1, profit=-5),
            position(103, magic=7, profit=99),
        ]
        self.assertEqual(self.t.running_profit(magic=42), 15)
        frame = self.t.get_open_positions(magic=42, side="sell")
        self.assertEqual(list(frame.ticket), [102])
        self.assertEqual(list(frame.magic), [42])

    def test_history_costs_deposits_and_filters(self):
        self.m.history_deals_get.return_value = (
            Deal(
                ticket=1,
                type=0,
                entry=0,
                profit=0,
                commission=-2,
                fee=-1,
                symbol="EURUSD",
                magic=42,
            ),
            Deal(
                ticket=2,
                type=1,
                entry=1,
                profit=100,
                swap=-3,
                commission=-2,
                symbol="EURUSD",
                magic=42,
            ),
            Deal(ticket=3, type=2, profit=500, symbol="", magic=0),
        )
        report = self.t.performance_report(START, END)
        self.assertEqual(report["realized_net"], 92)
        self.assertEqual(report["deal_count"], 2)
        self.assertEqual(len(self.t.history_deals(START, END, magic=42)), 2)
        self.assertEqual(self.t.performance_report(START, END, symbol="OTHER")["realized_net"], 0)

    def test_daily_loss_blocks_opens(self):
        self.m.history_deals_get.return_value = (Deal(type=0, profit=-100, commission=-5),)
        self.t.limits = ExecutionLimits(max_daily_loss=80)
        with self.assertRaises(TradeError):
            self.t.open_buy("EURUSD")
        self.m.order_send.assert_not_called()
        self.t.close_position(101)

    def test_naive_reversed_dates_and_query_failure(self):
        for start, end in [(START.replace(tzinfo=None), END), (END, START)]:
            with self.assertRaises(TradeError):
                self.t.history_deals(start, end)
        self.m.history_deals_get.return_value = None
        with self.assertRaises(TradeError):
            self.t.history_deals(START, END)

    def test_rates_and_ticks_stable_empty_schema_and_utc(self):
        rates = self.t.get_rates("EURUSD", 1, START, END)
        ticks = self.t.get_ticks("EURUSD", START, END)
        self.assertEqual(
            list(rates.columns),
            ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"],
        )
        self.assertEqual(str(ticks.time.dtype), "datetime64[ns, UTC]")
        self.m.copy_rates_range.return_value = [
            dict(
                time=0, open=1, high=2, low=0.5, close=1.5, tick_volume=10, spread=2, real_volume=5
            )
        ]
        self.assertEqual(
            self.t.get_rates("EURUSD", 1, START, END).iloc[0].time,
            datetime(1970, 1, 1, tzinfo=timezone.utc),
        )
        self.m.copy_ticks_range.return_value = None
        with self.assertRaises(TradeError):
            self.t.get_ticks("EURUSD", START, END)

    def test_polling_deduplicates_and_tracks_changes(self):
        first = position()
        second = first._replace(volume=0.05)
        self.m.positions_get.side_effect = [
            (first,),
            (first._replace(profit=25),),
            (first, position(102)),
            (second,),
            (),
        ]
        events = []
        count = self.t.watch_positions(events.append, max_polls=5, stop_event=NoWait())
        self.assertEqual(count, 4)
        self.assertEqual(
            [(e.kind, e.ticket) for e in events],
            [("opened", 102), ("updated", 101), ("closed", 102), ("closed", 101)],
        )

    def test_poll_failure_does_not_emit_false_closes(self):
        self.m.positions_get.side_effect = [(position(),), None, (position(),)]
        events, reconnections = [], []
        count = self.t.watch_positions(
            events.append,
            max_polls=3,
            stop_event=NoWait(),
            reconnect=lambda t: reconnections.append(t),
        )
        self.assertEqual(count, 0)
        self.assertEqual(len(reconnections), 1)

    def test_poll_limits_stop_and_callback_errors(self):
        stop = NoWait()
        stop.stopped = True
        self.assertEqual(self.t.watch_positions(lambda e: None, stop_event=stop), 0)
        self.m.positions_get.assert_not_called()
        self.m.positions_get.side_effect = [None, None]
        with self.assertRaises(TradeError):
            self.t.watch_positions(
                lambda e: None, max_errors=2, reconnect=lambda t: None, stop_event=NoWait()
            )
        self.m.positions_get.side_effect = [(position(),), ()]

        def callback(_):
            raise ValueError("callback failure")

        with self.assertRaises(ValueError):
            self.t.watch_positions(callback, max_polls=2, stop_event=NoWait())

    def test_poll_reconnect_rejects_account_switch(self):
        self.m.positions_get.side_effect = None
        self.m.positions_get.return_value = None

        def reconnect(t):
            t._identity = (999, "Other")

        with self.assertRaisesRegex(TradeError, "switched accounts"):
            self.t.watch_positions(lambda e: None, reconnect=reconnect, stop_event=NoWait())

    def test_trailing_does_not_loosen_or_duplicate(self):
        self.m.position_rows = [position(sl=1.101)]
        self.assertEqual(self.t.trail_stop(101, 200).status, "unchanged")
        first = self.t.trail_stop(101, 50)
        self.assertEqual(first.request["sl"], 1.1015)
        self.assertEqual(first.request["tp"], 1.12)
        self.m.position_rows = [position(sl=1.1015)]
        self.assertEqual(self.t.trail_stop(101, 50).status, "unchanged")
        self.assertEqual(self.m.order_send.call_count, 1)

    def test_trailing_sell_and_bounded_manager(self):
        self.m.position_rows = [position(side=1, sl=1.12)]
        self.assertAlmostEqual(self.t.trail_stop(101, 50).request["sl"], 1.1027)
        self.m.position_rows = [position(sl=1.101)]
        results = self.t.run_trailing_stop(101, 200, max_polls=2, stop_event=NoWait())
        self.assertEqual([r.status for r in results], ["unchanged", "unchanged"])

    def test_trailing_stops_after_unknown_result(self):
        self.m.order_send.side_effect = None
        self.m.order_send.return_value = None
        results = self.t.run_trailing_stop(101, 50, max_polls=5, stop_event=NoWait())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "unknown")


if __name__ == "__main__":
    unittest.main()
