# app/ui/chat.py

import time
import streamlit as st
from services.api import (
    list_courses,
    list_sessions,
    create_session,
    delete_session,
    generate_rag_answer,
    get_chat_log,
    get_course_status
)

def chat_page():
    username = st.session_state.get("username", "anonymous")
    all_courses = list_courses(username)
    if isinstance(all_courses, dict) and all_courses.get("error"):
        st.error(all_courses["error"])
        return

    if not all_courses:
        st.warning("등록된 과목이 없습니다. 먼저 강의자료를 업로드해주세요.")
        return

    with st.sidebar:
        st.markdown("## 📚 과목 및 세션 관리")

        prev_course = st.session_state.get("prev_course")
        course = st.selectbox("과목 선택", options=all_courses, key="chat_course")

        if prev_course and prev_course != course:
            st.session_state.pop("session_id", None)
            st.session_state.pop("chat_messages", None)
            st.session_state.pop("chat_loaded_for", None)
        st.session_state["prev_course"] = course

        cols = st.columns([6, 1])
        with cols[0]:
            st.markdown("### 💬 세션 목록")
        with cols[1]:
            if st.button("➕", key="new_session"):
                new_session_id = create_session(username, course)
                if not new_session_id:
                    st.error("세션 생성에 실패했습니다.")
                else:
                    st.session_state["session_id"] = new_session_id
                    st.session_state["chat_messages"] = []
                    st.session_state["chat_loaded_for"] = new_session_id
                    st.rerun()

        sessions = list_sessions(username, course)
        if isinstance(sessions, dict) and sessions.get("error"):
            st.error(sessions["error"])
            return

        for session in sessions:
            session_id = session["session_id"]
            title = session["title"]
            cols = st.columns([6, 1])
            with cols[0]:
                if st.button(title, key=f"load_{session_id}"):
                    if st.session_state.get("session_id") != session_id:
                        st.session_state["session_id"] = session_id
                        st.session_state.pop("chat_messages", None)
                        st.session_state.pop("chat_loaded_for", None)
                        st.rerun()
            with cols[1]:
                if st.button("🗑️", key=f"del_{session_id}"):
                    delete_session(username, course, session_id)
                    if st.session_state.get("session_id") == session_id:
                        st.session_state.pop("session_id", None)
                        st.session_state.pop("chat_messages", None)
                        st.session_state.pop("chat_loaded_for", None)
                    st.rerun()

    st.markdown("# 💬 강의자료 Q&A")

    remaining = get_course_status(username, course)
    if isinstance(remaining, dict) and remaining.get("error"):
        st.error(remaining["error"])
        return
    if remaining > 0:
        placeholder = st.empty()
        with placeholder.container():
            st.warning(f"⚙️ '{course}' 과목 벡터 DB 정리 중입니다. 남은 파일: {remaining}")
        time.sleep(3)
        st.rerun()

    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None
        st.session_state["chat_messages"] = []
        st.session_state["chat_loaded_for"] = None

    session_id = st.session_state["session_id"]

    if session_id:
        loaded_for = st.session_state.get("chat_loaded_for")
        if loaded_for != session_id:
            logs = get_chat_log(username, course, session_id)
            if isinstance(logs, dict) and logs.get("error"):
                st.error(logs["error"])
                return
            st.session_state["chat_messages"] = logs
            st.session_state["chat_loaded_for"] = session_id

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["message"])
            if msg["role"] == "assistant" and msg.get("context"):
                with st.expander("🔍 출처 보기"):
                    for i, doc in enumerate(msg["context"]):
                        st.markdown(f"**[{i+1}] {doc['metadata'].get('source', '알 수 없음')}**")
                        st.code(doc["page_content"][:500])

    user_input = st.chat_input("질문을 입력하세요")
    if user_input:
        if not session_id:
            session_id = create_session(username, course)
            if not session_id:
                st.error("세션 생성에 실패했습니다.")
                return
            st.session_state["session_id"] = session_id
            st.session_state["chat_messages"] = []
            st.session_state["chat_loaded_for"] = session_id

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                response = generate_rag_answer(username, course, session_id, user_input)
                if isinstance(response, dict) and response.get("error"):
                    st.error(response["error"])
                    return
                answer = response.get("answer") or response.get("data", {}).get("answer", "")
                sources = response.get("context") or response.get("data", {}).get("context", [])
                st.markdown(answer)

        logs = get_chat_log(username, course, session_id)
        if isinstance(logs, dict) and logs.get("error"):
            st.error(logs["error"])
        else:
            st.session_state["chat_messages"] = logs
            st.session_state["chat_loaded_for"] = session_id

            if sources:
                with st.expander("🔍 출처 보기"):
                    for i, doc in enumerate(sources):
                        st.markdown(f"**[{i+1}] {doc['metadata'].get('source', '알 수 없음')}**")
                        st.code(doc["page_content"][:500])

        st.rerun()
