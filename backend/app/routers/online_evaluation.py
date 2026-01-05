from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
import json
import logging
from ..models.schemas import OnlineEvaluationRequest, OnlineEvaluationResponse
from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/online", tags=["online-evaluation"])
gemini_service = GeminiService()


@router.post("/evaluate", response_model=OnlineEvaluationResponse)
async def evaluate_online(request: OnlineEvaluationRequest):
    """
    Execute online evaluation with single or multiple iterations
    """
    try:
        # Convert string to proper Gemini request format if needed
        gemini_request = request.gemini_request

        if isinstance(gemini_request, str):
            # Wrap string in proper Gemini request format
            gemini_request = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": gemini_request}]
                    }
                ]
            }

        responses = []

        for i in range(request.iterations):
            try:
                response = await gemini_service.generate_content(
                    request=gemini_request,
                    model_name=request.model,
                    project=request.project,
                    system_instruction=request.system_instruction,
                    config_override=request.gemini_config,
                    multimodal_files=request.multimodal_files
                )
                # Add iteration metadata
                response["iteration"] = i + 1
                response["model"] = request.model
                responses.append(response)
            except Exception as e:
                logger.error(f"Error in iteration {i+1}: {e}")
                responses.append({
                    "error": str(e),
                    "iteration": i + 1,
                    "model": request.model
                })

        return OnlineEvaluationResponse(
            responses=responses,
            success=True,
            message=f"Completed {len(responses)} iterations"
        )

    except Exception as e:
        logger.error(f"Error in online evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-multimodal")
async def upload_multimodal(files: List[UploadFile] = File(...)):
    """
    Upload multimodal files and return base64 encoded data
    """
    try:
        file_data = []

        for file in files:
            content = await file.read()
            import base64
            encoded = base64.b64encode(content).decode('utf-8')

            file_data.append({
                "filename": file.filename,
                "mime_type": file.content_type,
                "data": encoded,
                "size": len(content)
            })

        return {
            "success": True,
            "files": file_data
        }

    except Exception as e:
        logger.error(f"Error uploading multimodal files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
