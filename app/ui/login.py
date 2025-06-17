# app/ui/login.py

import os
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
from services.api import login_user

load_dotenv()

FASTAPI_URL = "http://localhost:8000"
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD")

cookies = EncryptedCookieManager(password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()
#cookies.clear()

def logout():
    cookies.clear()

def login_page():
    st.title("🔐 로그인")

    if "access_token" not in st.session_state:
        if "access_token" in cookies:
            st.session_state["access_token"] = cookies["access_token"]
            st.session_state["username"] = cookies["username"]
            st.rerun()

    if "show_register" not in st.session_state:
        st.session_state["show_register"] = False

    if st.session_state["show_register"]:
        show_register_form()
    else:
        show_login_form()

def show_login_form():
    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    if submitted:
        with st.spinner("로그인 중..."):
            result = login_user(username, password)
            if isinstance(result, dict) and result.get("error"):
                st.error(f"❌ 로그인 실패: {result['error']}")
            else:
                st.session_state["access_token"] = result["access_token"]
                st.session_state["username"] = username
                cookies["access_token"] = result["access_token"]
                cookies["username"] = username
                cookies.save()

                st.success("✅ 로그인 성공!")
                st.rerun()

    if st.button("회원가입"):
        st.session_state["show_register"] = True
        st.rerun()

def show_register_form():
    st.subheader("📝 회원가입")

    new_user = st.text_input("새 아이디", key="new_user")
    new_pass = st.text_input("새 비밀번호", type="password", key="new_pass")

    if st.button("가입하기"):
        with st.spinner("회원가입 처리 중..."):
            res = requests.post(
                f"{FASTAPI_URL}/register",
                json={"username": new_user, "password": new_pass}
            )
            try:
                data = res.json()
                if res.status_code == 200 and data.get("message") == "회원가입 성공":
                    st.success("🎉 회원가입 성공! 이제 로그인해주세요.")
                    st.session_state["show_register"] = False
                    st.rerun()
                else:
                    st.error(f"❌ 실패: {data.get('detail', data.get('message', '오류 발생'))}")
            except Exception:
                st.error("❌ 회원가입 실패: 서버 오류")

    if st.button("← 로그인으로 돌아가기"):
        st.session_state["show_register"] = False
        st.rerun()
