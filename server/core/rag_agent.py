# server/core/rag_agent.py

import sqlite3
from pathlib import Path
from database import get_db_engine
from typing import TypedDict, Annotated, Sequence
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.chains import create_retrieval_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.retrievers import EnsembleRetriever
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.constants import START
from langgraph.checkpoint.sqlite import SqliteSaver


MATERIALS_DIR = Path("data/materials")
VECTOR_DIR = Path("data/vectorstores")
CHECKPOINT_DIR = Path("data/checkpoints")

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-4o", temperature=0.8)

graph_checkpoints = {}


system_prompt = (
    "You are an academic assistant helping university students understand their course materials. "
    "Use the following retrieved context to provide clear, well-structured answers in Korean. "
    "Ensure your response is informative and appropriate for a university-level audience. "
    "If the answer is not found in the context, say you don't know in Korean. Do not guess or make up information.\n\n"
    "{context}"
)

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])

contextualize_q_system_prompt = (
    "You are given a conversation history and the user's latest question. "
    "If the question depends on previous context, rewrite it as a standalone question that makes sense on its own. "
    "If it already stands alone, return it as-is. "
    "Do NOT answer the question—only return the reformulated or original question."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])


def load_retriever(user: str, course: str, k=5):
    vector_path = VECTOR_DIR / user / course / "faiss_index"
    docs_path = MATERIALS_DIR / user / course

    documents = []
    for file in docs_path.glob("*.pdf"):
        loader = PyMuPDFLoader(str(file))
        documents += loader.load()

    bm25 = BM25Retriever.from_documents(documents)
    bm25.k = k

    faiss = FAISS.load_local(str(vector_path), embedding_model, allow_dangerous_deserialization=True)
    dense = faiss.as_retriever(search_kwargs={"k": k})

    return EnsembleRetriever(retrievers=[bm25, dense], weights=[0.4, 0.6])


class State(TypedDict):
    input: str
    chat_history: Annotated[Sequence[BaseMessage], add_messages]
    context: str
    answer: str


def build_rag_graph(user: str, course: str):
    retriever = create_history_aware_retriever(llm, load_retriever(user, course), contextualize_q_prompt)
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    def call_rag(state: State):
        response = rag_chain.invoke(state)
        return {
            "chat_history": [
                HumanMessage(state["input"]),
                AIMessage(response["answer"]),
            ],
            "context": response["context"],
            "answer": response["answer"],
        }

    builder = StateGraph(state_schema=State)
    builder.add_edge(START, "RAG")
    builder.add_node("RAG", call_rag)

    engine = get_db_engine()
    conn = sqlite3.connect(engine.url.database, check_same_thread=False)
    saver = SqliteSaver(conn)

    return builder.compile(checkpointer=saver)


def get_or_create_graph(user: str, course: str, session_id: str):
    key = f"{user}:{course}:{session_id}"
    if key not in graph_checkpoints:
        graph = build_rag_graph(user, course)
        graph_checkpoints[key] = graph
    return graph_checkpoints[key]


def delete_graphs_and_checkpoints_by_course(user: str, course: str):
    prefix = f"{user}:{course}:"
    to_delete = [key for key in graph_checkpoints if key.startswith(prefix)]
    for key in to_delete:
        del graph_checkpoints[key]
    
    engine = get_db_engine()
    try:
        with sqlite3.connect(engine.url.database, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checkpoints WHERE thread_id LIKE ?", (f"{prefix}%",))
            cursor.execute("DELETE FROM writes WHERE thread_id LIKE ?", (f"{prefix}%",))
            conn.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            pass
        else:
            raise