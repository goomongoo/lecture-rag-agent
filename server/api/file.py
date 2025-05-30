# server/api/file.py

from pydantic import BaseModel
from typing import List
from pathlib import Path
from fastapi import APIRouter, UploadFile, Form, File
from fastapi.responses import JSONResponse
from langchain_core.documents import Document

# Business logic & utility imports
from api.manage import list_courses
from core.utils import (
    save_temp_pdf,
    load_and_split_pdf,
    extract_course,
    save_pdf_to_course_folder,
    embed_and_store_chunks,
)


# -------------------------------
# Router Initialization
# -------------------------------

# Initialize FastAPI router
router = APIRouter()


# -------------------------------
# PDF Processing Endpoints
# -------------------------------

@router.post("/process_pdf")
def process_pdf(user: str = Form(...), file: UploadFile = File(...)):
    """
    Analyzes a PDF file and returns:
    - Text chunks extracted from the file
    - Inferred course name candidates
    - Temporary file path for later saving
    """
    try:
        temp_path = save_temp_pdf(file)
        chunks = load_and_split_pdf(temp_path)
        existing_courses = list_courses(user)
        course_candidates = extract_course(chunks[0].page_content, existing_courses)

        chunk_payload = [
            {"page_content": c.page_content, "metadata": {"source": file.filename}}
            for c in chunks
        ]

        return {
            "status": "ok",
            "filename": file.filename,
            "course_candidates": course_candidates,
            "temp_path": str(temp_path),
            "chunks": chunk_payload,
        }
    except Exception as e:
        print("Analyze failed:", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/process_pdf_basic")
def process_pdf_basic(user: str = Form(...), file: UploadFile = Form(...)):
    """
    Performs basic PDF processing:
    - Extracts and returns text chunks from the PDF
    - Does not perform course inference
    """
    temp_path = save_temp_pdf(file)
    chunks = load_and_split_pdf(temp_path)
    filename = file.filename

    chunk_payload = [
        {"page_content": c.page_content, "metadata": {"source": filename}} for c in chunks
    ]

    return {
        "status": "ok",
        "filename": filename,
        "temp_path": str(temp_path),
        "chunks": chunk_payload,
    }


# -------------------------------
# Request Models
# -------------------------------

class Chunk(BaseModel):
    """
    Schema representing a single chunk of extracted text from a PDF.
    """
    page_content: str
    metadata: dict


class SaveRequest(BaseModel):
    """
    Schema used to persist analyzed PDF content.
    """
    user: str
    course: str
    filename: str
    temp_path: str
    chunks: List[Chunk]


# -------------------------------
# PDF Saving Endpoint
# -------------------------------

@router.post("/save_pdf")
def save_pdf(req: SaveRequest):
    """
    Saves a processed PDF:
    - Moves the temporary file to the course directory
    - Embeds the text chunks and stores them in vector storage
    """
    chunk_docs = []
    for c in req.chunks:
        doc = Document(**c.model_dump())
        doc.metadata["source"] = req.filename
        chunk_docs.append(doc)

    saved_path = save_pdf_to_course_folder(
        Path(req.temp_path), req.filename, req.user, req.course
    )

    embed_and_store_chunks(req.user, req.course, chunk_docs)

    return {"status": "success", "saved_path": str(saved_path)}
