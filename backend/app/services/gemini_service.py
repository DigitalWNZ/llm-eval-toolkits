import os
import time
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        """Initialize Gemini service with Application Default Credentials"""
        self.client = None
        self.default_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        logger.info(f"Initialized with project: {self.default_project}")

    def _get_client(self, project: str) -> genai.Client:
        """Get or create a Gemini client for the specified project"""
        try:
            # Create client with project
            client = genai.Client(
                vertexai=True,
                project=project,
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            )
            return client
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            raise

    def _merge_request(
        self,
        base_request: Dict[str, Any],
        system_instruction: Optional[str],
        config_override: Optional[Dict[str, Any]],
        multimodal_files: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Merge system instruction, config, and multimodal files into request"""
        request = base_request.copy()

        # Handle system instruction
        if system_instruction is not None:
            request["system_instruction"] = system_instruction

        # Handle config override
        if config_override:
            if "generation_config" not in request:
                request["generation_config"] = {}
            request["generation_config"].update(config_override)

        # Handle multimodal files
        if multimodal_files:
            if "contents" not in request:
                request["contents"] = []

            # Add multimodal content to the contents array
            for file_data in multimodal_files:
                mime_type = file_data.get("mime_type")
                data = file_data.get("data")

                # Decode base64 string to bytes if needed
                if isinstance(data, str):
                    # Remove data URL prefix if present (e.g., "data:image/png;base64,")
                    if data.startswith("data:"):
                        data = data.split(",", 1)[1]
                    data = base64.b64decode(data)

                # Create inline data part
                part = types.Part.from_bytes(
                    data=data,
                    mime_type=mime_type
                )

                # Add to first content entry or create new one
                if request["contents"]:
                    if "parts" not in request["contents"][0]:
                        request["contents"][0]["parts"] = []
                    request["contents"][0]["parts"].append(part)
                else:
                    request["contents"].append({
                        "role": "user",
                        "parts": [part]
                    })

        return request

    async def generate_content(
        self,
        request: Dict[str, Any],
        model_name: str,
        project: str,
        system_instruction: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        multimodal_files: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate content using Gemini API"""
        try:
            client = self._get_client(project)

            # Merge request components
            final_request = self._merge_request(
                request, system_instruction, config_override, multimodal_files
            )

            # Extract contents and configuration
            contents = final_request.get("contents", [])
            generation_config = final_request.get("generation_config", {})
            system_inst = final_request.get("system_instruction")

            # Build config with camelCase parameters for latest google-genai
            config = types.GenerateContentConfig(
                temperature=generation_config.get("temperature"),
                topP=generation_config.get("top_p"),
                topK=generation_config.get("top_k"),
                maxOutputTokens=generation_config.get("max_output_tokens"),
                systemInstruction=system_inst
            )

            # Generate content
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )

            # Convert response to dict with proper None handling
            usage_metadata = getattr(response, "usage_metadata", None)

            result = {
                "text": response.text if hasattr(response, "text") else "",
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": part.text} for part in candidate.content.parts if hasattr(part, "text")],
                            "role": candidate.content.role
                        },
                        "finish_reason": candidate.finish_reason,
                        "safety_ratings": [
                            {
                                "category": rating.category,
                                "probability": rating.probability
                            }
                            for rating in candidate.safety_ratings
                        ] if hasattr(candidate, "safety_ratings") and candidate.safety_ratings else []
                    }
                    for candidate in response.candidates
                ] if hasattr(response, "candidates") and response.candidates else [],
                "usage_metadata": {
                    "prompt_token_count": getattr(usage_metadata, "prompt_token_count", 0) or 0,
                    "candidates_token_count": getattr(usage_metadata, "candidates_token_count", 0) or 0,
                    "total_token_count": getattr(usage_metadata, "total_token_count", 0) or 0,
                }
            }

            return result

        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise

    async def benchmark_request(
        self,
        model_name: str,
        request_size: int,
        thinking_level: Optional[str],
        thinking_budget: Optional[int],
        cache_enabled: bool,
        project: str
    ) -> Dict[str, Any]:
        """Execute a single benchmark request and return metrics

        Note: cache_enabled is reserved for future use with cachedContent parameter
        """
        try:
            client = self._get_client(project)

            # Load benchmark request from file
            request_data = self._load_benchmark_request(request_size)

            # Extract contents and existing config
            contents = request_data.get("contents", [])
            existing_config = request_data.get("generation_config", {})
            system_instruction = request_data.get("system_instruction")

            # Build thinking config if needed
            thinking_config = None
            if thinking_level or thinking_budget:
                thinking_config_params = {}

                # Convert thinking level string to enum
                if thinking_level:
                    level_map = {
                        "minimal": types.ThinkingLevel.MINIMAL,
                        "low": types.ThinkingLevel.LOW,
                        "medium": types.ThinkingLevel.MEDIUM,
                        "high": types.ThinkingLevel.HIGH
                    }
                    thinking_config_params["thinkingLevel"] = level_map.get(
                        thinking_level.lower(),
                        types.ThinkingLevel.MEDIUM
                    )

                if thinking_budget:
                    thinking_config_params["thinkingBudget"] = thinking_budget

                thinking_config = types.ThinkingConfig(**thinking_config_params)

            # Build generation config with camelCase parameters
            config = types.GenerateContentConfig(
                temperature=existing_config.get("temperature"),
                topP=existing_config.get("top_p"),
                topK=existing_config.get("top_k"),
                maxOutputTokens=existing_config.get("max_output_tokens"),
                systemInstruction=system_instruction,
                thinkingConfig=thinking_config
            )

            # Measure TTFT using streaming mode
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

            # Extract metrics with proper None handling
            metrics = {
                "ttft_ms": ttft,
                "input_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
                "cached_tokens": getattr(usage_metadata, "cached_content_token_count", 0) or 0,
            }

            return metrics

        except Exception as e:
            logger.error(f"Error in benchmark: {e}")
            raise

    def _load_benchmark_request(self, request_size: int) -> Dict[str, Any]:
        """Load benchmark request from file based on request size"""
        # Map request size to file name
        size_to_file = {
            1000: "request_1k.json",
            2000: "request_2k.json",
            5000: "request_5k.json",
            10000: "request_10k.json",
            50000: "request_50k.json",
            100000: "request_100k.json"
        }

        # Find the closest matching file
        filename = size_to_file.get(request_size)
        if not filename:
            # Find closest size
            available_sizes = sorted(size_to_file.keys())
            closest_size = min(available_sizes, key=lambda x: abs(x - request_size))
            filename = size_to_file[closest_size]
            logger.warning(
                f"Request size {request_size} not found, using closest size {closest_size}"
            )

        # Load the benchmark request file
        benchmark_dir = Path(__file__).parent.parent.parent / "benchmark"
        file_path = benchmark_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Benchmark request file not found: {file_path}"
            )

        with open(file_path, 'r') as f:
            request_data = json.load(f)

        return request_data

    async def evaluate_outputs(
        self,
        expected_output: Dict[str, Any],
        actual_outputs: List[Dict[str, Any]],
        model_name: str,
        project: str,
        pass_threshold: int = 75
    ) -> Dict[str, Any]:
        """Evaluate similarity between expected and actual outputs using Gemini

        Args:
            expected_output: Expected output JSON
            actual_outputs: List of actual output JSONs (one per iteration)
            model_name: Gemini model to use for evaluation
            project: GCP project ID
            pass_threshold: Similarity score threshold for pass/fail

        Returns:
            Evaluation result with scores and analysis
        """
        try:
            client = self._get_client(project)

            # Load evaluation system instruction
            instruction_path = Path(__file__).parent.parent.parent / "evaluation_system_instruction.md"
            with open(instruction_path, 'r') as f:
                system_instruction = f.read()

            # Construct evaluation prompt
            evaluation_prompt = f"""You are evaluating LLM outputs. Please compare the expected output with each actual output provided.

**Expected Output:**
```json
{json.dumps(expected_output, indent=2)}
```

**Actual Outputs (Multiple Iterations):**
"""
            for i, actual in enumerate(actual_outputs, 1):
                evaluation_prompt += f"""
**Iteration {i}:**
```json
{json.dumps(actual, indent=2)}
```
"""

            evaluation_prompt += f"""

**Pass Threshold:** {pass_threshold}%

Please evaluate each iteration separately and provide your analysis in the specified JSON format."""

            # Build config
            config = types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent evaluation
                systemInstruction=system_instruction
            )

            # Generate evaluation
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[{"role": "user", "parts": [{"text": evaluation_prompt}]}],
                config=config
            )

            # Extract and parse JSON from response
            response_text = response.text if hasattr(response, "text") else ""

            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # Parse evaluation result
            evaluation_result = json.loads(response_text)

            return evaluation_result

        except Exception as e:
            logger.error(f"Error in output evaluation: {e}")
            raise
