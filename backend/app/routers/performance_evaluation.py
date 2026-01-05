from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import csv
import os
from pathlib import Path
from datetime import datetime
import statistics
import logging
from ..models.schemas import (
    PerformanceEvaluationRequest,
    PerformanceEvaluationResponse,
    PerformanceMetric,
    PerformanceStatistics
)
from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/performance", tags=["performance-evaluation"])
gemini_service = GeminiService()


def validate_gemini_3_constraints(request: PerformanceEvaluationRequest):
    """Validate that Gemini 3.0 models don't use both thinking level and budget"""
    for model in request.models:
        if "3.0" in model or "3-0" in model:
            if request.thinking_levels and request.thinking_budgets:
                raise ValueError(
                    "Gemini 3.0 models cannot use both thinking_levels and thinking_budgets"
                )


def validate_thinking_budgets(request: PerformanceEvaluationRequest):
    """Validate thinking budgets are in valid range based on model"""
    if not request.thinking_budgets:
        return

    # Model-specific thinking budget ranges
    # Order matters: check more specific patterns first
    model_budget_ranges = [
        ("gemini-2.5-flash-lite", 512, 24576),
        ("gemini-2.5-flash", 1, 24576),
        ("gemini-2.5-pro", 128, 32768),
        ("gemini-3.0-flash-lite", 512, 24576),
        ("gemini-3.0-flash", 1, 24576),
        ("gemini-3.0-pro", 128, 32768),
    ]

    for model in request.models:
        # Find matching range for model
        min_budget = None
        max_budget = None

        for model_pattern, min_val, max_val in model_budget_ranges:
            if model_pattern in model:
                min_budget = min_val
                max_budget = max_val
                break

        # If no specific range found, use most restrictive (512-24576)
        if min_budget is None:
            min_budget = 512
            max_budget = 24576

        # Validate all budgets for this model
        for budget in request.thinking_budgets:
            if budget < min_budget or budget > max_budget:
                raise ValueError(
                    f"Thinking budget {budget} is out of range for model '{model}'. "
                    f"Supported values are integers from {min_budget} to {max_budget}."
                )


def generate_configurations(request: PerformanceEvaluationRequest) -> List[Dict[str, Any]]:
    """Generate all configuration combinations"""
    configs = []

    for model in request.models:
        is_gemini_3 = "3.0" in model or "3-0" in model

        for request_size in request.request_sizes:
            # Handle thinking parameters based on model version
            if is_gemini_3:
                # For Gemini 3.0: use either levels OR budgets, not both
                if request.thinking_levels:
                    for level in request.thinking_levels:
                        configs.append({
                            "model": model,
                            "request_size": request_size,
                            "thinking_level": level,
                            "thinking_budget": None,
                            "cache_enabled": request.cache_enabled
                        })
                elif request.thinking_budgets:
                    for budget in request.thinking_budgets:
                        configs.append({
                            "model": model,
                            "request_size": request_size,
                            "thinking_level": None,
                            "thinking_budget": budget,
                            "cache_enabled": request.cache_enabled
                        })
                else:
                    # No thinking parameters
                    configs.append({
                        "model": model,
                        "request_size": request_size,
                        "thinking_level": None,
                        "thinking_budget": None,
                        "cache_enabled": request.cache_enabled
                    })
            else:
                # For Gemini 2.5: can use both
                levels = request.thinking_levels or [None]
                budgets = request.thinking_budgets or [None]

                for level in levels:
                    for budget in budgets:
                        configs.append({
                            "model": model,
                            "request_size": request_size,
                            "thinking_level": level,
                            "thinking_budget": budget,
                            "cache_enabled": request.cache_enabled
                        })

    return configs


