#!/usr/bin/env python3
"""
Submit converted Claude requests to Claude on Vertex AI.

Picks 5 requests from input_claude folder and submits them to
Claude Opus on Vertex AI, saving responses to output_claude folder.
"""

import json
import os
import glob
import time
import traceback
from anthropic import AnthropicVertex

# Configuration
PROJECT_ID = "cloud-llm-preview1"
REGION = "global"
MODEL = "claude-opus-4@20250514"
MAX_TOKENS = 4096

INPUT_FOLDER = "agentic_data_demo/input_claude"
OUTPUT_FOLDER = "agentic_data_demo/output_claude"


def prepare_request(raw_request: dict) -> dict:
    """
    Prepare a converted Claude request for the Vertex AI Messages API.

    - Extracts system messages from messages array into top-level `system` param
    - Removes non-standard fields like `tool_call_id` from messages
    - Ensures message format is compatible with the Claude API
    """
    messages = raw_request.get("messages", [])
    tools = raw_request.get("tools", [])

    # Separate system messages from conversation messages
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
            # Clean the message: remove non-standard fields
            clean_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            conversation_messages.append(clean_msg)

    # Build the API request kwargs
    api_kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": conversation_messages,
    }

    # Add system prompt if present
    if system_parts:
        api_kwargs["system"] = "\n".join(system_parts)

    # Add tools if present
    if tools:
        api_kwargs["tools"] = tools

    return api_kwargs


def select_files(input_folder: str, count: int = 5) -> list:
    """Select `count` files from distinct trace folders, preferring step_0 files."""
    all_files = sorted(glob.glob(os.path.join(input_folder, "**/*_claude.json"), recursive=True))

    # Group by trace folder
    folders = {}
    for f in all_files:
        folder = os.path.dirname(f)
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(f)

    selected = []
    for folder, files in folders.items():
        # Prefer step_0 (simplest, fewest messages)
        step_0 = [f for f in files if "step_0" in os.path.basename(f)]
        if step_0:
            selected.append(step_0[0])
        else:
            selected.append(files[0])

        if len(selected) >= count:
            break

    return selected[:count]


def main():
    """Submit 5 Claude requests to Vertex AI."""
    # Check input folder exists
    if not os.path.exists(INPUT_FOLDER):
        print(f"Error: Input folder '{INPUT_FOLDER}' not found!")
        return

    # Select 5 files
    files = select_files(INPUT_FOLDER, count=5)
    print(f"Selected {len(files)} files to submit:\n")
    for f in files:
        print(f"  {os.path.relpath(f, INPUT_FOLDER)}")
    print()

    # Create output folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Initialize Vertex AI client
    print(f"Connecting to Vertex AI (project={PROJECT_ID}, region={REGION})...")
    client = AnthropicVertex(project_id=PROJECT_ID, region=REGION)

    results = {"successful": 0, "failed": 0, "details": []}

    for i, filepath in enumerate(files):
        relative = os.path.relpath(filepath, INPUT_FOLDER)
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(files)}] Submitting: {relative}")
        print(f"{'='*60}")

        try:
            # Load the request
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_request = json.load(f)

            # Prepare for API
            api_kwargs = prepare_request(raw_request)

            msg_count = len(api_kwargs["messages"])
            tool_count = len(api_kwargs.get("tools", []))
            has_system = "system" in api_kwargs
            print(f"  Messages: {msg_count}, Tools: {tool_count}, Has system: {has_system}")

            # Submit to Vertex AI
            start_time = time.time()
            response = client.messages.create(**api_kwargs)
            elapsed = time.time() - start_time

            # Convert response to dict
            response_dict = json.loads(response.model_dump_json())

            print(f"  Status: SUCCESS ({elapsed:.1f}s)")
            print(f"  Stop reason: {response_dict.get('stop_reason', 'N/A')}")
            print(f"  Usage: input={response_dict.get('usage', {}).get('input_tokens', '?')}, "
                  f"output={response_dict.get('usage', {}).get('output_tokens', '?')}")

            # Preview response content
            for block in response_dict.get("content", []):
                if block.get("type") == "text":
                    preview = block["text"][:150].replace("\n", " ")
                    print(f"  Response preview: {preview}...")
                elif block.get("type") == "tool_use":
                    print(f"  Tool call: {block.get('name', '?')}({json.dumps(block.get('input', {}))[:100]}...)")

            # Save response
            trace_folder = os.path.basename(os.path.dirname(filepath))
            step_name = os.path.basename(filepath).replace("_claude.json", "")
            output_dir = os.path.join(OUTPUT_FOLDER, trace_folder)
            os.makedirs(output_dir, exist_ok=True)

            output_file = os.path.join(output_dir, f"{step_name}_response.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(response_dict, f, indent=2, ensure_ascii=False)

            print(f"  Saved to: {os.path.relpath(output_file)}")
            results["successful"] += 1
            results["details"].append({
                "file": relative,
                "status": "success",
                "elapsed": elapsed,
                "stop_reason": response_dict.get("stop_reason"),
                "input_tokens": response_dict.get("usage", {}).get("input_tokens"),
                "output_tokens": response_dict.get("usage", {}).get("output_tokens"),
            })

        except Exception as e:
            print(f"  Status: FAILED")
            print(f"  Error: {str(e)}")
            traceback.print_exc()
            results["failed"] += 1
            results["details"].append({
                "file": relative,
                "status": "failed",
                "error": str(e),
            })

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {results['successful']} successful, {results['failed']} failed out of {len(files)}")
    print(f"{'='*60}")

    for detail in results["details"]:
        status_icon = "OK" if detail["status"] == "success" else "FAIL"
        line = f"  [{status_icon}] {detail['file']}"
        if detail["status"] == "success":
            line += f" ({detail['elapsed']:.1f}s, {detail['input_tokens']}+{detail['output_tokens']} tokens)"
        else:
            line += f" - {detail['error'][:80]}"
        print(line)

    # Save summary
    summary_file = os.path.join(OUTPUT_FOLDER, "submission_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    main()
