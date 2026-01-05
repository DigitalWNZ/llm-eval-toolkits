# Product Requirements Document: LLM Evaluation Toolkit

## 1. Product Overview

### 1.1 Purpose
The LLM Evaluation Toolkit is a web-based application designed to facilitate comprehensive testing and evaluation of Google Gemini models. It provides three core evaluation modes: online single-request evaluation, batch evaluation with expected output comparison, and performance benchmarking.

### 1.2 Target Users
- ML Engineers testing and validating Gemini model responses
- QA teams performing regression testing on model outputs
- Performance engineers benchmarking model configurations
- Product teams evaluating model behavior across different scenarios

### 1.3 Key Objectives
- Enable rapid iteration and testing of Gemini model requests
- Support batch processing for comprehensive evaluation workflows
- Provide performance metrics for informed model selection
- Simplify comparison between expected and actual outputs

---

## 2. Feature Requirements

### 2.1 Online Evaluation

#### 2.1.1 Purpose
Provide an interactive interface for single-request evaluation with real-time model responses.

#### 2.1.2 Input Parameters

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| **Gemini Request** | File upload or Text input | JSON file containing Gemini API request or direct text input | Valid JSON format |
| **Multimodal Files** | File upload (multiple) | Upload images, audio, video, PDFs, or other media files to include in the request | Supported formats: JPG, PNG, GIF, WEBP, MP4, MOV, MP3, WAV, PDF; Max 20MB per file; Max 10 files per request |
| **System Instruction** | Text area (auto-populated) | Extracted from request if present; `\n` characters replaced with actual newlines for editing | Optional |
| **Gemini Configuration** | JSON input | Configuration overrides (e.g., temperature, top_k, top_p) | Valid JSON; overwrites request config on submit |
| **Model** | Dropdown + Text input | Pre-defined options: Gemini 2.5 Pro/Flash/Flash Lite, Gemini 3.0 Pro/Flash/Flash Lite, or custom input | Required |
| **Project** | Text input | Google Cloud project ID for API calls | Required |
| **Number of Iterations** | Number input | Number of times to submit the request | Integer ≥ 1 |

#### 2.1.3 Processing Flow

1. **Request Upload/Input**
   - User uploads a Gemini request file or enters request directly
   - System parses the request and extracts system instruction if present
   - Replace `\n` escape sequences with actual newline characters for display

2. **Multimodal File Upload**
   - User uploads one or more multimodal files (images, audio, video, PDFs)
   - System validates file formats and sizes
   - Display uploaded file thumbnails/names with remove option
   - On submit, convert files to base64 or upload to Cloud Storage
   - Inject file references into request's `contents` array with appropriate MIME types

3. **System Instruction Editing**
   - Display extracted system instruction in editable text area
   - Allow user to modify the instruction
   - On submit, replace newline characters with `\n` escape sequences
   - Merge modified instruction back into the original request

4. **Configuration Override**
   - Accept Gemini configuration JSON
   - On submit, merge configuration into request, overwriting existing values

5. **Submit**
   - Validate all required fields
   - Construct final request with text, multimodal files, and configuration
   - Submit request to Gemini API specified number of times
   - Display progress indicator during processing

#### 2.1.4 Output Display

| Feature | Description |
|---------|-------------|
| **Response List** | Display all JSON responses from iterations in a list format |
| **JSON Formatting** | Syntax-highlighted, formatted JSON display |
| **Expand/Collapse** | Collapsible JSON tree view for nested objects |
| **Save Functionality** | "Save" button to export responses to a JSON file |

#### 2.1.5 User Stories

- **US-OE-01**: As a user, I want to upload a Gemini request file so that I can quickly test pre-configured requests
- **US-OE-02**: As a user, I want to upload images, videos, audio files, or PDFs so that I can test multimodal capabilities of Gemini models
- **US-OE-03**: As a user, I want to see previews of uploaded multimodal files so that I can verify I've uploaded the correct content
- **US-OE-04**: As a user, I want to edit the system instruction in a readable format so that I can iterate on prompts without manual escape sequence handling
- **US-OE-05**: As a user, I want to override model configurations so that I can test different parameter settings without modifying the original request
- **US-OE-06**: As a user, I want to run multiple iterations so that I can observe response variability
- **US-OE-07**: As a user, I want to save responses to a file so that I can analyze them later

