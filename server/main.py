# server/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, file, manage, chat
from database import init_db


init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           
    allow_credentials=True,       
    allow_methods=["*"],           
    allow_headers=["*"],          
)

app.include_router(auth.router)    
app.include_router(file.router)    
app.include_router(manage.router)   
app.include_router(chat.router)    
