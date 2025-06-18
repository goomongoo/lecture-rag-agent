# 딱알이

딱알이는 사용자가 강의자료(PDF)를 업로드하면 과목을 자동 분류하고, 문서를 임베딩하여 강의자료 기반 Q&A 기능을 제공하는 시스템.  
Streamlit 프론트엔드와 FastAPI 백엔드로 구성되며, LangChain, FAISS, OpenAI API를 활용한 Retrieval-Augmented Generation(RAG) 구조를 따름.

---

## 주요 기능

### 사용자 인증
- 회원가입 및 JWT 기반 로그인 지원
- 쿠키 기반 세션 유지로 자동 로그인 가능

### 강의자료 관리
- PDF 업로드 시 GPT를 활용한 과목 추천 제공
- 파일 중복 여부 확인 및 덮어쓰기 여부 선택 가능
- 과목 생성/삭제, ZIP 파일 일괄 다운로드 기능 포함

### 강의자료 Q&A (RAG 기반)
- 세션 단위의 멀티턴 대화 관리 (생성/삭제/불러오기)
- LangGraph 기반 RAG 응답 생성
- 응답에 포함된 출처 문서 chunk 표시 기능 제공

### 성능 평가
- `evaluate_rag.py`를 통해 자동 질문 생성 및 응답 평가 수행
- Retrieval (Recall@k, MRR 등) 및 Generation (BERTScore 등) 기준 제공

---

## 프로젝트 구조

```
lecture_agent/
├── server/
│   ├── api/             # FastAPI 라우터 정의
│   ├── core/            # RAG 및 벡터화 처리 로직
│   ├── models/          # SQLAlchemy 모델 정의
│   ├── evaluate_rag.py  # RAG 성능 평가 스크립트
│   └── main.py          # FastAPI 앱 실행 진입점
│
├── app/
│   ├── ui/              # Streamlit UI 페이지 (login, manage, chat)
│   ├── services/        # FastAPI API 호출 래퍼
│   └── main.py          # Streamlit 실행 진입점
│
├── data/
│   ├── materials/       # 업로드된 PDF 파일 저장소
│   ├── vectorstores/    # FAISS 벡터 인덱스 저장소
│   └── checkpoints/     # LangGraph 세션 체크포인트
```

---

## 실행 방법

### 1. 환경 변수 설정

`.env` 파일 생성:

```env
JWT_SECRET_KEY=your_jwt_secret
COOKIE_PASSWORD=your_cookie_key
OPENAI_API_KEY=your_openai_key
```

### 2. 의존성 설치

```bash
conda create -n lecture-agent python=3.10
conda activate lecture-agent
pip install -r requirements.txt
```

### 3. 서버 실행

FastAPI 백엔드 실행:

```bash
cd server
uvicorn main:app --reload
```

Streamlit 프론트엔드 실행:

```bash
cd app
streamlit run main.py
```

---

## 성능 예시

`evaluate_rag.py` 실행 결과:

```
Recall@5     : 0.9333
Precision@5  : 0.1867
MRR          : 0.8833
nDCG         : 0.8964
BERTScore_F1 : 0.6648
```

---

## 문서 처리 및 RAG 파이프라인 설명

### 문서 처리 과정

1. 사용자가 PDF 파일을 업로드하면, 서버는 해당 파일을 `materials/` 디렉토리에 저장함.
2. Docling 기반 파이프라인을 통해 PDF에서 텍스트, 이미지, 표, 수식 등을 Markdown 형태로 추출함.  
   - 이 과정에서 OCR, 수식 감지, 구조 복원 등의 작업이 수행됨.
   - Docling은 멀티스레딩을 지원하며 GPU(CUDA) 환경에서 더욱 빠르게 동작함.
3. 추출된 문서는 LangChain의 `RecursiveCharacterTextSplitter`를 통해 일정 길이의 chunk로 분할됨.
4. 각 chunk는 OpenAI의 `text-embedding-3-large` 모델을 통해 벡터로 임베딩되고, 사용자-과목 단위의 FAISS 인덱스에 저장됨.

### RAG 파이프라인

1. 사용자가 질문을 입력하면 LangGraph 기반 RAG 상태기계가 실행됨.
2. 시스템은 다음 단계를 거쳐 답변을 생성함:
   - 질문 전처리 및 standalone question 재구성 (Contextualizer)
   - BM25와 FAISS 기반 Ensemble Retriever로 관련 문서 chunk 검색
   - LangChain의 `StuffDocumentsChain`을 통해 retrieved context와 함께 답변 생성
3. 답변 결과와 함께 참조한 문서 chunk 목록이 프론트엔드로 반환되며, 사용자는 답변 출처 확인 가능
4. 모든 대화 및 문맥 정보는 session_id 기준으로 DB에 저장되어 멀티턴 대화 유지 가능



- 현재 시스템은 Docling을 활용하여 PDF 내 텍스트, 이미지, 표 등을 분석하고 구조화함
- Docling은 OCR 및 문서 파싱 시 CPU보다 **GPU(CUDA)** 환경에서 성능이 훨씬 뛰어남
- 따라서 **CUDA 사용 가능한 환경**에서 실행할 것을 권장함

---

## 개선 사항 및 고려사항

- UpstageAI의 Document Parsing API를 활용하면 문서 처리 속도를 크게 단축할 수 있으나, **API 호출 시 비용이 발생**함

---

## 주요 기술 스택

- 백엔드: FastAPI, SQLAlchemy, SQLite
- 프론트엔드: Streamlit
- RAG: LangChain, LangGraph, OpenAI GPT-4o, FAISS
- 문서 처리: Docling, PyMuPDF

---

## 참고 문서

- [LangChain Documentation](https://docs.langchain.com/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://docs.streamlit.io/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Docling](https://github.com/upstage-ai/docling)