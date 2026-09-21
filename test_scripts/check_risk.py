"""Check sizing, margin failure, exposure/spread/symbol limits, and daily loss."""

from _support import run_checks

if __name__ == "__main__":
    run_checks(
        [
            "test_execution.ExecutionTests.test_risk_sizing_in_account_currency",
            "test_execution.ExecutionTests.test_limits_block_opening_but_allow_exit",
            "test_execution.ExecutionTests.test_exposure_includes_pending_orders",
            "test_data.DataTests.test_daily_loss_blocks_opens",
            "test_contracts.ContractTests.test_none_preflight_and_calc_failures_raise",
        ]
    )
