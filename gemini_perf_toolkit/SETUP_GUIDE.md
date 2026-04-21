# Gemini Performance Testing - Setup Guide for Debian 12

This guide walks you through setting up and running the Gemini performance testing tools on a fresh Debian 12 VM.

## Prerequisites

- Debian 12 VM with internet access
- GCP project with Vertex AI API enabled
- Service account credentials or gcloud CLI configured

---

## Step 1: Install System Dependencies

Update the system and install required packages:

```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Install git (optional, for cloning repositories)
sudo apt install -y git

# Verify Python version (should be 3.11+)
python3 --version
```

---

## Step 2: Set Up Google Cloud Authentication

### Option A: Using Service Account Key File (Recommended for VMs)

1. **Create a service account** in your GCP project with these roles:
   - `Vertex AI User` or `Vertex AI Administrator`

2. **Download the JSON key file** for the service account

3. **Copy the key file to your VM**:
   ```bash
   # If using scp from your local machine:
   scp /path/to/service-account-key.json user@vm-ip:~/sa-key.json
   ```

4. **Set the environment variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/sa-key.json"

   # Add to your shell profile to persist
   echo 'export GOOGLE_APPLICATION_CREDENTIALS="$HOME/sa-key.json"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Option B: Using gcloud CLI

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize and authenticate
gcloud init
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

---

## Step 3: Set Up the Project Directory

```bash
# Create project directory
mkdir -p ~/gemini-perf-test
cd ~/gemini-perf-test

# Create directory structure
mkdir -p benchmark logs json_results
```

---

## Step 4: Copy Performance Testing Scripts

### Copy the Python scripts to your VM

**Option 1: Using scp from your local machine**
```bash
# From your local machine where you have the files
scp gemini_perf_test.py user@vm-ip:~/gemini-perf-test/
scp gemini_perf_controller.py user@vm-ip:~/gemini-perf-test/
```

**Option 2: Create files directly on the VM**
```bash
# SSH into your VM first, then create the files
cd ~/gemini-perf-test
nano gemini_perf_test.py        # Paste content and save (Ctrl+X, Y, Enter)
nano gemini_perf_controller.py  # Paste content and save
```

**Option 3: Download from your repository (if available)**
```bash
cd ~/gemini-perf-test
wget https://your-repo/gemini_perf_test.py
wget https://your-repo/gemini_perf_controller.py
```

Make the scripts executable:
```bash
chmod +x gemini_perf_test.py gemini_perf_controller.py
```

---

## Step 5: Copy Benchmark Request Files

Copy your request JSON files to the `benchmark/` directory:

```bash
# From your local machine
scp backend/benchmark/*.json user@vm-ip:~/gemini-perf-test/benchmark/
```

Or create sample request files manually:
```bash
cd ~/gemini-perf-test/benchmark

# Create a simple 1k request file
cat > request_1k.json <<'EOF'
{
  "contents": [
    {
      "role": "user",
      "parts": [
        {
          "text": "Please analyze and summarize the following comprehensive document about artificial intelligence and machine learning technologies.\n\nArtificial Intelligence: A Comprehensive Overview\n\nIntroduction to Artificial Intelligence\nArtificial intelligence (AI) represents one of the most transformative technologies of the modern era..."
        }
      ]
    }
  ],
  "generation_config": {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 2048
  }
}
EOF
```

---

## Step 6: Install Python Dependencies

```bash
cd ~/gemini-perf-test

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required packages
pip install --upgrade pip
pip install google-genai

# Verify installation
python3 -c "import google.genai; print('google-genai installed successfully')"
```

**Important**: Always activate the virtual environment before running the scripts:
```bash
source ~/gemini-perf-test/venv/bin/activate
```

---

## Step 7: Verify Setup

Test that everything is configured correctly:

```bash
# Check Python version
python3 --version

# Check google-genai installation
python3 -c "from google import genai; print('OK')"

# Verify authentication
python3 -c "from google import genai; client = genai.Client(vertexai=True, project='cloud-llm-preview1', location='global'); print('Authentication OK')"
```

---

## Step 8: Run the Performance Tests

### Running Single Test (gemini_perf_test.py)

**Basic usage:**
```bash
cd ~/gemini-perf-test
source venv/bin/activate

python3 gemini_perf_test.py \
  --model gemini-3-flash-preview \
  --project cloud-llm-preview1 \
  --location global \
  --iterations 5 \
  --request-file benchmark/request_1k.json
```

**With thinking level (Gemini 3.x):**
```bash
python3 gemini_perf_test.py \
  --model gemini-3-flash-preview \
  --project cloud-llm-preview1 \
  --iterations 5 \
  --request-file benchmark/request_1k.json \
  --thinking-level medium
```

**With thinking budget (Gemini 2.x):**
```bash
python3 gemini_perf_test.py \
  --model gemini-2.5-flash \
  --project cloud-llm-preview1 \
  --iterations 5 \
  --request-file benchmark/request_1k.json \
  --thinking-budget 1024
```

### Running Batch Tests (gemini_perf_controller.py)

