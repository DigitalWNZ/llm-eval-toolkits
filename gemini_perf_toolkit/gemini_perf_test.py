#!/usr/bin/env python3
"""
Standalone CLI tool for testing Gemini model performance.

This script runs multiple iterations of requests to a Gemini model and reports
performance statistics including TTFT, token counts, and percentiles.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from google import genai
from google.genai import types


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Gemini model performance with multiple iterations"
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Gemini model name (e.g., gemini-2.0-flash-exp)"
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
        required=True,
        help="Number of iterations to run"
    )
    parser.add_argument(
        "--request-file",
        required=True,
        help="Path to the JSON request file"
    )
    parser.add_argument(
        "--thinking-level",
        choices=["minimal", "low", "medium", "high"],
        help="Thinking level for Gemini 3.x models (minimal, low, medium, high)"
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        help="Thinking budget for Gemini 2.x/3.x models (integer value)"
    )

    return parser.parse_args()


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
        "thinking_tokens": getattr(usage_metadata, "thoughts_token_count", 0) or 0,
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
    thinking_token_values = [m.get("thinking_tokens", 0) for m in metrics_list]

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
        },
        "thinking_tokens": {
            "min": min(thinking_token_values),
            "max": max(thinking_token_values),
            **calculate_percentiles(thinking_token_values, percentiles)
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
    thinking_budget: int = None
) -> Dict[str, Any]:
    """Run performance test with specified iterations."""
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
    print(f"Running {iterations} iterations...")
    metrics_list = []

    for i in range(iterations):
        print(f"  Iteration {i + 1}/{iterations}...", end="", flush=True)
        try:
            metrics = await run_single_request(client, model_name, contents, config)
            metrics_list.append(metrics)
            print(f" ✓ (TTFT: {metrics['ttft_ms']:.2f}ms)")
        except Exception as e:
            print(f" ✗ Error: {e}")
            # Continue with remaining iterations

    if not metrics_list:
        raise RuntimeError("All iterations failed")

    # Calculate statistics
    stats = calculate_statistics(metrics_list)

    # Extract traffic types
    traffic_types = [m["traffic_type"] for m in metrics_list]
    traffic_type_summary = ", ".join(set(traffic_types))  # Unique traffic types

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


def save_json_results(results: Dict[str, Any], output_file: str):
    """Save results to JSON file."""
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_file}")


def print_results(results: Dict[str, Any]):
    """Print formatted results in table format."""
    print("\n" + "=" * 100)
    print("PERFORMANCE TEST RESULTS")
    print("=" * 100)
    print(f"Model: {results['model']}")
    print(f"Project: {results['project']}")
    print(f"Location: {results['location']}")
    print(f"Successful Iterations: {results['iterations']}")
    if results.get('thinking_level'):
        print(f"Thinking Level: {results['thinking_level']}")
    if results.get('thinking_budget'):
        print(f"Thinking Budget: {results['thinking_budget']}")
    if results.get('traffic_type'):
        print(f"Traffic Type: {results['traffic_type']}")
    print("=" * 100)

    stats = results["statistics"]

    # Print table header
    print(f"\n{'Metric':<20} {'Min':>12} {'P50':>12} {'P90':>12} {'P95':>12} {'P99':>12} {'Max':>12}")
    print("-" * 100)

    # TTFT row
    print(f"{'TTFT (ms)':<20} "
          f"{stats['ttft_ms']['min']:>12.2f} "
          f"{stats['ttft_ms']['p50']:>12.2f} "
          f"{stats['ttft_ms']['p90']:>12.2f} "
          f"{stats['ttft_ms']['p95']:>12.2f} "
          f"{stats['ttft_ms']['p99']:>12.2f} "
          f"{stats['ttft_ms']['max']:>12.2f}")

    # Input tokens row
    print(f"{'Input Tokens':<20} "
          f"{stats['input_tokens']['min']:>12.0f} "
          f"{stats['input_tokens']['p50']:>12.0f} "
          f"{stats['input_tokens']['p90']:>12.0f} "
          f"{stats['input_tokens']['p95']:>12.0f} "
          f"{stats['input_tokens']['p99']:>12.0f} "
          f"{stats['input_tokens']['max']:>12.0f}")

    # Output tokens row
    print(f"{'Output Tokens':<20} "
          f"{stats['output_tokens']['min']:>12.0f} "
          f"{stats['output_tokens']['p50']:>12.0f} "
          f"{stats['output_tokens']['p90']:>12.0f} "
          f"{stats['output_tokens']['p95']:>12.0f} "
          f"{stats['output_tokens']['p99']:>12.0f} "
          f"{stats['output_tokens']['max']:>12.0f}")

    # Cached tokens row
    print(f"{'Cached Tokens':<20} "
          f"{stats['cached_tokens']['min']:>12.0f} "
          f"{stats['cached_tokens']['p50']:>12.0f} "
          f"{stats['cached_tokens']['p90']:>12.0f} "
          f"{stats['cached_tokens']['p95']:>12.0f} "
          f"{stats['cached_tokens']['p99']:>12.0f} "
          f"{stats['cached_tokens']['max']:>12.0f}")

    # Thinking tokens row
    print(f"{'Thinking Tokens':<20} "
          f"{stats['thinking_tokens']['min']:>12.0f} "
          f"{stats['thinking_tokens']['p50']:>12.0f} "
          f"{stats['thinking_tokens']['p90']:>12.0f} "
          f"{stats['thinking_tokens']['p95']:>12.0f} "
          f"{stats['thinking_tokens']['p99']:>12.0f} "
          f"{stats['thinking_tokens']['max']:>12.0f}")

    print("=" * 100)


async def main():
    """Main entry point."""
    args = parse_args()

    try:
        # Load request file
        print(f"Loading request file: {args.request_file}")
        request_data = load_request_file(args.request_file)

        # Run performance test
        results = await run_performance_test(
            model_name=args.model,
            project=args.project,
            location=args.location,
            iterations=args.iterations,
            request_data=request_data,
            thinking_level=args.thinking_level,
            thinking_budget=args.thinking_budget
        )

        # Print results
        print_results(results)

        # Save JSON results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_safe_name = results['model'].replace('/', '_').replace('.', '_')
        output_file = f"perf_results_{model_safe_name}_{timestamp}.json"
        save_json_results(results, output_file)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
