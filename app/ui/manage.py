# app/ui/manage.py

import streamlit as st
from services.api import (
    list_files,
    delete_file,
    get_zip_download_url,
    get_webview_url,
    save_pdf,
    process_pdf,
    process_pdf_basic,
    create_course,
    list_courses,
    delete_course,
    check_duplicate
)


# -------------------------------
# Lecture Material Management Page
# -------------------------------

def manage_page():
    """
    Streamlit UI for managing lecture materials.
    Allows file upload, course creation, file viewing, deletion, and duplication handling.
    """
    st.title("📂 강의자료 관리")

    username = st.session_state.get("username", "anonymous")

    # Fetch user files and available course names
    files = list_files(username)
    file_courses = set(f["course"] for f in files)
    all_courses = sorted(set(list_courses(username)) | file_courses)

    # -------------------------------
    # Toggle Upload / Course Create Panels
    # -------------------------------

    with st.container():
        if st.button("➕ 과목 추가"):
            st.session_state["show_add_course"] = not st.session_state.get("show_add_course", False)

        if st.button("📁 개별 파일 업로드"):
            st.session_state["show_indiv_upload"] = not st.session_state.get("show_indiv_upload", False)

    # -------------------------------
    # Individual File Upload Section
    # -------------------------------

    if st.session_state.get("show_indiv_upload"):
        indiv_file = st.file_uploader("📄 업로드할 PDF 파일을 선택하세요", type=["pdf"], key="indiv_file_upload")
        if indiv_file and st.button("📤 분석 시작"):
            result = process_pdf(indiv_file, username)
            if result.get("status") == "ok":
                st.session_state["indiv_result"] = result
                st.session_state["indiv_file"] = indiv_file

        # File analyzed, choose course and save or overwrite
        if "indiv_result" in st.session_state:
            result = st.session_state["indiv_result"]
            candidates = result.get("course_candidates", [])
            unique = list(dict.fromkeys(candidates))

            # Sort courses into recommended, new, and remaining
            intersect = [c for c in unique if c in all_courses]
            unique_recommend = [c for c in unique if c not in all_courses]
            remaining = [c for c in all_courses if c not in unique]

            course_options = (
                [(c, f"{c} (AI 추천 · 기존 과목)") for c in intersect] +
                [(c, f"{c} (AI 추천)") for c in unique_recommend] +
                [(c, c) for c in remaining]
            )

            course_choice = st.selectbox("과목 선택", options=course_options, format_func=lambda x: x[1])

            # Check for duplicates and handle accordingly
            is_duplicate = check_duplicate(username, course_choice[0], result["filename"])
            if is_duplicate:
                st.warning(f"⚠️ '{result['filename']}' 파일은 이미 '{course_choice[0]}' 과목에 존재합니다. 덮어쓰시겠습니까?")
                if st.button("📄 덮어쓰기 저장", key="indiv_overwrite"):
                    for c in result.get("chunks", []):
                        c["metadata"]["source"] = result["filename"]
                    save_pdf({
                        "user": username,
                        "course": course_choice[0],
                        "filename": result["filename"],
                        "temp_path": result["temp_path"],
                        "chunks": result["chunks"]
                    })
                    st.success("✅ 업로드가 완료되었습니다.")
                    _reset_individual_upload()
                if st.button("❌ 취소", key="indiv_overwrite_cancel"):
                    _reset_individual_upload()
                    st.success("업로드가 취소되었습니다.")
            else:
                if st.button("💾 저장", key="indiv_save"):
                    for c in result.get("chunks", []):
                        c["metadata"]["source"] = result["filename"]
                    save_pdf({
                        "user": username,
                        "course": course_choice[0],
                        "filename": result["filename"],
                        "temp_path": result["temp_path"],
                        "chunks": result["chunks"]
                    })
                    st.success("✅ 업로드가 완료되었습니다.")
                    _reset_individual_upload()

    # -------------------------------
    # Course Creation Section
    # -------------------------------

    if "show_add_course" not in st.session_state:
        st.session_state["show_add_course"] = False
    if "add_course_error" not in st.session_state:
        st.session_state["add_course_error"] = ""

    if st.session_state["show_add_course"]:
        new_course = st.text_input("새 과목 이름 입력", key="new_course_input")
        if st.button("✅ 과목 생성"):
            if not new_course.strip():
                st.session_state["add_course_error"] = "과목 이름을 입력해주세요."
            elif new_course in all_courses:
                st.session_state["add_course_error"] = "이미 존재하는 과목입니다."
            else:
                create_course(username, new_course)
                st.session_state["show_add_course"] = False
                st.session_state["add_course_error"] = ""
                st.rerun()

        if st.session_state["add_course_error"]:
            st.error(st.session_state["add_course_error"])

    # -------------------------------
    # Course File Listing & Actions
    # -------------------------------

    if not all_courses:
        st.info("업로드된 강의자료가 없습니다.")
        return

    selected_course = st.selectbox("과목 선택", options=all_courses)

    zip_url = get_zip_download_url(username, selected_course)
    st.markdown(
        f'''<a href="{zip_url}" target="_blank">
            <button style="margin-bottom: 1rem; padding: 6px 10px; background-color: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer;">
                📦 ZIP 다운로드
            </button>
        </a>''',
        unsafe_allow_html=True
    )

    filtered_files = sorted(
        [f for f in files if f["course"] == selected_course],
        key=lambda x: x["filename"].lower()
    )

    if not filtered_files:
        st.info("이 과목에는 업로드된 강의자료가 없습니다.")

    for f in filtered_files:
        col1, _, col3 = st.columns([6, 0.6, 0.6])
        with col1:
            url = get_webview_url(username, f["course"], f["filename"])
            st.markdown(
                f'<a href="{url}" target="_blank" style="text-decoration: none; font-weight: 500;">📄 {f["filename"]}</a>',
                unsafe_allow_html=True
            )
        with col3:
            if st.button("🗑️", key=f"delete-{f['filename']}"):
                delete_file(username, f["course"], f["filename"])
                st.success(f"{f['filename']} 삭제 완료")
                st.rerun()

    if st.button("🗑️ 선택한 과목 전체 삭제"):
        delete_course(username, selected_course)
        st.session_state["delete_complete"] = True

    if st.session_state.get("delete_complete"):
        st.success("✅ 삭제가 완료되었습니다.")
        if st.button("🔄 확인"):
            del st.session_state["delete_complete"]
            st.rerun()

    # -------------------------------
    # Bulk File Upload Section
    # -------------------------------

    if st.button("📤 현재 과목 강의자료 업로드"):
        st.session_state["show_upload"] = not st.session_state.get("show_upload", False)

    if st.session_state.get("upload_complete"):
        st.success("✅ 업로드가 완료되었습니다.")
        st.session_state["upload_complete"] = False

    if st.session_state.get("show_upload"):
        uploaded_files = st.file_uploader("여러 PDF 파일 업로드", type=["pdf"], accept_multiple_files=True)
        if uploaded_files and st.button("💾 업로드 시작"):
            duplicate_files = []
            total = len(uploaded_files)
            progress_bar = st.progress(0, text="업로드 진행 중...")

            for i, f in enumerate(uploaded_files):
                result = process_pdf_basic(f, username)
                if result.get("status") != "ok":
                    continue
                filename, temp_path, chunks = result["filename"], result["temp_path"], result["chunks"]
                for c in chunks:
                    c["metadata"]["source"] = filename
                if check_duplicate(username, selected_course, filename):
                    duplicate_files.append({"filename": filename, "temp_path": temp_path, "chunks": chunks})
                else:
                    save_pdf({
                        "user": username,
                        "course": selected_course,
                        "filename": filename,
                        "temp_path": temp_path,
                        "chunks": chunks
                    })
                progress = (i + 1) / total
                progress_bar.progress(progress, text=f"{i+1}/{total} 파일 업로드 완료")

            progress_bar.empty()
            st.session_state["duplicate_files"] = duplicate_files
            st.session_state["upload_complete"] = not duplicate_files
            st.session_state["show_upload"] = False
            st.rerun()

    # -------------------------------
    # Duplicate Conflict Resolution
    # -------------------------------

    if st.session_state.get("duplicate_files"):
        st.warning("⚠️ 중복된 파일이 있습니다. 덮어쓸 파일을 선택한 뒤 업로드를 진행하세요.")
        if "overwrite_checked" not in st.session_state:
            st.session_state["overwrite_checked"] = {}
        for file in st.session_state["duplicate_files"]:
            key = f"overwrite_{file['filename']}"
            st.session_state["overwrite_checked"][file["filename"]] = st.checkbox(file["filename"], key=key)

        if st.button("📄 덮어쓰기 업로드"):
            files_to_overwrite = [
                f for f in st.session_state["duplicate_files"]
                if st.session_state["overwrite_checked"].get(f["filename"])
            ]
            total = len(files_to_overwrite)
            progress_bar = st.progress(0, text="덮어쓰기 업로드 진행 중...")

            for i, file in enumerate(files_to_overwrite):
                save_pdf({
                    "user": username,
                    "course": selected_course,
                    "filename": file["filename"],
                    "temp_path": file["temp_path"],
                    "chunks": file["chunks"]
                })
                progress_bar.progress((i + 1) / total, text=f"{i+1}/{total} 파일 저장 완료")

            progress_bar.empty()
            st.success("✅ 덮어쓰기 업로드가 완료되었습니다.")
            del st.session_state["duplicate_files"]
            del st.session_state["overwrite_checked"]
            st.rerun()

        if st.button("❌ 취소"):
            del st.session_state["duplicate_files"]
            del st.session_state["overwrite_checked"]
            st.session_state["show_upload"] = False
            st.success("업로드가 취소되었습니다.")
            st.rerun()


# -------------------------------
# Utility: Reset Individual Upload State
# -------------------------------

def _reset_individual_upload():
    """
    Clears session state related to individual file upload.
    """
    st.session_state.pop("indiv_result", None)
    st.session_state.pop("indiv_file", None)
    st.session_state["show_indiv_upload"] = False
    st.rerun()
