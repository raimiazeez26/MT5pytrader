# Changelog

## 2.0.0 — Unreleased

- Correct market quote sides, filling-policy selection, position direction and
  ticket handling; validate volumes, remaining partial volumes and stop distances.
- Preserve TP and better SL during break-even/trailing updates.
- Return structured execution/check results; raise explicit validation/query
  errors; distinguish partial fills, placement and uncertain execution without retries.
- Add preview/preflight, pending-order lifecycle, risk/margin estimates, execution
  limits, UTC history/data, deal-level reports and bounded event/trailing loops.
- Add verified account lifecycle, terminal-path support, injectable adapter and
  credential-free audit fields; retain historical import and wrapper names.
- Declare runtime dependencies, package the MIT license, modernize build metadata,
  add offline tests and CI, and document migration and release validation.
- Breaking: explicit error/result contracts, Python 3.10+, empty DataFrames, all
  matching batch tickets, and inherited constructor magic/comment defaults.

## 1.0 — 2022-08-22

Published historical release. The repository previously still declared 0.61.
