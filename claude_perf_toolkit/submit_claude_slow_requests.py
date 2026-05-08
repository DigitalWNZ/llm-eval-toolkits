#!/usr/bin/env python3
"""
Submit converted Claude requests to multiple Claude models on Vertex AI.
"""

import json
import os
import time
import traceback
from anthropic import AnthropicVertex

PROJECT_ID = "cloud-llm-preview1"
REGION = "global"
MAX_TOKENS = 4096

MODELS = [
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
]

REQUEST_FILES = [
    os.path.expanduser("~/slow_request_40s_claude.json"),
    os.path.expanduser("~/slow_request_60s_claude.json"),
]

OUTPUT_DIR = os.path.expanduser("~/claude_perf_results")


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


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    client = AnthropicVertex(project_id=PROJECT_ID, region=REGION)
    print(f"Connected to Vertex AI (project={PROJECT_ID}, region={REGION})")

    results = []

    for model in MODELS:
        for request_file in REQUEST_FILES:
            request_name = os.path.basename(request_file).replace("_claude.json", "")
            print(f"\n{'='*80}")
            print(f"Model: {model}")
            print(f"Request: {request_name}")
            print(f"{'='*80}")

            try:
                with open(request_file, 'r', encoding='utf-8') as f:
                    raw_request = json.load(f)

                api_kwargs = prepare_request(raw_request, model)

                msg_count = len(api_kwargs["messages"])
                tool_count = len(api_kwargs.get("tools", []))
                has_system = "system" in api_kwargs
                print(f"  Messages: {msg_count}, Tools: {tool_count}, System: {has_system}")

                start_time = time.time()
                response = client.messages.create(**api_kwargs)
                elapsed = time.time() - start_time

                response_dict = json.loads(response.model_dump_json())

                input_tokens = response_dict.get("usage", {}).get("input_tokens", 0)
                output_tokens = response_dict.get("usage", {}).get("output_tokens", 0)
                stop_reason = response_dict.get("stop_reason", "N/A")

                print(f"  Status: SUCCESS ({elapsed:.1f}s)")
                print(f"  Stop reason: {stop_reason}")
                print(f"  Usage: input={input_tokens}, output={output_tokens}")
                print(f"  TTFT: ~{elapsed*1000:.0f}ms (total response time)")

                for block in response_dict.get("content", []):
                    if block.get("type") == "text":
                        preview = block["text"][:150].replace("\n", " ")
                        print(f"  Response preview: {preview}...")
                    elif block.get("type") == "tool_use":
                        print(f"  Tool call: {block.get('name', '?')}")

                model_safe = model.replace("@", "_")
                output_file = os.path.join(OUTPUT_DIR, f"{model_safe}_{request_name}_response.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(response_dict, f, indent=2, ensure_ascii=False)
                print(f"  Saved to: {output_file}")

                results.append({
                    "model": model,
                    "request": request_name,
                    "status": "success",
                    "elapsed_s": round(elapsed, 2),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "stop_reason": stop_reason,
                })

            except Exception as e:
                print(f"  Status: FAILED")
                print(f"  Error: {str(e)}")
                traceback.print_exc()
                results.append({
                    "model": model,
                    "request": request_name,
                    "status": "failed",
                    "error": str(e),
                })

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"Total: {success} successful, {failed} failed out of {len(results)}\n")

    for r in results:
        if r["status"] == "success":
            print(f"  [OK]   {r['model']} + {r['request']} ({r['elapsed_s']}s, {r['input_tokens']}+{r['output_tokens']} tokens)")
        else:
            print(f"  [FAIL] {r['model']} + {r['request']} - {r['error'][:80]}")

    summary_file = os.path.join(OUTPUT_DIR, "submission_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    main()
