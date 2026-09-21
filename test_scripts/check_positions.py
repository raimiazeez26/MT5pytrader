"""Check ticket targeting, partial closes, and preservation of protection."""

from _support import run_checks

if __name__ == "__main__":
    run_checks(
        [
            "test_execution.ExecutionTests.test_ticket_only_close_and_correct_sides",
            "test_execution.ExecutionTests.test_symbol_closing_filters_direction_magic_and_all_tickets",
            "test_execution.ExecutionTests.test_partial_step_floor_and_remainder",
            "test_execution.ExecutionTests.test_break_even_preserves_tp_both_sides",
            "test_execution.ExecutionTests.test_break_even_never_loosens_or_moves_losing_trade",
            "test_contracts.ContractTests.test_direction_is_rechecked_after_selection",
        ]
    )
