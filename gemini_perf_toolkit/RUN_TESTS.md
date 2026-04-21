# How to Run Performance Tests

## Quick Reference

### 🚀 Option 1: Run in Screen Session (Recommended for Long Tests)

```bash
# Start comprehensive test in background screen session
./run_in_screen.sh

# Detach from screen: Press Ctrl+A, then D
# Re-attach later: screen -r perf
```

### ⚡ Option 2: Run Directly (Foreground)

```bash
# Run comprehensive test in current terminal
./run_comprehensive_test.sh
```

### 🎯 Option 3: Run Custom Tests

```bash
# Activate environment first
source ~/gemini-perf-test/venv/bin/activate

# Run custom test
python gemini_perf_controller.py \
  --models gemini-3-flash-preview \
  --request-files benchmark/request_1k.json \
  --thinking-levels medium \
  --iterations 5
```

---

## Comprehensive Test Configuration

The `run_comprehensive_test.sh` script runs:

**Models:**
- `gemini-3-flash-preview`
- `gemini-2.5-flash`

**Request Sizes:**
- 1k tokens (`benchmark/request_1k.json`)
- 2k tokens (`benchmark/request_2k.json`)
- 5k tokens (`benchmark/request_5k.json`)
- 10k tokens (`benchmark/request_10k.json`)

**Thinking Configurations:**
- **Levels** (Gemini 3.x): minimal, low, medium, high
- **Budgets** (Gemini 2.x): -1, 512, 1024, 2048, 4096, 8192, 16384, 32768

**Iterations:** 10 per test

**Total Combinations:** ~96 tests

**Estimated Time:** 2-4 hours (depends on quota and model availability)

---

## Screen Session Commands

### Start test in screen:
```bash
./run_in_screen.sh
```

### Attach to running test:
```bash
screen -r perf
```

### Detach from screen:
```
Press: Ctrl+A, then D
```

### List all screen sessions:
```bash
screen -ls
```

### Kill screen session:
```bash
screen -X -S perf quit
```

### View logs while test is running:
```bash
# In another terminal
tail -f ~/gemini-perf-test/logs/perf_test_*.log
```

---

## Monitoring Progress

### Watch log file in real-time:
```bash
# Find latest log
ls -lt ~/gemini-perf-test/logs/perf_test_*.log | head -1

# Tail the latest log
tail -f ~/gemini-perf-test/logs/perf_test_YYYYMMDD_HHMMSS.log
```

### Check partial results:
```bash
# View latest CSV (updates as tests complete)
ls -lt ~/gemini-perf-test/perf_results_*.csv | head -1

# Count completed tests
wc -l ~/gemini-perf-test/perf_results_*.csv
```

---

## Customizing Tests

### Edit `run_comprehensive_test.sh` to modify:

**Change models:**
```bash
--models gemini-3-flash-preview gemini-2.0-flash-exp
```

**Change request sizes:**
```bash
--request-files benchmark/request_1k.json benchmark/request_50k.json
```

**Change thinking levels:**
```bash
--thinking-levels low medium high
```

**Change thinking budgets:**
```bash
--thinking-budgets 512 1024 2048 4096
```

**Change iterations:**
```bash
--iterations 5  # Reduce for faster testing
```

### Or create your own script:
```bash
#!/bin/bash
source ~/gemini-perf-test/venv/bin/activate
cd ~/gemini-perf-test

python gemini_perf_controller.py \
  --models gemini-3-flash-preview \
  --request-files benchmark/request_1k.json benchmark/request_2k.json \
  --thinking-levels medium high \
  --iterations 5
```

---

## Expected Output

### During execution:
```
====================================================================================================
GEMINI PERFORMANCE TEST CONTROLLER
====================================================================================================
Run ID: 20260401_145808
Models: gemini-3-flash-preview, gemini-2.5-flash
...

Test 1/96
  Model: gemini-3-flash-preview
  Request File: benchmark/request_1k.json
  Thinking Level: minimal
----------------------------------------------------------------------------------------------------
Running 10 iterations...
  Iteration 1/10...
    ✓ TTFT: 5154.11ms, Traffic Type: TrafficType.PROVISIONED_THROUGHPUT
...
```

### After completion:
```
CSV results saved to: perf_results_20260401_145808.csv
Total successful tests: 96/96
```

---

## Results Location

After test completes, find results in:

```
~/gemini-perf-test/
├── perf_results_YYYYMMDD_HHMMSS.csv     # Consolidated CSV
├── json_results/                         # Individual JSON files
│   ├── gemini-3-flash-preview_request_1k_level_minimal_*.json
│   └── ...
└── logs/
    └── perf_test_YYYYMMDD_HHMMSS.log    # Execution log
```

### Download results:
```bash
# From local machine
scp user@vm-ip:~/gemini-perf-test/perf_results_*.csv ./
scp -r user@vm-ip:~/gemini-perf-test/json_results ./
```

---

## Troubleshooting

### Script not found:
```bash
# Make scripts executable
chmod +x *.sh
```

### Screen session exists:
```bash
# Kill old session
screen -X -S perf quit

# Or use different session name in run_in_screen.sh
```

### Virtual environment not found:
```bash
# Adjust VENV_PATH in run_comprehensive_test.sh
# or run setup.sh first
```

### Authentication error:
```bash
# Check credentials are set
echo $GOOGLE_APPLICATION_CREDENTIALS

# Re-set if needed
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/sa-key.json"
```

---

## Quick Test (Before Running Full Suite)

```bash
# Test with minimal configuration
python gemini_perf_controller.py \
  --models gemini-3-flash-preview \
  --request-files benchmark/request_1k.json \
  --thinking-levels minimal \
  --iterations 2

# If this works, run the full comprehensive test
./run_in_screen.sh
```

---

## Tips

1. **Start small** - Test with 1-2 iterations first to validate setup
2. **Use screen** - For long tests, always use screen session
3. **Monitor logs** - Check logs periodically for errors
4. **Check quotas** - Ensure you have sufficient GCP quota
5. **Save results** - Results are timestamped, safe to run multiple times
6. **Background execution** - Screen lets you disconnect and reconnect safely

---

## Need Help?

- Check log files: `tail -f logs/perf_test_*.log`
- Review `SETUP_GUIDE.md` for setup issues
- See `DEPLOYMENT_CHECKLIST.md` for verification steps
- Check authentication: `gcloud auth list`

---

**Ready to start?** Run `./run_in_screen.sh` and monitor with `screen -r perf`
