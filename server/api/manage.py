# server/api/manage.py

import os
import shutil
import tempfile
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from core.utils import remove_documents_by_source
from core.state import get_status
from core.rag_agent import delete_graphs_and_checkpoints_by_course
from models.chat import ChatLog, SessionTitle
from database import get_db


router = APIRouter()

MATERIALS_DIR = Path("data/materials")
VECTOR_DIR = Path("data/vectorstores")


@router.get("/list_files")
def list_files(user: str):
    try:
        user_path = MATERIALS_DIR / user
        if not user_path.exists():
            return {"status": "success", "data": []}

        result = []
        for course_dir in user_path.iterdir():
            if course_dir.is_dir():
                for file in course_dir.glob("*.pdf"):
                    result.append({
                        "course": course_dir.name,
                        "filename": file.name,
                        "path": str(file.relative_to(MATERIALS_DIR))
                    })

        return {"status": "success", "data": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"파일 목록 조회 실패: {str(e)}"})


@router.delete("/delete_file")
def delete_file(user: str, course: str, filename: str):
    try:
        file_path = MATERIALS_DIR / user / course / filename
        if file_path.exists():
            os.remove(file_path)
            remove_documents_by_source(user, course, filename)

            course_dir = file_path.parent
            if not any(course_dir.iterdir()):
                course_dir.rmdir()

        return {"status": "success", "message": "파일 삭제 완료"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"파일 삭제 실패: {str(e)}"})


@router.get("/view_file")
def view_file(user: str, course: str, filename: str):
    try:
        file_path = MATERIALS_DIR / user / course / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"파일 보기 실패: {str(e)}"})


@router.get("/download_zip")
def download_zip(user: str, course: str, background_tasks: BackgroundTasks):
    try:
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"ZIP 다운로드 실패: {str(e)}"})


class CreateCourseRequest(BaseModel):
    user: str
    course: str


@router.post("/create_course")
def create_course(req: CreateCourseRequest):
    course_path = MATERIALS_DIR / req.user / req.course
    if course_path.exists():
        return JSONResponse(status_code=400, content={"status": "error", "message": "이미 존재하는 과목입니다."})
    try:
        os.makedirs(course_path, exist_ok=False)
        return {"status": "success", "message": "과목 생성 완료"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"과목 생성 실패: {str(e)}"})


@router.get("/list_courses")
def list_courses(user: str):
    try:
        user_dir = MATERIALS_DIR / user
        if not user_dir.exists():
            return {"status": "success", "data": []}
        return {"status": "success", "data": sorted([p.name for p in user_dir.iterdir() if p.is_dir()])}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"과목 목록 조회 실패: {str(e)}"})


@router.delete("/delete_course")
def delete_course(user: str, course: str, db: Session = Depends(get_db)):
    try:
        course_path = MATERIALS_DIR / user / course
        vectorstore_path = VECTOR_DIR / user / course

        if course_path.exists():
            shutil.rmtree(course_path)
        if vectorstore_path.exists():
            shutil.rmtree(vectorstore_path)

        db.query(ChatLog).filter_by(user=user, course=course).delete()
        db.query(SessionTitle).filter_by(user=user, course=course).delete()
        db.commit()

        delete_graphs_and_checkpoints_by_course(user, course)

        return {"status": "success", "message": "과목 삭제 완료"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"과목 삭제 실패: {str(e)}"})


@router.get("/course_status")
def course_status(user: str, course: str):
    try:
        remaining = get_status(user, course)
        return {"status": "success", "data": {"remaining": remaining}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"상태 조회 실패: {str(e)}"})


@router.post("/check_duplicate")
def check_duplicate(data: dict = Body(...)):
    try:
        user = data["user"]
        course = data["course"]
        filename = data["filename"]

        file_path = MATERIALS_DIR / user / course / filename
        return {"status": "success", "data": {"duplicate": file_path.exists()}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"중복 확인 실패: {str(e)}"})
