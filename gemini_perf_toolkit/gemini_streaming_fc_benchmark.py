#!/usr/bin/env python3
"""
Gemini benchmark with streaming function calling enabled.

Adds stream_function_call_arguments=True to the tool config.
"""

import asyncio
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from google import genai
from google.genai import types


PROJECT_ID = "cloud-llm-preview1"
LOCATION = "global"


def calculate_percentiles(values: List[float], percentiles: List[int]) -> Dict[str, float]:
    if not values:
        return {f"p{p}": 0 for p in percentiles}
    sorted_values = sorted(values)
    n = len(sorted_values)
    result = {}
    for p in percentiles:
        index = (p / 100) * (n - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, n - 1)
        weight = index - lower_idx
        value = sorted_values[lower_idx] * (1 - weight) + sorted_values[upper_idx] * weight
        result[f"p{p}"] = value
    return result


async def run_single_request(
    client: genai.Client,
    model_name: str,
    contents: List[Dict[str, Any]],
    config: types.GenerateContentConfig
) -> Dict[str, Any]:
    start_time = time.time()
    first_token_time = None
    usage_metadata = None

    stream = await client.aio.models.generate_content_stream(
        model=model_name,
        contents=contents,
        config=config
    )

    async for chunk in stream:
        if first_token_time is None:
            first_token_time = time.time()
        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
            usage_metadata = chunk.usage_metadata

    ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
    traffic_type = getattr(usage_metadata, "traffic_type", None) or "UNKNOWN"

    return {
        "ttft_ms": ttft,
        "input_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
        "cached_tokens": getattr(usage_metadata, "cached_content_token_count", 0) or 0,
        "thinking_tokens": getattr(usage_metadata, "thoughts_token_count", 0) or 0,
        "traffic_type": str(traffic_type),
    }


async def run_benchmark(model_name: str, request_file: str, iterations: int):
    with open(request_file, 'r') as f:
        request_data = json.load(f)

    contents = request_data.get("contents", [])
    system_instruction = request_data.get("system_instruction")
    tools_raw = request_data.get("tools", [])

    # Convert raw tools to SDK types
    sdk_tools = []
    for tool_group in tools_raw:
        func_decls = []
        for fd in tool_group.get("functionDeclarations", []):
            func_decls.append(types.FunctionDeclaration(**fd))
        sdk_tools.append(types.Tool(function_declarations=func_decls))

    # Build config with streaming function calling enabled
    config = types.GenerateContentConfig(
        systemInstruction=system_instruction,
        tools=sdk_tools,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO,
                stream_function_call_arguments=True,
            )
        ),
    )

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    request_name = Path(request_file).stem
    print(f"Model: {model_name}")
    print(f"Request: {request_name}")
    print(f"Endpoint: {LOCATION}")
    print(f"Streaming FC: enabled")
    print(f"Iterations: {iterations}")
    print(f"{'='*90}")

    metrics_list = []
    for i in range(iterations):
        print(f"  Iteration {i+1}/{iterations}...", end="", flush=True)
        try:
            metrics = await run_single_request(client, model_name, contents, config)
            metrics_list.append(metrics)
            print(
                f" TTFT={metrics['ttft_ms']:.0f}ms, "
                f"in={metrics['input_tokens']}, out={metrics['output_tokens']}, "
                f"think={metrics['thinking_tokens']}, "
                f"traffic={metrics['traffic_type']}"
            )
        except Exception as e:
            print(f" FAILED - {e}")

    if not metrics_list:
        print("All iterations failed!")
        return None

    # Calculate stats
    percentiles = [50, 90, 95, 99]
    stats = {}
    for key in ["ttft_ms", "input_tokens", "output_tokens", "cached_tokens", "thinking_tokens"]:
        values = [m.get(key, 0) for m in metrics_list]
        stats[key] = {
            "min": min(values),
            "max": max(values),
            **calculate_percentiles(values, percentiles),
        }

    # Print stats
    print(f"\n{'Metric':<20} {'Min':>10} {'P50':>10} {'P90':>10} {'P95':>10} {'P99':>10} {'Max':>10}")
    print("-" * 90)
    for key, label in [("ttft_ms", "TTFT (ms)"), ("input_tokens", "Input Tokens"),
                        ("output_tokens", "Output Tokens"), ("cached_tokens", "Cached Tokens"),
                        ("thinking_tokens", "Thinking Tokens")]:
        s = stats[key]
        print(f"{label:<20} {s['min']:>10.1f} {s['p50']:>10.1f} {s['p90']:>10.1f} "
              f"{s['p95']:>10.1f} {s['p99']:>10.1f} {s['max']:>10.1f}")

    return {
        "model": model_name,
        "request_file": request_name,
        "location": LOCATION,
        "streaming_fc": True,
        "iterations": len(metrics_list),
        "all_metrics": metrics_list,
        "statistics": stats,
    }


async def main():
    model = "gemini-3.5-flash"
    request_files = [
        "/home/wangez/llm-eval-toolkits/slow_request_40s.json",
        "/home/wangez/llm-eval-toolkits/slow_request_60s.json",
    ]
    iterations = 10

    all_results = []
    for request_file in request_files:
        print(f"\n{'='*90}")
        result = await run_benchmark(model, request_file, iterations)
        if result:
            all_results.append(result)
        print()

    # Save JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"streaming_fc_benchmark_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"JSON saved to: {json_file}")

    # Save CSV
    csv_file = f"streaming_fc_benchmark_{timestamp}.csv"
    csv_columns = [
        "model", "request_file", "location", "streaming_fc", "iteration",
        "ttft_ms", "input_tokens", "output_tokens", "cached_tokens",
        "thinking_tokens", "traffic_type",
        "ttft_p50", "ttft_p90", "ttft_p95",
        "thinking_tokens_p50", "thinking_tokens_p90", "thinking_tokens_p95",
    ]
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for result in all_results:
            s = result["statistics"]
            for i, m in enumerate(result["all_metrics"], 1):
                writer.writerow({
                    "model": result["model"],
                    "request_file": result["request_file"],
                    "location": result["location"],
                    "streaming_fc": result["streaming_fc"],
                    "iteration": i,
                    "ttft_ms": f"{m['ttft_ms']:.2f}",
                    "input_tokens": m["input_tokens"],
                    "output_tokens": m["output_tokens"],
                    "cached_tokens": m["cached_tokens"],
                    "thinking_tokens": m["thinking_tokens"],
                    "traffic_type": m["traffic_type"],
                    "ttft_p50": f"{s['ttft_ms']['p50']:.2f}",
                    "ttft_p90": f"{s['ttft_ms']['p90']:.2f}",
                    "ttft_p95": f"{s['ttft_ms']['p95']:.2f}",
                    "thinking_tokens_p50": f"{s['thinking_tokens']['p50']:.0f}",
                    "thinking_tokens_p90": f"{s['thinking_tokens']['p90']:.0f}",
                    "thinking_tokens_p95": f"{s['thinking_tokens']['p95']:.0f}",
                })
    print(f"CSV saved to: {csv_file}")


if __name__ == "__main__":
    asyncio.run(main())
