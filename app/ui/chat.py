# app/ui/chat.py

import streamlit as st
from services.api import (
    list_courses,
    list_sessions,
    create_session,
    delete_session,
    generate_rag_answer,
    get_chat_log,
)

def chat_page():
    """
    Streamlit chat interface for RAG-based Q&A on lecture materials.
    """
    username = st.session_state.get("username", "anonymous")
    all_courses = list_courses(username)

    if not all_courses:
        st.warning("등록된 과목이 없습니다. 먼저 강의자료를 업로드해주세요.")
        return

    # -------------------------------
    # Sidebar: Course and Session Control
    # -------------------------------
    with st.sidebar:
        st.markdown("## 📚 과목 및 세션 관리")

        prev_course = st.session_state.get("prev_course")
        course = st.selectbox("과목 선택", options=all_courses, key="chat_course")

        # Reset session if course changes
        if prev_course and prev_course != course:
            st.session_state.pop("session_id", None)
            st.session_state.pop("chat_messages", None)
            st.session_state.pop("chat_loaded_for", None)
        st.session_state["prev_course"] = course

        # New session button
        cols = st.columns([6, 1])
        with cols[0]:
            st.markdown("### 💬 세션 목록")
        with cols[1]:
            if st.button("➕", key="new_session"):
                new_session_id = create_session(username, course)
                st.session_state["session_id"] = new_session_id
                st.session_state["chat_messages"] = []
                st.session_state["chat_loaded_for"] = new_session_id
                st.rerun()

        # List existing sessions
        sessions = list_sessions(username, course)
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

    # -------------------------------
    # Main Chat Interface
    # -------------------------------
    st.markdown("# 💬 강의자료 Q&A")

    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None
        st.session_state["chat_messages"] = []
        st.session_state["chat_loaded_for"] = None

    session_id = st.session_state["session_id"]

    # Load chat messages only if not already loaded
    if session_id:
        loaded_for = st.session_state.get("chat_loaded_for")
        if loaded_for != session_id:
            st.session_state["chat_messages"] = get_chat_log(username, course, session_id)
            st.session_state["chat_loaded_for"] = session_id

    # Display chat messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["message"])
            if msg["role"] == "assistant" and msg.get("context"):
                with st.expander("🔍 출처 보기"):
                    for i, doc in enumerate(msg["context"]):
                        st.markdown(f"**[{i+1}] {doc['metadata'].get('source', '알 수 없음')}**")
                        st.code(doc["page_content"][:500])

    # User input
    user_input = st.chat_input("질문을 입력하세요")
    if user_input:
        # Create session if not exists
        if not session_id:
            session_id = create_session(username, course)
            st.session_state["session_id"] = session_id
            st.session_state["chat_messages"] = []
            st.session_state["chat_loaded_for"] = session_id

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                response = generate_rag_answer(username, course, session_id, user_input)

            answer = response.get("answer", "")
            sources = response.get("context", [])

            st.markdown(answer)

            # Refresh chat log from backend
            st.session_state["chat_messages"] = get_chat_log(username, course, session_id)
            st.session_state["chat_loaded_for"] = session_id

            if sources:
                with st.expander("🔍 출처 보기"):
                    for i, doc in enumerate(sources):
                        st.markdown(f"**[{i+1}] {doc['metadata'].get('source', '알 수 없음')}**")
                        st.code(doc["page_content"][:500])

        st.rerun()
