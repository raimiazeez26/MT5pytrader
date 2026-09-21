# Package usage examples

These are sample programs that call MT5pytrader's public APIs against a real MT5
terminal. They are **not unit-test runners**. Automated tests remain in `tests/`.
Each file has an `example(args, trader)` function containing the feature calls so
you can copy them into your application.

## Setup

Use Windows with a supported Python and MT5 terminal. From the repository root:

```powershell
python -m pip install -e .
```

Set the account credentials in environment variables. For example, in PowerShell,
enter the account number as the username in the credential prompt:

```powershell
$accountCredential = Get-Credential -Message 'MT5 account number and password'
$env:MT5_LOGIN = $accountCredential.UserName
$env:MT5_PASSWORD = $accountCredential.GetNetworkCredential().Password
$env:MT5_SERVER = 'YourBroker-Demo'
# Optional, when you need a specific terminal installation:
# $env:MT5_PATH = 'C:\Program Files\MetaTrader 5\terminal64.exe'
```

Use your broker's exact symbol name, including suffixes. All scripts accept
`--symbol` (default `EURUSD`) and `--magic` (default `260001`). Position/order
management requires the ticket to match both, so inspect positions before choosing
a ticket. `_common.py` shows `Trader` construction, login, error handling, and
context-manager cleanup without storing credentials in code.

Run examples individually; there is no run-all script that might execute a series
of trades. `--help` displays arguments without connecting. The following commands
use illustrative prices/tickets that you must replace with values for your account.
Use a demo account when learning the APIs.

## Read-only examples

```powershell
# Connect and inspect current positions/profit.
python test_scripts/connection.py --symbol EURUSD

# Filter strategy positions and pending orders.
python test_scripts/positions.py --symbol EURUSD --magic 260001 --side buy

# Estimate risk-sized volume and margin in account currency.
python test_scripts/risk_sizing.py --entry 1.1000 --stop 1.0980 --risk 25

# Apply symbol/spread/exposure/daily-loss limits to a broker preflight check.
python test_scripts/execution_limits.py --lot 0.01 --max-spread 30 --max-exposure 1 --max-daily-loss 100

# UTC deal history and profit/commission/swap/fee summary.
python test_scripts/history.py --days 7 --magic 260001

# Five-minute bars for the past day and ticks for the past five minutes.
python test_scripts/market_data.py --symbol EURUSD

# Print position-change events for up to 30 polls; Ctrl+C stops early.
python test_scripts/watch_positions.py --interval 2 --polls 30
```

## Opening orders

These commands preview requests without submitting orders. Market examples also
call `check_order()` to show the broker's preflight result.

```powershell
python test_scripts/market_orders.py --side buy --lot 0.01 --stop-loss 200 --take-profit 400
python test_scripts/market_orders.py --side sell --lot 0.01 --stop-loss 200 --take-profit 400

python test_scripts/pending_orders.py --side buy --kind limit --price 1.0800
python test_scripts/pending_orders.py --side sell --kind limit --price 1.1200
python test_scripts/pending_orders.py --side buy --kind stop --price 1.1200 --expires-minutes 60
python test_scripts/pending_orders.py --side sell --kind stop --price 1.0800
python test_scripts/pending_orders.py --side buy --kind stop_limit --price 1.1200 --stoplimit 1.1190
python test_scripts/pending_orders.py --side sell --kind stop_limit --price 1.0800 --stoplimit 1.0810
```

Add `--execute` to one selected command when you intend to submit it. SL/TP on
opening methods are **point distances**. Pending `price` and `stoplimit` are
**absolute prices** and must be valid relative to the current market. The pending
example shows all six placement methods but calls only the one you select.

## Managing a position or pending order

These inspect the current ticket and print the intended action. They do not
validate the full proposed modification until you add `--execute`.

```powershell
# Full close, explicit lots, or fractional close (choose one).
python test_scripts/close_position.py --ticket 123456789
python test_scripts/close_position.py --ticket 123456789 --volume 0.01
python test_scripts/close_position.py --ticket 123456789 --percent 0.5

# Absolute SL/TP prices; 0 removes the selected protective level.
python test_scripts/modify_protection.py --ticket 123456789 --sl 1.0800
python test_scripts/modify_protection.py --ticket 123456789 --tp 1.1200
python test_scripts/modify_protection.py --ticket 123456789 --break-even --offset-points 10

# Inspect, modify, or cancel a pending ORDER ticket.
python test_scripts/manage_pending.py --ticket 987654321
python test_scripts/manage_pending.py --ticket 987654321 --price 1.0790 --sl 1.0770
python test_scripts/manage_pending.py --ticket 987654321 --cancel

# One trailing update, or a bounded client-side trailing loop.
python test_scripts/trailing_stop.py --ticket 123456789 --distance-points 200
python test_scripts/trailing_stop.py --ticket 123456789 --distance-points 200 --polls 30 --interval 2
```

For example, appending `--execute` to the fractional-close command actually sends
that close request. Read every returned status: `placed` and `partial` are not
complete fills; `unknown` requires reconciling orders/positions/history before any
retry. Trailing is client-side and needs this process to keep running. These
examples never automatically retry an uncertain send.

The examples are included in the Git checkout and source distribution, not
installed as console commands by the wheel. The automated suite also smoke-tests
their feature calls using a fake adapter; CI never connects to an account.
