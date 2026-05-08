#!/bin/bash
set -e

SESSION="caclaude"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"   # CaClaude repo root
CACLAUDE_MD="$SCRIPT_DIR/CLAUDE.md"

PROJECT_DIR="${1:-$PWD}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
TARGET_MD="$PROJECT_DIR/CLAUDE.md"
BACKUP_MD="$PROJECT_DIR/CLAUDE.md.caclaude_backup"

echo "=== CaClaude Launcher ==="
echo "Project: $PROJECT_DIR"

# Inject claude.md
INJECT_MD=false
if [ "$(realpath "$PROJECT_DIR")" != "$(realpath "$ROOT_DIR")" ]; then
    INJECT_MD=true
    if [ -f "$TARGET_MD" ]; then
        cp "$TARGET_MD" "$BACKUP_MD"
        echo "Backed up existing CLAUDE.md"
    fi
    cp "$CACLAUDE_MD" "$TARGET_MD"
    echo "Injected CaClaude CLAUDE.md"
fi

# Cleanup
cleanup() {
    echo ""
    if [ "$INJECT_MD" = true ]; then
        echo "Cleaning up CLAUDE.md..."
        rm -f "$TARGET_MD"
        if [ -f "$BACKUP_MD" ]; then
            mv "$BACKUP_MD" "$TARGET_MD"
            echo "Restored original CLAUDE.md"
        fi
    fi
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT

# Kill any stale session
tmux kill-session -t "$SESSION" 2>/dev/null && echo "Killed old session." || true

# Create new tmux session, cd into project, then launch Claude
tmux new-session -d -s "$SESSION" -x 220 -y 55
tmux send-keys -t "$SESSION" "cd \"$PROJECT_DIR\" && claude" Enter

echo "Tmux session '$SESSION' created."

# Open a new Terminal window attached to that session
osascript <<'APPLESCRIPT'
tell application "Terminal"
    activate
    set newWin to do script "tmux attach -t caclaude"
    delay 0.3
    set frontmost of window 1 to true
end tell
APPLESCRIPT

echo "Terminal window opened. Attach manually with: tmux attach -t $SESSION"
echo ""
echo "Starting trackers (close either overlay window or press q to stop)..."
sleep 0.5

cd "$ROOT_DIR"
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

python3 tracker.py
