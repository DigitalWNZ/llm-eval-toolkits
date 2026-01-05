from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
import os
from pathlib import Path
from datetime import datetime
import logging
from ..models.schemas import (
    BatchEvaluationRequest,
    BatchMappingResponse,
    BatchSubmitResponse,
    FileMapping,
    EvaluateResultsRequest,
    EvaluateResultsResponse,
    EvaluationResult,
    EvaluationDimensionScores,
    EvaluationDifference
)
from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/batch", tags=["batch-evaluation"])
gemini_service = GeminiService()


def scan_files(folder: str, max_files: int = 10) -> List[str]:
    """Scan folder for JSON files, respecting max file limit"""
    files = []
    folder_path = Path(folder)

    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder}")

    for file_path in folder_path.rglob("*.json"):
        if len(files) >= max_files:
            break
        files.append(str(file_path.relative_to(folder_path)))

    return sorted(files)


def create_file_mapping(
    input_folder: str,
    expected_folder: str,
    output_folder: str,
    iterations: int
) -> List[FileMapping]:
    """Create file mappings between input, expected, and output files"""
    mappings = []

    # Scan input files
    input_files = scan_files(input_folder, max_files=10)

    for input_file in input_files:
        # Check for expected output
        expected_path = Path(expected_folder) / input_file
        has_expected = expected_path.exists()

        # Generate output file paths
        output_files = []
        base_name = Path(input_file).stem
        parent_dir = Path(input_file).parent
        output_dir = Path(output_folder) / parent_dir

        for i in range(1, iterations + 1):
            output_file = output_dir / f"{base_name}_{i}.json"
            output_files.append(str(output_file))

        mappings.append(FileMapping(
            input_request=input_file,
            expected_output=str(expected_path.relative_to(expected_folder)) if has_expected else None,
            output_files=output_files,
            has_expected=has_expected
        ))

    return mappings


@router.post("/mapping", response_model=BatchMappingResponse)
async def get_batch_mapping(request: BatchEvaluationRequest):
    """
    Generate file mappings for batch evaluation
    """
    try:
        # Set output folder if not specified
        output_folder = request.output_folder
        if not output_folder:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = f"{request.input_folder}_output_{timestamp}"

        # Create mappings
        mappings = create_file_mapping(
            request.input_folder,
            request.expected_folder,
            output_folder,
            request.iterations
        )

        return BatchMappingResponse(
            mappings=mappings,
            total_files=len(mappings),
            success=True,
            message=f"Found {len(mappings)} files to process"
        )

    except Exception as e:
        logger.error(f"Error creating batch mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview")
async def preview_file(folder: str, file: str):
    """
    Preview a file from the input folder
    """
    try:
        # Handle both absolute and relative paths
        if folder:
            file_path = Path(folder) / file
            # Security check: ensure file is within the specified folder
            try:
                file_path.resolve().relative_to(Path(folder).resolve())
            except ValueError:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            # If folder is empty, file should be an absolute or relative path
            file_path = Path(file)
            # Security check: ensure it's not trying to access sensitive areas
            resolved_path = file_path.resolve()
            # Don't allow access to parent directories outside the project
            if '..' in str(file_path):
                raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Read and return JSON content
        with open(file_path, 'r') as f:
            content = json.load(f)

        return content

    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit", response_model=BatchSubmitResponse)
async def submit_batch(request: BatchEvaluationRequest):
    """
    Submit batch evaluation requests and save responses
    """
    try:
        # Set output folder if not specified
        output_folder = request.output_folder
        if not output_folder:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = f"{request.input_folder}_output_{timestamp}"

        # Create output folder
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        # Get mappings
        mappings = create_file_mapping(
            request.input_folder,
            request.expected_folder,
            output_folder,
            request.iterations
        )

        successful = 0
        failed = 0

        # Process each file
        for mapping in mappings:
            input_path = Path(request.input_folder) / mapping.input_request

            try:
                # Read input request
                with open(input_path, 'r') as f:
                    gemini_request = json.load(f)

                # Process iterations
                for i in range(request.iterations):
                    try:
                        # Generate content
                        response = await gemini_service.generate_content(
                            request=gemini_request,
                            model_name=request.model,
                            project=request.project,
                            config_override=request.gemini_config
                        )

                        # Save response
                        output_path = Path(mapping.output_files[i])
                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        with open(output_path, 'w') as f:
                            json.dump(response, f, indent=2)

                        successful += 1

                    except Exception as e:
                        logger.error(f"Error processing {mapping.input_request} iteration {i+1}: {e}")

                        # Save error to output file
                        error_data = {
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                            "input_file": mapping.input_request,
                            "iteration": i + 1
                        }

                        output_path = Path(mapping.output_files[i])
                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        with open(output_path, 'w') as f:
                            json.dump(error_data, f, indent=2)

                        failed += 1

            except Exception as e:
                logger.error(f"Error reading {mapping.input_request}: {e}")
                failed += request.iterations

        return BatchSubmitResponse(
            success=True,
            total_processed=len(mappings) * request.iterations,
            successful=successful,
            failed=failed,
            output_folder=output_folder,
            message=f"Processed {successful} successful, {failed} failed"
        )

    except Exception as e:
        logger.error(f"Error in batch submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate", response_model=EvaluateResultsResponse)
