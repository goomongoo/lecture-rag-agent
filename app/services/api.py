# app/services/api.py

import json
import requests

FASTAPI_URL = "http://localhost:8000"

def handle_response(res):
    try:
        data = res.json()
        if res.status_code == 200:
            if data.get("status") == "error":
                return {"error": data.get("message", f"오류: {res.status_code}")}
            return data.get("data") or data
    except Exception:
        return {"error": f"오류: {res.status_code}"}

def login_user(username, password):
    res = requests.post(
        f"{FASTAPI_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return handle_response(res)

def get_user_info(access_token):
    res = requests.get(
        f"{FASTAPI_URL}/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return handle_response(res)

def upload_pdfs(username, course, file_objs, overwrite_list):
    files = [("files", (f.name, f.getvalue(), "application/pdf")) for f in file_objs]
    data = {
        "user": username,
        "course": course,
        "overwrite_files": json.dumps(overwrite_list)
    }
    res = requests.post(f"{FASTAPI_URL}/upload_pdfs", data=data, files=files)
    return handle_response(res)

def analyze_pdf(file, username):
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    data = {"user": username}
    res = requests.post(f"{FASTAPI_URL}/analyze_pdf", files=files, data=data)
    return handle_response(res)

def list_files(username):
    res = requests.get(f"{FASTAPI_URL}/list_files", params={"user": username})
    data = handle_response(res)
    return data.get("data", []) if isinstance(data, dict) else data

def delete_file(username, course, filename):
    res = requests.delete(f"{FASTAPI_URL}/delete_file", params={
        "user": username,
        "course": course,
        "filename": filename,
    })
    return handle_response(res)

def get_webview_url(username, course, filename):
    return f"{FASTAPI_URL}/view_file?user={username}&course={course}&filename={filename}"

def get_zip_download_url(username, course):
    return f"{FASTAPI_URL}/download_zip?user={username}&course={course}"

def create_course(user, course):
    res = requests.post(f"{FASTAPI_URL}/create_course", json={"user": user, "course": course})
    return handle_response(res)

def list_courses(user):
    res = requests.get(f"{FASTAPI_URL}/list_courses", params={"user": user})
    return handle_response(res)

def delete_course(user, course):
    res = requests.delete(
        f"{FASTAPI_URL}/delete_course",
        params={"user": user, "course": course},
    )
    return handle_response(res)

def check_duplicate(user: str, course: str, filename: str):
    payload = {"user": user, "course": course, "filename": filename}
    res = requests.post(f"{FASTAPI_URL}/check_duplicate", json=payload)
    data = handle_response(res)
    return data.get("duplicate", False)

def get_course_status(user: str, course: str):
    res = requests.get(f"{FASTAPI_URL}/course_status", params={"user": user, "course": course})
    data = handle_response(res)
    return data.get("remaining", 0)

def generate_rag_answer(user, course, session_id, question):
    url = f"{FASTAPI_URL}/chat/answer"
    payload = {
        "user": user,
        "course": course,
        "session_id": session_id,
        "question": question,
    }
    res = requests.post(url, json=payload)
    return handle_response(res)

def create_session(user, course):
    payload = {"user": user, "course": course}
    res = requests.post(f"{FASTAPI_URL}/chat/session", json=payload)
    data = handle_response(res)
    return data.get("session_id")

def list_sessions(user, course):
    res = requests.get(f"{FASTAPI_URL}/chat/sessions", params={"user": user, "course": course})
    data = handle_response(res)
    return data.get("data", []) if isinstance(data, dict) else data

def delete_session(user, course, session_id):
    res = requests.delete(
        f"{FASTAPI_URL}/chat/session",
        params={"user": user, "course": course, "session_id": session_id}
    )
    return handle_response(res)

def update_chat_log(user, course, session_id, role, message):
    payload = {
        "user": user,
        "course": course,
        "session_id": session_id,
        "role": role,
        "message": message,
    }
    res = requests.post(f"{FASTAPI_URL}/chat/log", json=payload)
    return handle_response(res)

def get_chat_log(user, course, session_id):
    res = requests.get(f"{FASTAPI_URL}/chat/log", params={
        "user": user,
        "course": course,
        "session_id": session_id,
    })
    data = handle_response(res)
    return data.get("data", []) if isinstance(data, dict) else data
