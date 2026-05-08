#!/bin/bash
#
# Claude Performance Benchmark Script
#
# Models: claude-opus-4-7, claude-opus-4-6, claude-sonnet-4-6
# Request files: ~/slow_request_40s_claude.json, ~/slow_request_60s_claude.json
# Effort levels: high, medium, low
# Iterations: 10
#
# Total: 3 models x 2 requests x 3 efforts x 10 iterations = 180 API calls
#

set -e

echo "========================================"
echo "Claude Performance Benchmark"
echo "========================================"
echo ""
echo "Test Configuration:"
echo "  Models: claude-opus-4-7, claude-opus-4-6, claude-sonnet-4-6"
echo "  Request Files: slow_request_40s, slow_request_60s"
echo "  Effort Levels: high, medium, low"
echo "  Iterations: 10"
echo ""

# Check request files exist
for f in ~/slow_request_40s_claude.json ~/slow_request_60s_claude.json; do
    if [ ! -f "$f" ]; then
        echo "Error: Request file not found: $f"
        exit 1
    fi
done

# Countdown
for i in 5 4 3 2 1; do
    echo "Starting in $i seconds... (Ctrl+C to cancel)"
    sleep 1
done
echo ""

echo "========================================"
echo "Starting Performance Tests..."
echo "========================================"
echo ""

python3 ~/claude_perf_benchmark.py \
    --models claude-opus-4-7 claude-opus-4-6 claude-sonnet-4-6 \
    --request-files ~/slow_request_40s_claude.json ~/slow_request_60s_claude.json \
    --efforts high medium low \
    --iterations 10

echo ""
echo "========================================"
echo "Benchmark Completed!"
echo "========================================"
echo ""
echo "Results:"
echo "  - CSV: ~/claude_perf_results/perf_results_*.csv"
echo "  - JSON: ~/claude_perf_results/json_results/"
echo ""
