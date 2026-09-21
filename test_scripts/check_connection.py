"""Check lifecycle, account identity, failed login, and shutdown."""

from _support import run_checks

if __name__ == "__main__":
    run_checks(
        [
            "test_execution.ExecutionTests.test_initialization_failure_and_login_fail_closed",
            "test_execution.ExecutionTests.test_account_switch_and_trading_permission",
            "test_execution.ExecutionTests.test_context_shutdown_terminal_path_no_password_retention",
            "test_contracts.ContractTests.test_delayed_initialization_and_missing_account",
            "test_contracts.ContractTests.test_login_verifies_account_and_server",
        ]
    )
