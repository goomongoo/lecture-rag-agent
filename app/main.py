# app/main.py

import streamlit as st
from dotenv import load_dotenv
from ui.login import login_page, logout
from ui.manage import manage_page
from ui.chat import chat_page


# -------------------------------
# App Initialization
# -------------------------------

# Load environment variables from .env file
load_dotenv()


# -------------------------------
# Main Application Page
# -------------------------------

def main_page():
    """
    Renders the main interface after login.
    Provides sidebar navigation to manage files or access chat.
    """
    # Configure Streamlit page
    st.set_page_config(page_title="딱알이", layout="wide")

    # Greet the user
    st.title(f"안녕하세요, {st.session_state['username']}님!")

    # Sidebar navigation menu
    st.sidebar.markdown("## 📋 메뉴")

    # Navigation: Manage, Chat, Logout
    if st.sidebar.button("📁 강의자료 관리"):
        st.session_state["page"] = "manage"
    if st.sidebar.button("💬 강의자료 기반 Q&A"):
        st.session_state["page"] = "chat"
    if st.sidebar.button("🔓 로그아웃"):
        logout()
        st.session_state.clear()
        st.rerun()

    # Render selected page
    page = st.session_state.get("page", "manage")
    if page == "manage":
        manage_page()
    elif page == "chat":
        chat_page()


# -------------------------------
# Entry Point: Login or Main Page
# -------------------------------

if "access_token" not in st.session_state:
    login_page()
else:
    main_page()
