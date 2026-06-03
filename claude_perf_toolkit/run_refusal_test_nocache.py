#!/usr/bin/env python3
"""Refusal test WITHOUT prompt caching — strips all cache_control from request."""

import json
import copy
import traceback
from anthropic import AnthropicVertex

PROJECT_ID = "cloud-llm-preview1"
REGION = "global"
MAX_TOKENS = 4096

REQUEST_FILE = "claude_opus_request_refusal_null_fixed.json"
MODELS = ["claude-opus-4-7", "claude-opus-4-6"]
ITERATIONS = 10


def strip_cache_control(obj):
    """Recursively remove all cache_control keys from dicts."""
    if isinstance(obj, dict):
        return {k: strip_cache_control(v) for k, v in obj.items() if k != "cache_control"}
    elif isinstance(obj, list):
        return [strip_cache_control(item) for item in obj]
    return obj


def prepare_request(raw_request: dict, model: str) -> dict:
    messages = raw_request.get("messages", [])
    tools = raw_request.get("tools", [])
    raw_system = raw_request.get("system")

    system_blocks = []
    if isinstance(raw_system, str):
        system_blocks = [{"type": "text", "text": raw_system}]
    elif isinstance(raw_system, list):
        for block in raw_system:
            if isinstance(block, dict) and block.get("type") == "text":
                system_blocks.append({"type": "text", "text": block["text"]})
            elif isinstance(block, str):
                system_blocks.append({"type": "text", "text": block})

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

    if system_parts:
        combined = "\n".join(system_parts)
        system_blocks.append({"type": "text", "text": combined})

    api_kwargs = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": strip_cache_control(conversation_messages),
    }

    if system_blocks:
        api_kwargs["system"] = strip_cache_control(system_blocks)

    if tools:
        fixed_tools = []
        for tool in tools:
            t = strip_cache_control(dict(tool))
            schema = t.get("input_schema", {})
            if "type" not in schema:
                schema = dict(schema)
                schema["type"] = "object"
                t["input_schema"] = schema
            fixed_tools.append(t)
        api_kwargs["tools"] = fixed_tools

    return api_kwargs


def main():
    client = AnthropicVertex(project_id=PROJECT_ID, region=REGION)
    print(f"Connected to Vertex AI (project={PROJECT_ID}, region={REGION})")

    with open(REQUEST_FILE, "r", encoding="utf-8") as f:
        raw_request = json.load(f)

    results = {}

    for model in MODELS:
        print(f"\n{'='*80}")
        print(f"Model: {model} — {ITERATIONS} iterations (NO CACHE)")
        print(f"{'='*80}")

        api_kwargs = prepare_request(raw_request, model)
        print(f"  Messages: {len(api_kwargs['messages'])}, Tools: {len(api_kwargs.get('tools', []))}")

        model_results = []
        for i in range(ITERATIONS):
            try:
                response = client.messages.create(**api_kwargs)
                resp_dict = json.loads(response.model_dump_json())
                usage = resp_dict.get("usage", {})

                row = {
                    "iteration": i + 1,
                    "input_tokens": usage.get("input_tokens", 0),
                    "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "stop_reason": resp_dict.get("stop_reason", "N/A"),
                    "stop_sequence": resp_dict.get("stop_sequence"),
                }

                model_results.append(row)
                print(
                    f"  [{i+1:2d}/{ITERATIONS}] "
                    f"input={row['input_tokens']}, "
                    f"cache_create={row['cache_creation_input_tokens']}, "
                    f"cache_read={row['cache_read_input_tokens']}, "
                    f"output={row['output_tokens']}, "
                    f"stop_reason={row['stop_reason']}"
                )
            except Exception as e:
                print(f"  [{i+1:2d}/{ITERATIONS}] FAILED — {e}")
                traceback.print_exc()
                model_results.append({"iteration": i + 1, "error": str(e)})

        results[model] = model_results

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY (no cache)")
    print(f"{'='*80}")
    for model, rows in results.items():
        print(f"\n  Model: {model}")
        print(f"  {'Iter':>4}  {'Input':>8}  {'CacheCreate':>12}  {'CacheRead':>10}  {'Output':>8}  {'Stop Reason':<15}")
        print(f"  {'----':>4}  {'-----':>8}  {'-----------':>12}  {'----------':>10}  {'------':>8}  {'-----------':<15}")
        for r in rows:
            if "error" in r:
                print(f"  {r['iteration']:4d}  {'ERROR':>8}  {'':>12}  {'':>10}  {'':>8}  {r['error']}")
            else:
                print(
                    f"  {r['iteration']:4d}  {r['input_tokens']:8d}  "
                    f"{r['cache_creation_input_tokens']:12d}  "
                    f"{r['cache_read_input_tokens']:10d}  "
                    f"{r['output_tokens']:8d}  {r['stop_reason']:<15}"
                )

    out_file = "refusal_test_nocache_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nRaw results saved to: {out_file}")


if __name__ == "__main__":
    main()
