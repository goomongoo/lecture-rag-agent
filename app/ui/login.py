# app/ui/login.py

import os
import streamlit as st
import requests
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
from services.api import login_user


# -------------------------------
# Configuration & Cookie Setup
# -------------------------------

# Load environment variables from .env
load_dotenv()

# FastAPI backend URL and cookie encryption password
FASTAPI_URL = "http://localhost:8000"
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD")

# Initialize encrypted cookie manager
cookies = EncryptedCookieManager(password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()


# -------------------------------
# Authentication Utilities
# -------------------------------

def logout():
    """
    Clears all stored cookies and effectively logs the user out.
    """
    cookies.clear()


# -------------------------------
# Login Page Entry Point
# -------------------------------

def login_page():
    """
    Streamlit login page.
    Supports login via form and optional registration toggle.
    """
    st.title("🔐 로그인")

    # Restore session from cookies if available
    if "access_token" not in st.session_state:
        if "access_token" in cookies:
            st.session_state["access_token"] = cookies["access_token"]
            st.session_state["username"] = cookies["username"]
            st.rerun()

    # Initialize toggle for showing registration form
    if "show_register" not in st.session_state:
        st.session_state["show_register"] = False

    # Show either login or registration form
    if st.session_state["show_register"]:
        show_register_form()
    else:
        show_login_form()


# -------------------------------
# Login Form
# -------------------------------

def show_login_form():
    """
    Renders the login form and handles authentication.
    """
    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    if submitted:
        with st.spinner("로그인 중..."):
            result = login_user(username, password)
            if result:
                # Save login data to session state and cookies
                st.session_state["access_token"] = result["access_token"]
                st.session_state["username"] = username
                cookies["access_token"] = result["access_token"]
                cookies["username"] = username
                cookies.save()

                st.success("✅ 로그인 성공!")
                st.rerun()
            else:
                st.error("❌ 로그인 실패: 아이디 또는 비밀번호를 확인해주세요.")

    # Toggle to registration form
    if st.button("회원가입"):
        st.session_state["show_register"] = True
        st.rerun()


# -------------------------------
# Registration Form
# -------------------------------

def show_register_form():
    """
    Renders the user registration form and handles user creation.
    """
    st.subheader("📝 회원가입")

    new_user = st.text_input("새 아이디", key="new_user")
    new_pass = st.text_input("새 비밀번호", type="password", key="new_pass")

    if st.button("가입하기"):
        with st.spinner("회원가입 처리 중..."):
            res = requests.post(
                f"{FASTAPI_URL}/register",
                json={"username": new_user, "password": new_pass}
            )
            if res.status_code == 200:
                st.success("🎉 회원가입 성공! 이제 로그인해주세요.")
                st.session_state["show_register"] = False
                st.rerun()
            else:
                st.error(f"❌ 실패: {res.json().get('detail', '오류 발생')}")

    # Toggle back to login form
    if st.button("← 로그인으로 돌아가기"):
        st.session_state["show_register"] = False
        st.rerun()