---

### 2.2 Batch Evaluation

#### 2.2.1 Purpose
Process multiple request files in batch, compare outputs with expected results, and generate evaluation reports.

#### 2.2.2 Input Parameters

| Parameter | Type | Description | Default Value |
|-----------|------|-------------|---------------|
| **Input Request Folder (folder_A)** | Directory path | Folder containing request files; supports nested folders; max 10 files per batch | Required |
| **Expected Output Folder (folder_B)** | Directory path | Folder containing expected output files with matching structure | Required |
| **Gemini Configuration** | JSON input | Configuration overrides for all requests | Optional |
| **Model** | Dropdown + Text input | Same as Online Evaluation | Required |
| **Project** | Text input | Google Cloud project ID | Required |
| **Iterations** | Number input | Number of iterations per request | Integer ≥ 1 |
| **Output Folder (folder_C)** | Directory path | Folder for saving output responses (or error details for failed requests) | `{folder_A}_output_{timestamp}` |

#### 2.2.3 File Mapping Rules

- **Request to Expected Output**:
  - `folder_B/subfolder_1/file_X` maps to `folder_A/subfolder_1/file_X`
  - `folder_B/file_X` maps to `folder_A/file_X`
  - Preserve folder structure; match by relative path

- **Request to Output**:
  - `folder_C/{relative_path}/{filename}_{iteration}.json`
  - Example: `folder_A/sub/request.json` (3 iterations) → `folder_C/sub/request_1.json`, `folder_C/sub/request_2.json`, `folder_C/sub/request_3.json`

#### 2.2.4 Processing Workflow

**Step 0: Configuration Page Options**

Users can choose one of two paths:

**Path A: New Batch Evaluation**
1. Enter folder paths, configuration, and parameters
2. Click "Process Request" to proceed to Step 1

**Path B: Import Previous Results**
1. Click "Import Previous Evaluation Results" button
2. Select a previously saved evaluation JSON file
3. System automatically:
   - Restores all configuration parameters (folders, model, project)
   - Loads evaluation results and processing summary
   - Navigates directly to Results page (Step 3)
4. User can view, re-evaluate, or export results

**Step 1: Process Files and Display Mapping**

1. User clicks "Process Request" button
2. Application scans all three folders
3. Generate file mappings based on rules above
4. System automatically checks if output files already exist in folder_C
5. Navigate to mapping review page with four columns:

| Column | Description | Visual Treatment |
|--------|-------------|------------------|
| **Input Request** | File path of input request (relative to folder_A) | Plain text |
| **Expected Output** | File path of expected output (relative to folder_B) | Display "no mapping" in **red bold** if not found |
| **Output Files** | List of output file paths (all iterations) | Multiple files if iterations > 1 |
| **Preview** | Link to preview files | Clickable "Preview" link in dialog |

6. Display status based on output file check:
   - If all output files exist: Show success alert "All output files exist! You can evaluate results directly..."
   - If output files missing: Show info alert "Output files not found. You need to submit the batch first..."
   - "Evaluate Results" button enabled only when all output files exist

**Step 2A: Submit Requests (Generate New Outputs)**

1. User reviews mapping table
2. Clicks "Submit Batch" button
3. For each input request file:
   - Read request from file
   - Apply configuration overrides
   - Submit to Gemini API {iterations} times
   - On success: Save each response to corresponding output file in folder_C
   - On failure: Save error details (error message, stack trace, timestamp) as JSON to the respective output file in folder_C
   - Continue processing remaining files regardless of individual failures
4. Display progress (e.g., "Processing 15/50 requests...")
5. After completion, navigate to Results page showing processing summary

