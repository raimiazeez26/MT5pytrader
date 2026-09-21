"""Validated synchronous execution using an injectable MT5 adapter."""

import importlib
import logging
import math
from datetime import datetime, timezone
from decimal import Decimal

from .data import DataMixin
from .models import CheckResult, ExecutionLimits, RiskEstimate, TradeError, TradeResult
from .validation import integer, number, quantize, utc

logger = logging.getLogger("MT5pytrader")

# SYMBOL_FILLING_* are MQL5 bit flags, not exported by the Python extension.
# https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants
_FILLING_FOK_FLAG = 1
_FILLING_IOC_FLAG = 2


class Trader(DataMixin):
    """Manage a process-wide MT5 connection; do not use concurrently.

    Constructor initializes by default. Passwords are neither retained nor logged.
    ``adapter`` permits testing without the native MetaTrader5 package.
    """

    def __init__(
        self,
        comment="MT5pytrader",
        magic=260000,
        deviation=20,
        type_time=None,
        type_filling=None,
        *,
        path=None,
        adapter=None,
        auto_initialize=True,
        preflight=True,
        limits=None,
    ):
        if adapter is None:
            try:
                adapter = importlib.import_module("MetaTrader5")
            except ImportError as exc:
                raise TradeError(
                    "Install MetaTrader5 on a supported Windows/Python environment",
                    code="connection",
                ) from exc
        self.mt5 = adapter
        self.comment = self._comment(comment)
        self.magic = integer(magic, "magic")
        self.deviation = integer(deviation, "deviation")
        self.type_time = adapter.ORDER_TIME_GTC if type_time is None else type_time
        self.type_filling = type_filling
        self.path = path
        self.preflight = preflight
        self.limits = limits or ExecutionLimits()
        for name in ("max_spread_points", "max_exposure_lots", "max_daily_loss"):
            if getattr(self.limits, name) is not None:
                number(getattr(self.limits, name), name)
        self._ready = False
        self._initialized = False
        self._identity = None
        if auto_initialize:
            self.initialize()

    def __repr__(self):
        return f"Trader(connected={self._ready}, magic={self.magic})"

    @staticmethod
    def _comment(value):
        if not isinstance(value, str) or len(value) > 31:
            raise TradeError("comment must be a string of at most 31 characters")
        return value

    def _failure(self, operation):
        return TradeError(f"{operation} failed", code="terminal", last_error=self.mt5.last_error())

    def initialize(self):
        self._ready = False
        args = () if self.path is None else (str(self.path),)
        if not self.mt5.initialize(*args):
            raise self._failure("initialize")
        self._initialized = True
        account = self.mt5.account_info()
        self._identity = None if account is None else (account.login, account.server)
        self._ready = account is not None
        return self

    def connect(self, account, password, server):
        self._ready = False
        account = integer(account, "account", minimum=1)
        if not isinstance(password, str) or not isinstance(server, str) or not server:
            raise TradeError("password and server must be strings; server must not be empty")
        if not self._initialized:
            self.initialize()
            self._ready = False
        if not self.mt5.login(account, password=password, server=server):
            raise self._failure("login")
        info = self.mt5.account_info()
        if info is None or (info.login, info.server) != (account, server):
            raise TradeError("Active account does not match requested account", code="connection")
        self._identity = (account, server)
        self._ready = True
        return info

    def disconnect(self):
        self._ready = False
        self._identity = None
        if self._initialized:
            self.mt5.shutdown()
            self._initialized = False

    def __enter__(self):
        if not self._initialized:
            self.initialize()
        return self

    def __exit__(self, *_):
        self.disconnect()

    def _account(self):
        if not self._ready:
            raise TradeError("Connect to an account before this operation", code="connection")
        account = self.mt5.account_info()
        if account is None:
            raise self._failure("account_info")
        if (account.login, account.server) != self._identity:
            self._ready = False
            raise TradeError("Active account changed; reconnect explicitly", code="connection")
        return account

    def _symbol(self, symbol):
        self._account()
        if not isinstance(symbol, str) or not symbol:
            raise TradeError("symbol must be a nonempty string")
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise self._failure(f"symbol_info({symbol})")
        if not info.visible:
            if not self.mt5.symbol_select(symbol, True):
                raise self._failure(f"symbol_select({symbol})")
            info = self.mt5.symbol_info(symbol)
            if info is None:
                raise self._failure(f"symbol_info({symbol})")
        return info

    def _tick(self, symbol):
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            raise self._failure(f"symbol_info_tick({symbol})")
        bid, ask = number(tick.bid, "bid"), number(tick.ask, "ask")
        if ask < bid:
            raise TradeError("Quote ask is below bid", code="quote")
        return tick

    def _side(self, side):
        if side == "buy":
            return self.mt5.ORDER_TYPE_BUY
        if side == "sell":
            return self.mt5.ORDER_TYPE_SELL
        raise TradeError("side must be 'buy' or 'sell'")

    def _price(self, value, info):
        return number(
            quantize(number(value, "price"), info.trade_tick_size or info.point), "normalized price"
        )

    def _volume(self, value, info, *, floor=False):
        value = number(value, "volume")
        rounded = quantize(value, info.volume_step, floor=floor)
        if not floor and not math.isclose(value, rounded, abs_tol=1e-9, rel_tol=1e-9):
            raise TradeError(f"volume must be a multiple of {info.volume_step}")
        if rounded < info.volume_min - 1e-9 or rounded > info.volume_max + 1e-9:
            raise TradeError(f"volume must be between {info.volume_min} and {info.volume_max}")
        return rounded

    def _filling(self, info, *, pending=False):
        m = self.mt5
        if pending:
            return m.ORDER_FILLING_RETURN
        mode = info.trade_exemode
        if mode in (m.SYMBOL_TRADE_EXECUTION_INSTANT, m.SYMBOL_TRADE_EXECUTION_REQUEST):
            allowed = [m.ORDER_FILLING_FOK, m.ORDER_FILLING_IOC, m.ORDER_FILLING_RETURN]
        else:
            allowed = []
            if info.filling_mode & _FILLING_FOK_FLAG:
                allowed.append(m.ORDER_FILLING_FOK)
            if info.filling_mode & _FILLING_IOC_FLAG:
                allowed.append(m.ORDER_FILLING_IOC)
            if mode != m.SYMBOL_TRADE_EXECUTION_MARKET:
                allowed.append(m.ORDER_FILLING_RETURN)
        if self.type_filling is not None:
            if self.type_filling not in allowed:
                raise TradeError("Configured filling policy is unsupported for this symbol")
            return self.type_filling
        if not allowed:
            raise TradeError("No supported filling policy for this symbol")
        return allowed[0]

    def _expiration(self, type_time, expiration):
        m = self.mt5
        type_time = self.type_time if type_time is None else type_time
        if type_time not in (
            m.ORDER_TIME_GTC,
            m.ORDER_TIME_DAY,
            m.ORDER_TIME_SPECIFIED,
            m.ORDER_TIME_SPECIFIED_DAY,
        ):
            raise TradeError("Unsupported order time policy")
        if type_time in (m.ORDER_TIME_SPECIFIED, m.ORDER_TIME_SPECIFIED_DAY):
            expiry = utc(expiration, "expiration")
            if expiry <= datetime.now(timezone.utc):
                raise TradeError("expiration must be in the future")
            return type_time, int(expiry.timestamp())
        if expiration is not None:
            raise TradeError("expiration requires a specified expiration policy")
        return type_time, 0

    def _stops(self, side, reference, sl, tp, info, *, modifying=False):
        distance = info.trade_stops_level * info.point
        if modifying:
            distance = max(distance, info.trade_freeze_level * info.point)
        sign = 1 if side == "buy" else -1
        for name, price, delta in (("sl", sl, -1), ("tp", tp, 1)):
            if price:
                gap = (price - reference) * sign * delta
                if gap <= 0 or gap < distance - 1e-10:
                    raise TradeError(f"{name} violates direction or broker stop/freeze distance")
                if (
                    modifying
                    and info.trade_freeze_level
                    and gap <= info.trade_freeze_level * info.point + 1e-10
                ):
                    raise TradeError(f"{name} is inside broker freeze distance")

    def _pending_price(self, side, kind, price, stoplimit, tick, info):
        distance = info.trade_stops_level * info.point
        quote = tick.ask if side == "buy" else tick.bid
        sign = 1 if side == "buy" else -1
        gap = (price - quote) * sign * (-1 if kind == "limit" else 1)
        if gap <= 0 or gap < distance - 1e-10:
            raise TradeError("Pending price violates market direction or minimum distance")
        if kind == "stop_limit" and (stoplimit - price) * sign > 0:
            raise TradeError(
                "Stop-limit price must be at/below buy trigger or at/above sell trigger"
            )

    def preview_order(
        self,
        symbol,
        side,
        lot=0.1,
        *,
        kind="market",
        price=None,
        stoplimit=None,
        stop_loss=None,
        take_profit=None,
        magic=None,
        comment=None,
        type_time=None,
        expiration=None,
    ):
        """Build/validate without order_check/order_send. SL/TP are point distances."""
        info = self._symbol(symbol)
        tick = self._tick(symbol)
        self._side(side)
        if kind not in {"market", "limit", "stop", "stop_limit"}:
            raise TradeError("kind must be market, limit, stop, or stop_limit")
        pending = kind != "market"
        if not pending and (price is not None or stoplimit is not None or expiration is not None):
            raise TradeError("Market orders do not accept price, stoplimit, or expiration")
        if kind != "stop_limit" and stoplimit is not None:
            raise TradeError("stoplimit is only valid for stop_limit orders")
        entry = self._price(price if pending else (tick.ask if side == "buy" else tick.bid), info)
        limit = self._price(stoplimit, info) if kind == "stop_limit" else None
        if pending:
            self._pending_price(side, kind, entry, limit, tick, info)
        sign = 1 if side == "buy" else -1
        base = limit if limit is not None else entry
        sl = (
            0.0
            if stop_loss is None
            else self._price(base - sign * number(stop_loss, "stop_loss") * info.point, info)
        )
        tp = (
            0.0
            if take_profit is None
            else self._price(base + sign * number(take_profit, "take_profit") * info.point, info)
        )
        reference = base if pending else (tick.bid if side == "buy" else tick.ask)
        self._stops(side, reference, sl, tp, info)
        order_name = "ORDER_TYPE_" + side.upper() + ("" if not pending else "_" + kind.upper())
        request = {
            "action": self.mt5.TRADE_ACTION_PENDING if pending else self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self._volume(lot, info),
            "type": getattr(self.mt5, order_name),
            "magic": self.magic if magic is None else integer(magic, "magic"),
            "comment": self.comment if comment is None else self._comment(comment),
            "deviation": self.deviation,
            "sl": sl,
            "tp": tp,
            "type_filling": self._filling(info, pending=pending),
        }
        if pending or info.trade_exemode != self.mt5.SYMBOL_TRADE_EXECUTION_MARKET:
            request["price"] = entry
        if pending:
            request["type_time"], request["expiration"] = self._expiration(type_time, expiration)
        elif type_time is not None:
            raise TradeError("type_time is only configurable for pending orders")
        if limit is not None:
            request["stoplimit"] = limit
        self._limits(request, info, tick)
        return request

    def _limits(self, request, info, tick):
        limits = self.limits
        if limits.allowed_symbols is not None and request["symbol"] not in limits.allowed_symbols:
            raise TradeError("Symbol is not allowed by execution limits", code="limit")
        if (
            limits.max_spread_points is not None
            and (tick.ask - tick.bid) / info.point > limits.max_spread_points + 1e-9
        ):
            raise TradeError("Spread exceeds execution limit", code="limit")
        if limits.max_exposure_lots is not None:
            exposure = sum(p.volume for p in self.positions()) + sum(
                o.volume_current for o in self.get_orders()
            )
            if exposure + request["volume"] > limits.max_exposure_lots + 1e-9:
                raise TradeError("Gross account exposure exceeds limit", code="limit")
        if limits.max_daily_loss is not None:
            now = datetime.now(timezone.utc)
            report = self.performance_report(
                now.replace(hour=0, minute=0, second=0, microsecond=0), now
            )
            pnl = report["realized_net"] + sum(p.profit + p.swap for p in self.positions())
            if pnl <= -limits.max_daily_loss:
                raise TradeError("Daily loss limit reached", code="limit")

    def check_order(self, *args, **kwargs):
        """Preview an opening order then run the broker's non-executing check."""
        return self._check(self.preview_order(*args, **kwargs))

    def _check(self, request):
        result = self.mt5.order_check(dict(request))
        if result is None:
            raise self._failure("order_check")
        return CheckResult(
            result.retcode == 0,
            dict(request),
            result.retcode,
            getattr(result, "comment", ""),
            result,
        )

    def _send(self, request):
        account = self._account()
        terminal = self.mt5.terminal_info()
        if terminal is None:
            raise self._failure("terminal_info")
        if (
            not terminal.trade_allowed
            or terminal.tradeapi_disabled
            or not account.trade_allowed
            or not account.trade_expert
        ):
            raise TradeError("Trading is disabled in terminal/account settings", code="permission")
        if self.preflight:
            check = self._check(request)
            if not check.valid:
                return self._result(
                    "rejected", request, check.raw, message="Preflight: " + check.message
                )
        # An ambiguous result must be reconciled, never blindly retried.
        raw = self.mt5.order_send(dict(request))
        if raw is None:
            return self._result(
                "unknown",
                request,
                last_error=self.mt5.last_error(),
                message="Execution outcome unknown; reconcile orders/deals before retrying",
            )
        m = self.mt5
        if raw.retcode == m.TRADE_RETCODE_DONE:
            status = "done"
        elif raw.retcode == m.TRADE_RETCODE_PLACED:
            status = "placed"
        elif (
            raw.retcode == m.TRADE_RETCODE_DONE_PARTIAL and request["action"] == m.TRADE_ACTION_DEAL
        ):
            status = "partial"
        elif raw.retcode in (m.TRADE_RETCODE_TIMEOUT, m.TRADE_RETCODE_CONNECTION):
            status = "unknown"
        elif raw.retcode == m.TRADE_RETCODE_NO_CHANGES and request["action"] in (
            m.TRADE_ACTION_SLTP,
            m.TRADE_ACTION_MODIFY,
        ):
            status = "unchanged"
        else:
            status = "rejected"
        return self._result(status, request, raw)

    def _result(self, status, request, raw=None, *, message=None, last_error=None):
        executed = (
            getattr(raw, "volume", 0.0)
            if status in {"done", "partial"} and request.get("action") == self.mt5.TRADE_ACTION_DEAL
            else 0.0
        )
        result = TradeResult(
            status,
            dict(request),
            getattr(raw, "retcode", None),
            getattr(raw, "order", 0),
            getattr(raw, "deal", 0),
            request.get("volume", 0.0),
            executed,
            message if message is not None else getattr(raw, "comment", ""),
            last_error,
            raw,
        )
        # Exclude account IDs, credentials, request comments and raw replies.
        logger.info(
            "mt5_operation",
            extra={
                "mt5_event": {
                    "status": status,
                    "action": request.get("action"),
                    "symbol": request.get("symbol"),
                    "position": request.get("position"),
                    "retcode": result.retcode,
                    "order": result.order,
                    "deal": result.deal,
                    "requested_volume": result.requested_volume,
                    "executed_volume": result.executed_volume,
                }
            },
        )
        return result

    def _open(self, side, symbol, lot, stop_loss, take_profit, magic, comment, **kwargs):
        return self._send(
            self.preview_order(
                symbol,
                side,
                lot,
                stop_loss=stop_loss,
                take_profit=take_profit,
                magic=magic,
                comment=comment,
                **kwargs,
            )
        )

    def open_buy(self, symbol, lot=0.1, stop_loss=None, take_profit=None, magic=None, comment=None):
        return self._open("buy", symbol, lot, stop_loss, take_profit, magic, comment)

    def open_sell(
        self, symbol, lot=0.1, stop_loss=None, take_profit=None, magic=None, comment=None
    ):
        return self._open("sell", symbol, lot, stop_loss, take_profit, magic, comment)

    def open_buy_limit(
        self,
        symbol,
        price,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=None,
        comment=None,
        **kwargs,
    ):
        return self._open(
            "buy",
            symbol,
            lot,
            stop_loss,
            take_profit,
            magic,
            comment,
            kind="limit",
            price=price,
            **kwargs,
        )

    def open_sell_limit(
        self,
        symbol,
        price,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=None,
        comment=None,
        **kwargs,
    ):
        return self._open(
            "sell",
            symbol,
            lot,
            stop_loss,
            take_profit,
            magic,
            comment,
            kind="limit",
            price=price,
            **kwargs,
        )

    def open_buy_stop(
        self,
        symbol,
        price,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=None,
        comment=None,
        **kwargs,
    ):
        return self._open(
            "buy",
            symbol,
            lot,
            stop_loss,
            take_profit,
            magic,
            comment,
            kind="stop",
            price=price,
            **kwargs,
        )

    def open_sell_stop(
        self,
        symbol,
        price,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=None,
        comment=None,
        **kwargs,
    ):
        return self._open(
            "sell",
            symbol,
            lot,
            stop_loss,
            take_profit,
            magic,
            comment,
            kind="stop",
            price=price,
            **kwargs,
        )

    def open_buy_stop_limit(
        self,
        symbol,
        price,
        stoplimit,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=None,
        comment=None,
        **kwargs,
    ):
        return self._open(
            "buy",
            symbol,
            lot,
            stop_loss,
            take_profit,
            magic,
            comment,
            kind="stop_limit",
            price=price,
            stoplimit=stoplimit,
            **kwargs,
        )

    def open_sell_stop_limit(
        self,
        symbol,
        price,
        stoplimit,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=None,
        comment=None,
        **kwargs,
    ):
        return self._open(
            "sell",
            symbol,
            lot,
            stop_loss,
            take_profit,
            magic,
            comment,
            kind="stop_limit",
            price=price,
            stoplimit=stoplimit,
            **kwargs,
        )

    def _selection(self, symbol, ticket_id, magic=None, side=None):
        if ticket_id is None and symbol is None:
            raise TradeError("Specify symbol or ticket_id explicitly for management operations")
        positions = self.positions(symbol=symbol, ticket=ticket_id, magic=magic, side=side)
        if ticket_id is not None and not positions:
            raise TradeError(
                "Position not found or does not match symbol/magic/side", code="not_found"
            )
        return positions

    def _batch(self, positions, operation):
        results = []
        for position in positions:
            try:
                results.append(operation(position))
            except TradeError as exc:
                results.append(
                    self._result(
                        "error",
                        {"position": position.ticket, "symbol": position.symbol},
                        message=str(exc),
                        last_error=exc.last_error,
                    )
                )
        return results

    def close_position(self, ticket, volume=None, *, symbol=None, magic=None, side=None):
        """Close a current position ticket using its actual direction."""
        position = self._selection(symbol, ticket, magic, side)[0]
        info = self._symbol(position.symbol)
        tick = self._tick(position.symbol)
        volume = self._volume(position.volume if volume is None else volume, info)
        if volume > position.volume + 1e-9:
            raise TradeError("Close volume exceeds position volume")
        remainder = position.volume - volume
        if remainder > 1e-9:
            self._volume(remainder, info)
        buy = position.type == self.mt5.ORDER_TYPE_BUY
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "position": position.ticket,
            "volume": volume,
            "type": self.mt5.ORDER_TYPE_SELL if buy else self.mt5.ORDER_TYPE_BUY,
            "deviation": self.deviation,
            "type_filling": self._filling(info),
            "magic": self.magic,
            "comment": self.comment,
        }
        if info.trade_exemode != self.mt5.SYMBOL_TRADE_EXECUTION_MARKET:
            request["price"] = tick.bid if buy else tick.ask
        return self._send(request)

    def _close_selected(self, side, symbol, ticket_id, magic, percent=1.0):
        percent = number(percent, "percent")
        if percent > 1:
            raise TradeError("percent must be in (0, 1]")
        positions = self._selection(symbol, ticket_id, magic, side)

        def close(position):
            info = self._symbol(position.symbol)
            volume = self._volume(
                Decimal(str(position.volume)) * Decimal(str(percent)), info, floor=True
            )
            return self.close_position(
                position.ticket, volume, symbol=position.symbol, magic=magic, side=side
            )

        return close(positions[0]) if ticket_id is not None else self._batch(positions, close)

    def close_buy(self, symbol=None, ticket_id=None, *, magic=None):
        return self._close_selected("buy", symbol, ticket_id, magic)

    def close_sell(self, symbol=None, ticket_id=None, *, magic=None):
        return self._close_selected("sell", symbol, ticket_id, magic)

    def close_partial_buy(self, percent, symbol=None, ticket_id=None, *, magic=None):
        return self._close_selected("buy", symbol, ticket_id, magic, percent)

    def close_partial_sell(self, percent, symbol=None, ticket_id=None, *, magic=None):
        return self._close_selected("sell", symbol, ticket_id, magic, percent)

    def _modify_position(self, position, *, sl=None, tp=None, improve_only=False):
        info = self._symbol(position.symbol)
        tick = self._tick(position.symbol)
        side = "buy" if position.type == self.mt5.ORDER_TYPE_BUY else "sell"
        sl = position.sl if sl is None else (0.0 if sl == 0 else self._price(sl, info))
        tp = position.tp if tp is None else (0.0 if tp == 0 else self._price(tp, info))
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": position.ticket,
            "sl": sl,
            "tp": tp,
        }
        better = not position.sl or (sl > position.sl if side == "buy" else sl < position.sl)
        if (sl == position.sl and tp == position.tp) or (improve_only and not better):
            return self._result(
                "unchanged", request, message="Existing protection is equal or better"
            )
        reference = tick.bid if side == "buy" else tick.ask
        freeze = info.trade_freeze_level * info.point
        if freeze and any(
            p and abs(reference - p) <= freeze + 1e-10 for p in (position.sl, position.tp)
        ):
            raise TradeError("Existing protective level is inside the broker freeze distance")
        self._stops(side, reference, sl, tp, info, modifying=True)
        return self._send(request)

    def _manage(self, symbol, ticket_id, magic, operation):
        positions = self._selection(symbol, ticket_id, magic)
        return (
            operation(positions[0]) if ticket_id is not None else self._batch(positions, operation)
        )

    def modify_sl(self, symbol=None, ticket_id=None, sl=None, *, magic=None):
        number(sl, "sl", positive=False)
        return self._manage(symbol, ticket_id, magic, lambda p: self._modify_position(p, sl=sl))

    def modify_tp(self, symbol=None, ticket_id=None, tp=None, *, magic=None):
        number(tp, "tp", positive=False)
        return self._manage(symbol, ticket_id, magic, lambda p: self._modify_position(p, tp=tp))

    def break_even(self, symbol=None, ticket_id=None, *, offset_points=0, magic=None):
        offset = number(offset_points, "offset_points", positive=False)

        def move(position):
            if position.profit <= 0:
                return self._result(
                    "unchanged", {"position": position.ticket}, message="Position is not in profit"
                )
            info = self._symbol(position.symbol)
            sign = 1 if position.type == self.mt5.ORDER_TYPE_BUY else -1
            return self._modify_position(
                position, sl=position.price_open + sign * offset * info.point, improve_only=True
            )

        return self._manage(symbol, ticket_id, magic, move)

    def trail_stop(self, ticket, distance_points):
        distance = number(distance_points, "distance_points")
        position = self._selection(None, ticket)[0]
        info = self._symbol(position.symbol)
        tick = self._tick(position.symbol)
        price = (
            tick.bid - distance * info.point
            if position.type == self.mt5.ORDER_TYPE_BUY
            else tick.ask + distance * info.point
        )
        return self._modify_position(position, sl=price, improve_only=True)

    def _order(self, ticket):
        orders = self.get_orders(ticket=ticket)
        if not orders:
            raise TradeError("Pending order not found", code="not_found")
        return orders[0]

    def _order_unfrozen(self, order, info, tick):
        buy = order.type in (
            self.mt5.ORDER_TYPE_BUY_LIMIT,
            self.mt5.ORDER_TYPE_BUY_STOP,
            self.mt5.ORDER_TYPE_BUY_STOP_LIMIT,
        )
        if (
            info.trade_freeze_level
            and abs(order.price_open - (tick.ask if buy else tick.bid))
            <= info.trade_freeze_level * info.point
        ):
            raise TradeError("Pending order is within broker freeze distance")

    def cancel_order(self, ticket):
        order = self._order(ticket)
        info = self._symbol(order.symbol)
        self._order_unfrozen(order, info, self._tick(order.symbol))
        return self._send({"action": self.mt5.TRADE_ACTION_REMOVE, "order": order.ticket})

    def modify_order(
        self,
        ticket,
        *,
        price=None,
        sl=None,
        tp=None,
        stoplimit=None,
        type_time=None,
        expiration=None,
    ):
        """Modify pending entry and absolute SL/TP; None preserves each value."""
        for name, value in (("sl", sl), ("tp", tp)):
            if value is not None:
                number(value, name, positive=False)
        order = self._order(ticket)
        info = self._symbol(order.symbol)
        tick = self._tick(order.symbol)
        self._order_unfrozen(order, info, tick)
        types = {
            getattr(self.mt5, f"ORDER_TYPE_{side.upper()}_{kind.upper()}"): (side, kind)
            for side in ("buy", "sell")
            for kind in ("limit", "stop", "stop_limit")
        }
        if order.type not in types:
            raise TradeError("Only pending orders can be modified")
        side, kind = types[order.type]
        price = self._price(order.price_open if price is None else price, info)
        if kind != "stop_limit" and stoplimit is not None:
            raise TradeError("stoplimit only applies to stop-limit orders")
        limit = (
            self._price(order.price_stoplimit if stoplimit is None else stoplimit, info)
            if kind == "stop_limit"
            else None
        )
        self._pending_price(side, kind, price, limit, tick, info)
        sl = order.sl if sl is None else (0.0 if sl == 0 else self._price(sl, info))
        tp = order.tp if tp is None else (0.0 if tp == 0 else self._price(tp, info))
        self._stops(side, limit if limit is not None else price, sl, tp, info)
        selected_time = order.type_time if type_time is None else type_time
        if expiration is None and selected_time in (
            self.mt5.ORDER_TIME_SPECIFIED,
            self.mt5.ORDER_TIME_SPECIFIED_DAY,
        ):
            expiration = datetime.fromtimestamp(order.time_expiration, timezone.utc)
        selected_time, expiry = self._expiration(selected_time, expiration)
        request = {
            "action": self.mt5.TRADE_ACTION_MODIFY,
            "order": order.ticket,
            "price": price,
            "sl": sl,
            "tp": tp,
            "type_time": selected_time,
            "expiration": expiry,
        }
        if limit is not None:
            request["stoplimit"] = limit
        return self._send(request)

    def margin_required(self, symbol, side, volume, price=None):
        info = self._symbol(symbol)
        tick = self._tick(symbol)
        order_type = self._side(side)
        price = self._price(
            price if price is not None else (tick.ask if side == "buy" else tick.bid), info
        )
        result = self.mt5.order_calc_margin(order_type, symbol, self._volume(volume, info), price)
        if result is None:
            raise self._failure("order_calc_margin")
        return number(result, "margin", positive=False)

    def calculate_volume(self, symbol, side, entry, stop, risk_amount):
        """Estimate size/loss/margin in account currency, excluding gaps and costs."""
        info = self._symbol(symbol)
        order_type = self._side(side)
        entry, stop = self._price(entry, info), self._price(stop, info)
        risk = number(risk_amount, "risk_amount")
        if stop >= entry if side == "buy" else stop <= entry:
            raise TradeError("Stop must be on the losing side of entry")
        probe = info.volume_min
        loss = self.mt5.order_calc_profit(order_type, symbol, probe, entry, stop)
        if loss is None:
            raise self._failure("order_calc_profit")
        loss = number(-loss, "estimated loss")
        volume = self._volume(min(risk / loss * probe, info.volume_max), info, floor=True)
        actual = self.mt5.order_calc_profit(order_type, symbol, volume, entry, stop)
        if actual is None:
            raise self._failure("order_calc_profit")
        actual = number(-actual, "estimated loss")
        if actual > risk + 1e-8:
            raise TradeError("Normalized volume exceeds risk budget")
        return RiskEstimate(
            volume,
            actual,
            self.margin_required(symbol, side, volume, entry),
            self._account().currency,
        )
