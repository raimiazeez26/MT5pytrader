"""Queries and bounded polling; terminal failures are never empty snapshots."""

import threading

import pandas as pd

from .models import PositionEvent, TradeError
from .validation import date_range, integer, number

POSITION_COLUMNS = [
    "ticket",
    "time",
    "time_msc",
    "time_update",
    "time_update_msc",
    "type",
    "magic",
    "identifier",
    "reason",
    "volume",
    "price_open",
    "sl",
    "tp",
    "price_current",
    "swap",
    "profit",
    "symbol",
    "comment",
    "external_id",
]
DEAL_COLUMNS = [
    "ticket",
    "order",
    "time",
    "time_msc",
    "type",
    "entry",
    "magic",
    "position_id",
    "reason",
    "volume",
    "price",
    "commission",
    "swap",
    "profit",
    "fee",
    "symbol",
    "comment",
    "external_id",
]
RATE_COLUMNS = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
TICK_COLUMNS = ["time", "bid", "ask", "last", "volume", "time_msc", "flags", "volume_real"]


class DataMixin:
    def _query(self, method, **kwargs):
        self._account()
        rows = getattr(self.mt5, method)(**kwargs)
        if rows is None:
            raise self._failure(method)
        return tuple(rows)

    def positions(self, symbol=None, magic=None, side=None, *, ticket=None):
        """Return MT5 position records, filtered by all supplied criteria."""
        kwargs = {}
        if ticket is not None:
            kwargs["ticket"] = integer(ticket, "ticket", minimum=1)
        elif symbol is not None:
            kwargs["symbol"] = symbol
        rows = self._query("positions_get", **kwargs)
        side_type = self._side(side) if side is not None else None
        if magic is not None:
            magic = integer(magic, "magic")
        return tuple(
            p
            for p in rows
            if (symbol is None or p.symbol == symbol)
            and (ticket is None or p.ticket == ticket)
            and (magic is None or p.magic == magic)
            and (side_type is None or p.type == side_type)
        )

    def get_orders(self, symbol=None, magic=None, *, ticket=None):
        kwargs = {}
        if ticket is not None:
            kwargs["ticket"] = integer(ticket, "ticket", minimum=1)
        elif symbol is not None:
            kwargs["symbol"] = symbol
        rows = self._query("orders_get", **kwargs)
        if magic is not None:
            magic = integer(magic, "magic")
        return tuple(
            o
            for o in rows
            if (symbol is None or o.symbol == symbol)
            and (ticket is None or o.ticket == ticket)
            and (magic is None or o.magic == magic)
        )

    @staticmethod
    def _frame(rows, columns):
        # Canonical columns and types also exist for an empty result.
        records = [r._asdict() if hasattr(r, "_asdict") else dict(r) for r in rows]
        frame = pd.DataFrame.from_records(records, columns=columns)
        for name in columns:
            if name == "time":
                frame[name] = pd.to_datetime(frame[name], unit="s", utc=True).astype(
                    "datetime64[ns, UTC]"
                )
            elif name in {"symbol", "comment", "external_id"}:
                frame[name] = frame[name].astype("string")
            elif name in {
                "volume",
                "volume_real",
                "price",
                "price_open",
                "price_current",
                "sl",
                "tp",
                "swap",
                "profit",
                "fee",
                "commission",
                "open",
                "high",
                "low",
                "close",
                "bid",
                "ask",
                "last",
            }:
                frame[name] = pd.to_numeric(frame[name]).astype("float64")
            else:
                frame[name] = pd.to_numeric(frame[name]).astype("Int64")
        return frame

    def get_open_positions(self, symbol=None, magic=None, side=None):
        return self._frame(self.positions(symbol, magic, side), POSITION_COLUMNS)

    def running_profit(self, symbol=None, magic=None, side=None):
        return round(sum(p.profit for p in self.positions(symbol, magic, side)), 2)

    def history_deals(self, start, end, *, symbol=None, magic=None):
        self._account()
        start, end = date_range(start, end)
        rows = self.mt5.history_deals_get(start, end)
        if rows is None:
            raise self._failure("history_deals_get")
        if magic is not None:
            magic = integer(magic, "magic")
        rows = [
            r
            for r in rows
            if (symbol is None or r.symbol == symbol) and (magic is None or r.magic == magic)
        ]
        return self._frame(rows, DEAL_COLUMNS)

    def performance_report(self, start, end, *, symbol=None, magic=None):
        """Deal-level cash flow, not round-trip win rates or equity drawdown.

        BUY/SELL deals only: excludes deposits/withdrawals and separately posted
        broker adjustments. Entry commissions are included in their posting period.
        """
        frame = self.history_deals(start, end, symbol=symbol, magic=magic)
        trades = frame[frame["type"].isin([self.mt5.DEAL_TYPE_BUY, self.mt5.DEAL_TYPE_SELL])]
        totals = {
            name: float(trades[name].sum()) for name in ("profit", "commission", "swap", "fee")
        }
        return {
            "deal_count": len(trades),
            **totals,
            "realized_net": sum(totals.values()),
            "currency": self._account().currency,
        }

    def get_rates(self, symbol, timeframe, start, end):
        self._symbol(symbol)
        start, end = date_range(start, end)
        rows = self.mt5.copy_rates_range(
            symbol, integer(timeframe, "timeframe", minimum=1), start, end
        )
        if rows is None:
            raise self._failure("copy_rates_range")
        records = pd.DataFrame(rows).to_dict("records")
        return self._frame(records, RATE_COLUMNS)

    def get_ticks(self, symbol, start, end, flags=None):
        self._symbol(symbol)
        start, end = date_range(start, end)
        flags = self.mt5.COPY_TICKS_ALL if flags is None else flags
        if isinstance(flags, bool) or flags not in (
            self.mt5.COPY_TICKS_ALL,
            self.mt5.COPY_TICKS_INFO,
            self.mt5.COPY_TICKS_TRADE,
        ):
            raise TradeError("flags must be COPY_TICKS_ALL, COPY_TICKS_INFO, or COPY_TICKS_TRADE")
        flags = int(flags)
        rows = self.mt5.copy_ticks_range(symbol, start, end, flags)
        if rows is None:
            raise self._failure("copy_ticks_range")
        return self._frame(pd.DataFrame(rows).to_dict("records"), TICK_COLUMNS)

    def watch_positions(
        self,
        callback,
        *,
        symbol=None,
        magic=None,
        side=None,
        interval=1.0,
        max_polls=60,
        stop_event=None,
        reconnect=None,
        max_errors=3,
    ):
        """Bounded synchronous polling. First successful snapshot is a baseline.

        Emit opened/updated/closed for ticket, side, size, entry, SL and TP changes.
        Quotes/profit are excluded to avoid repeated events. Optional reconnect
        callback is invoked only after query failure; it must restore the same
        account. A missing query never emits false closed events. Callback failures
        propagate; polling cannot observe changes wholly between snapshots.
        """
        interval = number(interval, "interval")
        max_polls = integer(max_polls, "max_polls", minimum=1)
        max_errors = integer(max_errors, "max_errors", minimum=1)
        stop_event = stop_event or threading.Event()
        identity = self._identity
        previous = None
        errors = emitted = 0
        for index in range(max_polls):
            if stop_event.is_set():
                break
            try:
                rows = self.positions(symbol, magic, side)
                if self._identity != identity:
                    raise TradeError("Polling cannot switch accounts", code="connection")
            except TradeError:
                errors += 1
                if reconnect is None or errors >= max_errors:
                    raise
                reconnect(self)
                if self._identity != identity:
                    raise TradeError("Reconnect switched accounts", code="connection")
            else:
                errors = 0
                current = {
                    p.ticket: {
                        k: getattr(p, k)
                        for k in (
                            "ticket",
                            "symbol",
                            "type",
                            "magic",
                            "volume",
                            "price_open",
                            "sl",
                            "tp",
                        )
                    }
                    for p in rows
                }
                if previous is not None:
                    for ticket in sorted(previous.keys() | current.keys()):
                        before, after = previous.get(ticket), current.get(ticket)
                        if before != after:
                            kind = (
                                "opened"
                                if before is None
                                else "closed"
                                if after is None
                                else "updated"
                            )
                            callback(PositionEvent(kind, ticket, before, after))
                            emitted += 1
                previous = current
            if index + 1 < max_polls and stop_event.wait(interval):
                break
        return emitted

    def run_trailing_stop(
        self, ticket, distance_points, *, interval=1.0, max_polls=60, stop_event=None, callback=None
    ):
        """Bounded client-side trailing loop; must stay running. No send retries."""
        interval = number(interval, "interval")
        number(distance_points, "distance_points")
        max_polls = integer(max_polls, "max_polls", minimum=1)
        ticket = integer(ticket, "ticket", minimum=1)
        stop_event = stop_event or threading.Event()
        results = []
        for index in range(max_polls):
            if stop_event.is_set() or not self.positions(ticket=ticket):
                break
            result = self.trail_stop(ticket, distance_points)
            results.append(result)
            if callback is not None:
                callback(result)
            if not result.completed:
                break
            if index + 1 < max_polls and stop_event.wait(interval):
                break
        return results
