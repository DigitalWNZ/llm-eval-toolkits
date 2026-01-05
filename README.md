# LLM Evaluation Toolkit

A web-based application for comprehensive testing and evaluation of Google Gemini models, featuring online evaluation, batch processing, and performance benchmarking.

## Features

- **Online Evaluation**: Interactive single-request testing with multimodal support
- **Batch Evaluation**: Process multiple requests with expected output comparison
- **Performance Evaluation**: Benchmark model performance with detailed metrics

## Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- Google Cloud Project with Gemini API enabled
- Google Cloud CLI (`gcloud`) installed

## Project Structure

```
llm_eval_toolkits/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── routers/     # API route handlers
│   │   ├── services/    # Business logic and Gemini integration
│   │   └── models/      # Pydantic schemas
│   ├── main.py          # FastAPI application entry point
│   └── requirements.txt # Python dependencies
│
├── frontend/            # React frontend
│   ├── src/
│   │   ├── pages/      # Page components
│   │   ├── services/   # API client
│   │   └── App.jsx     # Main application
│   └── package.json    # Node dependencies
│
└── PRD.md              # Product requirements document
```

## Setup Instructions

### 1. Authentication Setup

Before running the backend, authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

This configures Application Default Credentials (ADC) that the backend will use to access Gemini API.

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (optional)
cp .env.example .env
# Edit .env with your settings if needed
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## Running the Application

### Start Backend Server

```bash
cd backend
source venv/bin/activate  # if not already activated
python main.py
```

The backend API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend application will be available at `http://localhost:3000`

## Usage

### Online Evaluation

1. Navigate to the "Online Evaluation" tab
2. Upload a Gemini request JSON file or paste JSON directly
3. (Optional) Upload multimodal files (images, audio, video, PDFs)
4. Edit system instruction if needed
5. Configure model, project ID, and iterations
6. Click "Submit" to generate responses
7. View results in JSON format
8. Click "Save" to export responses

**Supported Multimodal Formats**: JPG, PNG, GIF, WEBP, MP4, MOV, MP3, WAV, PDF (max 20MB per file, max 10 files)

### Batch Evaluation

1. Navigate to the "Batch Evaluation" tab
2. Enter paths for:
   - Input request folder (folder_A)
   - Expected output folder (folder_B)
   - Output folder (optional, defaults to `{folder_A}_output_{timestamp}`)
3. Configure model, project ID, and iterations
4. Click "Process Request" to see file mappings
5. Review the mapping table (red "no mapping" indicates missing expected outputs)
6. Click "Submit Batch" to process all files
7. View results summary with success/failure counts

**Note**: Maximum 10 files per batch. Errors are saved to respective output files.

### Performance Evaluation

1. Navigate to the "Performance Evaluation" tab
2. Select models to benchmark (multi-select)
3. Choose request sizes (1K, 2K, 5K, 10K, 50K, 100K tokens)
4. Configure thinking parameters:
   - **Gemini 2.5**: Can use both levels and budgets
   - **Gemini 3.0**: Use either levels OR budgets (mutually exclusive)
5. Set iterations and cache settings
6. Enter GCP project ID
7. Click "Run Benchmark"
8. View statistics table with median, P90, P99 TTFT metrics
9. Download raw CSV or analysis CSV

## API Endpoints

### Online Evaluation
- `POST /api/online/evaluate` - Execute online evaluation
- `POST /api/online/upload-multimodal` - Upload multimodal files

### Batch Evaluation
- `POST /api/batch/mapping` - Generate file mappings
- `POST /api/batch/submit` - Submit batch requests

### Performance Evaluation
- `POST /api/performance/benchmark` - Run performance benchmark

## Configuration

### Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```env
GCP_PROJECT_ID=your-project-id
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend Environment Variables

Create a `.env` file in the `frontend/` directory (optional):

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Development

### Backend Development

The backend uses FastAPI with hot reload enabled:

```bash
cd backend
python main.py
```

### Frontend Development

The frontend uses Vite with hot module replacement:

```bash
cd frontend
npm run dev
```

### Building for Production

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm run build
npm run preview
```

## Troubleshooting

### Authentication Errors

If you see authentication errors:
1. Ensure you've run `gcloud auth application-default login`
2. Verify your GCP project has Gemini API enabled
3. Check that you have necessary permissions

### CORS Errors

If you encounter CORS errors:
1. Check `CORS_ORIGINS` in backend `.env` file
2. Ensure frontend URL matches allowed origins
3. Restart backend server after changing configuration

### File Upload Errors

For multimodal file upload issues:
1. Verify file size is under 20MB
2. Check file format is supported
3. Ensure total files don't exceed 10

## Architecture

- **Backend**: Python FastAPI + Google AI SDK
- **Frontend**: React + Material-UI + Vite
- **Authentication**: Google Cloud Application Default Credentials
- **API Communication**: REST API with JSON
- **File Storage**: Local filesystem

## License

See PRD.md for detailed product requirements and specifications.

## Support

For issues and feature requests, refer to the PRD.md document or contact the development team.
