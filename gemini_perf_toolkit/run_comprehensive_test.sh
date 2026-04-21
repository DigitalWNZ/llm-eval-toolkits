#!/bin/bash
#
# Comprehensive Gemini Performance Test Script
#
# This script runs extensive performance tests across:
# - 2 models: gemini-3-flash-preview, gemini-2.5-flash
# - 4 request sizes: 1k, 2k, 5k, 10k
# - 4 thinking levels (for Gemini 3.x): minimal, low, medium, high
# - 8 thinking budgets (for Gemini 2.x): -1, 512, 1024, 2048, 4096, 8192, 16384, 32768
# - 10 iterations per test
#
# Total test combinations: ~96 tests (may take several hours)
#
# Usage:
#   ./run_comprehensive_test.sh
#
# Note: This script assumes it's running in a screen session or background process.
#

set -e  # Exit on error

echo "========================================"
echo "Gemini Performance Comprehensive Test"
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

# Display test configuration
echo "Test Configuration:"
echo "  Models: gemini-3-flash-preview, gemini-2.5-flash"
echo "  Request Files: 1k, 2k, 5k, 10k"
echo "  Thinking Levels: minimal, low, medium, high"
echo "  Thinking Budgets: -1, 512, 1024, 2048, 4096, 8192, 16384, 32768"
echo "  Iterations: 10"
echo ""
echo "Estimated time: 2-4 hours (depending on quota and model availability)"
echo ""

# Countdown before starting
for i in 5 4 3 2 1; do
    echo "Starting in $i seconds... (Ctrl+C to cancel)"
    sleep 1
done
echo ""

# Run the comprehensive test
echo "========================================"
echo "Starting Performance Tests..."
echo "========================================"
echo ""

python gemini_perf_controller.py \
    --models gemini-3-flash-preview gemini-2.5-flash \
    --request-files benchmark/request_1k.json benchmark/request_2k.json benchmark/request_5k.json benchmark/request_10k.json \
    --thinking-levels minimal low medium high \
    --thinking-budgets -1 512 1024 2048 4096 8192 16384 32768 \
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
