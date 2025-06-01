# app/services/api.py

import requests


FASTAPI_URL = "http://localhost:8000"


def login_user(username, password):
    response = requests.post(
        f"{FASTAPI_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return response.json() if response.status_code == 200 else None


def get_user_info(access_token):
    response = requests.get(
        f"{FASTAPI_URL}/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json() if response.status_code == 200 else None


def upload_pdf(username, course, file_obj, overwrite):
    files = {"file": (file_obj.name, file_obj.getvalue(), "application/pdf")}
    data = {
        "user": username,
        "course": course,
        "filename": file_obj.name,
        "overwrite": overwrite
    }
    res = requests.post(f"{FASTAPI_URL}/upload_pdf", data=data, files=files)
    return res.json()


def analyze_pdf(file, username):
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    data = {"user": username}
    res = requests.post(f"{FASTAPI_URL}/analyze_pdf", files=files, data=data)
    return res.json()


def list_files(username):
    res = requests.get(f"{FASTAPI_URL}/list_files", params={"user": username})
    data = res.json()
    if isinstance(data, list):
        return data
    else:
        return []


def delete_file(username, course, filename):
    res = requests.delete(f"{FASTAPI_URL}/delete_file", params={
        "user": username,
        "course": course,
        "filename": filename,
    })
    return res.json()


def get_webview_url(username, course, filename):
    return f"{FASTAPI_URL}/view_file?user={username}&course={course}&filename={filename}"


def get_zip_download_url(username, course):
    return f"{FASTAPI_URL}/download_zip?user={username}&course={course}"


def create_course(user, course):
    try:
        res = requests.post(f"{FASTAPI_URL}/create_course", json={"user": user, "course": course})
        if res.status_code == 200:
            return {"status": "success"}
        elif res.status_code == 400:
            return {"status": "error", "message": "이미 존재하는 과목입니다."}
        else:
            return {"status": "error", "message": f"오류 발생: {res.status_code}"}
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}


def list_courses(user):
    res = requests.get(f"{FASTAPI_URL}/list_courses", params={"user": user})
    return res.json()


def delete_course(user, course):
    try:
        res = requests.delete(
            f"{FASTAPI_URL}/delete_course",
            params={"user": user, "course": course},
        )

        print(res.json())

        if res.status_code == 200:
            return res.json()
        else:
            return {"status": "error", "message": f"삭제 실패: {res.text}"}
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}


def check_duplicate(user: str, course: str, filename: str) -> bool:
    payload = {
        "user": user,
        "course": course,
        "filename": filename
    }
    res = requests.post(f"{FASTAPI_URL}/check_duplicate", json=payload)
    return res.json().get("duplicate", False)


def get_course_status(user: str, course: str) -> int:
    try:
        res = requests.get(f"{FASTAPI_URL}/course_status", params={"user": user, "course": course})
        if res.status_code == 200:
            return res.json().get("remaining", 0)
        return 0
    except Exception:
        return 0


def generate_rag_answer(user, course, session_id, question):
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


def create_session(user, course):
    payload = {"user": user, "course": course}
    res = requests.post(f"{FASTAPI_URL}/chat/session", json=payload)
    return res.json()["session_id"]


def list_sessions(user, course):
    res = requests.get(f"{FASTAPI_URL}/chat/sessions", params={"user": user, "course": course})
    return res.json()


def delete_session(user, course, session_id):
    res = requests.delete(
        f"{FASTAPI_URL}/chat/session",
        params={"user": user, "course": course, "session_id": session_id}
    )
    return res.json()


def update_chat_log(user, course, session_id, role, message):
    payload = {
        "user": user,
        "course": course,
        "session_id": session_id,
        "role": role,
        "message": message,
    }
    return requests.post(f"{FASTAPI_URL}/chat/log", json=payload).json()


def get_chat_log(user, course, session_id):
    res = requests.get(f"{FASTAPI_URL}/chat/log", params={
        "user": user,
        "course": course,
        "session_id": session_id,
    })
    return res.json()
