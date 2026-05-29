#!/usr/bin/env python3
"""
Claude Performance Benchmark on Vertex AI.

Supports two modes:
  - effort:   uses output_config.effort (high/medium/low)
  - thinking: uses extended thinking with budget_tokens (produces visible thinking tokens)

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
    for key in ["ttft_ms", "response_time_ms", "input_tokens", "output_tokens", "thinking_tokens"]:
        values = [m.get(key, 0) for m in metrics_list]
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


ADAPTIVE_ONLY_MODELS = ["claude-opus-4-7"]


def run_single_test(client, api_kwargs: dict, mode: str, config_value: str) -> Dict[str, Any]:
    kwargs = dict(api_kwargs)
    model = kwargs.get("model", "")

    if mode == "effort":
        kwargs["output_config"] = {"effort": config_value}
    elif mode == "thinking":
        budget = int(config_value)
        if any(model.startswith(m) for m in ADAPTIVE_ONLY_MODELS):
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["max_tokens"] = budget + MAX_TOKENS
        else:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
            kwargs["max_tokens"] = budget + MAX_TOKENS

    start_time = time.time()
    first_token_time = None

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if first_token_time is None:
                event_type = getattr(event, 'type', '')
                if event_type in ('content_block_start', 'content_block_delta', 'text'):
                    first_token_time = time.time()
        response = stream.get_final_message()

    end_time = time.time()
    ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0
    total_ms = (end_time - start_time) * 1000

    response_dict = json.loads(response.model_dump_json())
    usage = response_dict.get("usage", {})

    thinking_tokens = 0
    output_tokens_details = usage.get("output_tokens_details")
    if output_tokens_details:
        thinking_tokens = output_tokens_details.get("thinking_tokens", 0) or 0

    return {
        "ttft_ms": round(ttft_ms, 2),
        "response_time_ms": round(total_ms, 2),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "thinking_tokens": thinking_tokens,
        "stop_reason": response_dict.get("stop_reason", "N/A"),
    }


def make_config_label(mode: str, config_value: str) -> str:
    if mode == "effort":
        return f"effort:{config_value}"
    return f"budget:{config_value}"


def main():
    parser = argparse.ArgumentParser(description="Claude Performance Benchmark")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--request-files", nargs="+", required=True)
    parser.add_argument("--mode", choices=["effort", "thinking", "none"], required=True,
                        help="effort: use output_config.effort; thinking: use extended thinking with budget_tokens; none: no effort/thinking config")
    parser.add_argument("--efforts", nargs="+", choices=["high", "medium", "low"],
                        help="Effort levels (used with --mode effort)")
    parser.add_argument("--thinking-budgets", nargs="+", type=int,
                        help="Thinking budget values (used with --mode thinking)")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output-dir", default=os.path.expanduser("~/claude_perf_results"))
    args = parser.parse_args()

    if args.mode == "effort" and not args.efforts:
        parser.error("--efforts is required when --mode is effort")
    if args.mode == "thinking" and not args.thinking_budgets:
        parser.error("--thinking-budgets is required when --mode is thinking")

    if args.mode == "none":
        config_values = ["none"]
    elif args.mode == "effort":
        config_values = args.efforts
    else:
        config_values = [str(b) for b in args.thinking_budgets]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_dir = os.path.join(args.output_dir, f"json_results_{run_id}")
    os.makedirs(json_dir, exist_ok=True)

    client = AnthropicVertex(project_id=PROJECT_ID, region=REGION)
    print(f"Connected to Vertex AI (project={PROJECT_ID}, region={REGION})")
    print(f"Mode: {args.mode}")

    tests = []
    for model in args.models:
        for request_file in args.request_files:
            for cv in config_values:
                tests.append((model, request_file, cv))

    print(f"\nTest matrix: {len(tests)} combinations x {args.iterations} iterations = {len(tests) * args.iterations} total calls\n")

    all_results = []

    for test_idx, (model, request_file, config_value) in enumerate(tests):
        config_label = make_config_label(args.mode, config_value)
        request_name = os.path.basename(request_file).replace("_claude.json", "")
        print(f"{'='*80}")
        print(f"[{test_idx+1}/{len(tests)}] Model: {model} | Request: {request_name} | Config: {config_label}")
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
                metrics = run_single_test(client, api_kwargs, args.mode, config_value)
                metrics_list.append(metrics)
                print(
                    f"  Iteration {i+1}/{args.iterations}: "
                    f"TTFT={metrics['ttft_ms']:.0f}ms, total={metrics['response_time_ms']:.0f}ms, "
                    f"in={metrics['input_tokens']}, out={metrics['output_tokens']}, "
                    f"think={metrics['thinking_tokens']}, stop={metrics['stop_reason']}"
                )
            except Exception as e:
                print(f"  Iteration {i+1}/{args.iterations}: FAILED - {e}")
                traceback.print_exc()

        if not metrics_list:
            print(f"  All iterations failed, skipping.")
            all_results.append({
                "model": model,
                "request_file": request_name,
                "thinking_config": config_label,
                "status": "failed",
            })
            continue

        stats = calculate_statistics(metrics_list)

        model_safe = model.replace("@", "_").replace("/", "_")
        config_safe = config_value.replace(":", "_")
        json_file = os.path.join(json_dir, f"{model_safe}_{request_name}_{config_safe}_{run_id}.json")
        json_data = {
            "model": model,
            "thinking_mode": args.mode,
            "thinking_config": config_label,
            "request_file": request_file,
            "project": PROJECT_ID,
            "region": REGION,
            "iterations": len(metrics_list),
            "all_metrics": metrics_list,
            "statistics": stats,
        }
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)
        print(f"  Stats: TTFT p50={stats['ttft_ms']['p50']:.0f}ms p90={stats['ttft_ms']['p90']:.0f}ms | total p50={stats['response_time_ms']['p50']:.0f}ms p90={stats['response_time_ms']['p90']:.0f}ms | think p50={stats['thinking_tokens']['p50']:.0f}")
        print(f"  Saved: {json_file}")

        all_results.append({
            "model": model,
            "request_file": request_name,
            "thinking_config": config_label,
            "status": "success",
            "iterations": len(metrics_list),
            "statistics": stats,
            "source_json": json_file,
        })

    # Write CSV
    csv_file = os.path.join(args.output_dir, f"perf_results_{run_id}.csv")
    csv_columns = [
        "model", "request_file", "thinking_config", "iterations",
        "ttft_min_ms", "ttft_p50_ms", "ttft_p90_ms",
        "ttft_p95_ms", "ttft_p99_ms", "ttft_max_ms",
        "response_time_min_ms", "response_time_p50_ms", "response_time_p90_ms",
        "response_time_p95_ms", "response_time_p99_ms", "response_time_max_ms",
        "input_tokens_min", "input_tokens_p50", "input_tokens_p90",
        "input_tokens_p95", "input_tokens_p99", "input_tokens_max",
        "output_tokens_min", "output_tokens_p50", "output_tokens_p90",
        "output_tokens_p95", "output_tokens_p99", "output_tokens_max",
        "thinking_tokens_min", "thinking_tokens_p50", "thinking_tokens_p90",
        "thinking_tokens_p95", "thinking_tokens_p99", "thinking_tokens_max",
        "source_json",
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
                "thinking_config": r["thinking_config"],
                "iterations": r["iterations"],
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
                "source_json": r.get("source_json", ""),
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
                f"  [OK]   {r['model']} + {r['request_file']} + {r['thinking_config']} "
                f"(TTFT p50={s['ttft_ms']['p50']:.0f}ms p90={s['ttft_ms']['p90']:.0f}ms, "
                f"in={s['input_tokens']['p50']:.0f}, out={s['output_tokens']['p50']:.0f}, "
                f"think={s['thinking_tokens']['p50']:.0f})"
            )
        else:
            print(f"  [FAIL] {r['model']} + {r['request_file']} + {r['thinking_config']}")

    print(f"\nCSV: {csv_file}")
    print(f"JSON: {json_dir}/")


if __name__ == "__main__":
    main()