**Step 2B: Direct Evaluation (Existing Outputs)**

1. If output files already exist, user can click "Evaluate Results" button from mapping review page
2. Skips batch submission and proceeds directly to Step 3
3. Loads existing output files for evaluation

**Step 3: Evaluate Results and Generate Report**

1. User clicks "Evaluate Results" button (from either mapping review page or results page)
2. System loads evaluation configuration:
   - Reads system instruction from `backend/evaluation_system_instruction.md`
   - Sets evaluation model (default: gemini-2.5-flash)
   - Applies pass/fail threshold (default: 75%)

3. For each input request that has an expected output:
   - Load the expected output file from folder_B
   - Load all generated output files from folder_C (all iterations: `filename_1.json`, `filename_2.json`, etc.)
   - Group outputs by base filename
   - Submit to Gemini with evaluation prompt containing:
     - Expected output JSON
     - All iteration output JSONs
     - Pass threshold
   - Gemini performs evaluation using specialized system instruction

4. Gemini Evaluation Process:
   - **System Instruction**: Located in `backend/evaluation_system_instruction.md`
   - **Input**: Expected output JSON + all iteration output JSONs
   - **Evaluation Dimensions** (100 points total):
     - Semantic Similarity (40 points): Meaning preservation, key facts/concepts
     - Structural Consistency (25 points): Format, JSON schema, data types
     - Key Information Preservation (25 points): Critical data accuracy, completeness
     - Response Quality (10 points): Completeness, no errors/hallucinations
   - **Special Focus Areas**:
     - Function call comparison: Exact name match, all parameters (name, value, type), parameter ordering
     - Individual iteration scoring: Each output evaluated separately, not averaged
   - **Output**: Structured JSON with:
     - Overall similarity score (0-100%) per iteration
     - Dimension scores breakdown
     - Key differences with severity (critical/major/minor)
     - Strengths identified
     - Overall assessment
     - Pass/fail status

5. Results Page Display:
   - **Processing Summary** (displayed first):
     - Total Processed: Count of all requests × iterations
     - Successful: Number of successful API calls
     - Failed: Number of failed API calls

   - **Score Distribution** (displayed after evaluation, only when results exist):
     - Six color-coded score ranges:
       - 90-100 (Excellent) - Green
       - 75-89 (Good) - Light Green
       - 60-74 (Moderate) - Yellow
       - 40-59 (Fair) - Orange
       - 20-39 (Poor) - Deep Orange
       - 0-19 (Failing) - Red
     - Count displayed for each range

   - **Detailed Evaluation Table**:
     - Columns: Input Request, Expected Output, Output File, Similarity Score
     - Similarity Score displayed as clickable color-coded link
     - Link color matches score range (green for success, blue for info, yellow for warning, red for error)
     - Bold text and underline on hover for better visibility
     - One row per output file (multiple rows per input if iterations > 1)
     - Clicking the score link opens the Evaluation Detail Dialog

6. Evaluation Detail Dialog (opened when clicking score button):
   - **File Contents Section**:
     - Input Request: JSON content of input file
     - Expected Output: JSON content of expected file
     - Actual Output: JSON content of generated file
     - All displayed in scrollable pre-formatted blocks

   - **Overall Similarity Score**: Large display with color coding

   - **Dimension Scores**: Four cards showing breakdown
     - Semantic: X/40
     - Structural: X/25
     - Information: X/25
     - Quality: X/10

   - **Key Differences**: List of identified issues
     - Category (semantic/structural/information/quality)
     - Description
     - Severity (critical/major/minor) with color-coded border
     - Location in output

   - **Strengths**: Bullet list of positive aspects

   - **Overall Assessment**: Text summary of evaluation

7. System Instruction Requirements:
   - **Multi-Output Evaluation**: Each iteration compared individually against expected output
   - **Function Call Precision**: Exact function name + all parameters must match
   - **Type Sensitivity**: Distinguish "123" (string) vs 123 (integer)
   - **Consistent Scoring**: Same standards applied to all iterations
   - **Structured Output**: Returns parseable JSON for UI rendering

