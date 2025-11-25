"""Integration tests for scripts/auto-work.py

These tests verify the actual signal handling behavior with real subprocesses.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


class TestGracefulShutdown:
    """Integration tests for graceful shutdown behavior"""

    @pytest.fixture
    def mock_work_script(self, tmp_path: Path) -> Path:
        """Create a mock script that simulates /work-next command"""
        script_path = tmp_path / "mock_work.py"
        script_content = '''#!/usr/bin/env python3
"""Mock work script that simulates a long-running task"""
import signal
import sys
import time

# Track if we received SIGINT
received_sigint = False

def handle_sigint(signum, frame):
    global received_sigint
    received_sigint = True
    print("SIGINT_RECEIVED", flush=True)
    sys.exit(1)

signal.signal(signal.SIGINT, handle_sigint)

print("START", flush=True)
time.sleep(1)  # Reduced from 5 to 1 second
print("END", flush=True)

if received_sigint:
    sys.exit(1)
sys.exit(0)
'''
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        return script_path

    @pytest.fixture
    def mock_auto_work_script(self, tmp_path: Path, mock_work_script: Path) -> Path:
        """Create a modified auto-work.py that uses mock_work_script"""
        script_path = tmp_path / "test_auto_work.py"

        # Read the original auto-work.py
        original_script = Path(__file__).parent.parent / "scripts" / "auto-work.py"
        content = original_script.read_text()

        # Modify to use mock script and shorter timeouts
        modified_content = (
            content.replace("MAX_PRS = 5", "MAX_PRS = 5")
            .replace("SLEEP_MINUTES = 5", "SLEEP_MINUTES = 1")
            .replace(
                '["claude", "--dangerously-skip-permissions", "--print", "/work-next"]',
                f'["{mock_work_script}"]',
            )
        )

        script_path.write_text(modified_content)
        script_path.chmod(0o755)
        return script_path

    def test_graceful_shutdown_allows_child_to_complete(
        self, mock_auto_work_script: Path, tmp_path: Path
    ) -> None:
        """
        Test that sending SIGINT to auto-work.py allows the child process to complete.

        This test verifies:
        1. Child process prints "START"
        2. SIGINT is sent to parent
        3. Child process continues and prints "END"
        4. Child process does NOT receive SIGINT
        """
        # Mock git commands to succeed
        mock_git = tmp_path / "git"
        mock_git.write_text(
            """#!/bin/bash
exit 0
"""
        )
        mock_git.chmod(0o755)

        # Mock gh command to return PR count below limit
        mock_gh = tmp_path / "gh"
        mock_gh.write_text(
            """#!/bin/bash
echo "0"
"""
        )
        mock_gh.chmod(0o755)

        # Set up environment with mocked commands
        env = os.environ.copy()
        env["PATH"] = f"{tmp_path}:{env['PATH']}"

        # Start auto-work.py process
        process = subprocess.Popen(
            [sys.executable, str(mock_auto_work_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,  # Line buffered
        )

        try:
            # Collect all output while waiting for START
            all_output = []
            start_seen = False
            start_time = time.time()
            timeout = 5  # Reduced from 10 to 5 seconds

            while not start_seen and (time.time() - start_time) < timeout:
                # Use non-blocking read
                import select

                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    line = process.stdout.readline()  # type: ignore[union-attr]
                    all_output.append(line)
                    print(f"Output: {line.rstrip()}")
                    if "START" in line:
                        start_seen = True
                        break

            assert start_seen, "Child process did not print START"

            # Send SIGINT to parent process (simulating ^C)
            print("Sending SIGINT to auto-work process...")
            process.send_signal(signal.SIGINT)

            # Wait for process to complete (it should wait for child)
            try:
                stdout, stderr = process.communicate(timeout=8)  # Reduced from 15 to 8 seconds
                all_output.append(stdout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                pytest.fail("Process did not complete within timeout")

            full_output = "".join(all_output)
            print(f"\nFull stdout:\n{full_output}")
            print(f"\nFull stderr:\n{stderr}")

            # Verify child process completed successfully
            assert "START" in full_output, "START not found in output"
            assert "END" in full_output, "Child process did not complete (END not found)"
            assert "SIGINT_RECEIVED" not in full_output, (
                "Child process received SIGINT (should not happen)"
            )
            assert "Auto-work script stopped cleanly" in full_output or process.returncode in [
                0,
                -2,
            ], "Parent did not exit cleanly"

        finally:
            # Cleanup: ensure process is terminated
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_child_completes_before_next_iteration(
        self, mock_auto_work_script: Path, tmp_path: Path
    ) -> None:
        """
        Test that after SIGINT, the script completes current work but doesn't start new work.

        This verifies:
        1. First work task starts
        2. SIGINT is sent
        3. First work task completes
        4. No second work task is started
        """
        # Mock git commands
        mock_git = tmp_path / "git"
        mock_git.write_text(
            """#!/bin/bash
exit 0
"""
        )
        mock_git.chmod(0o755)

        # Mock gh command - always return 0 (below limit, would trigger multiple iterations)
        mock_gh = tmp_path / "gh"
        mock_gh.write_text(
            """#!/bin/bash
echo "0"
"""
        )
        mock_gh.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{tmp_path}:{env['PATH']}"

        process = subprocess.Popen(
            [sys.executable, str(mock_auto_work_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
        )

        try:
            # Collect all output and wait for first START
            all_output = []
            start_count = 0
            start_time = time.time()
            timeout = 5  # Reduced from 10 to 5 seconds

            while start_count < 1 and (time.time() - start_time) < timeout:
                import select

                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    line = process.stdout.readline()  # type: ignore[union-attr]
                    all_output.append(line)
                    print(f"Output: {line.rstrip()}")
                    if "START" in line:
                        start_count += 1
                        if start_count == 1:
                            # Send SIGINT after first START
                            print("Sending SIGINT after first START...")
                            process.send_signal(signal.SIGINT)

            assert start_count == 1, f"Expected 1 START, got {start_count}"

            # Wait for completion
            try:
                stdout, stderr = process.communicate(timeout=8)  # Reduced from 15 to 8 seconds
                all_output.append(stdout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                pytest.fail("Process did not complete within timeout")

            full_output = "".join(all_output)
            print(f"\nFull stdout:\n{full_output}")

            # Count how many times work started
            start_count = full_output.count("START")

            # Should see exactly 1 START (first iteration completed, second not started)
            assert start_count == 1, f"Expected exactly 1 START, found {start_count}"

            # Should see the END for the first (and only) work
            assert full_output.count("END") == 1, "Expected exactly 1 END"

            # Should see clean shutdown message
            assert "Auto-work script stopped cleanly" in full_output or process.returncode in [
                0,
                -2,
            ]

        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
