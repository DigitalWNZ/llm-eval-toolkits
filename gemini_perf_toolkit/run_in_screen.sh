#!/bin/bash
#
# Run Comprehensive Performance Test in Screen Session
#
# This script starts a screen session and runs the comprehensive performance test.
# You can detach from the screen session and let it run in the background.
#
# Usage:
#   ./run_in_screen.sh
#
# Screen commands:
#   Detach from screen:  Ctrl+A, then D
#   Re-attach to screen: screen -r perf
#   List screen sessions: screen -ls
#   Kill screen session: screen -X -S perf quit
#

# Check if screen is installed
if ! command -v screen &> /dev/null; then
    echo "Error: 'screen' is not installed"
    echo "Install it with: sudo apt install screen"
    exit 1
fi

# Check if screen session already exists
if screen -list | grep -q "perf"; then
    echo "Screen session 'perf' already exists"
    echo ""
    echo "Options:"
    echo "  1. Attach to existing session: screen -r perf"
    echo "  2. Kill existing session: screen -X -S perf quit"
    echo "  3. Use a different session name in this script"
    echo ""
    read -p "Do you want to kill the existing session and start fresh? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        screen -X -S perf quit
        echo "Existing session killed"
        sleep 1
    else
        echo "Exiting. Please attach to existing session or kill it first."
        exit 1
    fi
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "Starting Comprehensive Performance Test"
echo "========================================"
echo ""
echo "Screen session: perf"
echo "Script: $SCRIPT_DIR/run_comprehensive_test.sh"
echo ""
echo "This will run in the background. You can:"
echo "  - Detach: Press Ctrl+A, then D"
echo "  - Re-attach later: screen -r perf"
echo "  - Check status: screen -ls"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Start screen session with the test script
screen -dmS perf bash -c "
    cd '$SCRIPT_DIR'
    source ~/gemini-perf-test/venv/bin/activate
    bash run_comprehensive_test.sh
    echo ''
    echo 'Test completed! Press any key to close this screen session...'
    read -n 1
"

# Give screen a moment to start
sleep 1

echo ""
echo "✓ Screen session 'perf' started successfully!"
echo ""
echo "To attach to the session and monitor progress:"
echo "  screen -r perf"
echo ""
echo "To detach from the session (while inside):"
echo "  Press Ctrl+A, then press D"
echo ""
echo "To list all screen sessions:"
echo "  screen -ls"
echo ""
echo "The test is now running in the background."
echo "Results will be saved in the working directory when complete."
echo ""
