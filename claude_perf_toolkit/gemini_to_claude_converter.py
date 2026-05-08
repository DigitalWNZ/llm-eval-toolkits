#!/usr/bin/env python3
"""
Gemini to Claude API Request Converter

This script converts API requests from Gemini's format to Claude's format.
It is the reverse of claude_to_gemini_converter.py.

1. Message Conversion

  - Roles mapping:
    - user -> user (same)
    - model -> assistant
  - Content structure:
    - Gemini: {"role": "...", "parts": [{"text": "..."}]}
    - Claude: {"role": "...", "content": "..."}

  2. System Instructions

  - Gemini format:
  {
    "systemInstruction": {
      "parts": [{"text": "system message content"}]
    }
  }
  - Claude format: Message with role: "system" in messages array
  {
    "role": "system",
    "content": "system message content"
  }

  3. Function Calls (from model)

  - Gemini format:
  {
    "role": "model",
    "parts": [{
      "functionCall": {
        "name": "...",
        "args": {...}
      }
    }]
  }
  - Claude format:
  {
    "role": "assistant",
    "content": [
      {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
    ]
  }
    - args -> input
    - functionCall -> tool_use

  4. Function Responses

  - Gemini format:
  {
    "role": "user",
    "parts": [{
      "functionResponse": {
        "name": "function_name",
        "response": {
          "result": "..."
        }
      }
    }]
  }
  - Claude format:
  {
    "role": "user",
    "content": [
      {"type": "tool_result", "tool_use_id": "...", "content": "..."}
    ]
  }

  5. Tools/Functions Definition

  - Gemini format:
  {
    "tools": [{
      "functionDeclarations": [{
        "name": "...",
        "description": "...",
        "parameters": {...}
      }]
    }]
  }
  - Claude format:
  {
    "name": "...",
    "description": "...",
    "input_schema": {...}
  }

  6. Request Structure

  - Gemini: {"contents": [...], "systemInstruction": {...}, "tools": [...]}
  - Claude: {"messages": [...], "tools": [...]}
    - contents -> messages
    - systemInstruction -> system message prepended to messages
    - functionDeclarations -> tools with input_schema
"""

import json
import os
import glob
import copy
import re
import uuid
from typing import Dict, List, Any, Optional


