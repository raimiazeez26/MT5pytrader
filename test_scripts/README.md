# Standalone test scripts

These scripts run focused groups from the shared `tests/` regression suite. They
use the in-memory fake MT5 adapter; no credentials, terminal, or trading account
are needed, and they never submit real trades. Keeping assertions in `tests/`
ensures the standalone checks and CI exercise the same behavior.

From a repository checkout, install dependencies once:

```bash
python -m pip install -e ".[dev]"
```

| Command | Checks |
| --- | --- |
| `python test_scripts/check_connection.py` | Initialization/login errors, account selection, shutdown |
| `python test_scripts/check_orders.py` | Quotes, preflight, filling, pending lifecycle, result states |
| `python test_scripts/check_positions.py` | Ticket/side/magic targeting, partial close, SL/TP preservation |
| `python test_scripts/check_risk.py` | Sizing, margin errors, exposure/spread/symbol/daily-loss limits |
| `python test_scripts/check_data.py` | Empty/error queries, history costs, timezone-aware frames |
| `python test_scripts/check_polling.py` | Event deduplication, reconnect behavior, cancellation, trailing |
| `python test_scripts/run_all.py` | Full regression suite, including additional edge cases |

Every runner prints individual test outcomes and exits with status 0 on success
or 1 on failure. Paths resolve from the script location, so an absolute script
path also works outside the repository. Native constant compatibility is checked
without connecting when MetaTrader5 is installed, and skipped when unavailable.

The scripts are included in the source distribution and Git checkout. They are
not installed as commands by the wheel. Offline tests cannot establish broker
acceptance; validate broker-specific behavior separately on a demo account.
