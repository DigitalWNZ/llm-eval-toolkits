#!/bin/bash
#
# Automated setup script for Gemini Performance Testing on Debian 12
# Usage: bash setup.sh
#

set -e  # Exit on error

echo "========================================"
echo "Gemini Performance Testing - Setup"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Debian/Ubuntu
if ! command -v apt &> /dev/null; then
    echo -e "${RED}Error: This script is designed for Debian/Ubuntu systems${NC}"
    exit 1
fi

# Step 1: Update system and install dependencies
echo -e "${GREEN}[1/6] Installing system dependencies...${NC}"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl

# Verify Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Step 2: Set up project directory
echo -e "${GREEN}[2/6] Setting up project directory...${NC}"
PROJECT_DIR="$HOME/gemini-perf-test"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create directory structure
mkdir -p benchmark logs json_results

echo "Project directory: $PROJECT_DIR"

# Step 3: Set up Python virtual environment
echo -e "${GREEN}[3/6] Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Step 4: Install Python dependencies
echo -e "${GREEN}[4/6] Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install google-genai

# Verify installation
if python3 -c "import google.genai" 2>/dev/null; then
    echo -e "${GREEN}✓ google-genai installed successfully${NC}"
else
    echo -e "${RED}✗ Failed to install google-genai${NC}"
    exit 1
fi

# Step 5: Check for authentication
echo -e "${GREEN}[5/6] Checking Google Cloud authentication...${NC}"

if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${GREEN}✓ Service account credentials found: $GOOGLE_APPLICATION_CREDENTIALS${NC}"
elif command -v gcloud &> /dev/null; then
    echo -e "${YELLOW}⚠ Using gcloud authentication${NC}"
    echo "Run 'gcloud auth application-default login' if not authenticated"
else
    echo -e "${YELLOW}⚠ No authentication found${NC}"
    echo ""
    echo "Please set up authentication using ONE of these methods:"
    echo ""
    echo "Option 1 - Service Account (Recommended):"
    echo "  1. Copy your service account key to this VM"
    echo "  2. Run: export GOOGLE_APPLICATION_CREDENTIALS=\"/path/to/key.json\""
    echo "  3. Add to ~/.bashrc: echo 'export GOOGLE_APPLICATION_CREDENTIALS=\"/path/to/key.json\"' >> ~/.bashrc"
    echo ""
    echo "Option 2 - gcloud CLI:"
    echo "  1. Install: curl https://sdk.cloud.google.com | bash"
    echo "  2. Run: gcloud auth application-default login"
    echo ""
fi

# Step 6: Final checks
echo -e "${GREEN}[6/6] Verifying setup...${NC}"

# Create activation helper script
cat > activate.sh <<'EOF'
#!/bin/bash
source ~/gemini-perf-test/venv/bin/activate
echo "Virtual environment activated"
echo "Project directory: ~/gemini-perf-test"
EOF
chmod +x activate.sh

# Create sample request file if none exist
if [ ! -f "benchmark/request_1k.json" ]; then
    echo "Creating sample request file..."
    cat > benchmark/request_1k.json <<'EOFJ'
{
  "contents": [
    {
      "role": "user",
      "parts": [
        {
          "text": "Please write a short summary about artificial intelligence and its applications in modern technology. Include at least 3 key areas where AI is making an impact."
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
EOFJ
    echo -e "${GREEN}✓ Sample request file created: benchmark/request_1k.json${NC}"
fi

# Print summary
echo ""
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Copy your Python scripts to: $PROJECT_DIR"
echo "   - gemini_perf_test.py"
echo "   - gemini_perf_controller.py"
echo ""
echo "2. Copy your request files to: $PROJECT_DIR/benchmark/"
echo ""
echo "3. Activate the environment:"
echo "   source ~/gemini-perf-test/venv/bin/activate"
echo "   (or run: ./activate.sh)"
echo ""
echo "4. Run a test:"
echo "   python3 gemini_perf_test.py --model gemini-3-flash-preview --project cloud-llm-preview1 --iterations 5 --request-file benchmark/request_1k.json"
echo ""
echo "Directory structure:"
echo "  $PROJECT_DIR/"
echo "  ├── gemini_perf_test.py         (copy here)"
echo "  ├── gemini_perf_controller.py   (copy here)"
echo "  ├── benchmark/                   (request JSON files)"
echo "  ├── logs/                        (test logs)"
echo "  ├── json_results/                (individual JSON results)"
echo "  └── venv/                        (Python virtual environment)"
echo ""

# Deactivate virtual environment for clean exit
deactivate 2>/dev/null || true

echo -e "${GREEN}Setup script completed successfully!${NC}"
