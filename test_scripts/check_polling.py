"""Check event deduplication, read recovery, cancellation, and trailing loops."""

from _support import run_checks

if __name__ == "__main__":
    run_checks(
        [
            "test_data.DataTests.test_polling_deduplicates_and_tracks_changes",
            "test_data.DataTests.test_poll_failure_does_not_emit_false_closes",
            "test_data.DataTests.test_poll_limits_stop_and_callback_errors",
            "test_data.DataTests.test_poll_reconnect_rejects_account_switch",
            "test_data.DataTests.test_trailing_does_not_loosen_or_duplicate",
            "test_data.DataTests.test_trailing_stops_after_unknown_result",
        ]
    )
