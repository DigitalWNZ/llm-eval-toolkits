#!/usr/bin/env python3
"""
Full Gemini benchmark: all request files x all thinking levels x streaming FC on/off.

Usage:
  python gemini_full_benchmark.py --iterations 50
  python gemini_full_benchmark.py --iterations 1 --request-files slow_request_40s.json  # quick test
"""

import argparse
import asyncio
import csv
import json
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from google import genai
from google.genai import types


PROJECT_ID = "cloud-llm-preview1"
LOCATION = "global"
MODEL = "gemini-3.5-flash"

BENCHMARK_DIR = Path(__file__).parent / "benchmark"
THINKING_LEVELS = ["minimal", "low", "medium", "high"]
STREAMING_FC_MODES = [True, False]


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
    percentiles = [50, 90, 95]
    stats = {}
    for key in ["ttft_ms", "response_time_ms", "input_tokens", "output_tokens", "thinking_tokens", "cached_tokens"]:
        values = [m.get(key, 0) for m in metrics_list]
        stats[key] = {
            "min": min(values),
            "max": max(values),
            **calculate_percentiles(values, percentiles),
        }
    return stats


def load_request(request_file: Path) -> Dict[str, Any]:
    with open(request_file, 'r') as f:
        return json.load(f)


def build_config(
    request_data: Dict[str, Any],
    thinking_level: str,
    streaming_fc: bool,
) -> types.GenerateContentConfig:
    system_instruction = request_data.get("system_instruction") or request_data.get("systemInstruction")
    tools_raw = request_data.get("tools", [])

    sdk_tools = None
    tool_config = None

    if tools_raw:
        sdk_tools = []
        for tool_group in tools_raw:
            func_decls = []
            for fd in tool_group.get("functionDeclarations", []):
                func_decls.append(types.FunctionDeclaration(**fd))
            sdk_tools.append(types.Tool(function_declarations=func_decls))

        tool_config = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO,
                stream_function_call_arguments=streaming_fc,
            )
        )

    level_map = {
        "minimal": types.ThinkingLevel.MINIMAL,
        "low": types.ThinkingLevel.LOW,
        "medium": types.ThinkingLevel.MEDIUM,
        "high": types.ThinkingLevel.HIGH,
    }
    thinking_config = types.ThinkingConfig(thinkingLevel=level_map[thinking_level])

    config_kwargs = {
        "thinkingConfig": thinking_config,
    }
    if system_instruction:
        config_kwargs["systemInstruction"] = system_instruction
    if sdk_tools:
        config_kwargs["tools"] = sdk_tools
    if tool_config:
        config_kwargs["tool_config"] = tool_config

    return types.GenerateContentConfig(**config_kwargs)


