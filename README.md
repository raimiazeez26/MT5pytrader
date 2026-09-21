# MT5pytrader

Validated Python helpers for MetaTrader 5 execution, position management, and reporting.

[PyPI](https://pypi.org/project/MT5pytrader/) · [Source](https://github.com/raimiazeez26/MT5pytrader) · [Issues](https://github.com/raimiazeez26/MT5pytrader/issues)

**This branch prepares version 2.0.0.** It has not been published to PyPI as part
of this change. Version 2 introduces explicit errors, structured results, and
consistent empty DataFrames; read the [migration guide](https://github.com/raimiazeez26/MT5pytrader/blob/codex/mt5pytrader-2.0/docs/MIGRATION.md)
before upgrading from 1.0.

## Features

- Market, limit, stop, and stop-limit buy/sell orders.
- Request preview, broker preflight checks, and distinct execution outcomes.
- Position selection by ticket, symbol, direction, and magic number.
- Full/partial closes using broker volume steps, with per-ticket batch results.
- SL/TP modification, break-even offsets, and bounded client-side trailing stops.
- Pending-order listing, modification, expiration, and cancellation.
- Risk-based volume estimates and account-currency margin estimates.
- Optional symbol, spread, gross-exposure, and daily-loss limits.
- Open-position tables, UTC deal history, cost-aware cash-flow summaries, bars, and ticks.
- Bounded position-change polling and structured audit logging.
- Injectable MT5 adapter and offline tests; importing the module does not connect.

## Requirements and installation

Native trading needs Windows, the MetaTrader 5 desktop terminal, an account, and
a Python interpreter supported by the [MetaTrader5 wheels](https://pypi.org/project/MetaTrader5/#files).
Python 3.10+ is required. CI exercises Python 3.10–3.13 on Windows and Linux with a
fake adapter; Linux support is for offline development, not native terminal trading.

To evaluate this branch before release:

```bash
python -m pip install "MT5pytrader @ git+https://github.com/raimiazeez26/MT5pytrader.git@codex/mt5pytrader-2.0"
```

After 2.0.0 is published:

```bash
python -m pip install --upgrade "MT5pytrader==2.0.0"
```

pandas is installed automatically. The native MetaTrader5 dependency is installed
automatically on Windows. Set the broker's exact server/symbol names and enable
terminal/account permissions for Python API trading before executing requests.

## Connect, inspect, and preview

Set `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` in your environment. This example
does not submit a trade. Preview may select the symbol in Market Watch.

```python
import os
from MT5pytrader import Trader, TradeError

try:
    with Trader(magic=260001, comment="my-strategy") as trader:
        trader.connect(
            int(os.environ["MT5_LOGIN"]),
            os.environ["MT5_PASSWORD"],
            os.environ["MT5_SERVER"],
        )
        print(trader.get_open_positions(magic=260001))
        request = trader.preview_order("EURUSD", "buy", lot=0.01, stop_loss=200, take_profit=400)
        print(request)
        check = trader.check_order("EURUSD", "buy", lot=0.01, stop_loss=200, take_profit=400)
        print(check.valid, check.retcode, check.message)
except TradeError as exc:
    print(exc.code, str(exc), exc.last_error)
```

`Trader()` initializes the terminal and binds to the account currently active.
`connect()` verifies the requested login/server; a failed login blocks subsequent
operations. To choose a terminal, use `Trader(path=r"C:\path\terminal64.exe")`.
For delayed initialization, pass `auto_initialize=False`, then call `initialize()`
or `connect()`. `disconnect()` and context exit call `mt5.shutdown()`.

The native connection is process-wide. Use one owner per process; do not run
multiple accounts or concurrent operations through shared Trader instances.
Account switching is detected and requires explicit reconnection. Passwords are
passed to MT5 but not retained by the wrapper.

## Units and execution behavior

| Parameter | Meaning |
| --- | --- |
| `lot`, `volume` | Lots. Opening/explicit close volumes must match broker min/max/step. |
| `stop_loss`, `take_profit` | Positive point distances for opening methods; `None` omits a level. |
| `price` | Absolute pending entry/trigger price. |
| `stoplimit` | Absolute limit price placed when a stop-limit trigger is reached. |
| `sl`, `tp` | Absolute prices for modification; zero removes that level. |
| `percent` | Fraction in `(0, 1]`; `0.5` means half, not `50`. |
| `ticket_id`, `ticket` | Current position ticket for position methods; order ticket for order methods. |
| `deviation` | Points, configured on Trader. |
| `offset_points`, `distance_points` | Points for break-even and trailing stops. |

A point is the symbol's `point` property: 200 points at `0.00001` is `0.00200`.
Prices round to `trade_tick_size`; opening SL/TP is calculated from normalized
entry (the limit price for stop-limit orders). Market entries use ask for buys and
bid for sells. Market Execution requests omit `price` as required by MT5; the
current quote still determines the protective prices. Stops are not recalculated
after a fill, so slippage can change their distance from actual entry.

Partial-close fractions round **down** to the broker's volume step. A zero/below-min
close or invalid remaining volume is rejected; it never silently becomes a full
close. Inspect the result's requested volume to see the normalized amount.

Filling policy is chosen from symbol capabilities. Pending orders use RETURN.
An explicit `type_filling=` override must be supported for a market deal. Local
price/volume/distance checks supplement the broker's `order_check`; broker checks
cannot guarantee later execution. Preflight runs by default on sends; advanced
callers can opt out with `preflight=False`.

## Submit and inspect an outcome

These examples assume `trader` is connected and submit actual requests. Validate
the build on a demo account with your broker before production use.

```python
result = trader.open_buy("EURUSD", lot=0.01, stop_loss=200, take_profit=400)
print(result.status, result.retcode, result.order, result.deal)
print(result.requested_volume, result.executed_volume)
```

| Result status | Meaning |
| --- | --- |
| `done` | Broker reports operation completed. |
| `placed` | Accepted/placed; not proof of a completed fill. |
| `partial` | Partially executed; inspect executed volume and reconcile remainder. |
| `unchanged` | No modification needed, or broker reports no changes. |
| `rejected` | Preflight or broker rejected the request. |
| `unknown` | Send returned no result, timed out, or lost connection; reconcile before retrying. |
| `error` | A per-ticket local error collected by a symbol-wide batch operation. |

`result.accepted` includes `partial` and `placed`; `result.completed` does not.
The result retains the request, raw broker response, IDs, and error context.
Validation, login, and query failures raise `TradeError`; a batch collects local
errors per ticket. No request is automatically retried. After an unknown outcome,
inspect `get_orders()`, `positions()`, and `history_deals()` before any resubmission.

## Position management

```python
# Read current position tickets; filter by strategy ownership and direction.
buys = trader.positions(symbol="EURUSD", magic=260001, side="buy")
if buys:
    ticket = buys[0].ticket
    outcome = trader.close_partial_buy(0.5, ticket_id=ticket)
    print(outcome.status)

# Independent examples; choose the action you intend to perform:
# trader.modify_sl(ticket_id=ticket, sl=1.08000)
# trader.modify_tp(ticket_id=ticket, tp=1.11000)
# trader.break_even(ticket_id=ticket, offset_points=10)
# trader.close_position(ticket)
```

An explicit ticket returns one `TradeResult`. Symbol-wide management returns a
list, processes every matching position, and accepts `magic=`. Direction-specific
close methods skip opposite-side positions; an explicit ticket with the wrong
side raises. When both symbol and ticket are supplied, both must match. No
implicit close-all operation is allowed: select a symbol or ticket explicitly.

On netting accounts, positions aggregate deals for a symbol; a magic filter is
not per-strategy volume attribution. Use separate symbols/accounts when strategies
need independent ownership of netted exposure.

`modify_sl()` preserves TP and `modify_tp()` preserves SL. Break-even preserves TP,
only acts on profitable positions, and never loosens an existing better stop.
Its offset is a point amount you choose; it does not automatically reimburse
commission, swap, or slippage.

## Pending orders

```python
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5

# Illustrative price: must be valid relative to the current market.
result = trader.open_buy_limit(
    "EURUSD",
    price=1.08000,
    lot=0.01,
    stop_loss=200,
    take_profit=400,
    type_time=mt5.ORDER_TIME_SPECIFIED,
    expiration=datetime.now(timezone.utc) + timedelta(hours=1),
)
print(result.status, result.order)

# Use an existing pending order's ticket from trader.get_orders().
# trader.modify_order(order_ticket, price=1.07900, sl=1.07700)
# trader.cancel_order(order_ticket)
```

Available methods: `open_buy_limit`, `open_sell_limit`, `open_buy_stop`,
`open_sell_stop`, `open_buy_stop_limit`, and `open_sell_stop_limit`. Stop-limit
methods require both `price` (trigger) and `stoplimit` (limit entry).
`modify_order()` preserves unspecified SL, TP, entry, and expiry. `sl=0` or `tp=0`
removes a level. Cancellation uses the **order** ticket, not a position ticket.
Broker order-type/expiration support is checked by preflight.

## Risk sizing, margin, and limits

```python
estimate = trader.calculate_volume("EURUSD", "buy", entry=1.10000, stop=1.09800, risk_amount=25.0)
print(estimate.volume, estimate.estimated_loss, estimate.margin, estimate.currency)
print(trader.margin_required("EURUSD", "buy", volume=estimate.volume))
```

Sizing uses `order_calc_profit`, rounds down to the volume step, caps at the symbol
maximum, and rejects budgets below the minimum lot. Loss/margin are estimates in
account currency. They exclude gaps, slippage, commission, and swap; size is not a
guarantee of maximum realized loss. Margin is a broker estimate, not a reservation.

```python
from MT5pytrader import ExecutionLimits, Trader

limits = ExecutionLimits(
    allowed_symbols=frozenset({"EURUSD", "GBPUSD"}),
    max_spread_points=30,
    max_exposure_lots=1.0,
    max_daily_loss=100.0,
)
# Use these limits when constructing your connection owner:
# trader = Trader(magic=260001, limits=limits)
```

Limits apply to new openings, including pending placements, and leave exits and
protective changes available. Exposure conservatively sums gross lots across all
open positions and pending remaining volumes plus the request, without currency
conversion or netting credit. Daily loss is today's UTC BUY/SELL deal cash flow
plus current floating profit and swap across the account; separate balance-style
fees/adjustments are excluded. Limits are local snapshot checks, not atomic
account controls, and do not reserve capacity for other processes.

## Data and reporting

```python
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5

end = datetime.now(timezone.utc)
start = end - timedelta(days=7)
deals = trader.history_deals(start, end, magic=260001)
report = trader.performance_report(start, end, magic=260001)
bars = trader.get_rates("EURUSD", mt5.TIMEFRAME_M5, start, end)
ticks = trader.get_ticks("EURUSD", end - timedelta(minutes=5), end)
```

All date inputs must be timezone-aware; they are converted to UTC. DataFrames
use UTC `time` and consistent empty schemas. Position tables retain magic and
identifiers. `running_profit()` sums the selected open positions' `profit` field;
it does not add swap. `performance_report()` sums BUY/SELL deal profit, commission,
swap, and fee in the requested period, excluding deposits/withdrawals and separate
broker adjustments. Entry commissions count in their posting period. It is a
deal cash-flow summary, not a matched-trade win-rate or equity-drawdown report.
Broker/terminal history availability limits bars and ticks. Query failures raise,
while valid empty position/history queries return empty data.

## Trailing stops and events

```python
# One update, or a bounded loop (both can send SL modifications):
# trader.trail_stop(ticket, distance_points=200)
# trader.run_trailing_stop(ticket, 200, interval=2, max_polls=30)

# Read-only polling: first snapshot is the baseline.
trader.watch_positions(
    lambda event: print(event.kind, event.ticket),
    magic=260001,
    interval=2,
    max_polls=30,
)
```

Trailing preserves TP, never loosens SL, and skips unchanged normalized stops.
The loop stops on a noncompleted outcome and never automatically retries an
uncertain send. The Python process must remain running.

Position events are `opened`, `updated`, and `closed`. Polling compares tickets,
symbol, direction, magic, volume, entry, SL, and TP; quote/profit fluctuations do not
produce repeated events. It can miss changes occurring entirely between polls.
Both loops accept a `threading.Event` as `stop_event`. `watch_positions()` also
accepts `reconnect(trader)` and `max_errors=3`; the callback may reinitialize/login
to the **same** account after a read failure. Failed reads never become false
closure events. User callback errors propagate. There is no hidden background thread.

Audit events use Python logging under `MT5pytrader`, with structured fields in
`LogRecord.mt5_event`. The library installs no handlers and omits account IDs,
credentials, user comments, and raw replies from its audit records. Full result
objects contain request comments; redact them before exporting your own logs.

## API overview

| Group | Methods |
| --- | --- |
| Lifecycle | `initialize`, `connect`, `disconnect`, context manager |
| Open/check | `preview_order`, `check_order`, `open_buy`, `open_sell`, six pending methods |
| Position queries | `positions`, `get_open_positions`, `running_profit` |
| Closing | `close_position`, `close_buy`, `close_sell`, `close_partial_buy`, `close_partial_sell` |
| Protection | `modify_sl`, `modify_tp`, `break_even`, `trail_stop`, `run_trailing_stop` |
| Pending management | `get_orders`, `modify_order`, `cancel_order` |
| Risk | `calculate_volume`, `margin_required`, `ExecutionLimits` |
| Data | `history_deals`, `performance_report`, `get_rates`, `get_ticks`, `watch_positions` |

Opening wrappers preserve the original `symbol, lot, stop_loss, take_profit,
magic, comment` parameters; pending wrappers add `price`, and stop-limit wrappers
add `stoplimit`. Constructor defaults: `comment="MT5pytrader"`, `magic=260000`,
`deviation=20`, `type_time=ORDER_TIME_GTC`, automatic filling, `preflight=True`.
Per-call `magic=None` and `comment=None` inherit constructor values.

## Development

```bash
git clone https://github.com/raimiazeez26/MT5pytrader.git
cd MT5pytrader
git checkout codex/mt5pytrader-2.0
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check .
python -m build
python -m twine check --strict dist/*
```

Tests use an in-memory adapter and never place trades. See
[demo validation](https://github.com/raimiazeez26/MT5pytrader/blob/codex/mt5pytrader-2.0/docs/DEMO_VALIDATION.md),
[release instructions](https://github.com/raimiazeez26/MT5pytrader/blob/codex/mt5pytrader-2.0/docs/RELEASING.md),
and the [review implementation map](https://github.com/raimiazeez26/MT5pytrader/blob/codex/mt5pytrader-2.0/docs/IMPLEMENTATION.md).
Report issues with version, retcode, symbol properties, and a minimal reproduction;
remove credentials and account identifiers.

## License

MIT; see [LICENSE](https://github.com/raimiazeez26/MT5pytrader/blob/codex/mt5pytrader-2.0/LICENSE).
