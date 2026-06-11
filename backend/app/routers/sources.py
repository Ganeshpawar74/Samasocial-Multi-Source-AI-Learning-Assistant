"""
Endpoints for adding knowledge sources to a session:
  - PDF upload
  - PPTX upload
  - YouTube URL
  - Webpage URL

Each endpoint: parses -> chunks -> embeds & indexes -> generates a short
summary -> returns SourceMeta to the frontend (which renders a "source badge").

Processing happens synchronously within the request for simplicity and
clear error reporting (the task is "process them" before chat begins).
For larger files this would move to a background task + polling/WS,
noted in the README as a scaling improvement.
"""
from __future__ import annotations

import os
import tempfile
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import SourceMeta, SourceStatus, SourceType
from app.services import llm, parsers
from app.services.chunking import chunk_slides, chunk_text, chunk_transcript_segments
from app.services.session_store import session_store

router = APIRouter(prefix="/api/sources", tags=["sources"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


@router.post("/pdf", response_model=SourceMeta)
async def add_pdf_source(session_id: str = Form(...), file: UploadFile = File(...)) -> SourceMeta:
    session = session_store.get_or_create(session_id)
    source_id = str(uuid.uuid4())
    meta = SourceMeta(
        source_id=source_id,
        type=SourceType.PDF,
        title=file.filename or "PDF",
        origin=file.filename or "",
    )
    session.sources[source_id] = meta

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        meta.status = SourceStatus.FAILED
        meta.error = "File too large (max 25MB)."
        return meta

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        parsed = parsers.parse_pdf(tmp_path)

        chunks = []
        full_text_parts = []
        for page in parsed["pages"]:
            page_chunks = chunk_text(page["text"], source_id, locator_prefix=f"Page {page['page_number']}")
            for c in page_chunks:
                if len(page_chunks) == 1:
                    c.locator = f"Page {page['page_number']}"
            chunks.extend(page_chunks)
            full_text_parts.append(page["text"])

        session.vector_store.add_chunks(chunks)

        if parsed["title"]:
            meta.title = parsed["title"]

        meta.summary = await llm.generate_summary("\n\n".join(full_text_parts))
        meta.num_chunks = len(chunks)
        meta.status = SourceStatus.READY

    except Exception as exc:  # noqa: BLE001
        meta.status = SourceStatus.FAILED
        meta.error = str(exc)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return meta


@router.post("/pptx", response_model=SourceMeta)
async def add_pptx_source(session_id: str = Form(...), file: UploadFile = File(...)) -> SourceMeta:
    session = session_store.get_or_create(session_id)
    source_id = str(uuid.uuid4())
    meta = SourceMeta(
        source_id=source_id,
        type=SourceType.PPTX,
        title=file.filename or "Presentation",
        origin=file.filename or "",
    )
    session.sources[source_id] = meta

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        meta.status = SourceStatus.FAILED
        meta.error = "File too large (max 25MB)."
        return meta

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        parsed = parsers.parse_pptx(tmp_path)
        chunks = chunk_slides(parsed["slides"], source_id)
        session.vector_store.add_chunks(chunks)

        full_text = "\n\n".join(s["text"] for s in parsed["slides"])
        meta.summary = await llm.generate_summary(full_text)
        meta.num_chunks = len(chunks)
        meta.status = SourceStatus.READY

    except Exception as exc:  
        meta.status = SourceStatus.FAILED
        meta.error = str(exc)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return meta


@router.post("/youtube", response_model=SourceMeta)
async def add_youtube_source(
    session_id: str = Form(...),
    url: str = Form(...),
    language: str = Form("english"),
) -> SourceMeta:
    """
    Add a YouTube video as a knowledge source.

    `language` controls which transcription engine is used:
      - "english"  (default) → openai-whisper (local, accurate for English)
      - "hindi"    → Sarvam AI (STT + English translation, requires SARVAM_API_KEY)
      - "hinglish" → Sarvam AI (same as hindi)
    """
    session = session_store.get_or_create(session_id)
    source_id = str(uuid.uuid4())
    meta = SourceMeta(
        source_id=source_id,
        type=SourceType.YOUTUBE,
        title="YouTube video",
        origin=url,
    )
    session.sources[source_id] = meta

    try:
        parsed = parsers.parse_youtube(url, language=language)
        processing_method = parsed.get("processing_method", "captions")

        # Surface to the frontend which path was taken
        meta.processing_method = processing_method  # type: ignore[assignment]

        # Update title optimistically while chunking runs
        if parsed.get("title"):
            meta.title = parsed["title"]

        chunks = chunk_transcript_segments(parsed["segments"], source_id)
        session.vector_store.add_chunks(chunks)

        full_text = " ".join(seg["text"] for seg in parsed["segments"])
        meta.summary = await llm.generate_summary(full_text)
        meta.num_chunks = len(chunks)
        meta.status = SourceStatus.READY

    except Exception as exc:  # noqa: BLE001
        meta.status = SourceStatus.FAILED
        meta.error = str(exc)

    return meta


@router.post("/webpage", response_model=SourceMeta)
async def add_webpage_source(session_id: str = Form(...), url: str = Form(...)) -> SourceMeta:
    session = session_store.get_or_create(session_id)
    source_id = str(uuid.uuid4())
    meta = SourceMeta(
        source_id=source_id,
        type=SourceType.WEBPAGE,
        title=url,
        origin=url,
    )
    session.sources[source_id] = meta

    try:
        parsed = parsers.parse_webpage(url)
        chunks = chunk_text(parsed["text"], source_id, locator_prefix="Webpage")
        session.vector_store.add_chunks(chunks)

        if parsed["title"]:
            meta.title = parsed["title"]

        meta.summary = await llm.generate_summary(parsed["text"])
        meta.num_chunks = len(chunks)
        meta.status = SourceStatus.READY

    except Exception as exc:  # noqa: BLE001
        meta.status = SourceStatus.FAILED
        meta.error = str(exc)

    return meta


@router.get("/{session_id}", response_model=list[SourceMeta])
async def list_sources(session_id: str) -> list[SourceMeta]:
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return list(session.sources.values())


@router.delete("/{session_id}/{source_id}")
async def remove_source(session_id: str, source_id: str) -> dict:
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if source_id not in session.sources:
        raise HTTPException(status_code=404, detail="Source not found.")

    session.vector_store.remove_source(source_id)
    del session.sources[source_id]
    return {"status": "removed", "source_id": source_id}