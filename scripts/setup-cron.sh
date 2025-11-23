#!/usr/bin/env bash
set -euo pipefail

# Get the absolute path to the scripts directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_MERGE_SCRIPT="$SCRIPT_DIR/auto-merge-prs.sh"

# Get repository directory (use current directory by default, or first argument)
REPO_DIR="${1:-$(pwd)}"

# Verify it's a git repository (check for .git directory or file for worktrees)
if [ ! -e "$REPO_DIR/.git" ]; then
    echo "ERROR: $REPO_DIR is not a git repository"
    echo ""
    echo "Usage: $0 [repository_directory]"
    echo ""
    echo "Example:"
    echo "  cd /path/to/your/repo"
    echo "  $0"
    echo ""
    echo "Or:"
    echo "  $0 /path/to/your/repo"
    exit 1
fi

# Get absolute path
REPO_DIR="$(cd "$REPO_DIR" && pwd)"

echo "Setting up auto-merge for repository: $REPO_DIR"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS. Using launchd for scheduling..."

    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_FILE="$PLIST_DIR/com.automerge.prs.plist"

    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$PLIST_DIR"

    # Create launchd plist
    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.automerge.prs</string>
    <key>ProgramArguments</key>
    <array>
        <string>${AUTO_MERGE_SCRIPT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${HOME}/Library/Logs/auto-merge-prs.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/Library/Logs/auto-merge-prs-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

    echo "Created launchd plist at: $PLIST_FILE"

    # Load the plist
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"

    echo ""
    echo "Auto-merge PR job installed successfully!"
    echo ""
    echo "The script will run every minute."
    echo ""
    echo "Logs are available at:"
    echo "  - Standard output: ~/Library/Logs/auto-merge-prs.log"
    echo "  - Errors: ~/Library/Logs/auto-merge-prs-error.log"
    echo ""
    echo "To uninstall, run:"
    echo "  launchctl unload $PLIST_FILE"
    echo "  rm $PLIST_FILE"

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux. Using cron for scheduling..."

    CRON_ENTRY="* * * * * cd $REPO_DIR && $AUTO_MERGE_SCRIPT >> $HOME/auto-merge-prs.log 2>&1"

    # Check if entry already exists
    if crontab -l 2>/dev/null | grep -q "$AUTO_MERGE_SCRIPT"; then
        echo "Cron job already exists. Skipping."
    else
        # Add to crontab
        (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
        echo "Added cron job to run every minute"
        echo ""
        echo "Logs are available at: ~/auto-merge-prs.log"
        echo ""
        echo "To remove the cron job, run:"
        echo "  crontab -e"
        echo "and delete the line containing: $AUTO_MERGE_SCRIPT"
    fi
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi
