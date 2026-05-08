#!/bin/bash
#
# XHS Gemini Performance Test Script
#
# This script runs performance tests across:
# - 3 models: gemini-3.1-pro-preview, gemini-3-flash-preview, gemini-3.1-flash-lite
# - 2 request files: ~/slow_request_40s.json, ~/slow_request_60s.json
# - Thinking levels: low, medium, high (gemini-3.1-pro-preview)
#                    minimal, low, medium, high (gemini-3-flash-preview, gemini-3.1-flash-lite)
# - 10 iterations per test
#
# Usage:
#   ./run_comprehensive_test_xhs.sh
#

set -e  # Exit on error

echo "========================================"
echo "Gemini Performance XHS Test"
echo "========================================"
echo ""

# Configuration
VENV_PATH="$HOME/gemini-perf-test/venv"
WORK_DIR="$HOME/gemini-perf-test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please run setup.sh first or adjust VENV_PATH in this script"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Change to working directory
if [ ! -d "$WORK_DIR" ]; then
    echo "Warning: Working directory $WORK_DIR does not exist"
    echo "Using current directory: $SCRIPT_DIR"
    WORK_DIR="$SCRIPT_DIR"
fi

cd "$WORK_DIR"
echo "Working directory: $(pwd)"
echo ""

# Check if controller script exists
if [ ! -f "gemini_perf_controller.py" ]; then
    echo "Error: gemini_perf_controller.py not found in $WORK_DIR"
    exit 1
fi

# Check if request files exist
for f in ~/slow_request_40s.json ~/slow_request_60s.json; do
    if [ ! -f "$f" ]; then
        echo "Error: Request file not found: $f"
        exit 1
    fi
done

# Display test configuration
echo "Test Configuration:"
echo "  Models: gemini-3.1-pro-preview, gemini-3-flash-preview, gemini-3.1-flash-lite"
echo "  Request Files: ~/slow_request_40s.json, ~/slow_request_60s.json"
echo "  Thinking Levels: low, medium, high (gemini-3.1-pro-preview)"
echo "                   minimal, low, medium, high (gemini-3-flash-preview, gemini-3.1-flash-lite)"
echo "  Iterations: 10"
echo ""

# Countdown before starting
for i in 5 4 3 2 1; do
    echo "Starting in $i seconds... (Ctrl+C to cancel)"
    sleep 1
done
echo ""

# Run the test
echo "========================================"
echo "Starting Performance Tests..."
echo "========================================"
echo ""

# Run gemini-3.1-pro-preview with low/medium/high (minimal not supported)
python gemini_perf_controller.py \
    --models gemini-3.1-pro-preview \
    --request-files ~/slow_request_40s.json ~/slow_request_60s.json \
    --thinking-levels low medium high \
    --iterations 10

# Run gemini-3-flash-preview and gemini-3.1-flash-lite with all thinking levels
python gemini_perf_controller.py \
    --models gemini-3-flash-preview gemini-3.1-flash-lite \
    --request-files ~/slow_request_40s.json ~/slow_request_60s.json \
    --thinking-levels minimal low medium high \
    --iterations 10

# Deactivate virtual environment
deactivate

echo ""
echo "========================================"
echo "Test Completed!"
echo "========================================"
echo ""
echo "Results can be found in:"
echo "  - CSV: perf_results_*.csv"
echo "  - JSON: json_results/"
echo "  - Logs: logs/"
echo ""