def calculate_statistics(metrics: List[PerformanceMetric]) -> List[PerformanceStatistics]:
    """Calculate statistical summaries from raw metrics"""
    # Group by configuration
    grouped = {}

    for metric in metrics:
        key = (
            metric.model,
            metric.request_size,
            metric.thinking_level,
            metric.thinking_budget,
            metric.cache_enabled
        )

        if key not in grouped:
            grouped[key] = []
        grouped[key].append(metric)

    # Calculate statistics for each group
    statistics_list = []

    for key, group_metrics in grouped.items():
        ttfts = [m.ttft_ms for m in group_metrics]
        input_tokens = [m.input_tokens for m in group_metrics]
        output_tokens = [m.output_tokens for m in group_metrics]
        cached_tokens = [m.cached_tokens for m in group_metrics]

        stats = PerformanceStatistics(
            model=key[0],
            request_size=key[1],
            thinking_level=key[2],
            thinking_budget=key[3],
            cache_enabled=key[4],
            median_ttft_ms=statistics.median(ttfts),
            p90_ttft_ms=statistics.quantiles(ttfts, n=10)[8] if len(ttfts) >= 10 else max(ttfts),
            p99_ttft_ms=statistics.quantiles(ttfts, n=100)[98] if len(ttfts) >= 100 else max(ttfts),
            avg_input_tokens=statistics.mean(input_tokens),
            avg_output_tokens=statistics.mean(output_tokens),
            avg_cached_tokens=statistics.mean(cached_tokens)
        )

        statistics_list.append(stats)

    return statistics_list


@router.post("/benchmark", response_model=PerformanceEvaluationResponse)
async def run_performance_benchmark(request: PerformanceEvaluationRequest):
    """
    Execute performance benchmark across configurations
    """
    try:
        # Validate constraints
        validate_gemini_3_constraints(request)
        validate_thinking_budgets(request)

        # Generate configurations
        configs = generate_configurations(request)

        # Create output directory
        output_dir = Path("performance_results")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_csv_path = output_dir / f"raw_metrics_{timestamp}.csv"
        analysis_csv_path = output_dir / f"analysis_{timestamp}.csv"

        # Collect metrics
        all_metrics = []

        # Write raw CSV header
        with open(raw_csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'model', 'request_size', 'thinking_level',
                'thinking_budget', 'cache_enabled', 'ttft_ms', 'input_tokens',
                'output_tokens', 'cached_tokens', 'iteration'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Execute benchmarks
            for config in configs:
                for i in range(request.iterations):
                    try:
                        # Run benchmark
                        result = await gemini_service.benchmark_request(
                            model_name=config["model"],
                            request_size=config["request_size"],
                            thinking_level=config["thinking_level"],
                            thinking_budget=config["thinking_budget"],
                            cache_enabled=config["cache_enabled"],
                            project=request.project
                        )

                        # Create metric
                        metric = PerformanceMetric(
                            timestamp=datetime.now().isoformat(),
                            model=config["model"],
                            request_size=config["request_size"],
                            thinking_level=config["thinking_level"],
                            thinking_budget=config["thinking_budget"],
                            cache_enabled=config["cache_enabled"],
                            ttft_ms=result["ttft_ms"],
                            input_tokens=result["input_tokens"],
                            output_tokens=result["output_tokens"],
                            cached_tokens=result["cached_tokens"],
                            iteration=i + 1
                        )

                        all_metrics.append(metric)

                        # Write to CSV
                        writer.writerow(metric.dict())

                    except Exception as e:
                        logger.error(f"Error in benchmark iteration: {e}")
                        continue

        # Calculate statistics
        stats = calculate_statistics(all_metrics)

        # Write analysis CSV
        with open(analysis_csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'model', 'request_size', 'thinking_level', 'thinking_budget',
                'cache_enabled', 'median_ttft_ms', 'p90_ttft_ms', 'p99_ttft_ms',
                'avg_input_tokens', 'avg_output_tokens', 'avg_cached_tokens'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for stat in stats:
                writer.writerow(stat.dict())

        return PerformanceEvaluationResponse(
            success=True,
            raw_csv_path=str(raw_csv_path),
            analysis_csv_path=str(analysis_csv_path),
            statistics=stats,
            message=f"Completed {len(all_metrics)} benchmark runs"
        )

    except Exception as e:
        logger.error(f"Error in performance benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{file_type}/{filename}")
async def download_csv(file_type: str, filename: str):
    """
    Download CSV file (raw metrics or analysis)
    """
    try:
        # Validate file type
        if file_type not in ["raw", "analysis"]:
            raise HTTPException(status_code=400, detail="Invalid file type")

        # Construct file path
        file_path = Path("performance_results") / filename

        # Validate file exists and is in the correct directory
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Security check: ensure file is within performance_results directory
        try:
            file_path.resolve().relative_to(Path("performance_results").resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        # Return file as download
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="text/csv"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
