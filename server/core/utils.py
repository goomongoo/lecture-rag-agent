# server/core/utils.py

import os
import shutil
import tempfile
import json
import unicodedata
from pathlib import Path

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


# -------------------------------
# Configuration & Models
# -------------------------------

# Initialize embedding model
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

# Base directories for materials and vector stores
DATA_ROOT = Path("data")
MATERIALS_DIR = DATA_ROOT / "materials"
VECTOR_DIR = DATA_ROOT / "vectorstores"


# -------------------------------
# PDF Handling Functions
# -------------------------------

def save_temp_pdf(uploaded_file):
    """
    Saves an uploaded PDF to a temporary file.
    Returns the file path of the saved PDF.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(uploaded_file.file, tmp)
        return Path(tmp.name)


def load_and_split_pdf(pdf_path: Path):
    """
    Loads a PDF file and splits its content into text chunks.
    Uses RecursiveCharacterTextSplitter for semantic chunking.
    """
    loader = PyMuPDFLoader(str(pdf_path))
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    return splitter.split_documents(docs)


def save_pdf_to_course_folder(temp_pdf_path: Path, filename: str, user: str, course: str) -> Path:
    """
    Moves a temporary PDF to the user's course folder.
    Ensures Unicode normalization for the filename.
    Returns the final saved path.
    """
    base_path = MATERIALS_DIR / user / course
    os.makedirs(base_path, exist_ok=True)

    safe_filename = unicodedata.normalize("NFC", filename)
    dest = base_path / safe_filename
    shutil.move(str(temp_pdf_path), dest)
    return dest


# -------------------------------
# Course Extraction Using GPT
# -------------------------------

def extract_course(text: str, existing_courses: list[str]) -> list[str]:
    """
    Uses GPT to infer at least 3 candidate course names from the given text.
    Suggests relevant existing courses first, and fills with inferred ones.
    """
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


# -------------------------------
# Embedding & Vector Store Functions
# -------------------------------

def embed_and_store_chunks(user: str, course: str, chunks: list[Document]):
    """
    Embeds document chunks and stores them in the FAISS vector index.
    Updates the existing index if it exists; otherwise, creates a new one.
    """
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
    """
    Removes all vectors in the FAISS index that originated from a specific PDF file.
    Deletes the entire index folder if it becomes empty afterward.
    """
    index_path = VECTOR_DIR / user / course / "faiss_index"
    if not index_path.exists():
        return

    faiss_index = FAISS.load_local(str(index_path), embedding_model, allow_dangerous_deserialization=True)
    all_docs = list(faiss_index.docstore._dict.values())

    # Filter out documents by file name
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
