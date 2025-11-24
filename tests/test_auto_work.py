"""Tests for scripts/auto-work.py"""

import importlib.util
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, call

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

spec = importlib.util.spec_from_file_location(
    "auto_work", Path(__file__).parent.parent / "scripts" / "auto-work.py"
)
auto_work = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(auto_work)  # type: ignore[union-attr]


class TestCleanup:
    """Tests for cleanup signal handler"""

    def test_cleanup_sets_running_to_false(self) -> None:
        """cleanup() should set running flag to False"""
        auto_work.running = True  # type: ignore[attr-defined]
        auto_work.shutdown_requested = False  # type: ignore[attr-defined]
        auto_work.cleanup(signal.SIGINT, None)
        assert auto_work.running is False  # type: ignore[attr-defined]

    def test_cleanup_prints_shutdown_message(self, capsys: Any) -> None:
        """cleanup() should print shutdown message"""
        auto_work.running = True  # type: ignore[attr-defined]
        auto_work.shutdown_requested = False  # type: ignore[attr-defined]
        auto_work.cleanup(signal.SIGINT, None)
        captured = capsys.readouterr()
        assert "🛑 Received shutdown signal, stopping gracefully..." in captured.out

    def test_cleanup_force_quits_on_second_signal(self) -> None:
        """cleanup() should force quit on second ^C"""
        auto_work.running = False  # type: ignore[attr-defined]
        auto_work.shutdown_requested = True  # type: ignore[attr-defined]
        with pytest.raises(SystemExit) as exc_info:
            auto_work.cleanup(signal.SIGINT, None)
        assert exc_info.value.code == 130