async def run_single_request(
    client: genai.Client,
    model_name: str,
    contents: List[Dict[str, Any]],
    config: types.GenerateContentConfig,
) -> Dict[str, Any]:
    start_time = time.time()
    first_token_time = None
    usage_metadata = None

    stream = await client.aio.models.generate_content_stream(
        model=model_name,
        contents=contents,
        config=config,
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


async def run_combination(
    client: genai.Client,
    request_file: Path,
    thinking_level: str,
    streaming_fc: bool,
    iterations: int,
    combo_idx: int,
    total_combos: int,
) -> Dict[str, Any]:
    request_data = load_request(request_file)
    contents = request_data.get("contents", [])
    config = build_config(request_data, thinking_level, streaming_fc)

    request_name = request_file.stem
    has_tools = bool(request_data.get("tools"))
    fc_label = "on" if streaming_fc else "off"

    print(f"\n[{combo_idx}/{total_combos}] {request_name} | think={thinking_level} | streaming_fc={fc_label} | tools={has_tools}")
    print(f"{'='*100}")

    metrics_list = []
    for i in range(iterations):
        try:
            metrics = await run_single_request(client, MODEL, contents, config)
            metrics_list.append(metrics)
            print(
                f"  [{i+1:3d}/{iterations}] "
                f"TTFT={metrics['ttft_ms']:>8.0f}ms  "
                f"E2E={metrics['response_time_ms']:>8.0f}ms  "
                f"in={metrics['input_tokens']:>7}  out={metrics['output_tokens']:>5}  "
                f"think={metrics['thinking_tokens']:>6}  cache={metrics['cached_tokens']:>7}  "
                f"traffic={metrics['traffic_type']}"
            )
        except Exception as e:
            print(f"  [{i+1:3d}/{iterations}] FAILED - {e}")
            traceback.print_exc()

    if not metrics_list:
        print("  All iterations failed!")
        return None

    stats = calculate_statistics(metrics_list)

    print(f"\n  {'Metric':<20} {'P50':>10} {'P90':>10} {'P95':>10}")
    print(f"  {'-'*55}")
    for key, label in [("ttft_ms", "TTFT (ms)"), ("response_time_ms", "E2E (ms)"),
                        ("thinking_tokens", "Thinking Tokens")]:
        s = stats[key]
        print(f"  {label:<20} {s['p50']:>10.1f} {s['p90']:>10.1f} {s['p95']:>10.1f}")

    return {
        "model": MODEL,
        "request_file": request_name,
        "thinking_level": thinking_level,
        "streaming_fc": streaming_fc,
        "has_tools": has_tools,
        "iterations": len(metrics_list),
        "all_metrics": metrics_list,
        "statistics": stats,
    }


def write_csvs(all_results: List[Dict], timestamp: str, output_dir: str):
    # Detail CSV — one row per iteration
    detail_file = os.path.join(output_dir, f"benchmark_detail_{timestamp}.csv")
    detail_columns = [
        "model", "request_file", "thinking_level", "streaming_fc", "iteration",
        "ttft_ms", "response_time_ms", "input_tokens", "output_tokens",
        "thinking_tokens", "cached_tokens", "traffic_type",
    ]
    with open(detail_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=detail_columns)
        writer.writeheader()
        for result in all_results:
            for i, m in enumerate(result["all_metrics"], 1):
                writer.writerow({
                    "model": result["model"],
                    "request_file": result["request_file"],
                    "thinking_level": result["thinking_level"],
                    "streaming_fc": result["streaming_fc"],
                    "iteration": i,
                    "ttft_ms": m["ttft_ms"],
                    "response_time_ms": m["response_time_ms"],
                    "input_tokens": m["input_tokens"],
                    "output_tokens": m["output_tokens"],
                    "thinking_tokens": m["thinking_tokens"],
                    "cached_tokens": m["cached_tokens"],
                    "traffic_type": m["traffic_type"],
                })
    print(f"Detail CSV: {detail_file}")

    # Summary CSV — one row per combination
    summary_file = os.path.join(output_dir, f"benchmark_summary_{timestamp}.csv")
    summary_columns = [
        "model", "request_file", "thinking_level", "streaming_fc", "iterations",
        "ttft_p50_ms", "ttft_p90_ms", "ttft_p95_ms",
        "response_time_p50_ms", "response_time_p90_ms", "response_time_p95_ms",
        "input_tokens_p50", "input_tokens_p90", "input_tokens_p95",
        "output_tokens_p50", "output_tokens_p90", "output_tokens_p95",
        "thinking_tokens_p50", "thinking_tokens_p90", "thinking_tokens_p95",
        "cached_tokens_p50", "cached_tokens_p90", "cached_tokens_p95",
        "source_json",
    ]
    with open(summary_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=summary_columns)
        writer.writeheader()
        for result in all_results:
            s = result["statistics"]
            writer.writerow({
                "model": result["model"],
                "request_file": result["request_file"],
                "thinking_level": result["thinking_level"],
                "streaming_fc": result["streaming_fc"],
                "iterations": result["iterations"],
                "ttft_p50_ms": f"{s['ttft_ms']['p50']:.2f}",
                "ttft_p90_ms": f"{s['ttft_ms']['p90']:.2f}",
                "ttft_p95_ms": f"{s['ttft_ms']['p95']:.2f}",
                "response_time_p50_ms": f"{s['response_time_ms']['p50']:.2f}",
                "response_time_p90_ms": f"{s['response_time_ms']['p90']:.2f}",
                "response_time_p95_ms": f"{s['response_time_ms']['p95']:.2f}",
                "input_tokens_p50": f"{s['input_tokens']['p50']:.0f}",
                "input_tokens_p90": f"{s['input_tokens']['p90']:.0f}",
                "input_tokens_p95": f"{s['input_tokens']['p95']:.0f}",
                "output_tokens_p50": f"{s['output_tokens']['p50']:.0f}",
                "output_tokens_p90": f"{s['output_tokens']['p90']:.0f}",
                "output_tokens_p95": f"{s['output_tokens']['p95']:.0f}",
                "thinking_tokens_p50": f"{s['thinking_tokens']['p50']:.0f}",
                "thinking_tokens_p90": f"{s['thinking_tokens']['p90']:.0f}",
                "thinking_tokens_p95": f"{s['thinking_tokens']['p95']:.0f}",
                "cached_tokens_p50": f"{s['cached_tokens']['p50']:.0f}",
                "cached_tokens_p90": f"{s['cached_tokens']['p90']:.0f}",
                "cached_tokens_p95": f"{s['cached_tokens']['p95']:.0f}",
                "source_json": f"benchmark_full_{timestamp}.json",
            })
    print(f"Summary CSV: {summary_file}")


async def main():
    parser = argparse.ArgumentParser(description="Full Gemini 3.5 Flash Benchmark")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--request-files", nargs="+",
                        help="Specific request files to test (default: all in benchmark/)")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: gemini_perf_toolkit/)")
    args = parser.parse_args()

    output_dir = args.output_dir or str(Path(__file__).parent)

    if args.request_files:
        request_files = [BENCHMARK_DIR / f for f in args.request_files]
    else:
        request_files = sorted(BENCHMARK_DIR.glob("*.json"))

    total_combos = len(THINKING_LEVELS) * len(request_files) * len(STREAMING_FC_MODES)
    total_calls = total_combos * args.iterations

    print(f"Model: {MODEL}")
    print(f"Endpoint: {LOCATION}")
    print(f"Request files: {len(request_files)}")
    print(f"Thinking levels: {THINKING_LEVELS}")
    print(f"Streaming FC modes: on/off")
    print(f"Iterations: {args.iterations}")
    print(f"Total combinations: {total_combos}")
    print(f"Total API calls: {total_calls}")
    print(f"{'='*100}")

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    all_results = []
    combo_idx = 0

    for thinking_level in THINKING_LEVELS:
        for request_file in request_files:
            for streaming_fc in STREAMING_FC_MODES:
                combo_idx += 1
                result = await run_combination(
                    client, request_file, thinking_level, streaming_fc,
                    args.iterations, combo_idx, total_combos,
                )
                if result:
                    all_results.append(result)

    # Save JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"benchmark_full_{timestamp}.json")
    with open(json_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nJSON saved to: {json_file}")

    # Save CSVs
    write_csvs(all_results, timestamp, output_dir)

    # Final summary
    print(f"\n{'='*100}")
    print("FINAL SUMMARY")
    print(f"{'='*100}")
    print(f"{'Think':<8} {'Request':<20} {'FC':<4} {'Iter':>4} "
          f"{'TTFT p50':>10} {'TTFT p90':>10} {'E2E p50':>10} {'E2E p90':>10} "
          f"{'Think p50':>10} {'Think p90':>10}")
    print("-" * 100)
    for r in all_results:
        s = r["statistics"]
        fc = "on" if r["streaming_fc"] else "off"
        print(
            f"{r['thinking_level']:<8} {r['request_file']:<20} {fc:<4} {r['iterations']:>4} "
            f"{s['ttft_ms']['p50']:>10.0f} {s['ttft_ms']['p90']:>10.0f} "
            f"{s['response_time_ms']['p50']:>10.0f} {s['response_time_ms']['p90']:>10.0f} "
            f"{s['thinking_tokens']['p50']:>10.0f} {s['thinking_tokens']['p90']:>10.0f}"
        )

    print(f"\nTotal successful combinations: {len(all_results)}/{total_combos}")


if __name__ == "__main__":
    asyncio.run(main())
