# server/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, file, manage, chat
from database import init_db

# Initialize database and create tables
init_db()

# Initialize FastAPI application
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allow all origins (adjust for production)
    allow_credentials=True,        # Allow cookies and authorization headers
    allow_methods=["*"],           # Allow all HTTP methods
    allow_headers=["*"],           # Allow all headers
)

# Register routers from each API module
app.include_router(auth.router)     # Authentication (login, register)
app.include_router(file.router)     # PDF processing and storage
app.include_router(manage.router)   # File and course management
app.include_router(chat.router)     # Chat (RAG) and session handling
