#!/usr/bin/env python3
"""
Claude Performance Benchmark on Vertex AI.

Runs performance tests across models, request files, and reasoning effort levels.
Outputs CSV summary + per-test JSON files with percentile statistics.
"""

import argparse
import csv
import json
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List

from anthropic import AnthropicVertex

PROJECT_ID = "cloud-llm-preview1"
REGION = "global"
MAX_TOKENS = 4096


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
    for key in ["response_time_ms", "input_tokens", "output_tokens"]:
        values = [m[key] for m in metrics_list]
        stats[key] = {
            "min": min(values),
            "max": max(values),
            **calculate_percentiles(values, percentiles),
        }
    return stats


def prepare_request(raw_request: dict, model: str) -> dict:
    messages = raw_request.get("messages", [])
    tools = raw_request.get("tools", [])

    system_parts = []
    conversation_messages = []

    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        system_parts.append(block["text"])
                    elif isinstance(block, str):
                        system_parts.append(block)
        else:
            clean_msg = {"role": msg["role"], "content": msg["content"]}
            conversation_messages.append(clean_msg)

    api_kwargs = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": conversation_messages,
    }

    if system_parts:
        api_kwargs["system"] = "\n".join(system_parts)

    if tools:
        fixed_tools = []
        for tool in tools:
            t = dict(tool)
            schema = t.get("input_schema", {})
            if "type" not in schema:
                schema = dict(schema)
                schema["type"] = "object"
                t["input_schema"] = schema
            fixed_tools.append(t)
        api_kwargs["tools"] = fixed_tools

    return api_kwargs


def run_single_test(client, api_kwargs: dict, effort: str) -> Dict[str, Any]:
    kwargs = dict(api_kwargs)
    kwargs["output_config"] = {"effort": effort}

    start_time = time.time()
    response = client.messages.create(**kwargs)
    elapsed_ms = (time.time() - start_time) * 1000

    response_dict = json.loads(response.model_dump_json())
    return {
        "response_time_ms": round(elapsed_ms, 2),
        "input_tokens": response_dict.get("usage", {}).get("input_tokens", 0),
        "output_tokens": response_dict.get("usage", {}).get("output_tokens", 0),
        "stop_reason": response_dict.get("stop_reason", "N/A"),
    }


def main():
    parser = argparse.ArgumentParser(description="Claude Performance Benchmark")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--request-files", nargs="+", required=True)
    parser.add_argument("--efforts", nargs="+", required=True, choices=["high", "medium", "low"])
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output-dir", default=os.path.expanduser("~/claude_perf_results"))
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_dir = os.path.join(args.output_dir, "json_results")
    os.makedirs(json_dir, exist_ok=True)

    client = AnthropicVertex(project_id=PROJECT_ID, region=REGION)
    print(f"Connected to Vertex AI (project={PROJECT_ID}, region={REGION})")

    # Build test combinations
    tests = []
    for model in args.models:
        for request_file in args.request_files:
            for effort in args.efforts:
                tests.append((model, request_file, effort))

    print(f"\nTest matrix: {len(tests)} combinations x {args.iterations} iterations = {len(tests) * args.iterations} total calls\n")

    all_results = []

    for test_idx, (model, request_file, effort) in enumerate(tests):
        request_name = os.path.basename(request_file).replace("_claude.json", "")
        print(f"{'='*80}")
        print(f"[{test_idx+1}/{len(tests)}] Model: {model} | Request: {request_name} | Effort: {effort}")
        print(f"{'='*80}")

        with open(request_file, "r", encoding="utf-8") as f:
            raw_request = json.load(f)
        api_kwargs = prepare_request(raw_request, model)

        msg_count = len(api_kwargs["messages"])
        tool_count = len(api_kwargs.get("tools", []))
        print(f"  Messages: {msg_count}, Tools: {tool_count}")

        metrics_list = []
        for i in range(args.iterations):
            try:
                metrics = run_single_test(client, api_kwargs, effort)
                metrics_list.append(metrics)
                print(
                    f"  Iteration {i+1}/{args.iterations}: "
                    f"{metrics['response_time_ms']:.0f}ms, "
                    f"in={metrics['input_tokens']}, out={metrics['output_tokens']}, "
                    f"stop={metrics['stop_reason']}"
                )
            except Exception as e:
                print(f"  Iteration {i+1}/{args.iterations}: FAILED - {e}")
                traceback.print_exc()

        if not metrics_list:
            print(f"  All iterations failed, skipping.")
            all_results.append({
                "model": model,
                "request_file": request_name,
                "effort": effort,
                "status": "failed",
            })
            continue

        stats = calculate_statistics(metrics_list)

        # Save JSON
        model_safe = model.replace("@", "_").replace("/", "_")
        json_file = os.path.join(json_dir, f"{model_safe}_{request_name}_{effort}_{run_id}.json")
        json_data = {
            "model": model,
            "effort": effort,
            "request_file": request_file,
            "project": PROJECT_ID,
            "region": REGION,
            "iterations": len(metrics_list),
            "all_metrics": metrics_list,
            "statistics": stats,
        }
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)
        print(f"  Stats: response_time p50={stats['response_time_ms']['p50']:.0f}ms p90={stats['response_time_ms']['p90']:.0f}ms")
        print(f"  Saved: {json_file}")

        all_results.append({
            "model": model,
            "request_file": request_name,
            "effort": effort,
            "status": "success",
            "iterations": len(metrics_list),
            "statistics": stats,
        })

    # Write CSV
    csv_file = os.path.join(args.output_dir, f"perf_results_{run_id}.csv")
    csv_columns = [
        "model", "request_file", "effort", "iterations",
        "response_time_min_ms", "response_time_p50_ms", "response_time_p90_ms",
        "response_time_p95_ms", "response_time_p99_ms", "response_time_max_ms",
        "input_tokens_min", "input_tokens_p50", "input_tokens_p90",
        "input_tokens_p95", "input_tokens_p99", "input_tokens_max",
        "output_tokens_min", "output_tokens_p50", "output_tokens_p90",
        "output_tokens_p95", "output_tokens_p99", "output_tokens_max",
    ]

    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for r in all_results:
            if r["status"] != "success":
                continue
            s = r["statistics"]
            writer.writerow({
                "model": r["model"],
                "request_file": r["request_file"],
                "effort": r["effort"],
                "iterations": r["iterations"],
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
            })

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    success = sum(1 for r in all_results if r["status"] == "success")
    failed = sum(1 for r in all_results if r["status"] != "success")
    print(f"Total: {success} successful, {failed} failed out of {len(all_results)}\n")

    for r in all_results:
        if r["status"] == "success":
            s = r["statistics"]
            print(
                f"  [OK]   {r['model']} + {r['request_file']} + {r['effort']} "
                f"(p50={s['response_time_ms']['p50']:.0f}ms, p90={s['response_time_ms']['p90']:.0f}ms, "
                f"in={s['input_tokens']['p50']:.0f}, out={s['output_tokens']['p50']:.0f})"
            )
        else:
            print(f"  [FAIL] {r['model']} + {r['request_file']} + {r['effort']}")

    print(f"\nCSV: {csv_file}")
    print(f"JSON: {json_dir}/")


if __name__ == "__main__":
    main()
