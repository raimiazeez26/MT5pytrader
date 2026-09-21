"""Check position/history queries, costs, UTC frames, and query errors."""

from _support import run_checks

if __name__ == "__main__":
    run_checks(
        [
            "test_data.DataTests.test_empty_positions_schema_and_zero_profit",
            "test_data.DataTests.test_query_failures_are_not_empty_or_zero",
            "test_data.DataTests.test_history_costs_deposits_and_filters",
            "test_data.DataTests.test_naive_reversed_dates_and_query_failure",
            "test_data.DataTests.test_rates_and_ticks_stable_empty_schema_and_utc",
        ]
    )
