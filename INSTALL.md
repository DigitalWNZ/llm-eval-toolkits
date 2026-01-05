# Installation Guide

## Issue with Internal PyPI Mirror

Your system is configured to use an internal PyPI mirror which may not have all required packages. Follow these steps to install dependencies:

## Backend Setup

### Option 1: Using PyPI Directly (Recommended)

```bash
cd backend
source venv/bin/activate

# Install with PyPI override
PIP_INDEX_URL=https://pypi.org/simple pip install --timeout 300 \
  fastapi uvicorn python-dotenv google-generativeai \
  google-auth pydantic python-multipart aiofiles
```

### Option 2: Install Packages One by One

If network issues persist, install one at a time:

```bash
cd backend
source venv/bin/activate

# Core packages
PIP_INDEX_URL=https://pypi.org/simple pip install fastapi
PIP_INDEX_URL=https://pypi.org/simple pip install uvicorn[standard]
PIP_INDEX_URL=https://pypi.org/simple pip install python-dotenv

# Google packages
PIP_INDEX_URL=https://pypi.org/simple pip install google-generativeai
PIP_INDEX_URL=https://pypi.org/simple pip install google-auth

# Other dependencies
PIP_INDEX_URL=https://pypi.org/simple pip install pydantic
PIP_INDEX_URL=https://pypi.org/simple pip install python-multipart
PIP_INDEX_URL=https://pypi.org/simple pip install aiofiles
```

### Option 3: Create pip.conf Override

Create a temporary pip config:

```bash
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.org/simple
timeout = 300
EOF
```

Then install normally:

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

## Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### 1. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 2. Start Backend

```bash
cd backend
source venv/bin/activate
python main.py
```

Backend will run on http://localhost:8000

### 3. Start Frontend (in new terminal)

```bash
cd frontend
npm run dev
```

Frontend will run on http://localhost:3000

## Troubleshooting

### Cannot Connect to PyPI

If you continue to have network issues:
1. Check your internet connection
2. Try using a VPN if corporate firewall is blocking
3. Ask your IT team to whitelist pypi.org and files.pythonhosted.org
4. Use a different network

### Import Errors When Running

If you get import errors, the package may not have installed. Install it individually:

```bash
PIP_INDEX_URL=https://pypi.org/simple pip install <package-name>
```