**Step 4: Save and Export Results**

1. **Save Results Button**: Located on the Results page (after evaluation)
   - Green button labeled "Save Results"
   - Enabled only when evaluation results exist
   - Positioned alongside "Evaluate Results" and "Start New Batch" buttons

2. **Export Format**: Comprehensive JSON file containing:
   - **Metadata**:
     - Timestamp (ISO 8601 format)
     - Input folder path
     - Expected folder path
     - Output folder path
     - Model name
     - Project ID

   - **Processing Summary**:
     - Total processed count
     - Successful count
     - Failed count

   - **Score Distribution**:
     - Count in each score range (90-100, 75-89, 60-74, 40-59, 20-39, 0-19)

   - **Evaluation Results**: Complete array of all evaluation results
     - All dimension scores
     - Key differences
     - Strengths
     - Overall assessments

3. **File Naming**: `batch_evaluation_results_YYYY-MM-DDTHH-MM-SS.json`

4. **Re-import Capability**:
   - Saved files can be imported via "Import Previous Evaluation Results" button
   - Enables results sharing, archiving, and historical comparison

#### 2.2.5 Preview Functionality

**Preview Dialog**: Accessible from mapping review page

| Element | Content | Features |
|---------|---------|----------|
| **Input Request** | Content of input request file | Syntax-highlighted JSON in scrollable pre block |
| **Expected Output** | Content of expected output file (if exists) | Syntax-highlighted JSON or "No expected output" message |
| **Generated Outputs** | Content of all generated output files (iterations) | Multiple files displayed if iterations > 1; shows "Output files do not exist yet" if not generated |

**Evaluation Detail Dialog**: Accessible from results page by clicking score button

- Displays file contents (input, expected, actual output) at top
- Followed by evaluation details (score, dimensions, differences, etc.)
- All in single scrollable dialog

#### 2.2.6 User Stories

- **US-BE-01**: As a user, I want to process entire folders of requests so that I can run comprehensive test suites
- **US-BE-02**: As a user, I want to see file mappings before submission so that I can verify the test configuration
- **US-BE-03**: As a user, I want to preview files so that I can quickly inspect request/response content
- **US-BE-04**: As a user, I want missing expected outputs to be clearly marked so that I can identify incomplete test cases
- **US-BE-05**: As a user, I want outputs organized by iteration so that I can analyze response variability
- **US-BE-06**: As a user, I want to evaluate existing outputs without re-running batch submission so that I can save time and API costs
- **US-BE-07**: As a user, I want to see similarity scores in different ranges so that I can quickly identify which outputs need attention
- **US-BE-08**: As a user, I want detailed evaluation breakdowns so that I can understand why a score was given
- **US-BE-09**: As a user, I want to compare function calls precisely so that I can ensure API calls are correct
- **US-BE-10**: As a user, I want to see file contents alongside evaluation results so that I can verify the assessment
- **US-BE-11**: As a user, I want to save complete evaluation results to a file so that I can archive results for future reference
- **US-BE-12**: As a user, I want to import previously saved evaluation results so that I can review historical evaluations without re-running
- **US-BE-13**: As a user, I want evaluation results to include all metadata so that I can understand the context when reviewing saved files
- **US-BE-14**: As a user, I want clickable similarity score links instead of buttons so that the interface feels more lightweight and accessible

---

### 2.3 Performance Evaluation

#### 2.3.1 Purpose
Benchmark Gemini model performance across different configurations and collect latency metrics.

#### 2.3.2 Input Parameters

| Parameter | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| **Model** | Multi-select dropdown | Gemini 2.5 Pro/Flash/Flash Lite, Gemini 3.0 Pro/Flash/Flash Lite, or custom input | Multiple selection allowed |
| **Request Size** | Multi-select checkbox | Token count options: 1K, 2K, 5K, 10K, 50K, 100K | Multiple selection allowed |
| **Thinking Level** | Multi-select dropdown | Options: minimum, low, medium, high | Multiple selection; **not compatible with thinking budget for Gemini 3.0** |
| **Thinking Budget** | Text input | Comma-separated numeric values (e.g., "1000, 5000, 10000") | **Not compatible with thinking level for Gemini 3.0** |
| **Iterations** | Number input | Number of iterations per configuration | Integer ≥ 1 |
| **Cache** | Checkbox or toggle | Enable/disable caching | Boolean |