class GeminiToClaudeConverter:
    """Converts Gemini API requests to Claude API format."""

    # Model mapping from Gemini to Claude
    MODEL_MAPPING = {
        "gemini-1.5-pro": "claude-3-5-sonnet-20241022",
        "gemini-1.5-flash": "claude-3-5-haiku-20241022",
        "gemini-2.0-flash": "claude-3-5-sonnet-20241022",
        "gemini-2.5-flash": "claude-3-5-sonnet-20241022",
        "gemini-2.5-pro": "claude-3-5-sonnet-20241022",
    }

    def __init__(self):
        """Initialize the converter."""
        self._tool_call_counter = 0

    def _generate_tool_use_id(self) -> str:
        """Generate a unique tool_use_id in Claude's format."""
        self._tool_call_counter += 1
        short_id = uuid.uuid4().hex[:24]
        return f"toolu_bdrk_{short_id}"

    def _find_matching_tool_use_id(self, function_name: str, previous_messages: List[Dict[str, Any]]) -> str:
        """
        Find the tool_use_id from the most recent assistant message
        that made a function call with the given name.

        Args:
            function_name: The function name to look for
            previous_messages: Messages processed so far

        Returns:
            The matching tool_use_id, or a generated one if not found
        """
        # Search backwards through previous messages for matching tool_use
        for msg in reversed(previous_messages):
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if (isinstance(block, dict) and
                        block.get("type") == "tool_use" and
                        block.get("name") == function_name):
                        return block["id"]

        # Fallback: generate a new id
        return self._generate_tool_use_id()

    def convert_messages(self, gemini_contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Gemini message format to Claude format.

        Gemini format: {"role": "user/model", "parts": [{"text": "text"}]}
        Claude format: {"role": "user/assistant", "content": "text"}
        """
        claude_messages = []

        for content in gemini_contents:
            role = content.get("role", "")
            parts = content.get("parts", [])

            if not parts:
                continue

            # Check what types of parts we have
            has_function_call = any("functionCall" in p for p in parts if isinstance(p, dict))
            has_function_response = any("functionResponse" in p for p in parts if isinstance(p, dict))
            has_text = any("text" in p for p in parts if isinstance(p, dict))
            has_inline_data = any("inline_data" in p or "inlineData" in p for p in parts if isinstance(p, dict))

            if has_function_call:
                # Convert functionCall -> tool_use (assistant message)
                claude_content = []
                for part in parts:
                    if isinstance(part, dict):
                        if "functionCall" in part:
                            fc = part["functionCall"]
                            tool_use_id = self._generate_tool_use_id()
                            claude_content.append({
                                "type": "tool_use",
                                "id": tool_use_id,
                                "name": fc.get("name", "unknown"),
                                "input": fc.get("args", {})
                            })
                        elif "text" in part and part["text"].strip():
                            claude_content.append({
                                "type": "text",
                                "text": part["text"]
                            })

                claude_messages.append({
                    "role": "assistant",
                    "content": claude_content
                })

            elif has_function_response:
                # Convert functionResponse -> tool_result (user message)
                claude_content = []
                for part in parts:
                    if isinstance(part, dict) and "functionResponse" in part:
                        fr = part["functionResponse"]
                        function_name = fr.get("name", "unknown")
                        response = fr.get("response", {})
                        result = response.get("result", "") if isinstance(response, dict) else str(response)

                        # Find the matching tool_use_id from previous assistant messages
                        tool_use_id = self._find_matching_tool_use_id(function_name, claude_messages)

                        claude_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result
                        })

                if claude_content:
                    # Use the first tool_use_id at the message level too
                    claude_messages.append({
                        "role": "user",
                        "tool_call_id": claude_content[0]["tool_use_id"],
                        "content": claude_content
                    })

            else:
                # Regular text / inline_data message
                gemini_role = role
                if gemini_role == "model":
                    claude_role = "assistant"
                elif gemini_role == "user":
                    claude_role = "user"
                else:
                    claude_role = "user"  # Default fallback

                # Check if content is simple (single text part)
                text_parts = [p for p in parts if isinstance(p, dict) and "text" in p]
                image_parts = [p for p in parts if isinstance(p, dict) and ("inline_data" in p or "inlineData" in p)]

                if len(text_parts) == 1 and not image_parts:
                    # Simple text message
                    claude_messages.append({
                        "role": claude_role,
                        "content": text_parts[0]["text"]
                    })
                else:
                    # Multi-part message
                    claude_content = []
                    for part in parts:
                        if isinstance(part, dict):
                            if "text" in part:
                                claude_content.append({
                                    "type": "text",
                                    "text": part["text"]
                                })
                            elif "inline_data" in part or "inlineData" in part:
                                inline = part.get("inline_data", part.get("inlineData", {}))
                                claude_content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": inline.get("mime_type", inline.get("mimeType", "image/jpeg")),
                                        "data": inline.get("data", "")
                                    }
                                })

                    if claude_content:
                        claude_messages.append({
                            "role": claude_role,
                            "content": claude_content
                        })

        return claude_messages

    def convert_tools(self, gemini_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Gemini function declarations to Claude tools format.

        Gemini format: functionDeclarations with name, description, parameters
        Claude format: tools with name, description, input_schema
        """
        if not gemini_tools:
            return []

        claude_tools = []
        for tool_group in gemini_tools:
            declarations = tool_group.get("functionDeclarations", [])
            for func in declarations:
                claude_tool = {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                }
                claude_tools.append(claude_tool)

        return claude_tools

    def convert_request(self, gemini_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a complete Gemini API request to Claude format.

        Args:
            gemini_request: Gemini API request dictionary

        Returns:
            Claude API request dictionary
        """
        # Reset tool call counter for each request
        self._tool_call_counter = 0

        # Extract fields
        contents = gemini_request.get("contents", [])
        system_instruction = gemini_request.get("systemInstruction", {})
        tools = gemini_request.get("tools", [])

        # Build messages list
        claude_messages = []

        # Add system message if present
        if system_instruction:
            system_parts = system_instruction.get("parts", [])
            if system_parts:
                system_text = "\n".join([
                    p.get("text", "") for p in system_parts
                    if isinstance(p, dict) and "text" in p
                ])
                if system_text:
                    claude_messages.append({
                        "role": "system",
                        "content": system_text
                    })

        # Convert content messages
        converted_messages = self.convert_messages(contents)
        claude_messages.extend(converted_messages)

        # Build Claude request
        claude_request = {
            "messages": claude_messages
        }

        # Convert and add tools if present
        if tools:
            claude_tools = self.convert_tools(tools)
            if claude_tools:
                claude_request["tools"] = claude_tools

        return claude_request

    def convert_from_json(self, gemini_json: str) -> str:
        """
        Convert Gemini request from JSON string to Claude JSON string.

        Args:
            gemini_json: Gemini API request as JSON string

        Returns:
            Claude API request as JSON string
        """
        gemini_request = json.loads(gemini_json)
        claude_request = self.convert_request(gemini_request)
        return json.dumps(claude_request, indent=2)

    def process_folder(self, input_folder: str, output_folder: str = None):
        """
        Process all JSON files in the input folder and write converted files.

        Args:
            input_folder: Path to the folder containing Gemini request JSON files
            output_folder: Path to the output folder (defaults to input_claude)
        """
        if output_folder is None:
            parent_dir = os.path.dirname(input_folder)
            output_folder = os.path.join(parent_dir, "input_claude")

        # Find all JSON files recursively
        json_files = glob.glob(os.path.join(input_folder, "**/*.json"), recursive=True)

        print(f"Found {len(json_files)} JSON files to process")

        successful = 0
        failed = 0

        for json_file in json_files:
            try:
                # Read the Gemini request
                with open(json_file, 'r', encoding='utf-8') as f:
                    gemini_request = json.load(f)

                # Convert to Claude format
                claude_request = self.convert_request(gemini_request)

                # Create output file path
                relative_path = os.path.relpath(json_file, input_folder)
                output_file = os.path.join(output_folder, relative_path)

                # Add _claude suffix to filename
                base_name = os.path.basename(output_file)
                dir_name = os.path.dirname(output_file)
                name_without_ext = os.path.splitext(base_name)[0]
                # Remove _gemini suffix if present before adding _claude
                name_without_ext = re.sub(r'_gemini$', '', name_without_ext)
                output_file = os.path.join(dir_name, f"{name_without_ext}_claude.json")

                # Create output directory if needed
                output_dir = os.path.dirname(output_file)
                os.makedirs(output_dir, exist_ok=True)

                # Write the converted request
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(claude_request, f, indent=2, ensure_ascii=False)

                print(f"  Converted: {relative_path} -> {os.path.relpath(output_file, output_folder)}")
                successful += 1

            except Exception as e:
                print(f"  Failed to convert {json_file}: {str(e)}")
                failed += 1

        print(f"\nConversion complete: {successful} successful, {failed} failed")
        print(f"Output folder: {output_folder}")


def main():
    """Process all JSON files in the agentic_data_demo/input_gemini folder."""
    input_folder = "agentic_data_demo/input_gemini"

    # Check if input folder exists
    if not os.path.exists(input_folder):
        print(f"Error: Input folder '{input_folder}' not found!")
        print("Please make sure you're running the script from the correct directory.")
        return

    # Create converter instance
    converter = GeminiToClaudeConverter()

    # Process all files in the folder
    converter.process_folder(input_folder)

    # Example of converting a single file
    print("\n" + "="*50 + "\n")
    print("Example of single file conversion:")

    output_folder = "agentic_data_demo/input_claude"
    sample_files = glob.glob(os.path.join(output_folder, "**/*_claude.json"), recursive=True)
    if sample_files:
        sample_file = sample_files[0]
        print(f"\nConverted sample file: {sample_file}")

        with open(sample_file, 'r', encoding='utf-8') as f:
            claude_request = json.load(f)

        # Print summary instead of full content (can be very large)
        msg_count = len(claude_request.get("messages", []))
        tool_count = len(claude_request.get("tools", []))
        print(f"\nClaude Request Summary: {msg_count} messages, {tool_count} tools")


if __name__ == "__main__":
    main()
