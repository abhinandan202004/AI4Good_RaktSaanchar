from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Header
)
from typing import Optional

import os
import shutil

from app.modules.iron_overload.service import IronOverloadService
from app.modules.iron_overload.schemas.response import IronOverloadResponse

router = APIRouter(
    prefix="/analyze",
    tags=["Iron Overload Analysis"]
)

# Use /tmp as upload dir to avoid permission denied issues in serverless runtimes
UPLOAD_DIR = "/tmp/mri_reports"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@router.post("/text", response_model=IronOverloadResponse)
async def analyze_text(
    text: str,
    x_mistral_api_key: Optional[str] = Header(None, alias="X-Mistral-API-Key")
):
    try:
        result = IronOverloadService.analyze_text(text, api_key=x_mistral_api_key)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/pdf", response_model=IronOverloadResponse)
async def analyze_pdf(
    file: UploadFile = File(...),
    x_mistral_api_key: Optional[str] = Header(None, alias="X-Mistral-API-Key")
):
    try:
        file_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        with open(
            file_path,
            "wb"
        ) as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        result = IronOverloadService.analyze_pdf(file_path, api_key=x_mistral_api_key)
        # Clean up local file after analysis
        if os.path.exists(file_path):
            os.remove(file_path)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/image", response_model=IronOverloadResponse)
async def analyze_image(
    file: UploadFile = File(...),
    x_mistral_api_key: Optional[str] = Header(None, alias="X-Mistral-API-Key")
):
    try:
        file_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        with open(
            file_path,
            "wb"
        ) as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        result = IronOverloadService.analyze_image(file_path, api_key=x_mistral_api_key)
        # Clean up local file after analysis
        if os.path.exists(file_path):
            os.remove(file_path)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

