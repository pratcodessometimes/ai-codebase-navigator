from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import zipfile

from app.services.repository_service import (
    extract_repository,
    get_repository_files,
)

router = APIRouter()

UPLOAD_DIR = Path("uploads")
EXTRACT_DIR = Path("extracted")

UPLOAD_DIR.mkdir(exist_ok=True)
EXTRACT_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_repository(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided"
        )

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are currently supported"
        )

    file_path = UPLOAD_DIR / file.filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    repository_name = Path(file.filename).stem
    repository_extract_path = EXTRACT_DIR / repository_name

    try:
        extract_repository(
            file_path,
            repository_extract_path
        )

        files = get_repository_files(
            repository_extract_path
        )

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Invalid ZIP file"
        )

    return {
        "message": "Repository uploaded and analyzed successfully",
        "repository": repository_name,
        "file_count": len(files),
        "files": files,
    }