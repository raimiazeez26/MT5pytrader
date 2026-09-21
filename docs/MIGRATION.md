# Migrating 1.0 to 2.0

2.0 deliberately changes failure and return behavior. Pin 1.0 until your caller
has been updated and the new build validated against your demo terminal.

| 1.0 behavior | 2.0 behavior |
| --- | --- |
| Operations print and return None | Trading returns TradeResult; local validation/query failures raise TradeError. |
| Symbol-wide operations may affect only the final ticket | All matching positions are processed; results are returned per ticket. |
| None for empty positions or terminal failure | Empty DataFrame for no positions; TradeError for failure. |
| Constructor magic/comment overwritten by method defaults | Omitted overrides inherit constructor settings. |
| Ticket-only calls can fail before lookup | Position symbol is resolved from the current ticket. |
| Symbol and ticket may disagree | All supplied selection filters must match. |
| Arbitrary two-decimal partial volume | Fraction rounds down to broker volume step and checks remainder. |
| Native MetaTrader5 imported at module import | Native adapter is imported at Trader construction; module import is offline. |
| Initialization/login failure prints and continues | Failure raises; failed login blocks further operations. |
| Profit reported as zero on query failure | Query failure raises rather than reporting zero exposure. |

Update code that calls `.empty`, checks a result's status, or catches errors:

```python
from MT5pytrader import TradeError

try:
    result = trader.open_buy("EURUSD", lot=0.01)
except TradeError as exc:
    print("Not sent:", exc.code, str(exc))
else:
    if result.status == "unknown":
        print("Reconcile current orders, positions, and deal history before retrying")
    elif result.status in {"placed", "partial"}:
        print("Accepted but not fully completed:", result.status)
    elif not result.completed:
        print("Rejected:", result.retcode, result.message)
```

Single-ticket operations return one result. Symbol-based closing, modifying, and
break-even operations return a list; inspect every element. Batch local errors
become `status="error"` and do not prevent later selected tickets from being
processed. Explicit missing/mismatched tickets raise instead of silently succeeding.

Use `magic=` filters intentionally; no filter means all matching positions.
Netting positions cannot reliably allocate volume between strategies solely by
magic number. Buy/sell methods enforce direction. `close_position(ticket)` infers
the direction from the current position.

Opening stop distances remain in points (`stop_loss`, `take_profit`). Modification
levels remain absolute (`sl`, `tp`), with zero meaning remove. Break-even only
improves a stop and preserves the target. Default preflight adds an `order_check`
round trip before execution.

Python 3.10+ is required. The package uses pyproject.toml; install/build with pip
and `python -m build`, not `python setup.py`. Native trading still requires a
supported Windows MT5 installation. Never share one native connection across
multiple concurrent Trader instances or accounts.
