# server/core/utils.py

import os
import shutil
import tempfile
import json
from typing import List
from pathlib import Path
from fastapi import UploadFile
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from core.state import with_faiss_lock


embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

DATA_ROOT = Path("data")
MATERIALS_DIR = DATA_ROOT / "materials"
VECTOR_DIR = DATA_ROOT / "vectorstores"


def save_temp_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(uploaded_file.file, tmp)
        return Path(tmp.name)


def save_pdfs(files: List[UploadFile], user: str, course: str):
    save_dir = MATERIALS_DIR / user / course
    os.makedirs(save_dir, exist_ok=True)
    saved_paths = []

    for file in files:
        path = save_dir / file.filename
        with path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(path)
    
    return saved_paths


def parse_pdfs(paths: List[Path]):
    all_chunks = []

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.ocr_options.lang = ["es"]
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=4, device=AcceleratorDevice.AUTO
    )

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    markdown_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=[
        "\n\n```",                 
        "\n```",                  
        "\n\n<!-- image -->\n\n",  
        "\n\n### ",                
        "\n\n## ",
        "\n\n# ",
        "\n\n- ", "\n\n* ", "\n\n1. ",
        "\n\n", "\n", " ", ""
        ]
    )

    for path in paths:
        conv_result = doc_converter.convert(path)
        markdown_text = conv_result.document.export_to_markdown()
        doc = Document(
            page_content=markdown_text,
            metadata={"source": path.name}
        )
        chunks = markdown_splitter.split_documents([doc])
        all_chunks.extend(chunks)
    
    return all_chunks


def get_first_chunk_textonly(path: Path):
    loader = PyMuPDFLoader(str(path))
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
    chunks = splitter.split_documents(docs)

    return chunks[0]


def extract_course(text: str, existing_courses: list[str]) -> list[str]:
    model = ChatOpenAI(model="gpt-4o-mini")

    system_prompt = (
        "You are a lecture material analyst. From the text below, extract at least 3 likely course names (`course`).\n"
        "- A `course` is the name of a subject based on the lecture content.\n"
        "- Exclude course codes (e.g., CSE3050).\n"
        "- You may infer names freely from context.\n\n"
        f"Existing course list:\n{existing_courses}\n"
        "- First, check if any existing courses closely match the content. If so, include them.\n"
        "- Then, if needed, add new candidates based on the text to reach at least 3 suggestions.\n"
        "- Do not include unrelated existing courses.\n\n"
        "Respond in this format: {\"course_candidates\": [\"...\"]}"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text)
    ]

    try:
        response = model.invoke(messages)
        metadata = json.loads(response.content)
        courses = metadata.get("course_candidates", [])

        if not courses:
            raise ValueError("Missing candidates")
        return courses
    except Exception as e:
        print("GPT 추출 실패:", e)
        return ["과목명을 입력해주세요"]


def embed_and_store_chunks(user: str, course: str, chunks: list[Document]):
    lock = with_faiss_lock(user, course)

    with lock:
        index_path = VECTOR_DIR / user / course / "faiss_index"
        os.makedirs(index_path.parent, exist_ok=True)

        if index_path.exists():
            existing = FAISS.load_local(str(index_path), embedding_model, allow_dangerous_deserialization=True)
            existing.add_documents(chunks)
            existing.save_local(str(index_path))
        else:
            store = FAISS.from_documents(chunks, embedding_model)
            store.save_local(str(index_path))


def remove_documents_by_source(user: str, course: str, filename: str):
    lock = with_faiss_lock(user, course)

    with lock:
        index_path = VECTOR_DIR / user / course / "faiss_index"
        if not index_path.exists():
            return

        faiss_index = FAISS.load_local(str(index_path), embedding_model, allow_dangerous_deserialization=True)
        all_docs = list(faiss_index.docstore._dict.values())

        remaining_docs = [
            doc for doc in all_docs if doc.metadata.get("source") != filename
        ]

        if remaining_docs:
            new_index = FAISS.from_documents(remaining_docs, embedding_model)
            new_index.save_local(str(index_path))
        else:
            shutil.rmtree(index_path)
            parent_course_dir = index_path.parent
            if parent_course_dir.exists() and not any(parent_course_dir.iterdir()):
                parent_course_dir.rmdir()
