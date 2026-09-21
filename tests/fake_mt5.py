"""In-memory adapter: no native terminal or trading account is ever accessed."""

from collections import namedtuple
from types import SimpleNamespace
from unittest.mock import Mock

from MT5pytrader.data import POSITION_COLUMNS, DEAL_COLUMNS

Position = namedtuple("Position", POSITION_COLUMNS, defaults=[0] * len(POSITION_COLUMNS))
Deal = namedtuple("Deal", DEAL_COLUMNS, defaults=[0] * len(DEAL_COLUMNS))


def position(ticket=101, side=0, **kwargs):
    values = dict(
        ticket=ticket,
        type=side,
        symbol="EURUSD",
        magic=42,
        volume=0.1,
        price_open=1.1 if side == 0 else 1.11,
        sl=1.09 if side == 0 else 1.12,
        tp=1.12 if side == 0 else 1.09,
        profit=20,
        swap=-1,
        comment="test",
        external_id="",
    )
    values.update(kwargs)
    return Position(**values)


def order(ticket=201, **kwargs):
    values = dict(
        ticket=ticket,
        symbol="EURUSD",
        magic=42,
        volume_current=0.1,
        type=2,
        price_open=1.09,
        sl=1.08,
        tp=1.12,
        price_stoplimit=0,
        type_time=0,
        time_expiration=0,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


class FakeMT5:
    ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1
    ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT = 2, 3
    ORDER_TYPE_BUY_STOP, ORDER_TYPE_SELL_STOP = 4, 5
    ORDER_TYPE_BUY_STOP_LIMIT, ORDER_TYPE_SELL_STOP_LIMIT = 6, 7
    ORDER_TIME_GTC, ORDER_TIME_DAY, ORDER_TIME_SPECIFIED, ORDER_TIME_SPECIFIED_DAY = range(4)
    ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN = 0, 1, 2
    SYMBOL_TRADE_EXECUTION_REQUEST, SYMBOL_TRADE_EXECUTION_INSTANT = 0, 1
    SYMBOL_TRADE_EXECUTION_MARKET, SYMBOL_TRADE_EXECUTION_EXCHANGE = 2, 3
    TRADE_ACTION_DEAL, TRADE_ACTION_PENDING = 1, 5
    TRADE_ACTION_SLTP, TRADE_ACTION_MODIFY, TRADE_ACTION_REMOVE = 6, 7, 8
    TRADE_RETCODE_DONE, TRADE_RETCODE_PLACED, TRADE_RETCODE_DONE_PARTIAL = 10009, 10008, 10010
    TRADE_RETCODE_TIMEOUT, TRADE_RETCODE_CONNECTION, TRADE_RETCODE_NO_CHANGES = 10012, 10031, 10025
    DEAL_TYPE_BUY, DEAL_TYPE_SELL = 0, 1
    COPY_TICKS_ALL, COPY_TICKS_INFO, COPY_TICKS_TRADE = -1, 1, 2

    def __init__(self):
        self.info = SimpleNamespace(
            visible=True,
            point=0.00001,
            trade_tick_size=0.00001,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_exemode=1,
            filling_mode=3,
            trade_stops_level=10,
            trade_freeze_level=0,
        )
        self.tick = SimpleNamespace(bid=1.1020, ask=1.1022)
        self.account = SimpleNamespace(
            login=123, server="Demo", currency="USD", trade_allowed=True, trade_expert=True
        )
        self.terminal = SimpleNamespace(trade_allowed=True, tradeapi_disabled=False)
        self.position_rows = [position()]
        self.order_rows = []
        self.initialize = Mock(return_value=True)
        self.shutdown = Mock()
        self.login = Mock(return_value=True)
        self.account_info = Mock(side_effect=lambda: self.account)
        self.terminal_info = Mock(side_effect=lambda: self.terminal)
        self.symbol_info = Mock(side_effect=lambda _: self.info)
        self.symbol_select = Mock(return_value=True)
        self.symbol_info_tick = Mock(side_effect=lambda _: self.tick)
        self.positions_get = Mock(
            side_effect=lambda **kw: tuple(
                p for p in self.position_rows if all(getattr(p, k) == v for k, v in kw.items())
            )
        )
        self.orders_get = Mock(
            side_effect=lambda **kw: tuple(
                p for p in self.order_rows if all(getattr(p, k) == v for k, v in kw.items())
            )
        )
        self.order_check = Mock(return_value=SimpleNamespace(retcode=0, comment="Done"))
        self.order_send = Mock(
            side_effect=lambda r: SimpleNamespace(
                retcode=10009, order=999, deal=998, volume=r.get("volume", 0), comment="Done"
            )
        )
        self.last_error = Mock(return_value=(-1, "Mock terminal error"))
        self.order_calc_profit = Mock(
            side_effect=lambda side, symbol, vol, entry, close: (
                (close - entry) * vol * 100000 * (1 if side == 0 else -1)
            )
        )
        self.order_calc_margin = Mock(side_effect=lambda side, symbol, vol, price: vol * 1000)
        self.history_deals_get = Mock(return_value=())
        self.copy_rates_range = Mock(return_value=[])
        self.copy_ticks_range = Mock(return_value=[])


class NoWait:
    def __init__(self):
        self.stopped = False

    def is_set(self):
        return self.stopped

    def wait(self, _):
        return self.stopped