async def evaluate_results(request: EvaluateResultsRequest):
    """
    Evaluate batch results by comparing expected outputs with actual outputs
    """
    try:
        evaluation_results = []

        # Scan output folder for generated files
        output_path = Path(request.output_folder)
        if not output_path.exists():
            raise HTTPException(status_code=404, detail=f"Output folder does not exist: {request.output_folder}")

        # Group output files by base name (without iteration suffix)
        output_files_by_base = {}
        for output_file in output_path.rglob("*.json"):
            # Extract base name by removing _N.json suffix
            relative_path = output_file.relative_to(output_path)
            file_name = relative_path.stem
            parent_dir = relative_path.parent

            # Check if filename ends with _N pattern
            if "_" in file_name:
                parts = file_name.rsplit("_", 1)
                if parts[1].isdigit():
                    base_name = parts[0]
                    iteration = int(parts[1])

                    # Construct key as parent_dir/base_name
                    key = str(parent_dir / base_name) if str(parent_dir) != "." else base_name

                    if key not in output_files_by_base:
                        output_files_by_base[key] = []
                    output_files_by_base[key].append({
                        "path": str(output_file),
                        "iteration": iteration,
                        "relative_path": str(relative_path)
                    })

        # Process each base file
        for base_key, output_files in output_files_by_base.items():
            # Sort by iteration number
            output_files.sort(key=lambda x: x["iteration"])

            # Construct input request path
            input_request_path = Path(request.input_folder) / f"{base_key}.json"

            # Construct expected output path
            expected_output_path = Path(request.expected_folder) / f"{base_key}.json"

            # Check if expected output exists
            if not expected_output_path.exists():
                logger.warning(f"No expected output for {base_key}, skipping evaluation")
                continue

            try:
                # Load expected output
                with open(expected_output_path, 'r') as f:
                    expected_output = json.load(f)

                # Load all actual outputs for this base file
                actual_outputs = []
                for output_file_info in output_files:
                    with open(output_file_info["path"], 'r') as f:
                        actual_output = json.load(f)
                        actual_outputs.append(actual_output)

                # Call Gemini for evaluation
                evaluation = await gemini_service.evaluate_outputs(
                    expected_output=expected_output,
                    actual_outputs=actual_outputs,
                    model_name=request.model,
                    project=request.project,
                    pass_threshold=request.pass_threshold
                )

                # Parse evaluation results for each iteration
                iteration_evaluations = evaluation.get("iteration_evaluations", [])

                for idx, iteration_eval in enumerate(iteration_evaluations):
                    if idx >= len(output_files):
                        break

                    output_file_info = output_files[idx]

                    # Extract dimension scores
                    dimension_scores = None
                    if "dimension_scores" in iteration_eval:
                        ds = iteration_eval["dimension_scores"]
                        dimension_scores = EvaluationDimensionScores(
                            semantic_similarity=ds.get("semantic_similarity", 0),
                            structural_consistency=ds.get("structural_consistency", 0),
                            key_information_preservation=ds.get("key_information_preservation", 0),
                            response_quality=ds.get("response_quality", 0)
                        )

                    # Extract key differences
                    key_differences = None
                    if "key_differences" in iteration_eval:
                        key_differences = [
                            EvaluationDifference(
                                category=diff.get("category", ""),
                                description=diff.get("description", ""),
                                severity=diff.get("severity", "minor"),
                                location=diff.get("location")
                            )
                            for diff in iteration_eval["key_differences"]
                        ]

                    # Create evaluation result
                    result = EvaluationResult(
                        input_request=f"{base_key}.json",
                        expected_output=f"{base_key}.json",
                        output_file=output_file_info["relative_path"],
                        similarity_score=iteration_eval.get("similarity_score", 0),
                        dimension_scores=dimension_scores,
                        key_differences=key_differences,
                        strengths=iteration_eval.get("strengths"),
                        overall_assessment=iteration_eval.get("overall_assessment")
                    )

                    evaluation_results.append(result)

            except Exception as e:
                logger.error(f"Error evaluating {base_key}: {e}")
                # Continue with next file
                continue

        return EvaluateResultsResponse(
            success=True,
            evaluation_results=evaluation_results,
            message=f"Evaluated {len(evaluation_results)} outputs"
        )

    except Exception as e:
        logger.error(f"Error in batch evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
