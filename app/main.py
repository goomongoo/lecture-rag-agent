# app/main.py

import streamlit as st
from dotenv import load_dotenv
from ui.login import login_page, logout
from ui.manage import manage_page
from ui.chat import chat_page


load_dotenv()


#st.set_page_config(page_title="딱알이", layout="wide")

def main_page():
    st.title(f"안녕하세요, {st.session_state['username']}님!")

    st.sidebar.markdown("## 📋 메뉴")

    if st.sidebar.button("📁 강의자료 관리"):
        st.session_state["page"] = "manage"
    if st.sidebar.button("💬 강의자료 Q&A"):
        st.session_state["page"] = "chat"
    if st.sidebar.button("🔓 로그아웃"):
        logout()
        st.session_state.clear()
        st.rerun()

    page = st.session_state.get("page", "chat")
    if page == "manage":
        manage_page()
    elif page == "chat":
        chat_page()


if "access_token" not in st.session_state:
    login_page()
else:
    main_page()