#### 2.3.3 Gemini 3.0 Constraint
**Critical Rule**: For Gemini 3.0 models, thinking level and thinking budget are **mutually exclusive**.
- UI should validate and prevent selection of both
- Display warning message if user attempts to select both

#### 2.3.4 Processing Workflow

**Step 1: Generate Configuration Matrix**

1. User selects parameters and clicks "Submit"
2. System validates Gemini 3.0 constraint
3. Generate all combinations:
   - **For Gemini 2.5**: `model × request_size × thinking_level × thinking_budget × cache`
   - **For Gemini 3.0**: `model × request_size × (thinking_level OR thinking_budget) × cache`

**Example**:
- Models: Gemini 2.5 Flash, Gemini 3.0 Pro
- Request Sizes: 1K, 5K
- Thinking Levels: low, medium
- Thinking Budgets: 1000, 5000
- Cache: enabled
- **Result**:
  - Gemini 2.5: 2 request sizes × 2 thinking levels × 2 thinking budgets × 1 cache = 8 configs
  - Gemini 3.0: 2 request sizes × (2 thinking levels + 2 thinking budgets) × 1 cache = 8 configs
  - **Total**: 16 configurations

**Step 2: Execute Benchmark**

For each configuration:
1. Generate request with specified size
2. Submit to Gemini API with configuration parameters
3. Record metrics:
   - **TTFT** (Time to First Token) in milliseconds
   - **Input Token Count**
   - **Output Token Count**
   - **Cached Token Count** (if cache enabled)
4. Append metrics to CSV file
5. Repeat for specified iterations
6. Display progress indicator

**Step 3: Statistical Analysis**

After all requests complete:
1. Parse CSV file
2. For each unique configuration, calculate:
   - **Median TTFT**
   - **P90 TTFT** (90th percentile)
   - **P99 TTFT** (99th percentile)
3. Display results in table format
4. Export final analysis to CSV

#### 2.3.5 Output Format

**Raw CSV Columns**:
```
timestamp, model, request_size, thinking_level, thinking_budget, cache_enabled, ttft_ms, input_tokens, output_tokens, cached_tokens, iteration
```

**Analysis CSV Columns**:
```
model, request_size, thinking_level, thinking_budget, cache_enabled, median_ttft_ms, p90_ttft_ms, p99_ttft_ms, avg_input_tokens, avg_output_tokens, avg_cached_tokens
```

#### 2.3.6 User Stories

- **US-PE-01**: As a user, I want to benchmark multiple models simultaneously so that I can compare performance
- **US-PE-02**: As a user, I want to test different request sizes so that I can understand latency scaling
- **US-PE-03**: As a user, I want to evaluate thinking configurations so that I can optimize for my use case
- **US-PE-04**: As a user, I want statistical summaries so that I can make data-driven decisions
- **US-PE-05**: As a user, I want to export results to CSV so that I can perform custom analysis

---

## 3. Technical Requirements

### 3.1 Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Frontend** | React | Modern SPA framework with component-based architecture |
| **Backend** | Python | Python with Flask/FastAPI for API endpoints |
| **API Client** | Google AI Python SDK | Official Gemini API client library |
| **File Handling** | Python os/pathlib | For folder scanning and file I/O |
| **UI Components** | Material-UI/Ant Design | Pre-built components for forms, tables, JSON viewers |
| **JSON Display** | react-json-view or similar | Collapsible, syntax-highlighted JSON rendering |

### 3.2 API Integration

