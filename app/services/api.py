# app/services/api.py

import requests

# Base URL of the FastAPI backend
FASTAPI_URL = "http://localhost:8000"


# -------------------------------
# Authentication-related functions
# -------------------------------

def login_user(username, password):
    """
    Logs in a user and returns the access token.
    """
    response = requests.post(
        f"{FASTAPI_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if response.status_code == 200:
        return response.json()
    return None

def get_user_info(access_token):
    """
    Retrieves user information using the access token.
    """
    response = requests.get(
        f"{FASTAPI_URL}/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json() if response.status_code == 200 else None


# -----------------------
# PDF Analysis Operations
# -----------------------

def process_pdf(file, username):
    """
    Sends a PDF to the server for advanced processing.
    """
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    data = {"user": username}
    res = requests.post(f"{FASTAPI_URL}/process_pdf", files=files, data=data)
    return res.json()

def process_pdf_basic(file, user):
    """
    Sends a PDF for basic processing (less advanced than process_pdf).
    """
    files = {"file": (file.name, file, "application/pdf")}
    data = {"user": user}
    res = requests.post(f"{FASTAPI_URL}/process_pdf_basic", files=files, data=data)
    return res.json()

def save_pdf(payload: dict):
    """
    Saves processed PDF data on the server.
    """
    res = requests.post(f"{FASTAPI_URL}/save_pdf", json=payload)
    return res.json()


# -------------------------
# File and Course Management
# -------------------------

def list_files(username):
    """
    Lists all files uploaded by a specific user.
    """
    try:
        res = requests.get(f"{FASTAPI_URL}/list_files", params={"user": username})
        data = res.json()
        if isinstance(data, list):
            return data
        else:
            return []
    except Exception:
        return []

def delete_file(username, course, filename):
    """
    Deletes a specific file for a given course and user.
    """
    res = requests.delete(f"{FASTAPI_URL}/delete_file", params={
        "user": username,
        "course": course,
        "filename": filename,
    })
    return res.json()

def get_webview_url(username, course, filename):
    """
    Constructs a URL to view the file in the browser.
    """
    return f"{FASTAPI_URL}/view_file?user={username}&course={course}&filename={filename}"

def get_zip_download_url(username, course):
    """
    Constructs a URL to download all files of a course as a ZIP.
    """
    return f"{FASTAPI_URL}/download_zip?user={username}&course={course}"

def create_course(user, course):
    """
    Creates a new course for the user.
    """
    res = requests.post(f"{FASTAPI_URL}/create_course", json={"user": user, "course": course})
    return res.json()

def list_courses(user):
    """
    Lists all courses associated with the user.
    """
    res = requests.get(f"{FASTAPI_URL}/list_courses", params={"user": user})
    return res.json()

def delete_course(user, course):
    """
    Deletes a specific course for the user.
    """
    res = requests.delete(
        f"{FASTAPI_URL}/delete_course",
        params={"user": user, "course": course},
    )
    return res.json()

def check_duplicate(user: str, course: str, filename: str) -> bool:
    """
    Checks if a file with the same name already exists for the user/course.
    """
    payload = {
        "user": user,
        "course": course,
        "filename": filename
    }
    res = requests.post(f"{FASTAPI_URL}/check_duplicate", json=payload)
    return res.json().get("duplicate", False)


# -------------------------
# RAG (Retrieval-Augmented Generation)
# -------------------------

def generate_rag_answer(user, course, session_id, question):
    """
    Sends a question and receives an AI-generated answer using RAG.
    """
    url = f"{FASTAPI_URL}/chat/answer"
    payload = {
        "user": user,
        "course": course,
        "session_id": session_id,
        "question": question,
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return res.json()
        else:
            return {"answer": f"Error: Status {res.status_code}", "context": []}
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "context": []}


# -------------------------
# Chat Session Management
# -------------------------

def create_session(user, course, session_name=None):
    """
    Creates a new chat session for the user/course.
    """
    payload = {"user": user, "course": course}
    res = requests.post(f"{FASTAPI_URL}/chat/session", json=payload)
    return res.json()["session_id"]

def list_sessions(user, course):
    """
    Lists all chat sessions for a course and user.
    """
    res = requests.get(f"{FASTAPI_URL}/chat/sessions", params={"user": user, "course": course})
    try:
        return res.json()
    except Exception as e:
        print(f"[ERROR] list_sessions() JSON decode 실패: {e}")
        print("응답 내용:", res.text)
        return []

def delete_session(user, course, session_id):
    """
    Deletes a chat session.
    """
    res = requests.delete(
        f"{FASTAPI_URL}/chat/session",
        params={"user": user, "course": course, "session_id": session_id}
    )
    return res.json()

def update_chat_log(user, course, session_id, role, message):
    """
    Appends a new message to the chat log.
    """
    payload = {
        "user": user,
        "course": course,
        "session_id": session_id,
        "role": role,
        "message": message,
    }
    return requests.post(f"{FASTAPI_URL}/chat/log", json=payload).json()

def get_chat_log(user, course, session_id):
    """
    Retrieves the chat log for a session.
    """
    res = requests.get(f"{FASTAPI_URL}/chat/log", params={
        "user": user,
        "course": course,
        "session_id": session_id,
    })
    return res.json()
