# app/ui/manage.py

import streamlit as st
from services.api import (
    list_files,
    delete_file,
    get_zip_download_url,
    get_webview_url,
    upload_pdf,
    analyze_pdf,
    create_course,
    list_courses,
    delete_course,
    check_duplicate,
)


def manage_page():
    st.title("📂 강의자료 관리")

    username = st.session_state.get("username", "anonymous")

    files = list_files(username)
    file_courses = set(f["course"] for f in files)
    all_courses = sorted(set(list_courses(username)) | file_courses)

    with st.container():
        if st.button("➕ 과목 추가"):
            st.session_state["show_add_course"] = not st.session_state.get("show_add_course", False)

        if st.button("개별 파일 업로드"):
            st.session_state["show_single_upload"] = not st.session_state.get("show_single_upload", False)
    
    if st.session_state.get("show_single_upload"):
        handle_single_upload(username, all_courses)
    
    if "show_add_course" not in st.session_state:
        st.session_state["show_add_course"] = False
    if "add_course_error" not in st.session_state:
        st.session_state["add_course_error"] = ""
    
    if st.session_state.get("show_add_course"):
        handle_course_create(username, all_courses)
    
    if not all_courses:
        st.info("업로드된 강의자료가 없습니다.")
        return
    
    selected_course = st.selectbox("과목 선택", options=all_courses)

    handle_course_files(username, selected_course, files)
    

def handle_single_upload(username, all_courses):
    single_file = st.file_uploader("📄 업로드할 PDF 파일을 선택하세요", type=["pdf"], key="single_file_upload")

    if single_file and st.button("과목 추천"):
        result = analyze_pdf(single_file, username)
        if result.get("status") == "ok":
            st.session_state["single_result"] = result
            st.session_state["single_file"] = single_file
        
    if "single_result" in st.session_state:
        result = st.session_state.get("single_result")
        candidates = list(dict.fromkeys(result.get("course_candidates", [])))

        intersect = [c for c in candidates if c in all_courses]
        ai_recommend = [c for c in candidates if c not in all_courses]
        remaining = [c for c in all_courses if c not in candidates]

        course_options = (
            [(c, f"{c} (AI 추천 · 기존 과목)") for c in intersect] +
            [(c, f"{c} (AI 추천)") for c in ai_recommend] +
            [(c, c) for c in remaining]
        )

        course_choice = st.selectbox("과목 선택", options=course_options, format_func=lambda x: x[1])

        is_duplicate = check_duplicate(username, course_choice[0], single_file.name)
        if is_duplicate:
            st.warning(f"⚠️ '{single_file.name}' 파일은 이미 '{course_choice[0]}' 과목에 존재합니다. 덮어쓰시겠습니까?")
            if st.button("📄 덮어쓰기", key="single_overwrite"):
                upload_pdf(username, course_choice[0], single_file, True)
                st.success("✅ 업로드 완료. 벡터DB 정리중입니다.")
                st.session_state.pop("single_result", None)
                st.session_state.pop("single_file", None)
                st.session_state["show_single_upload"] = False
                if st.button("🔄 확인", key="single_overwrite_complete"):
                    st.rerun()
            if st.button("❌ 취소", key="single_overwrite_cancel"):
                st.session_state.pop("single_result", None)
                st.session_state.pop("single_file", None)
                st.session_state["show_single_upload"] = False
                st.rerun()
        else:
            if st.button("💾 저장", key="single_save"):
                upload_pdf(username, course_choice[0], single_file, False)
                st.success("✅ 업로드 완료. 벡터DB 정리중입니다.")
                st.session_state.pop("single_result", None)
                st.session_state.pop("single_file", None)
                st.session_state["show_single_upload"] = False
                if st.button("🔄 확인", key="single_overwrite_complete"):
                    st.rerun()


def handle_course_create(username, all_courses):
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


def handle_course_files(username, selected_course, files):
    if st.button("🗑️ 선택한 과목 전체 삭제", key="delete_course"):
        delete_course(username, selected_course)
        st.success("✅ 삭제가 완료되었습니다.")
        if st.session_state.get("prev_course") == selected_course:
            st.session_state.pop("prev_course", None)
            st.session_state.pop("session_id", None)
            st.session_state.pop("chat_messages", None)
            st.session_state.pop("chat_loaded_for", None)
        if st.button("🔄 확인", key="delete_course_complete"):
            st.rerun()
    
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
    
    if st.button("➕ 현재 과목 강의자료 업로드"):
        st.session_state["show_upload"] = not st.session_state.get("show_upload", False)

    if st.session_state.get("show_upload"):
        handle_upload(username, selected_course)


def handle_upload(username, selected_course):
    uploaded_files = st.file_uploader("📄 한 번에 여러 PDF 파일을 업로드 할 수 있습니다.", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files and st.button("💾 업로드 시작"):
        duplicated_files = []
        total = len(uploaded_files)
        progress_bar = st.progress(0, text="업로드 진행 중...")

        for i, f in enumerate(uploaded_files):
            if check_duplicate(username, selected_course, f.name):
                duplicated_files.append(f)
            else:
                upload_pdf(username, selected_course, f, False)
            progress = (i + 1) / total
            progress_bar.progress(progress, text=f"{i + 1}/{total} 파일 업로드 진행중")
        
        progress_bar.empty()
        
        if duplicated_files:
            st.warning("⚠️ 중복된 파일이 있습니다. 덮어쓸 파일을 선택한 뒤 업로드를 진행하세요.")
            if "overwrite_checked" not in st.session_state:
                st.session_state["overwrite_checked"] = {}
            for f in duplicated_files:
                key = f"overwrite_{f.name}"
                st.session_state["overwrite_checked"][f.name] = st.checkbox(f.name, key=key)
            
            if st.button("📄 선택한 파일 덮어쓰기"):
                files_to_overwrite = [
                    f for f in duplicated_files
                    if st.session_state["overwrite_checked"].get(f.name)
                ]
                total = len(files_to_overwrite)
                progress_bar = st.progress(0, text="덮어쓰기 진행 중...")

                for i, f in enumerate(files_to_overwrite):
                    upload_pdf(username, selected_course, f, True)
                    progress = (i + 1) / total
                    progress_bar.progress(progress, text=f"{i + 1}/{total} 파일 덮어쓰기 완료")
            
                progress_bar.empty()

                st.success("✅ 덮어쓰기 완료. 벡터DB 정리중입니다.")
                st.session_state.pop("overwrite_checked", None)
                st.session_state["show_upload"] = False
                if st.button("🔄 확인"):
                    st.rerun()
            
            if st.button("❌ 취소"):
                st.session_state.pop("overwrite_checked", None)
                st.session_state["show_upload"] = False
                st.rerun()

        else:
            st.success("✅ 업로드 완료. 벡터DB 정리중입니다.")
            st.session_state["show_upload"] = False
            if st.button("🔄 확인"):
                st.rerun()