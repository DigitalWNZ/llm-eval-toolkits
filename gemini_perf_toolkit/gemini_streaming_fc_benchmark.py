#!/usr/bin/env python3
"""
Gemini benchmark with streaming function calling enabled.

Adds stream_function_call_arguments=True to the tool config.
Supports all thinking levels (minimal, low, medium, high).
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


def calculate_statistics(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    percentiles = [50, 90, 95, 99]
    stats = {}
    for key in ["ttft_ms", "response_time_ms", "input_tokens", "output_tokens", "cached_tokens", "thinking_tokens"]:
        values = [m.get(key, 0) for m in metrics_list]
        stats[key] = {
            "min": min(values),
            "max": max(values),
            **calculate_percentiles(values, percentiles),
        }
    return stats


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

    end_time = time.time()
    ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
    response_time = (end_time - start_time) * 1000
    traffic_type = getattr(usage_metadata, "traffic_type", None) or "UNKNOWN"

    return {
        "ttft_ms": round(ttft, 2),
        "response_time_ms": round(response_time, 2),
        "input_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
        "cached_tokens": getattr(usage_metadata, "cached_content_token_count", 0) or 0,
        "thinking_tokens": getattr(usage_metadata, "thoughts_token_count", 0) or 0,
        "traffic_type": str(traffic_type),
    }


async def run_benchmark(model_name: str, request_file: str, iterations: int, thinking_level: str = None):
    with open(request_file, 'r') as f:
        request_data = json.load(f)

    contents = request_data.get("contents", [])
    system_instruction = request_data.get("system_instruction")
    tools_raw = request_data.get("tools", [])

    sdk_tools = []
    for tool_group in tools_raw:
        func_decls = []
        for fd in tool_group.get("functionDeclarations", []):
            func_decls.append(types.FunctionDeclaration(**fd))
        sdk_tools.append(types.Tool(function_declarations=func_decls))

    thinking_config = None
    if thinking_level:
        level_map = {
            "minimal": types.ThinkingLevel.MINIMAL,
            "low": types.ThinkingLevel.LOW,
            "medium": types.ThinkingLevel.MEDIUM,
            "high": types.ThinkingLevel.HIGH,
        }
        thinking_config = types.ThinkingConfig(thinkingLevel=level_map[thinking_level])

    config = types.GenerateContentConfig(
        systemInstruction=system_instruction,
        tools=sdk_tools,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO,
                stream_function_call_arguments=True,
            )
        ),
        thinkingConfig=thinking_config,
    )

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    request_name = Path(request_file).stem
    thinking_label = thinking_level or "default"
    print(f"Model: {model_name}")
    print(f"Request: {request_name}")
    print(f"Endpoint: {LOCATION}")
    print(f"Streaming FC: enabled")
    print(f"Thinking Level: {thinking_label}")
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
                f"e2e={metrics['response_time_ms']:.0f}ms, "
                f"in={metrics['input_tokens']}, out={metrics['output_tokens']}, "
                f"think={metrics['thinking_tokens']}, "
                f"traffic={metrics['traffic_type']}"
            )
        except Exception as e:
            print(f" FAILED - {e}")

    if not metrics_list:
        print("All iterations failed!")
        return None

    stats = calculate_statistics(metrics_list)

    print(f"\n{'Metric':<20} {'Min':>10} {'P50':>10} {'P90':>10} {'P95':>10} {'P99':>10} {'Max':>10}")
    print("-" * 90)
    for key, label in [("ttft_ms", "TTFT (ms)"), ("response_time_ms", "E2E (ms)"),
                        ("input_tokens", "Input Tokens"), ("output_tokens", "Output Tokens"),
                        ("cached_tokens", "Cached Tokens"), ("thinking_tokens", "Thinking Tokens")]:
        s = stats[key]
        print(f"{label:<20} {s['min']:>10.1f} {s['p50']:>10.1f} {s['p90']:>10.1f} "
              f"{s['p95']:>10.1f} {s['p99']:>10.1f} {s['max']:>10.1f}")

    return {
        "model": model_name,
        "request_file": request_name,
        "location": LOCATION,
        "streaming_fc": True,
        "thinking_level": thinking_label,
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
    thinking_levels = ["minimal", "low", "medium", "high"]
    iterations = 10

    all_results = []
    for thinking_level in thinking_levels:
        for request_file in request_files:
            print(f"\n{'='*90}")
            result = await run_benchmark(model, request_file, iterations, thinking_level)
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
        "model", "request_file", "location", "streaming_fc", "thinking_level", "iterations",
        "ttft_min_ms", "ttft_p50_ms", "ttft_p90_ms", "ttft_p95_ms", "ttft_p99_ms", "ttft_max_ms",
        "response_time_min_ms", "response_time_p50_ms", "response_time_p90_ms",
        "response_time_p95_ms", "response_time_p99_ms", "response_time_max_ms",
        "input_tokens_min", "input_tokens_p50", "input_tokens_p90",
        "input_tokens_p95", "input_tokens_p99", "input_tokens_max",
        "output_tokens_min", "output_tokens_p50", "output_tokens_p90",
        "output_tokens_p95", "output_tokens_p99", "output_tokens_max",
        "thinking_tokens_min", "thinking_tokens_p50", "thinking_tokens_p90",
        "thinking_tokens_p95", "thinking_tokens_p99", "thinking_tokens_max",
        "cached_tokens_min", "cached_tokens_p50", "cached_tokens_p90",
        "cached_tokens_p95", "cached_tokens_p99", "cached_tokens_max",
        "source_json",
    ]

    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for result in all_results:
            s = result["statistics"]
            writer.writerow({
                "model": result["model"],
                "request_file": result["request_file"],
                "location": result["location"],
                "streaming_fc": result["streaming_fc"],
                "thinking_level": result["thinking_level"],
                "iterations": result["iterations"],
                "ttft_min_ms": f"{s['ttft_ms']['min']:.2f}",
                "ttft_p50_ms": f"{s['ttft_ms']['p50']:.2f}",
                "ttft_p90_ms": f"{s['ttft_ms']['p90']:.2f}",
                "ttft_p95_ms": f"{s['ttft_ms']['p95']:.2f}",
                "ttft_p99_ms": f"{s['ttft_ms']['p99']:.2f}",
                "ttft_max_ms": f"{s['ttft_ms']['max']:.2f}",
                "response_time_min_ms": f"{s['response_time_ms']['min']:.2f}",
                "response_time_p50_ms": f"{s['response_time_ms']['p50']:.2f}",
                "response_time_p90_ms": f"{s['response_time_ms']['p90']:.2f}",
                "response_time_p95_ms": f"{s['response_time_ms']['p95']:.2f}",
                "response_time_p99_ms": f"{s['response_time_ms']['p99']:.2f}",
                "response_time_max_ms": f"{s['response_time_ms']['max']:.2f}",
                "input_tokens_min": s["input_tokens"]["min"],
                "input_tokens_p50": f"{s['input_tokens']['p50']:.0f}",
                "input_tokens_p90": f"{s['input_tokens']['p90']:.0f}",
                "input_tokens_p95": f"{s['input_tokens']['p95']:.0f}",
                "input_tokens_p99": f"{s['input_tokens']['p99']:.0f}",
                "input_tokens_max": s["input_tokens"]["max"],
                "output_tokens_min": s["output_tokens"]["min"],
                "output_tokens_p50": f"{s['output_tokens']['p50']:.0f}",
                "output_tokens_p90": f"{s['output_tokens']['p90']:.0f}",
                "output_tokens_p95": f"{s['output_tokens']['p95']:.0f}",
                "output_tokens_p99": f"{s['output_tokens']['p99']:.0f}",
                "output_tokens_max": s["output_tokens"]["max"],
                "thinking_tokens_min": s["thinking_tokens"]["min"],
                "thinking_tokens_p50": f"{s['thinking_tokens']['p50']:.0f}",
                "thinking_tokens_p90": f"{s['thinking_tokens']['p90']:.0f}",
                "thinking_tokens_p95": f"{s['thinking_tokens']['p95']:.0f}",
                "thinking_tokens_p99": f"{s['thinking_tokens']['p99']:.0f}",
                "thinking_tokens_max": s["thinking_tokens"]["max"],
                "cached_tokens_min": s["cached_tokens"]["min"],
                "cached_tokens_p50": f"{s['cached_tokens']['p50']:.0f}",
                "cached_tokens_p90": f"{s['cached_tokens']['p90']:.0f}",
                "cached_tokens_p95": f"{s['cached_tokens']['p95']:.0f}",
                "cached_tokens_p99": f"{s['cached_tokens']['p99']:.0f}",
                "cached_tokens_max": s["cached_tokens"]["max"],
                "source_json": json_file,
            })

    print(f"CSV saved to: {csv_file}")

    # Summary
    print(f"\n{'='*90}")
    print("SUMMARY")
    print(f"{'='*90}")
    for r in all_results:
        s = r["statistics"]
        print(
            f"  {r['thinking_level']:>8} | {r['request_file']:<20} | "
            f"TTFT p50={s['ttft_ms']['p50']:.0f}ms p90={s['ttft_ms']['p90']:.0f}ms | "
            f"E2E p50={s['response_time_ms']['p50']:.0f}ms p90={s['response_time_ms']['p90']:.0f}ms | "
            f"think p50={s['thinking_tokens']['p50']:.0f} p90={s['thinking_tokens']['p90']:.0f}"
        )


if __name__ == "__main__":
    asyncio.run(main())