class TestRunCommand:
    """Tests for run_command helper function"""

    def test_run_command_success(self, capsys: Any, monkeypatch: Any) -> None:
        """run_command should return True when command succeeds"""
        mock_run = Mock(return_value=None)
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = auto_work.run_command(["git", "fetch"], "Fetch failed")

        assert result is True
        mock_run.assert_called_once_with(["git", "fetch"], check=True, capture_output=False)

    def test_run_command_failure(self, capsys: Any, monkeypatch: Any) -> None:
        """run_command should return False when command fails"""
        mock_run = Mock(side_effect=subprocess.CalledProcessError(1, "git"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = auto_work.run_command(["git", "fetch"], "Fetch failed")

        assert result is False
        captured = capsys.readouterr()
        assert "❌ Fetch failed" in captured.out

    def test_run_command_calls_with_correct_args(self, monkeypatch: Any) -> None:
        """run_command should pass command list correctly to subprocess"""
        mock_run = Mock()
        monkeypatch.setattr(subprocess, "run", mock_run)

        auto_work.run_command(["git", "status"], "Status failed")

        mock_run.assert_called_once_with(["git", "status"], check=True, capture_output=False)


class TestGetPrCount:
    """Tests for get_pr_count function"""

    def test_get_pr_count_success(self, monkeypatch: Any) -> None:
        """get_pr_count should return PR count when command succeeds"""
        mock_result = Mock()
        mock_result.stdout = "3\n"
        mock_run = Mock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        count = auto_work.get_pr_count()

        assert count == 3
        mock_run.assert_called_once_with(
            ["gh", "pr", "list", "--state", "open", "--json", "number", "--jq", "length"],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_get_pr_count_zero(self, monkeypatch: Any) -> None:
        """get_pr_count should handle zero PRs"""
        mock_result = Mock()
        mock_result.stdout = "0\n"
        mock_run = Mock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        count = auto_work.get_pr_count()
        assert count == 0

    def test_get_pr_count_command_failure(self, monkeypatch: Any) -> None:
        """get_pr_count should exit when gh command fails"""
        mock_run = Mock(side_effect=subprocess.CalledProcessError(1, "gh"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(SystemExit) as exc_info:
            auto_work.get_pr_count()

        assert exc_info.value.code == 1

    def test_get_pr_count_invalid_output(self, monkeypatch: Any) -> None:
        """get_pr_count should exit when output is not a valid integer"""
        mock_result = Mock()
        mock_result.stdout = "not-a-number\n"
        mock_run = Mock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(SystemExit) as exc_info:
            auto_work.get_pr_count()

        assert exc_info.value.code == 1


class TestMainLoop:
    """Tests for main loop function"""

    def test_main_registers_signal_handlers(self, monkeypatch: Any) -> None:
        """main should register SIGINT and SIGTERM handlers"""
        mock_signal = Mock()
        monkeypatch.setattr(signal, "signal", mock_signal)

        # Set running to False immediately to exit loop
        auto_work.running = False  # type: ignore[attr-defined]

        auto_work.main()

        assert mock_signal.call_count == 2
        mock_signal.assert_any_call(signal.SIGINT, auto_work.cleanup)
        mock_signal.assert_any_call(signal.SIGTERM, auto_work.cleanup)

    def test_main_exits_when_running_false(self, monkeypatch: Any, capsys: Any) -> None:
        """main should exit cleanly when running is False"""
        mock_signal = Mock()
        monkeypatch.setattr(signal, "signal", mock_signal)

        auto_work.running = False  # type: ignore[attr-defined]

        auto_work.main()

        captured = capsys.readouterr()
        assert "✅ Auto-work script stopped cleanly" in captured.out

    def test_main_fetches_from_origin(self, monkeypatch: Any) -> None:
        """main should fetch from origin on each iteration"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_get_pr_count = Mock(return_value=10)
        mock_subprocess = Mock()
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)
        monkeypatch.setattr(subprocess, "run", mock_subprocess)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Make running False after first call to get_pr_count
        def set_running_false() -> int:
            auto_work.running = False  # type: ignore[attr-defined]
            return 10

        mock_get_pr_count.side_effect = set_running_false

        auto_work.main()

        # First run_command call should be git fetch
        assert mock_run_command.call_args_list[0] == call(
            ["git", "fetch", "origin"], "Failed to fetch from origin, stopping..."
        )

    def test_main_merges_origin_main(self, monkeypatch: Any) -> None:
        """main should merge origin/main on each iteration"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_get_pr_count = Mock(return_value=10)
        mock_subprocess = Mock()
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)
        monkeypatch.setattr(subprocess, "run", mock_subprocess)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Make running False after first call
        def set_running_false() -> int:
            auto_work.running = False  # type: ignore[attr-defined]
            return 10

        mock_get_pr_count.side_effect = set_running_false

        auto_work.main()

        # Second run_command call should be git merge
        assert mock_run_command.call_args_list[1] == call(
            ["git", "merge", "origin/main"], "Merge conflict detected, stopping..."
        )

    def test_main_exits_on_fetch_failure(self, monkeypatch: Any) -> None:
        """main should exit with code 1 when git fetch fails"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=False)

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)

        auto_work.running = True  # type: ignore[attr-defined]

        with pytest.raises(SystemExit) as exc_info:
            auto_work.main()

        assert exc_info.value.code == 1

    def test_main_exits_on_merge_failure(self, monkeypatch: Any) -> None:
        """main should exit and abort merge when git merge fails"""
        mock_signal = Mock()
        mock_run_command = Mock(side_effect=[True, False])
        mock_subprocess = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(subprocess, "run", mock_subprocess)

        auto_work.running = True  # type: ignore[attr-defined]

        with pytest.raises(SystemExit) as exc_info:
            auto_work.main()

        assert exc_info.value.code == 1
        # Should call git merge --abort
        mock_subprocess.assert_called_once_with(["git", "merge", "--abort"], check=False)

    def test_main_skips_work_when_at_limit(self, monkeypatch: Any, capsys: Any) -> None:
        """main should skip /work-next when at or above PR limit"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_get_pr_count = Mock(return_value=5)
        mock_subprocess = Mock()
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)
        monkeypatch.setattr(subprocess, "run", mock_subprocess)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Stop during sleep (not before)
        def sleep_side_effect(seconds: Any) -> None:
            auto_work.running = False  # type: ignore[attr-defined]

        mock_sleep.side_effect = sleep_side_effect

        auto_work.main()

        captured = capsys.readouterr()
        assert "⏸️  At PR limit (5/5), waiting..." in captured.out

        # Should not call claude command
        claude_calls = [
            call
            for call in mock_subprocess.call_args_list
            if call[0] and call[0][0] and call[0][0][0] == "claude"
        ]
        assert len(claude_calls) == 0

    def test_main_runs_work_next_below_limit(self, monkeypatch: Any, capsys: Any) -> None:
        """main should run /work-next when below PR limit"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_get_pr_count = Mock(return_value=3)
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Make subprocess.run succeed for claude command
        mock_subprocess = Mock()

        def subprocess_run_side_effect(*args: Any, **kwargs: Any) -> None:
            if args[0][0] == "claude":
                auto_work.running = False  # type: ignore[attr-defined]
            return None

        mock_subprocess.side_effect = subprocess_run_side_effect
        monkeypatch.setattr(subprocess, "run", mock_subprocess)

        auto_work.main()

        captured = capsys.readouterr()
        assert "🚀 Below limit (3/5), starting new work..." in captured.out
        assert "✅ Work completed successfully" in captured.out

        # Should call claude command with preexec_fn to create new process group
        import os

        mock_subprocess.assert_any_call(
            ["claude", "--dangerously-skip-permissions", "--print", "/work-next"],
            check=True,
            preexec_fn=os.setpgrp,
        )

    def test_main_handles_work_next_failure(self, monkeypatch: Any, capsys: Any) -> None:
        """main should handle /work-next failure gracefully"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_get_pr_count = Mock(return_value=3)
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Make subprocess.run fail for claude command
        mock_subprocess = Mock()

        def subprocess_run_side_effect(*args: Any, **kwargs: Any) -> None:
            if args[0][0] == "claude":
                auto_work.running = False  # type: ignore[attr-defined]
                raise subprocess.CalledProcessError(1, "claude")
            return None

        mock_subprocess.side_effect = subprocess_run_side_effect
        monkeypatch.setattr(subprocess, "run", mock_subprocess)

        auto_work.main()

        captured = capsys.readouterr()
        assert "❌ Work failed or interrupted" in captured.out

    def test_main_sleeps_between_iterations(self, monkeypatch: Any) -> None:
        """main should sleep for SLEEP_MINUTES * 60 seconds between iterations"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_get_pr_count = Mock(return_value=10)
        mock_subprocess = Mock()
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)
        monkeypatch.setattr(subprocess, "run", mock_subprocess)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Stop after first sleep call
        def sleep_side_effect(seconds: Any) -> None:
            auto_work.running = False  # type: ignore[attr-defined]

        mock_sleep.side_effect = sleep_side_effect

        auto_work.main()

        # Should sleep 60 seconds (first minute of SLEEP_MINUTES)
        mock_sleep.assert_called_with(60)

    def test_main_checks_running_during_sleep(self, monkeypatch: Any) -> None:
        """main should check running flag during sleep and exit early"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_get_pr_count = Mock(return_value=10)
        mock_subprocess = Mock()
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)
        monkeypatch.setattr(subprocess, "run", mock_subprocess)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Set running to False on second sleep call
        sleep_count = [0]

        def sleep_side_effect(seconds: Any) -> None:
            sleep_count[0] += 1
            if sleep_count[0] == 2:
                auto_work.running = False  # type: ignore[attr-defined]

        mock_sleep.side_effect = sleep_side_effect

        auto_work.main()

        # Should have called sleep twice before exiting
        assert mock_sleep.call_count == 2

    def test_main_checks_running_before_starting_work(self, monkeypatch: Any) -> None:
        """main should check running flag before starting new work"""
        mock_signal = Mock()
        mock_run_command = Mock(return_value=True)
        mock_subprocess = Mock()
        mock_sleep = Mock()

        monkeypatch.setattr(signal, "signal", mock_signal)
        monkeypatch.setattr(auto_work, "run_command", mock_run_command)
        monkeypatch.setattr(subprocess, "run", mock_subprocess)
        monkeypatch.setattr("time.sleep", mock_sleep)

        auto_work.running = True  # type: ignore[attr-defined]

        # Set running to False when get_pr_count is called
        def get_pr_count_side_effect() -> int:
            auto_work.running = False  # type: ignore[attr-defined]
            return 3  # Below limit

        mock_get_pr_count = Mock(side_effect=get_pr_count_side_effect)
        monkeypatch.setattr(auto_work, "get_pr_count", mock_get_pr_count)

        auto_work.main()

        # Should not call claude because running was set to False
        claude_calls = [
            call
            for call in mock_subprocess.call_args_list
            if len(call[0]) > 0 and len(call[0][0]) > 0 and call[0][0][0] == "claude"
        ]
        assert len(claude_calls) == 0