**Comprehensive test across multiple configurations:**
```bash
cd ~/gemini-perf-test
source venv/bin/activate

python3 gemini_perf_controller.py \
  --models gemini-3-flash-preview gemini-2.5-flash \
  --request-files benchmark/request_1k.json benchmark/request_2k.json \
  --thinking-levels minimal low medium high \
  --thinking-budgets -1 512 1024 2048 4096 \
  --iterations 5 \
  --project cloud-llm-preview1 \
  --location global
```

**Quick test (fewer iterations):**
```bash
python3 gemini_perf_controller.py \
  --models gemini-3-flash-preview \
  --request-files benchmark/request_1k.json \
  --thinking-levels low medium \
  --iterations 2
```

---

## Step 9: View Results

### CSV Results
```bash
# View the latest CSV results
ls -lt perf_results_*.csv | head -1

# Preview CSV content
head -5 perf_results_*.csv | column -t -s,
```

### JSON Results
```bash
# List all JSON results
ls -lh json_results/

# View a specific JSON result
cat json_results/gemini-3-flash-preview_request_1k_level_medium_*.json | python3 -m json.tool | less
```

### Logs
```bash
# View the latest log
ls -lt logs/perf_test_*.log | head -1

# Tail the log file in real-time during execution
tail -f logs/perf_test_*.log
```

### Download Results to Local Machine
```bash
# From your local machine
scp user@vm-ip:~/gemini-perf-test/perf_results_*.csv ./
scp -r user@vm-ip:~/gemini-perf-test/json_results ./
scp -r user@vm-ip:~/gemini-perf-test/logs ./
```

---

## Step 10: Running Tests in Background

For long-running tests, use `nohup` or `screen`:

### Using nohup
```bash
nohup python3 gemini_perf_controller.py \
  --models gemini-3-flash-preview gemini-2.5-flash \
  --request-files benchmark/request_1k.json \
  --thinking-levels minimal low medium high \
  --thinking-budgets 512 1024 2048 \
  --iterations 10 \
  > perf_test.out 2>&1 &

# Check progress
tail -f perf_test.out

# Check if still running
ps aux | grep gemini_perf_controller
```

### Using screen (recommended for long tests)
```bash
# Install screen if not available
sudo apt install -y screen

# Start a screen session
screen -S perf_test

# Run your test
python3 gemini_perf_controller.py [options...]

# Detach from screen: Press Ctrl+A, then D

# Re-attach later
screen -r perf_test

# List all screen sessions
screen -ls
```

---

## Troubleshooting

### Issue: "ImportError: No module named google.genai"
**Solution:**
```bash
source ~/gemini-perf-test/venv/bin/activate
pip install google-genai
```

### Issue: "Authentication error"
**Solution:**
```bash
# Verify credentials file exists
ls -l $GOOGLE_APPLICATION_CREDENTIALS

# Or re-authenticate with gcloud
gcloud auth application-default login
```

### Issue: "Permission denied"
**Solution:**
```bash
chmod +x gemini_perf_test.py gemini_perf_controller.py
```

### Issue: "Model not found" or "RESOURCE_EXHAUSTED"
**Solution:**
- Verify the model name is correct
- Check that your project has access to the model
- Try a different location (e.g., `us-central1` instead of `global`)
- Wait a few minutes and retry if quota is exhausted

### Issue: "Request file not found"
**Solution:**
```bash
# Use absolute path
python3 gemini_perf_test.py \
  --request-file /home/user/gemini-perf-test/benchmark/request_1k.json \
  [other options...]

# Or ensure you're in the correct directory
cd ~/gemini-perf-test
python3 gemini_perf_test.py --request-file benchmark/request_1k.json [options...]
```

---

## Quick Reference Commands

```bash
# Activate environment
source ~/gemini-perf-test/venv/bin/activate

# Single test
python3 gemini_perf_test.py --model MODEL --request-file FILE --iterations N

# Batch test
python3 gemini_perf_controller.py --models MODEL1 MODEL2 --request-files FILE1 FILE2 --iterations N

# View results
cat perf_results_*.csv

# Monitor logs in real-time
tail -f logs/perf_test_*.log
```

---

## Environment Variables Reference

```bash
# Required for authentication
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Optional: Set default project
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Add to .bashrc for persistence
echo 'export GOOGLE_APPLICATION_CREDENTIALS="$HOME/sa-key.json"' >> ~/.bashrc
echo 'export GOOGLE_CLOUD_PROJECT="your-project-id"' >> ~/.bashrc
```

---

## Next Steps

1. **Analyze Results**: Import the CSV file into your preferred analysis tool (Excel, Google Sheets, Python pandas)
2. **Compare Models**: Use the consolidated CSV to compare performance across different models and configurations
3. **Automate Testing**: Set up cron jobs for regular performance monitoring
4. **Scale Up**: Run tests with more iterations and request sizes for production-level insights

---

## Support

For issues or questions:
- Check the log files in `logs/` directory
- Review the error messages in console output
- Verify authentication and API access
- Ensure all dependencies are installed correctly
