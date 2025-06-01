# server/api/manage.py

import os
import shutil
import tempfile
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.utils import remove_documents_by_source
from core.state import get_status
from core.rag_agent import delete_graphs_and_checkpoints_by_course
from models.chat import ChatLog, SessionTitle
from database import get_db


# -------------------------------
# Router & Storage Configuration
# -------------------------------

# Initialize FastAPI router
router = APIRouter()

# Base directory where all user materials are stored
MATERIALS_DIR = Path("data/materials")

# Base directory where all vectorstores are stored
VECTOR_DIR = Path("data/vectorstores")


# -------------------------------
# File Management Endpoints
# -------------------------------

@router.get("/list_files")
def list_files(user: str):
    """
    Lists all PDF files uploaded by the user across all courses.
    Returns each file's course name, filename, and relative path.
    """
    user_path = MATERIALS_DIR / user
    if not user_path.exists():
        return []

    result = []
    for course_dir in user_path.iterdir():
        if course_dir.is_dir():
            for file in course_dir.glob("*.pdf"):
                result.append({
                    "course": course_dir.name,
                    "filename": file.name,
                    "path": str(file.relative_to(MATERIALS_DIR))
                })

    return result


@router.delete("/delete_file")
def delete_file(user: str, course: str, filename: str):
    """
    Deletes a specific PDF file and its vector-embedded data.
    Also removes the course folder if it becomes empty after deletion.
    """
    file_path = MATERIALS_DIR / user / course / filename
    if file_path.exists():
        os.remove(file_path)
        remove_documents_by_source(user, course, filename)

        course_dir = file_path.parent
        if not any(course_dir.iterdir()):
            course_dir.rmdir()

    return {"status": "success", "message": "File deleted or already absent."}


@router.get("/view_file")
def view_file(user: str, course: str, filename: str):
    """
    Returns the requested PDF file for inline browser viewing.
    Raises a 404 error if the file does not exist.
    """
    file_path = MATERIALS_DIR / user / course / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.get("/download_zip")
def download_zip(user: str, course: str, background_tasks: BackgroundTasks):
    """
    Compresses all files in a course folder into a ZIP file and returns it.
    Deletes the temporary ZIP file after it is served.
    """
    course_path = MATERIALS_DIR / user / course
    if not course_path.exists():
        raise HTTPException(status_code=404, detail="Course not found")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        zip_path = Path(tmp.name)
        shutil.make_archive(zip_path.with_suffix(''), 'zip', root_dir=course_path)

    background_tasks.add_task(os.remove, zip_path)

    return FileResponse(
        path=zip_path,
        filename=f"{course}.zip",
        media_type="application/zip",
        background=background_tasks
    )


# -------------------------------
# Course Management Endpoints
# -------------------------------

class CreateCourseRequest(BaseModel):
    """
    Request schema for creating a new course.
    """
    user: str
    course: str


@router.post("/create_course")
def create_course(req: CreateCourseRequest):
    """
    Creates a new course folder for the user.
    Returns an error if the course already exists or folder creation fails.
    """
    course_path = MATERIALS_DIR / req.user / req.course
    if course_path.exists():
        raise HTTPException(status_code=400, detail="이미 존재하는 과목입니다.")
    try:
        os.makedirs(course_path, exist_ok=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"과목 생성 실패: {str(e)}")


@router.get("/list_courses")
def list_courses(user: str):
    """
    Lists all course names (i.e., subfolders) for the given user.
    """
    user_dir = MATERIALS_DIR / user
    if not user_dir.exists():
        return []
    return sorted([p.name for p in user_dir.iterdir() if p.is_dir()])


@router.delete("/delete_course")
def delete_course(user: str, course: str, db: Session = Depends(get_db)):
    """
    Deletes the specified course folder and all files within it,
    and removes associated vectorstore data.
    """
    course_path = MATERIALS_DIR / user / course
    vectorstore_path = VECTOR_DIR / user / course

    try:
        if course_path.exists():
            shutil.rmtree(course_path)
        if vectorstore_path.exists():
            shutil.rmtree(vectorstore_path)
        
        db.query(ChatLog).filter_by(user=user, course=course).delete()
        db.query(SessionTitle).filter_by(user=user, course=course).delete()
        db.commit()

        delete_graphs_and_checkpoints_by_course(user, course)

        return {"status": "success", "message": "Course deleted or already absent."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"과목 삭제 실패: {str(e)}")
    

@router.get("/course_status")
def course_status(user: str, course: str):
    remaining = get_status(user, course)
    return {"remaining": remaining}


# -------------------------------
# Duplicate Check Endpoint
# -------------------------------

@router.post("/check_duplicate")
def check_duplicate(data: dict = Body(...)):
    """
    Checks if a file with the given name already exists in the specified course.
    Returns a boolean flag under 'duplicate'.
    """
    user = data["user"]
    course = data["course"]
    filename = data["filename"]

    file_path = MATERIALS_DIR / user / course / filename
    return {"duplicate": file_path.exists()}
