# Gemini Performance Testing Toolkit

Complete toolkit for running comprehensive Gemini model performance tests.

## 📦 Package Contents

### Core Programs
- **`gemini_perf_test.py`** - Single performance test with detailed metrics
- **`gemini_perf_controller.py`** - Batch test controller for multi-configuration testing
- **`setup.sh`** - Automated environment setup script for Debian/Ubuntu

### Documentation
- **`VM_DEPLOYMENT_README.md`** - ⭐ **START HERE** - Main deployment guide with examples
- **`QUICKSTART_VM.md`** - 5-minute quick start guide for Debian 12 VM
- **`SETUP_GUIDE.md`** - Detailed step-by-step setup instructions
- **`DEPLOYMENT_CHECKLIST.md`** - Deployment verification checklist
- **`DEPLOYMENT_PACKAGE_SUMMARY.txt`** - Quick reference summary

### Benchmark Data
- **`benchmark/`** - Request JSON files for different sizes:
  - `request_1k.json` - ~1,000 tokens
  - `request_2k.json` - ~2,000 tokens
  - `request_5k.json` - ~5,000 tokens
  - `request_10k.json` - ~10,000 tokens
  - `request_50k.json` - ~50,000 tokens
  - `request_100k.json` - ~100,000 tokens

### Sample Results
- **`test_results_20260401_145808/`** - Sample execution results:
  - CSV output with all metrics
  - JSON results for each test
  - Execution logs

---

## 🚀 Quick Start

### Local Testing (Current Machine)

```bash
# Run single test
python3 gemini_perf_test.py \
  --model gemini-3-flash-preview \
  --project cloud-llm-preview1 \
  --iterations 5 \
  --request-file benchmark/request_1k.json \
  --thinking-level medium

# Run batch tests
python3 gemini_perf_controller.py \
  --models gemini-3-flash-preview gemini-2.5-flash \
  --request-files benchmark/request_1k.json benchmark/request_2k.json \
  --thinking-levels minimal low medium high \
  --thinking-budgets 512 1024 2048 \
  --iterations 5
```

### Deploy to Debian 12 VM

**Read `VM_DEPLOYMENT_README.md` for complete instructions.**

Quick steps:
1. Transfer entire `gemini_perf_toolkit/` folder to VM
2. Run `bash setup.sh` on VM
3. Run tests

---

## 📊 What Gets Measured

### Performance Metrics
- **TTFT (Time to First Token)** - Min, P50, P90, P95, P99, Max
- **Token Counts** - Input, Output, Cached (with percentiles)
- **Traffic Type** - ON_DEMAND vs PROVISIONED_THROUGHPUT

### Output Formats
- **CSV** - Consolidated results for all test combinations
- **JSON** - Individual detailed results for each test
- **Logs** - Complete execution logs with traffic type info

---

## 📖 Documentation Guide

| Want to... | Read this |
|------------|-----------|
| Get started in 5 minutes | `QUICKSTART_VM.md` |
| See usage examples | `VM_DEPLOYMENT_README.md` |
| Understand every setup step | `SETUP_GUIDE.md` |
| Verify deployment | `DEPLOYMENT_CHECKLIST.md` |
| Quick reference | `DEPLOYMENT_PACKAGE_SUMMARY.txt` |

---

## 🔧 Requirements

### System Requirements
- Python 3.9+
- Debian 12 / Ubuntu 20.04+ (or compatible)
- Internet access

### Python Dependencies
```bash
pip install google-genai
```

### GCP Requirements
- GCP project with Vertex AI API enabled
- Service account with `Vertex AI User` role
- Service account key JSON file

---

## 📁 Folder Structure

```
gemini_perf_toolkit/
├── gemini_perf_test.py                 # Single test program
├── gemini_perf_controller.py           # Batch test controller
├── setup.sh                            # Environment setup script
├── VM_DEPLOYMENT_README.md             # Main guide
├── QUICKSTART_VM.md                    # Quick start
├── SETUP_GUIDE.md                      # Detailed setup
├── DEPLOYMENT_CHECKLIST.md             # Verification checklist
├── DEPLOYMENT_PACKAGE_SUMMARY.txt      # Quick reference
├── benchmark/                          # Request files
│   ├── request_1k.json
│   ├── request_2k.json
│   ├── request_5k.json
│   ├── request_10k.json
│   ├── request_50k.json
│   └── request_100k.json
└── test_results_20260401_145808/       # Sample results
    ├── perf_results_20260401_145808.csv
    ├── gemini-3-flash-preview_request_1k_level_minimal_*.json
    ├── gemini-3-flash-preview_request_1k_*.json
    └── perf_test_20260401_145808.log
```

---

## 🎯 Example Use Cases

### Compare Models
```bash
python3 gemini_perf_controller.py \
  --models gemini-2.5-flash gemini-3-flash-preview \
  --request-files benchmark/request_1k.json \
  --iterations 10
```

### Test Thinking Configurations
```bash
python3 gemini_perf_controller.py \
  --models gemini-3-flash-preview \
  --request-files benchmark/request_1k.json \
  --thinking-levels minimal low medium high \
  --iterations 5
```

### Scalability Testing
```bash
python3 gemini_perf_controller.py \
  --models gemini-3-flash-preview \
  --request-files benchmark/request_1k.json benchmark/request_5k.json benchmark/request_10k.json \
  --thinking-levels medium \
  --iterations 10
```

---

## 📈 Sample Results (Included)

The `test_results_20260401_145808/` folder contains real results showing:

- **Traffic Type Detection**: `PROVISIONED_THROUGHPUT` vs `ON_DEMAND`
- **Performance Metrics**: TTFT, token counts with percentiles
- **Different Configurations**: With and without thinking level

**CSV Preview:**
| Model | Thinking Level | Traffic Type | TTFT P50 |
|-------|----------------|--------------|----------|
| gemini-3-flash-preview | minimal | PROVISIONED_THROUGHPUT | 5154ms |
| gemini-3-flash-preview | none | ON_DEMAND | 8490ms |

---

## 🔐 Authentication Setup

You need a GCP service account key file. Place it in the toolkit directory or set:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

See `SETUP_GUIDE.md` for detailed authentication instructions.

---

## 💡 Tips

- **Start with small iterations** (2-5) to validate setup
- **Use baseline tests** (no thinking config) for comparison
- **Check logs** if tests fail - detailed error messages included
- **Monitor GCP quotas** for high-volume testing
- **Save results** regularly - CSV files are timestamped

---

## 📞 Need Help?

1. Check `DEPLOYMENT_CHECKLIST.md` for common issues
2. Review `SETUP_GUIDE.md` troubleshooting section
3. Examine log files in test results
4. Verify authentication is configured correctly

---

## 🚢 Ready to Deploy?

**Open `VM_DEPLOYMENT_README.md` and follow the guide!**

Or for fastest start: **Open `QUICKSTART_VM.md`** (5 minutes to first test)

---

**Version:** 1.0
**Last Updated:** 2026-04-01
**Features:** P50/P90/P95/P99 metrics, Traffic Type tracking, Thinking config support
