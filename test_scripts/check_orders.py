"""Check opening quotes, preflight, fill policies, pending orders, and outcomes."""

from _support import run_checks

if __name__ == "__main__":
    run_checks(
        [
            "test_execution.ExecutionTests.test_correct_quotes_both_sides",
            "test_execution.ExecutionTests.test_preview_and_check_never_send",
            "test_execution.ExecutionTests.test_filling_modes",
            "test_execution.ExecutionTests.test_pending_wrappers",
            "test_execution.ExecutionTests.test_pending_modify_preserves_fields_and_cancel_uses_order",
            "test_execution.ExecutionTests.test_preflight_rejection_no_send",
            "test_execution.ExecutionTests.test_result_states_no_retry",
        ]
    )
