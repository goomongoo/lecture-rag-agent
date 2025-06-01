# server/api/chat.py

import json
import uuid
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.chat import ChatLog, SessionTitle
from core.rag_agent import get_or_create_graph
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


router = APIRouter()

SESSION_DIR = Path("data/sessions")


class RagRequest(BaseModel):
    user: str
    course: str
    session_id: str
    question: str


class SessionCreateRequest(BaseModel):
    user: str
    course: str
    session_name: str | None = None


class ChatLogRequest(BaseModel):
    user: str
    course: str
    session_id: str
    role: str
    message: str


@router.post("/chat/answer")
def generate_rag_answer(req: RagRequest, db: Session = Depends(get_db)):
    graph = get_or_create_graph(req.user, req.course, req.session_id)
    state = graph.invoke({"input": req.question}, config={"thread_id": f"{req.user}:{req.course}:{req.session_id}"})
    answer = state["answer"].strip()

    raw_context = state.get("context", [])
    serializable_context = [
        {
            "page_content": doc.page_content,
            "metadata": doc.metadata
        } for doc in raw_context
    ]

    db.add(ChatLog(user=req.user, course=req.course, session_id=req.session_id, role="user", message=req.question))
    db.add(ChatLog(user=req.user, course=req.course, session_id=req.session_id, role="assistant", message=answer, context=json.dumps(serializable_context)))

    existing_title = db.query(SessionTitle).filter_by(
        user=req.user, course=req.course, session_id=req.session_id
    ).first()

    if existing_title and (existing_title.title == "(새 세션)" or not existing_title.title.strip()):
        summarizer = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        prompt = PromptTemplate.from_template(
            "다음 Q&A 내용을 바탕으로 간결한 세션 제목을 지어줘. 문장형이 아니라 짧은 문구 형태.\n\nQ: {question}\nA: {answer}"
        )
        title_chain = prompt | summarizer
        result = title_chain.invoke({"question": req.question, "answer": answer})
        session_title = result.content.strip().strip('"').strip()
        existing_title.title = session_title
        db.commit()

    db.commit()
    return {"answer": answer, "context": state["context"]}


@router.post("/chat/session")
def create_session(req: SessionCreateRequest, db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())

    db.add(SessionTitle(
        user=req.user,
        course=req.course,
        session_id=session_id,
        title="(새 세션)"
    ))
    db.commit()

    return {"session_id": session_id}


@router.get("/chat/sessions")
def list_sessions(user: str, course: str, db: Session = Depends(get_db)):
    results = (
        db.query(SessionTitle.session_id, SessionTitle.title)
        .filter_by(user=user, course=course)
        .order_by(SessionTitle.id.asc())
        .all()
    )
    return [{"session_id": r.session_id, "title": r.title} for r in results]


@router.delete("/chat/session")
def delete_session(user: str, course: str, session_id: str, db: Session = Depends(get_db)):
    db.query(ChatLog).filter_by(user=user, course=course, session_id=session_id).delete()
    db.query(SessionTitle).filter_by(user=user, course=course, session_id=session_id).delete()
    db.commit()
    return {"status": "deleted"}


@router.post("/chat/log")
def update_chat_log(req: ChatLogRequest, db: Session = Depends(get_db)):
    log = ChatLog(
        user=req.user,
        course=req.course,
        session_id=req.session_id,
        role=req.role,
        message=req.message,
        timestamp=datetime.now()
    )
    db.add(log)
    db.commit()
    return {"status": "ok"}


@router.get("/chat/log")
def get_chat_log(user: str, course: str, session_id: str, db: Session = Depends(get_db)):
    logs = (
        db.query(ChatLog)
        .filter_by(user=user, course=course, session_id=session_id)
        .order_by(ChatLog.timestamp.asc())
        .all()
    )

    return [
        {
            "role": log.role,
            "message": log.message,
            "context": json.loads(log.context) if log.context else None
        }
        for log in logs
    ]