- **Authentication**: Use Application Default Credentials (ADC) from `gcloud auth application-default login`. Users must run this command before starting the backend server.
- **Error Handling**: Display API errors (quota exceeded, authentication failures, etc.) with user-friendly messages
- **Rate Limiting**: Implement configurable delays between batch requests to respect API quotas
- **Retry Logic**: Automatic retry with exponential backoff for transient failures

### 3.3 Data Storage

- **Configuration Storage**: Store user preferences (default project, last used model, etc.) in browser localStorage
- **Result Caching**: Optional caching of responses for repeat requests (configurable)
- **File Management**: Support for large files (streaming for files > 10MB)

### 3.4 Performance Requirements

- **Batch Processing**: Support processing 100+ requests without UI freezing (use background workers or async processing)
- **CSV Export**: Handle 10,000+ rows efficiently
- **File Preview**: Load and render files up to 5MB without performance degradation

### 3.5 Security Requirements

- **API Credentials**: Never log or expose API keys/credentials in UI or console
- **Input Validation**: Sanitize all user inputs to prevent injection attacks
- **File Upload**: Validate file types and sizes; scan for malicious content
- **CORS**: Configure appropriate CORS policies if backend is separate

---

## 4. UI/UX Specifications

### 4.1 Navigation Structure

```
Home Page
├── Online Evaluation
├── Batch Evaluation
│   ├── Configuration Page
│   ├── Mapping Review Page
│   └── Preview Page (new tab)
└── Performance Evaluation
    ├── Configuration Page
    └── Results Dashboard
```

### 4.2 Common UI Elements

- **Header**: Application title, navigation menu, settings icon
- **Form Validation**: Real-time validation with error messages below fields
- **Progress Indicators**: Loading spinners and progress bars for long operations
- **Notifications**: Toast messages for success/error states
- **Responsive Design**: Mobile-friendly layouts (though primary use case is desktop)

### 4.3 Accessibility

- **Keyboard Navigation**: All interactive elements accessible via keyboard
- **Screen Readers**: Proper ARIA labels and semantic HTML
- **Color Contrast**: WCAG 2.1 AA compliance for text and UI elements
- **Error Messages**: Clear, actionable error descriptions

---

## 5. Success Metrics

### 5.1 Functional Metrics
- **Request Success Rate**: > 99% of valid requests successfully processed
- **Mapping Accuracy**: 100% correct file mapping in batch evaluation
- **Data Accuracy**: 100% accurate metric collection in performance evaluation

### 5.2 Performance Metrics
- **Online Evaluation Response Time**: < 2 seconds UI update after API response
- **Batch Processing Throughput**: Support 10+ concurrent requests
- **CSV Generation Time**: < 5 seconds for 1,000 rows

### 5.3 Usability Metrics
- **Time to First Evaluation**: < 2 minutes from app launch to first result (for experienced users)
- **Error Recovery Time**: < 1 minute to identify and fix configuration errors

---

## 6. Future Enhancements

### 6.1 Batch Evaluation Enhancements
- **Visual Diff Viewer**: Side-by-side comparison with highlighted differences
- **Custom Similarity Metrics**: Support for BLEU, ROUGE, and other traditional NLP metrics in addition to Gemini evaluation
- **Configurable Pass/Fail Thresholds**: UI controls for setting custom thresholds per dimension
- **Evaluation Report Export**: PDF and HTML report generation with charts and visualizations
- **Batch Evaluation History**: Track evaluation results over time to identify regression patterns

### 6.2 Advanced Features
- **Historical Tracking**: Database storage of all evaluations for trend analysis
- **A/B Testing**: Side-by-side comparison of two model configurations
- **Cost Estimation**: Calculate estimated API costs based on token usage
- **Scheduled Runs**: Cron-like scheduling for automated regression testing
- **Collaboration**: Share evaluation configurations and results with team members
- **Export Formats**: Support PDF, HTML reports in addition to CSV
- **Custom Metrics**: Plugin system for user-defined evaluation metrics

