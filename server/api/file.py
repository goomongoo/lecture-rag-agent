# server/api/file.py

from fastapi import APIRouter, UploadFile, File, Form
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from api.manage import list_courses
from core.state import mark_processing, mark_done
from core.rag_agent import refresh_graph
from core.utils import (
    save_temp_pdf,
    load_and_split_pdf,
    extract_course,
    save_pdf_to_course_folder,
    embed_and_store_chunks,
    remove_documents_by_source
)


router = APIRouter()

@router.post("/upload_pdf")
def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: str = Form(...),
    course: str = Form(...),
    filename: str = Form(...),
    overwrite: bool = Form(...)
):
    try:
        saved_path = save_pdf_to_course_folder(file, user, course)
        chunks = load_and_split_pdf(saved_path, filename)

        mark_processing(user, course)

        def background_embedding():
            try:
                if overwrite:
                    remove_documents_by_source(user, course, filename)
                refresh_graph(user, course)
                embed_and_store_chunks(user, course, chunks)
            finally:
                mark_done(user, course)

        background_tasks.add_task(background_embedding)

        return {"status": "success", "data": {"saved_path": str(saved_path)}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"업로드 실패: {str(e)}"})


@router.post("/analyze_pdf")
def analyze_pdf(file: UploadFile = File(...), user: str = Form(...)):
    try:
        temp_path = save_temp_pdf(file)
        chunks = load_and_split_pdf(temp_path, file.filename)
        existing_course = list_courses(user)
        course_candidates = extract_course(chunks[0].page_content, existing_course)

        if temp_path.exists():
            temp_path.unlink()

        return {"status": "success", "data": {"course_candidates": course_candidates}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"분석 실패: {str(e)}"})
