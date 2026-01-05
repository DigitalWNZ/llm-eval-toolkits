from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Online Evaluation Models
class OnlineEvaluationRequest(BaseModel):
    gemini_request: Dict[str, Any] | str = Field(..., description="Gemini API request JSON or plain text string")
    system_instruction: Optional[str] = Field(None, description="System instruction override")
    gemini_config: Optional[Dict[str, Any]] = Field(None, description="Configuration overrides")
    model: str = Field(..., description="Gemini model name")
    project: str = Field(..., description="GCP project ID")
    iterations: int = Field(1, ge=1, description="Number of iterations")
    multimodal_files: Optional[List[Dict[str, Any]]] = Field(None, description="Multimodal file data")


class OnlineEvaluationResponse(BaseModel):
    responses: List[Dict[str, Any]]
    success: bool
    message: Optional[str] = None


# Batch Evaluation Models
class BatchEvaluationRequest(BaseModel):
    input_folder: str = Field(..., description="Input request folder path")
    expected_folder: str = Field(..., description="Expected output folder path")
    output_folder: Optional[str] = Field(None, description="Output folder path")
    gemini_config: Optional[Dict[str, Any]] = Field(None, description="Configuration overrides")
    model: str = Field(..., description="Gemini model name")
    project: str = Field(..., description="GCP project ID")
    iterations: int = Field(1, ge=1, description="Number of iterations")


class FileMapping(BaseModel):
    input_request: str
    expected_output: Optional[str]
    output_files: List[str]
    has_expected: bool


class BatchMappingResponse(BaseModel):
    mappings: List[FileMapping]
    total_files: int
    success: bool
    message: Optional[str] = None


class BatchSubmitResponse(BaseModel):
    success: bool
    total_processed: int
    successful: int
    failed: int
    output_folder: str
    message: Optional[str] = None


class EvaluationDifference(BaseModel):
    category: str
    description: str
    severity: str
    location: Optional[str] = None


class EvaluationDimensionScores(BaseModel):
    semantic_similarity: float
    structural_consistency: float
    key_information_preservation: float
    response_quality: float


class EvaluationResult(BaseModel):
    input_request: str
    expected_output: Optional[str]
    output_file: str
    similarity_score: float
    dimension_scores: Optional[EvaluationDimensionScores] = None
    key_differences: Optional[List[EvaluationDifference]] = None
    strengths: Optional[List[str]] = None
    overall_assessment: Optional[str] = None


class EvaluateResultsRequest(BaseModel):
    input_folder: str
    expected_folder: str
    output_folder: str
    model: str = Field(default="gemini-2.5-flash", description="Model for evaluation")
    project: str
    pass_threshold: int = Field(default=75, ge=0, le=100, description="Pass/fail threshold")


class EvaluateResultsResponse(BaseModel):
    success: bool
    evaluation_results: List[EvaluationResult]
    message: Optional[str] = None


# Performance Evaluation Models
class PerformanceEvaluationRequest(BaseModel):
    models: List[str] = Field(..., description="List of Gemini models")
    request_sizes: List[int] = Field(..., description="Token count options")
    thinking_levels: Optional[List[str]] = Field(None, description="Thinking levels")
    thinking_budgets: Optional[List[int]] = Field(None, description="Thinking budgets")
    iterations: int = Field(1, ge=1, description="Number of iterations")
    cache_enabled: bool = Field(False, description="Enable caching")
    project: str = Field(..., description="GCP project ID")


class PerformanceMetric(BaseModel):
    timestamp: str
    model: str
    request_size: int
    thinking_level: Optional[str]
    thinking_budget: Optional[int]
    cache_enabled: bool
    ttft_ms: float
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    iteration: int


class PerformanceStatistics(BaseModel):
    model: str
    request_size: int
    thinking_level: Optional[str]
    thinking_budget: Optional[int]
    cache_enabled: bool
    median_ttft_ms: float
    p90_ttft_ms: float
    p99_ttft_ms: float
    avg_input_tokens: float
    avg_output_tokens: float
    avg_cached_tokens: float


class PerformanceEvaluationResponse(BaseModel):
    success: bool
    raw_csv_path: str
    analysis_csv_path: str
    statistics: List[PerformanceStatistics]
    message: Optional[str] = None
