from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

import os
import shutil

from app.core.dependencies import require_patient
from app.modules.iron_overload.service import IronOverloadService
from app.modules.iron_overload.schemas.response import IronOverloadResponse

router = APIRouter(
    prefix="/iron-overload",
    tags=["Iron Overload Analysis"]
)

UPLOAD_DIR = "/app/uploads/mri_reports"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@router.post("/analyze/text", response_model=IronOverloadResponse)
async def analyze_text(
    text: str,
    current_user=Depends(require_patient)
):
    try:
        result = IronOverloadService.analyze_text(text)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/analyze/pdf", response_model=IronOverloadResponse)
async def analyze_pdf(
    file: UploadFile = File(...),
    current_user=Depends(require_patient)
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

        result = IronOverloadService.analyze_pdf(file_path)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/analyze/image", response_model=IronOverloadResponse)
async def analyze_image(
    file: UploadFile = File(...),
    current_user=Depends(require_patient)
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

        result = IronOverloadService.analyze_image(file_path)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
