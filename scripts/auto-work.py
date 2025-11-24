#!/usr/bin/env python3
"""
Auto-work script: Automatically creates PRs when count drops below 5
Runs in a forever loop, checking PR count and spawning /work-next
"""

import os
import signal
import subprocess
import sys
import time
from datetime import datetime

MAX_PRS = 5
SLEEP_MINUTES = 1

# Flag for graceful shutdown
running = True
shutdown_requested = False


def cleanup(signum: int, frame: object) -> None:
    """Signal handler for graceful shutdown on first ^C, force quit on second"""
    global running, shutdown_requested

    if shutdown_requested:
        # Second ^C - force quit immediately
        print()
        print("🚨 Second interrupt received, forcing immediate exit...")
        sys.exit(130)  # Standard exit code for SIGINT

    # First ^C - graceful shutdown
    print()
    print("🛑 Received shutdown signal, stopping gracefully...")
    print("   Press Ctrl+C again to force quit immediately")
    shutdown_requested = True
    running = False


def run_command(cmd: list[str], error_msg: str) -> bool:
    """
    Run a command and return True if successful, False otherwise.

    Args:
        cmd: Command to run as list of strings
        error_msg: Error message to display if command fails

    Returns:
        True if command succeeded, False otherwise
    """
    try:
        subprocess.run(cmd, check=True, capture_output=False)
        return True
    except subprocess.CalledProcessError:
        print(f"  ❌ {error_msg}")
        return False


def get_pr_count() -> int:
    """Get count of open PRs using gh CLI"""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "number", "--jq", "length"],
            check=True,
            capture_output=True,
            text=True,
        )
        return int(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        print("  ❌ Failed to get PR count")
        sys.exit(1)


def main() -> None:
    """Main loop for auto-work script"""
    global running

    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("🤖 Auto-work script started")
    print(f"   Max PRs: {MAX_PRS}")
    print(f"   Check interval: {SLEEP_MINUTES} minutes")
    print("   Press Ctrl+C to stop gracefully")
    print()

    while running:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Starting iteration...")

        # Fetch from origin
        print("  📡 Fetching from origin...")
        if not run_command(["git", "fetch", "origin"], "Failed to fetch from origin, stopping..."):
            sys.exit(1)

        # Rebase on origin/main
        print("  🔄 Rebasing on origin/main...")
        try:
            subprocess.run(["git", "rebase", "origin/main"], check=True, capture_output=False)
        except subprocess.CalledProcessError:
            print("  ⚠️  Rebase failed, spawning Claude to resolve conflicts...")
            # Spawn a new Claude session to run /sync-main
            try:
                subprocess.run(
                    ["claude", "--print", "/sync-main"],
                    check=True,
                )
                print("  ✅ Claude finished processing")

                # Check if rebase is still in progress (stuck)
                rebase_dir_result = subprocess.run(
                    ["git", "rev-parse", "--git-path", "rebase-merge"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                rebase_in_progress = os.path.exists(rebase_dir_result.stdout.strip())

                if rebase_in_progress:
                    print("  ❌ Rebase is still stuck, aborting...")
                    subprocess.run(["git", "rebase", "--abort"], check=False)
                    sys.exit(1)
                else:
                    print("  ✅ Rebase completed successfully")

            except subprocess.CalledProcessError:
                print("  ❌ Failed to resolve conflicts, aborting rebase...")
                subprocess.run(["git", "rebase", "--abort"], check=False)
                sys.exit(1)

        # Count open PRs
        pr_count = get_pr_count()
        print(f"  📊 Open PRs: {pr_count}")

        # Check if we should stop before starting new work
        if not running:
            break

        # Check if we're at or above the limit
        if pr_count >= MAX_PRS:
            print(f"  ⏸️  At PR limit ({pr_count}/{MAX_PRS}), waiting...")
        else:
            print(f"  🚀 Below limit ({pr_count}/{MAX_PRS}), starting new work...")

            # Run /work-next command (signal handlers remain enabled for graceful shutdown)
            # Create a new process group for the child so it doesn't receive our SIGINT
            try:
                subprocess.run(
                    ["claude", "--dangerously-skip-permissions", "--print", "/work-next"],
                    check=True,
                    preexec_fn=os.setpgrp,  # Create new process group (Unix only)
                )
                print("  ✅ Work completed successfully")
            except subprocess.CalledProcessError:
                print("  ❌ Work failed or interrupted")

        print(f"  💤 Sleeping for {SLEEP_MINUTES} minutes...")
        print()

        # Sleep with ability to interrupt
        for _ in range(SLEEP_MINUTES):
            if not running:
                break
            time.sleep(60)

    print("✅ Auto-work script stopped cleanly")


if __name__ == "__main__":
    main()
