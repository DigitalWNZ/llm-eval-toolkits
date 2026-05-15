#!/usr/bin/env python3
"""
Controller program for running comprehensive Gemini performance tests.

This script runs performance tests across multiple models, request files, and configurations,
and outputs a consolidated CSV file with all results.
"""

import argparse
import asyncio
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from itertools import product

from google import genai
from google.genai import types


# Import functions from gemini_perf_test
def load_request_file(file_path: str) -> Dict[str, Any]:
    """Load and parse the request JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Request file not found: {file_path}")

    with open(path, 'r') as f:
        return json.load(f)


async def run_single_request(
    client: genai.Client,
    model_name: str,
    contents: List[Dict[str, Any]],
    config: types.GenerateContentConfig
) -> Dict[str, float]:
    """Run a single request and measure performance metrics."""
    import time

    start_time = time.time()
    first_token_time = None
    usage_metadata = None

    # Use streaming to get accurate TTFT
    stream = await client.aio.models.generate_content_stream(
        model=model_name,
        contents=contents,
        config=config
    )

    async for chunk in stream:
        # Capture time of first token
        if first_token_time is None:
            first_token_time = time.time()

        # Get usage metadata from the last chunk
        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
            usage_metadata = chunk.usage_metadata

    # Calculate TTFT in milliseconds
    ttft = (first_token_time - start_time) * 1000 if first_token_time else 0

    # Extract metrics including trafficType
    traffic_type = getattr(usage_metadata, "traffic_type", None) or "UNKNOWN"

    metrics = {
        "ttft_ms": ttft,
        "input_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
        "cached_tokens": getattr(usage_metadata, "cached_content_token_count", 0) or 0,
        "traffic_type": str(traffic_type),
    }

    return metrics


def calculate_percentiles(values: List[float], percentiles: List[int]) -> Dict[str, float]:
    """Calculate percentiles for a list of values."""
    if not values:
        return {f"p{p}": 0 for p in percentiles}

    sorted_values = sorted(values)
    n = len(sorted_values)

    result = {}
    for p in percentiles:
        # Calculate index using linear interpolation
        index = (p / 100) * (n - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, n - 1)
        weight = index - lower_idx

        # Interpolate between values
        value = sorted_values[lower_idx] * (1 - weight) + sorted_values[upper_idx] * weight
        result[f"p{p}"] = value

    return result


def calculate_statistics(metrics_list: List[Dict[str, float]]) -> Dict[str, Any]:
    """Calculate min, max, and percentiles for all metrics."""
    # Collect values for each metric
    ttft_values = [m["ttft_ms"] for m in metrics_list]
    input_token_values = [m["input_tokens"] for m in metrics_list]
    output_token_values = [m["output_tokens"] for m in metrics_list]
    cached_token_values = [m["cached_tokens"] for m in metrics_list]

    # Calculate statistics
    percentiles = [50, 90, 95, 99]

    stats = {
        "ttft_ms": {
            "min": min(ttft_values),
            "max": max(ttft_values),
            **calculate_percentiles(ttft_values, percentiles)
        },
        "input_tokens": {
            "min": min(input_token_values),
            "max": max(input_token_values),
            **calculate_percentiles(input_token_values, percentiles)
        },
        "output_tokens": {
            "min": min(output_token_values),
            "max": max(output_token_values),
            **calculate_percentiles(output_token_values, percentiles)
        },
        "cached_tokens": {
            "min": min(cached_token_values),
            "max": max(cached_token_values),
            **calculate_percentiles(cached_token_values, percentiles)
        }
    }

    return stats


async def run_performance_test(
    model_name: str,
    project: str,
    location: str,
    iterations: int,
    request_data: Dict[str, Any],
    thinking_level: str = None,
    thinking_budget: int = None,
    logger: logging.Logger = None
) -> Dict[str, Any]:
    """Run performance test with specified iterations."""
    if logger is None:
        logger = logging.getLogger(__name__)

    # Create Gemini client
    client = genai.Client(
        vertexai=True,
        project=project,
        location=location
    )

    # Extract request components (ignore generation_config from request)
    contents = request_data.get("contents", [])
    system_instruction = request_data.get("system_instruction")

    # Determine if this model supports thinking levels
    supports_thinking_level = model_name.startswith("gemini-3") or model_name.startswith("gemma-")

    # Build thinking config based on model version
    thinking_config = None
    if thinking_level or thinking_budget:
        thinking_config_params = {}

        # thinking_level is for Gemini 3.x and Gemma models
        if thinking_level and supports_thinking_level:
            level_map = {
                "minimal": types.ThinkingLevel.MINIMAL,
                "low": types.ThinkingLevel.LOW,
                "medium": types.ThinkingLevel.MEDIUM,
                "high": types.ThinkingLevel.HIGH
            }
            thinking_config_params["thinkingLevel"] = level_map[thinking_level]

        # thinking_budget is for both Gemini 2.x and 3.x models
        if thinking_budget:
            thinking_config_params["thinkingBudget"] = thinking_budget

        if thinking_config_params:
            thinking_config = types.ThinkingConfig(**thinking_config_params)

    # Build config without request's generation_config
    config = types.GenerateContentConfig(
        systemInstruction=system_instruction,
        thinkingConfig=thinking_config
    )

    # Run iterations
    logger.info(f"Running {iterations} iterations...")
    metrics_list = []

    for i in range(iterations):
        logger.info(f"  Iteration {i + 1}/{iterations}...")
        try:
            metrics = await run_single_request(client, model_name, contents, config)
            metrics_list.append(metrics)
            logger.info(f"    ✓ TTFT: {metrics['ttft_ms']:.2f}ms, Traffic Type: {metrics['traffic_type']}")
        except Exception as e:
            logger.error(f"    ✗ Error: {e}")
            # Continue with remaining iterations

    if not metrics_list:
        raise RuntimeError("All iterations failed")

    # Calculate statistics
    stats = calculate_statistics(metrics_list)

    # Build final request for output
    final_request = {
        "model": model_name,
        "contents": contents,
        "config": {
            "systemInstruction": system_instruction,
            "thinkingConfig": {
                "thinkingLevel": thinking_level,
                "thinkingBudget": thinking_budget
            } if (thinking_level or thinking_budget) else None
        }
    }

    # Extract traffic types
    traffic_types = [m["traffic_type"] for m in metrics_list]
    traffic_type_summary = ", ".join(set(traffic_types))  # Unique traffic types

    return {
        "model": model_name,
        "project": project,
        "location": location,
        "iterations": len(metrics_list),
        "thinking_level": thinking_level,
        "thinking_budget": thinking_budget,
        "traffic_type": traffic_type_summary,
        "final_request": final_request,
        "all_metrics": metrics_list,
        "statistics": stats
    }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive Gemini performance tests across multiple configurations"
    )
    parser.add_argument(
        "--models",
        nargs='+',
        required=True,
        help="List of model names (e.g., gemini-2.5-flash gemini-3-flash-preview)"
    )
    parser.add_argument(
        "--request-files",
        nargs='+',
        required=True,
        help="List of request file paths"
    )
    parser.add_argument(
        "--thinking-levels",
        nargs='+',
        choices=["minimal", "low", "medium", "high"],
        help="List of thinking levels for Gemini 3.x models"
    )
    parser.add_argument(
        "--thinking-budgets",
        nargs='+',
        type=int,
        help="List of thinking budgets for Gemini 2.x models"
    )
    parser.add_argument(
        "--project",
        default="cloud-llm-preview1",
        help="GCP project name (default: cloud-llm-preview1)"
    )
    parser.add_argument(
        "--location",
        default="global",
        help="GCP location (default: global)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations per test (default: 5)"
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for results (default: current directory)"
    )

    return parser.parse_args()


def setup_logging(output_dir: str, run_id: str) -> logging.Logger:
    """Set up logging configuration."""
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"perf_test_{run_id}.log"

    # Create logger
    logger = logging.getLogger(f"perf_controller_{run_id}")
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def generate_test_combinations(
    models: List[str],
    request_files: List[str],
    thinking_levels: Optional[List[str]],
    thinking_budgets: Optional[List[int]]
) -> List[Dict[str, Any]]:
    """Generate all test combinations."""
    combinations = []

    for model in models:
        supports_thinking_level = model.startswith("gemini-3") or model.startswith("gemma-")
        is_gemini_2 = model.startswith("gemini-2")

        for request_file in request_files:
            # Determine which configs to use based on model version
            if supports_thinking_level and thinking_levels:
                # Gemini 3: use thinking levels
                for level in thinking_levels:
                    combinations.append({
                        "model": model,
                        "request_file": request_file,
                        "thinking_level": level,
                        "thinking_budget": None
                    })
                # Also add a baseline run without thinking
                combinations.append({
                    "model": model,
                    "request_file": request_file,
                    "thinking_level": None,
                    "thinking_budget": None
                })
            elif is_gemini_2 and thinking_budgets:
                # Gemini 2: use thinking budgets
                for budget in thinking_budgets:
                    combinations.append({
                        "model": model,
                        "request_file": request_file,
                        "thinking_level": None,
                        "thinking_budget": budget
                    })
                # Also add a baseline run without thinking
                combinations.append({
                    "model": model,
                    "request_file": request_file,
                    "thinking_level": None,
                    "thinking_budget": None
                })
            else:
                # No thinking config or model doesn't match
                combinations.append({
                    "model": model,
                    "request_file": request_file,
                    "thinking_level": None,
                    "thinking_budget": None
                })

    return combinations


def write_csv_results(results: List[Dict[str, Any]], output_file: str):
    """Write all results to CSV file."""
    if not results:
        return

    # CSV headers
    headers = [
        "model",
        "request_file",
        "thinking_level",
        "thinking_budget",
        "traffic_type",
        "project",
        "location",
        "iterations",
        "ttft_min_ms",
        "ttft_p50_ms",
        "ttft_p90_ms",
        "ttft_p95_ms",
        "ttft_p99_ms",
        "ttft_max_ms",
        "input_tokens_min",
        "input_tokens_p50",
        "input_tokens_p90",
        "input_tokens_p95",
        "input_tokens_p99",
        "input_tokens_max",
        "output_tokens_min",
        "output_tokens_p50",
        "output_tokens_p90",
        "output_tokens_p95",
        "output_tokens_p99",
        "output_tokens_max",
        "cached_tokens_min",
        "cached_tokens_p50",
        "cached_tokens_p90",
        "cached_tokens_p95",
        "cached_tokens_p99",
        "cached_tokens_max"
    ]

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for result in results:
            stats = result["statistics"]
            row = {
                "model": result["model"],
                "request_file": result["request_file"],
                "thinking_level": result.get("thinking_level", ""),
                "thinking_budget": result.get("thinking_budget", ""),
                "traffic_type": result.get("traffic_type", ""),
                "project": result["project"],
                "location": result["location"],
                "iterations": result["iterations"],
                "ttft_min_ms": f"{stats['ttft_ms']['min']:.2f}",
                "ttft_p50_ms": f"{stats['ttft_ms']['p50']:.2f}",
                "ttft_p90_ms": f"{stats['ttft_ms']['p90']:.2f}",
                "ttft_p95_ms": f"{stats['ttft_ms']['p95']:.2f}",
                "ttft_p99_ms": f"{stats['ttft_ms']['p99']:.2f}",
                "ttft_max_ms": f"{stats['ttft_ms']['max']:.2f}",
                "input_tokens_min": f"{stats['input_tokens']['min']:.0f}",
                "input_tokens_p50": f"{stats['input_tokens']['p50']:.0f}",
                "input_tokens_p90": f"{stats['input_tokens']['p90']:.0f}",
                "input_tokens_p95": f"{stats['input_tokens']['p95']:.0f}",
                "input_tokens_p99": f"{stats['input_tokens']['p99']:.0f}",
                "input_tokens_max": f"{stats['input_tokens']['max']:.0f}",
                "output_tokens_min": f"{stats['output_tokens']['min']:.0f}",
                "output_tokens_p50": f"{stats['output_tokens']['p50']:.0f}",
                "output_tokens_p90": f"{stats['output_tokens']['p90']:.0f}",
                "output_tokens_p95": f"{stats['output_tokens']['p95']:.0f}",
                "output_tokens_p99": f"{stats['output_tokens']['p99']:.0f}",
                "output_tokens_max": f"{stats['output_tokens']['max']:.0f}",
                "cached_tokens_min": f"{stats['cached_tokens']['min']:.0f}",
                "cached_tokens_p50": f"{stats['cached_tokens']['p50']:.0f}",
                "cached_tokens_p90": f"{stats['cached_tokens']['p90']:.0f}",
                "cached_tokens_p95": f"{stats['cached_tokens']['p95']:.0f}",
                "cached_tokens_p99": f"{stats['cached_tokens']['p99']:.0f}",
                "cached_tokens_max": f"{stats['cached_tokens']['max']:.0f}",
            }
            writer.writerow(row)


async def main():
    """Main entry point."""
    args = parse_args()

    # Create run ID and setup logging
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logging(args.output_dir, run_id)

    logger.info("=" * 100)
    logger.info("GEMINI PERFORMANCE TEST CONTROLLER")
    logger.info("=" * 100)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Models: {', '.join(args.models)}")
    logger.info(f"Request Files: {', '.join(args.request_files)}")
    logger.info(f"Project: {args.project}")
    logger.info(f"Location: {args.location}")
    logger.info(f"Iterations: {args.iterations}")

    if args.thinking_levels:
        logger.info(f"Thinking Levels (Gemini 3.x): {', '.join(args.thinking_levels)}")
    if args.thinking_budgets:
        logger.info(f"Thinking Budgets (Gemini 2.x): {', '.join(map(str, args.thinking_budgets))}")

    logger.info("=" * 100)

    # Generate test combinations
    combinations = generate_test_combinations(
        args.models,
        args.request_files,
        args.thinking_levels,
        args.thinking_budgets
    )

    logger.info(f"\nTotal test combinations: {len(combinations)}\n")

    # Run all tests
    results = []
    for idx, combo in enumerate(combinations, 1):
        logger.info("=" * 100)
        logger.info(f"Test {idx}/{len(combinations)}")
        logger.info(f"  Model: {combo['model']}")
        logger.info(f"  Request File: {combo['request_file']}")
        if combo['thinking_level']:
            logger.info(f"  Thinking Level: {combo['thinking_level']}")
        if combo['thinking_budget']:
            logger.info(f"  Thinking Budget: {combo['thinking_budget']}")
        logger.info("-" * 100)

        try:
            # Load request file
            request_data = load_request_file(combo['request_file'])

            # Run performance test
            result = await run_performance_test(
                model_name=combo['model'],
                project=args.project,
                location=args.location,
                iterations=args.iterations,
                request_data=request_data,
                thinking_level=combo['thinking_level'],
                thinking_budget=combo['thinking_budget'],
                logger=logger
            )

            # Add request file info
            result["request_file"] = combo['request_file']

            results.append(result)

            logger.info(f"✓ Test {idx} completed successfully")
            logger.info(f"  TTFT P50: {result['statistics']['ttft_ms']['p50']:.2f}ms")
            logger.info(f"  Output Tokens P50: {result['statistics']['output_tokens']['p50']:.0f}")
            logger.info(f"  Traffic Type: {result.get('traffic_type', 'UNKNOWN')}")

            # Save individual JSON result
            output_dir = Path(args.output_dir) / "json_results"
            output_dir.mkdir(parents=True, exist_ok=True)

            model_safe = combo['model'].replace('/', '_').replace('.', '_')
            request_file_name = Path(combo['request_file']).stem
            thinking_suffix = ""
            if combo['thinking_level']:
                thinking_suffix = f"_level_{combo['thinking_level']}"
            elif combo['thinking_budget']:
                thinking_suffix = f"_budget_{combo['thinking_budget']}"

            json_file = output_dir / f"{model_safe}_{request_file_name}{thinking_suffix}_{run_id}.json"
            with open(json_file, 'w') as f:
                json.dump(result, f, indent=2)

        except Exception as e:
            logger.error(f"✗ Test {idx} failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

        logger.info("")

    # Write CSV results
    if results:
        csv_file = Path(args.output_dir) / f"perf_results_{run_id}.csv"
        write_csv_results(results, str(csv_file))
        logger.info("=" * 100)
        logger.info(f"CSV results saved to: {csv_file}")
        logger.info(f"Total successful tests: {len(results)}/{len(combinations)}")
        logger.info("=" * 100)
    else:
        logger.error("No successful tests to write to CSV")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
