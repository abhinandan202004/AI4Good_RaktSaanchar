import httpx
import logging
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from app.core.config import settings
from app.core.dependencies import require_patient
from app.modules.iron_overload.schemas import IronOverloadResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/iron-overload",
    tags=["Iron Overload Analysis"]
)


@router.post("/analyze/text", response_model=IronOverloadResponse)
async def analyze_text(
    text: str,
    current_user=Depends(require_patient)
):
    try:
        resp = httpx.post(
            f"{settings.ML_SERVICE_URL}/analyze/text",
            params={"text": text},
            timeout=30.0
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=resp.text
            )
        return resp.json()
    except Exception as e:
        logger.error("MRI Text analysis forward failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze text via ML service: {str(e)}"
        )


@router.post("/analyze/pdf", response_model=IronOverloadResponse)
async def analyze_pdf(
    file: UploadFile = File(...),
    current_user=Depends(require_patient)
):
    try:
        # Read file contents and prepare file upload dictionary
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        
        resp = httpx.post(
            f"{settings.ML_SERVICE_URL}/analyze/pdf",
            files=files,
            timeout=30.0
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=resp.text
            )
        return resp.json()
    except Exception as e:
        logger.error("MRI PDF analysis forward failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze PDF via ML service: {str(e)}"
        )


@router.post("/analyze/image", response_model=IronOverloadResponse)
async def analyze_image(
    file: UploadFile = File(...),
    current_user=Depends(require_patient)
):
    try:
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        
        resp = httpx.post(
            f"{settings.ML_SERVICE_URL}/analyze/image",
            files=files,
            timeout=30.0
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=resp.text
            )
        return resp.json()
    except Exception as e:
        logger.error("MRI Image analysis forward failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze image via ML service: {str(e)}"
        )
