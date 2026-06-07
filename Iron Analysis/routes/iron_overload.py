from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

import os
import shutil

from services.iron_overload_service import (
    IronOverloadService
)

router = APIRouter(
    prefix="/iron-overload",
    tags=["Iron Overload Analysis"]
)

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@router.post("/analyze/text")
async def analyze_text(
    text: str
):

    try:

        result = (
            IronOverloadService.analyze_text(
                text
            )
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/analyze/pdf")
async def analyze_pdf(
    file: UploadFile = File(...)
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

        result = (
            IronOverloadService.analyze_pdf(
                file_path
            )
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/analyze/image")
async def analyze_image(
    file: UploadFile = File(...)
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

        result = (
            IronOverloadService.analyze_image(
                file_path
            )
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
