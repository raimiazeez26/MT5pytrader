# Review and roadmap implementation map

This branch includes the useful restructuring and dependency fixes from PR #1 and
supersedes its proposed implementation. The original review refers to main
`0d960b2` and PR head `a57fa2b`, not the code in this branch.

| Review item | Implementation | Verification |
| --- | --- | --- |
| Reversed entry quotes | core.preview_order uses ask/bid and omits Market Execution price | Both sides and market-mode request tests |
| Break-even clears TP/loosens SL | _modify_position preserves the other level; improve-only check | Profitable/losing/better-stop and both-side tests |
| Closing wrong side/strategy | positions filters all supplied criteria; explicit mismatches fail | Mixed direction/magic and multi-ticket tests |
| Invalid partial volume | finite validation, decimal fraction multiplication, step floor, valid remainder | Nonfinite/zero/over-one/0.001-step tests |
| Wrong filling enum | mode/bitmask-aware policy selection; pending RETURN | Execution/fill mode matrix |
| Incorrect result classification | TradeResult completed/accepted/status, no send retries | Done/placed/partial/rejected/unknown tests |
| Missing quotes/query error conflation | TradeError with terminal context, stable empty frames | Quote/read failure and empty-schema tests |
| Return values and inherited defaults | Typed outcomes, per-ticket batch results, per-call None inheritance | Result/default/batch tests |
| Mutable per-request state | Local request objects; injectable adapter | Adapter-driven entire suite |
| Connection lifecycle | Path/init/login verification/context/disconnect | Failure/account-switch/shutdown tests |
| Metadata/license/docs | pyproject 2.0.0, MIT license in artifacts, canonical README, migration guide | Build, artifact inspection, twine, package checks |
| Automated checks | unittest and Ruff; Python/OS matrix; distribution job | CI workflow |

| Roadmap capability | Public implementation |
| --- | --- |
| Preview and broker validation | preview_order, check_order; preflight on send by default |
| Structured outcomes | TradeResult, CheckResult, TradeError; explicit uncertain state |
| Safe targeting | positions/get_orders filters; close_position; explicit batches |
| Pending lifecycle | Six pending placement methods, modify_order, cancel_order, get_orders |
| Risk/margin | calculate_volume returns RiskEstimate; margin_required |
| Lifecycle | initialize/connect/disconnect, path, context manager |
| Protection | break_even offset, trail_stop, bounded run_trailing_stop |
| History/reporting | UTC history_deals; cost-aware deal-level performance_report |
| Execution limits/audit | ExecutionLimits and structured LogRecord.mt5_event |
| Market data/events | get_rates/get_ticks; bounded watch_positions with deduplication, cancellation and same-account reconnect callback |

Explicit boundaries: no backtesting/strategy engine; no automatic resubmission of
uncertain trades; no server-side enforcement of local limits; no attribution of
netted position volume between strategies; no claim that an offline test proves
live broker acceptance. Trailing/polling are synchronous client-side loops. Reports
are deal cash flow, not matched-trade statistics. Native demo validation remains
the maintainer's release gate, documented separately.
