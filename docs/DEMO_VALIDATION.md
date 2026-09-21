# Broker integration validation before releasing 2.0

Offline tests do not establish broker compatibility. No demo or live account
orders were placed during implementation. Run this manually on an account that
you have verified is a demo account. Record terminal/package/build versions,
account mode, symbol properties, requests, and retcodes without credentials.

1. Install the built wheel in a clean Windows virtual environment. Connect using
   exact terminal path/login/server. Test failed login and a changed active
   account: subsequent sends must be blocked.
2. Confirm symbol visibility selection and missing-symbol/missing-tick errors.
   Preview/check a minimum-volume buy and sell with valid stop distances.
3. Submit minimum-volume buy/sell requests on a demo symbol for each available
   execution mode. Compare requested quote side, actual fill and protection.
   Check partial-fill, requote/rejection and unsupported-fill reporting where the
   broker supports reproducing them. Never manufacture market conditions.
4. On netting and hedging demo accounts, verify ticket selection, symbol-wide
   direction/magic filters, partial-close step/remainder rules, and every batch
   result. Confirm other positions remain untouched.
5. Modify SL and TP separately; verify the other level is retained. Run break-even
   on profitable, losing, and already-better-stop positions. Confirm freeze/stops
   level failures. Verify a trailing update and repeat with an unchanged quote.
6. Place, modify and cancel each supported pending type with future expiration.
   Verify trigger/limit relationships, existing SL/TP preservation and order ticket.
   Unsupported order/expiration combinations must be rejected at preflight.
7. Compare risk loss/margin estimates against terminal calculations for FX and a
   non-FX instrument. Check 0.001/0.01/0.1 lot steps when available.
8. Compare UTC history with terminal deal records and manually total BUY/SELL
   profit/commission/swap/fee. Check empty results and disconnected query errors.
   Confirm separate balance-style charges are excluded as documented.
9. Exercise allowed-symbol, spread, gross-exposure and daily-loss guards. Confirm
   closing and protective management remain possible when a limit is reached.
10. Poll while opening/modifying/closing a demo position. Verify unchanged polls
    do not repeat events. Reconnect to the same account after a read failure;
    ensure no false close events. Stop loops with a threading.Event.
11. For a send timeout/unknown result, verify the application reconciles position,
    order and deal history and does not automatically repeat execution.

Record pass/fail per supported broker/account configuration in the release notes.
Do not claim unsupported modes were tested. This procedure is a release gate, not
an automated job with account secrets.
