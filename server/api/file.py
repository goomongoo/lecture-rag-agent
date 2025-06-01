# server/api/file.py

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
import json

from api.manage import list_courses
from core.state import mark_processing, mark_done
from core.rag_agent import refresh_graph
from core.utils import (
    embed_and_store_chunks,
    remove_documents_by_source,
    save_temp_pdf,
    extract_course,
    save_pdfs,
    parse_pdfs
)

router = APIRouter()

@router.post("/upload_pdfs")
def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    user: str = Form(...),
    course: str = Form(...),
    overwrite_files: str = Form(...)
):
    try:
        overwrite_list = json.loads(overwrite_files)
        saved_paths = save_pdfs(files, user, course)

        for file in files:
            if file.filename in overwrite_list:
                remove_documents_by_source(user, course, file.filename)

        mark_processing(user, course)

        def background_embedding():
            try:
                refresh_graph(user, course)
                all_chunks = parse_pdfs(saved_paths)
                embed_and_store_chunks(user, course, all_chunks)
            finally:
                mark_done(user, course)

        background_tasks.add_task(background_embedding)

        return {
            "status": "success",
            "data": {
                "saved_files": saved_paths,
                "overwrite": overwrite_list
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"업로드 실패: {str(e)}"}
        )


@router.post("/analyze_pdf")
def analyze_pdf(file: UploadFile = File(...), user: str = Form(...)):
    try:
        temp_path = save_temp_pdf(file)
        chunks = parse_pdfs([temp_path])
        existing_course = list_courses(user)
        course_candidates = extract_course(chunks[0].page_content, existing_course)

        if temp_path.exists():
            temp_path.unlink()

        return {"status": "success", "data": {"course_candidates": course_candidates}}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"분석 실패: {str(e)}"}
        )
