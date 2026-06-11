"""
Endpoints for the chat experience:
  - POST /api/chat/session       -> create a new session
  - POST /api/chat/stream        -> streaming Q&A / "explain simply" (SSE)
  - POST /api/chat/quiz          -> generate a quiz from loaded sources
  - GET  /api/chat/{id}/history  -> retrieve session chat history
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.schemas import ChatMessage, ChatRequest, QuizRequest, SourceStatus
from app.services import llm
from app.services.session_store import session_store

router = APIRouter(prefix="/api/chat", tags=["chat"])
_settings = get_settings()


@router.post("/session")
async def create_session() -> dict:
    session = session_store.create()
    return {"session_id": session.session_id}


@router.get("/{session_id}/history")
async def get_history(session_id: str) -> list[ChatMessage]:
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session.history


@router.post("/stream")
async def chat_stream(payload: ChatRequest):
    session = session_store.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Create a session first.")

    ready_sources = {sid for sid, m in session.sources.items() if m.status == SourceStatus.READY}
    if not ready_sources:
        raise HTTPException(
            status_code=400,
            detail="No processed sources available yet. Add at least one source and wait for it to finish processing.",
        )

    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Retrieve relevant chunks (top_k across all ready sources)
    retrieved = session.vector_store.search(user_message, top_k=_settings.top_k_chunks)
    retrieved = [(c, s) for c, s in retrieved if c.source_id in ready_sources]
    chunks = [c for c, _ in retrieved]
    citations = sorted({f"{session.sources[c.source_id].title} — {c.locator}" for c in chunks})

    history_payload = [{"role": m.role, "content": m.content} for m in session.history]

    # Record the user's turn immediately
    session.history.append(ChatMessage(role="user", content=user_message))

    async def event_generator():
        full_response = ""
        try:
            async for token in llm.stream_chat_completion(
                history=history_payload,
                user_message=user_message,
                retrieved_chunks=chunks,
                source_titles=session.source_titles(),
                mode=payload.mode,
            ):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
            return

        session.history.append(ChatMessage(role="assistant", content=full_response, citations=citations))
        yield f"data: {json.dumps({'type': 'done', 'citations': citations})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/quiz")
async def generate_quiz(payload: QuizRequest) -> dict:
    session = session_store.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    ready_sources = {sid for sid, m in session.sources.items() if m.status == SourceStatus.READY}
    if not ready_sources:
        raise HTTPException(status_code=400, detail="No processed sources available for quiz generation.")

    if payload.source_id and payload.source_id not in ready_sources:
        raise HTTPException(status_code=400, detail="Requested source is not ready.")

    # Pull a broad sample of chunks: if a specific source is requested, use all
    # of its chunks (capped); otherwise sample across all sources.
    all_chunks = session.vector_store.chunks
    if payload.source_id:
        candidate_chunks = [c for c in all_chunks if c.source_id == payload.source_id]
    else:
        candidate_chunks = [c for c in all_chunks if c.source_id in ready_sources]

    if not candidate_chunks:
        raise HTTPException(status_code=400, detail="No content available to build a quiz from.")

    # Cap context size sent to the LLM
    max_chunks = 20
    if len(candidate_chunks) > max_chunks:
        step = len(candidate_chunks) / max_chunks
        candidate_chunks = [candidate_chunks[int(i * step)] for i in range(max_chunks)]

    num_questions = max(1, min(payload.num_questions, 10))

    try:
        questions = await llm.generate_quiz(candidate_chunks, session.source_titles(), num_questions)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"questions": questions}
