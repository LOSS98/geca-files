from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi import Security
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import shutil
from pathlib import Path
import time
from dotenv import load_dotenv
from celery import Celery
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FILES_DIR = os.getenv("FILES_DIR", "/var/www/public.losbarryachis.fr/public/shared")
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY is not defined in the .env file")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

os.makedirs(FILES_DIR, exist_ok=True)

celery_app = Celery("file_tasks", broker=REDIS_URL)

app = FastAPI(
    title="File Management API",
    description="API for managing files in a shared directory",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-KEY")

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'zip', 'doc', 'docx', 'xls', 'xlsx'}


def is_allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


@celery_app.task
def process_file_upload(file_path: str, original_filename: str):
    try:
        logger.info(f"Processing file: {original_filename}")
        time.sleep(2)
        logger.info(f"File processed successfully: {original_filename}")
        return {"status": "success", "file": original_filename}
    except Exception as e:
        logger.error(f"Error processing file {original_filename}: {str(e)}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def cleanup_temp_files(days=1):
    try:
        cutoff_time = time.time() - (days * 86400)
        temp_dir = Path(FILES_DIR) / "temp"

        if not temp_dir.exists():
            temp_dir.mkdir(exist_ok=True)
            return {"status": "success", "message": "No temp directory found"}

        count = 0
        for item in temp_dir.iterdir():
            if item.is_file() and item.stat().st_mtime < cutoff_time:
                item.unlink()
                count += 1

        return {"status": "success", "files_removed": count}
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")
        return {"status": "error", "message": str(e)}


class FileListResponse(BaseModel):
    data: List[Dict[str, Any]]


class FileResponse(BaseModel):
    filename: str
    path: str
    status: str


class StatusResponse(BaseModel):
    status: str
    message: str


@app.get("/")
def home(api_key: str = Depends(verify_api_key)):
    return {"message": "File Management API is running", "status": 200}


@app.get("/health")
async def health_check(api_key: str = Depends(verify_api_key)):
    return {"status": "healthy"}


@app.get("/files", response_model=FileListResponse)
async def list_files(
        directory: Optional[str] = Query(None),
        api_key: str = Depends(verify_api_key)
):
    base_dir = Path(FILES_DIR)

    if directory:
        target_dir = base_dir / directory
        if not str(target_dir).startswith(str(base_dir)):
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        target_dir = base_dir

    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    files = []
    for item in target_dir.iterdir():
        if item.is_file():
            files.append({
                "name": item.name,
                "path": str(item.relative_to(base_dir)),
                "size": item.stat().st_size,
                "modified": item.stat().st_mtime,
                "is_file": True
            })
        elif item.is_dir():
            files.append({
                "name": item.name,
                "path": str(item.relative_to(base_dir)),
                "modified": item.stat().st_mtime,
                "is_file": False
            })

    return {"data": files}


@app.post("/files/upload", response_model=FileResponse)
async def upload_file(
        file: UploadFile = File(...),
        directory: Optional[str] = Form(None),
        api_key: str = Depends(verify_api_key)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    if not is_allowed_file(file.filename):
        raise HTTPException(status_code=400,
                            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")

    base_dir = Path(FILES_DIR)

    if directory:
        target_dir = base_dir / directory
        if not str(target_dir).startswith(str(base_dir)):
            raise HTTPException(status_code=403, detail="Access denied")

        os.makedirs(target_dir, exist_ok=True)
    else:
        target_dir = base_dir

    filename = file.filename
    file_path = target_dir / filename
    counter = 1

    while file_path.exists():
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{counter}{ext}"
        file_path = target_dir / filename
        counter += 1

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        process_file_upload.delay(str(file_path), filename)

        return {"filename": filename, "path": str(file_path.relative_to(base_dir)), "status": "success"}
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.get("/files/{file_path:path}")
async def download_file(
        file_path: str,
        api_key: str = Depends(verify_api_key)
):
    base_dir = Path(FILES_DIR)
    full_path = base_dir / file_path

    if not str(full_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=str(full_path), filename=full_path.name)


@app.delete("/files/{file_path:path}", response_model=StatusResponse)
async def delete_file(
        file_path: str,
        api_key: str = Depends(verify_api_key)
):
    base_dir = Path(FILES_DIR)
    full_path = base_dir / file_path

    if not str(full_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if full_path.is_file():
        os.remove(full_path)
        return {"status": "success", "message": f"File {file_path} deleted"}
    elif full_path.is_dir():
        shutil.rmtree(full_path)
        return {"status": "success", "message": f"Directory {file_path} deleted"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=False)