### 6.3 Performance Evaluation Extensions
- **Real-time Visualization**: Live charts during benchmark execution
- **Multi-provider Support**: Extend to other LLM providers (OpenAI, Anthropic, etc.)
- **Cost-Performance Analysis**: Compare cost per token vs. latency
- **Automated Recommendations**: Suggest optimal configurations based on requirements

---

## 7. Design Decisions

1. **Authentication Method**: Application Default Credentials (ADC) via `gcloud auth application-default login`. Users must authenticate before starting the backend.
2. **Batch Size Limits**: Maximum 10 files per batch processing run.
3. **Response Storage**: All responses stored as JSON files; no database required.
4. **Evaluation Method**: Gemini-powered similarity evaluation with 4-dimension scoring system (semantic, structural, information, quality). System instruction stored in `backend/evaluation_system_instruction.md`.
5. **Evaluation Model**: Default gemini-2.5-flash for evaluation tasks (configurable). Low temperature (0.1) for consistent scoring.
6. **Score Ranges**: Six predefined ranges (90-100, 75-89, 60-74, 40-59, 20-39, 0-19) with color coding for quick visual assessment.
7. **Pass/Fail Threshold**: Default 75% similarity score; configurable per evaluation request.
8. **File Existence Check**: Automatic detection of existing output files to enable direct evaluation without re-running batch submission.
9. **Evaluation Results Export**: JSON file format with comprehensive metadata, processing summary, score distribution, and complete evaluation results. Enables archiving, sharing, and historical comparison.
10. **Import Previous Results**: Allows users to import previously saved evaluation files to review results without re-running evaluations. Restores all configuration and navigates directly to results page.
11. **Similarity Score Display**: Clickable color-coded links instead of buttons for lightweight, accessible interface. Links maintain visual hierarchy while reducing UI complexity.
12. **Request Templates**: Not provided; users must supply their own request configurations.
13. **Error Handling in Batch**: Save error details to respective output files in folder_C and continue processing remaining requests.
14. **Performance Baseline**: No predefined TTFT thresholds; users interpret metrics based on their requirements.

---

## 8. Glossary

| Term | Definition |
|------|------------|
| **TTFT** | Time to First Token - latency from request submission to first token in response |
| **P90/P99** | 90th/99th percentile - metric value below which 90%/99% of observations fall |
| **System Instruction** | Special instruction field in Gemini API requests that guides model behavior |
| **Thinking Level** | Gemini parameter controlling depth of reasoning (minimum, low, medium, high) |
| **Thinking Budget** | Numeric parameter limiting computational resources for thinking (Gemini specific) |
| **Cached Tokens** | Number of tokens retrieved from cache (reduces latency and cost) |
| **Similarity Score** | 0-100% score indicating how closely an actual output matches the expected output |
| **Semantic Similarity** | Evaluation dimension measuring meaning preservation (40 points max) |
| **Structural Consistency** | Evaluation dimension measuring format and schema matching (25 points max) |
| **Key Information Preservation** | Evaluation dimension measuring critical data accuracy (25 points max) |
| **Response Quality** | Evaluation dimension measuring completeness and correctness (10 points max) |
| **Evaluation Dimensions** | Four scoring criteria used by Gemini to assess output similarity |
| **Pass/Fail Threshold** | Minimum similarity score required for an output to be considered passing (default 75%) |
| **Score Distribution** | Breakdown of evaluation results across six score ranges |
| **Iteration** | Single execution of a request; multiple iterations test response variability |
| **Evaluation Export** | JSON file containing complete evaluation results with metadata, processing summary, and score distribution |
| **Import Previous Results** | Feature allowing users to load previously saved evaluation files to review historical results |
| **Score Link** | Clickable link displaying similarity score percentage; opens detailed evaluation dialog when clicked |

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-04 | Initial | First draft based on requirements |
| 1.1 | 2026-01-05 | Update | Added Save/Import evaluation results functionality; Changed similarity score display from buttons to links; Added Step 0 for import workflow; Added 4 new user stories (US-BE-11 to US-BE-14); Added 4 new design decisions; Added 3 new glossary terms |
