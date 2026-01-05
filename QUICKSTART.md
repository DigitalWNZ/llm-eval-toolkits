# Quick Start Guide

## Current Status

✅ **Application code is complete** - Backend and frontend are fully implemented
⚠️ **Dependencies need to be installed** - Network issues during automated installation

## What You Need to Do

### Step 1: Install Backend Dependencies

Your system has a custom PyPI configuration that's blocking installation. Run this:

```bash
cd /Users/wangez/Downloads/llm_eval_toolkits/backend

# Activate virtual environment
source venv/bin/activate

# Install with PyPI override (may take a few minutes)
PIP_INDEX_URL=https://pypi.org/simple PIP_TIMEOUT=300 pip install \
  fastapi \
  uvicorn[standard] \
  python-dotenv \
  google-generativeai \
  google-auth \
  pydantic \
  python-multipart \
  aiofiles
```

**If this fails due to network timeout**, install packages one by one as shown in `INSTALL.md`.

### Step 2: Install Frontend Dependencies

The frontend already has `.npmrc` configured to use the public npm registry.

```bash
cd /Users/wangez/Downloads/llm_eval_toolkits/frontend
npm install
```

**Note:** If you encounter authentication errors, the `.npmrc` file will override your system's npm configuration.

### Step 3: Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### Step 4: Run the Application

**Terminal 1 - Backend:**
```bash
cd /Users/wangez/Downloads/llm_eval_toolkits/backend
source venv/bin/activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd /Users/wangez/Downloads/llm_eval_toolkits/frontend
npm run dev
```

### Step 5: Access the Application

Open your browser to: **http://localhost:3000**

## Application Features

### Online Evaluation Tab
- Upload Gemini API request JSON
- Upload multimodal files (images, videos, audio, PDFs)
- Edit system instructions
- Configure model parameters
- Run multiple iterations
- View and save responses

### Batch Evaluation Tab
- Process up to 10 request files
- Map requests to expected outputs
- Review file mappings
- Execute batch processing
- View success/failure summary

### Performance Evaluation Tab
- Benchmark multiple models
- Test different request sizes
- Configure thinking parameters
- Run performance tests with statistics
- Export results to CSV

## Network Issue Notes

The automated installation encountered network timeouts connecting to PyPI. This is due to your system's custom pip configuration:

```
global.index-url='https://us-python.pkg.dev/artifact-foundry-prod/ah-3p-staging-python/simple/'
```

The workaround is to override this with `PIP_INDEX_URL=https://pypi.org/simple` when installing packages.

## Need Help?

See `INSTALL.md` for detailed installation troubleshooting and `README.md` for complete usage documentation.
