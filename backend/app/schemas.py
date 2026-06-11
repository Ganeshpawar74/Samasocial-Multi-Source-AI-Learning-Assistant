"""
Shared Pydantic models / data classes used across the API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    PDF = "pdf"
    PPTX = "pptx"
    YOUTUBE = "youtube"
    WEBPAGE = "webpage"


class SourceStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Chunk(BaseModel):
    """A single retrievable unit of text plus where it came from."""
    chunk_id: str
    source_id: str
    text: str

    locator: str = ""


class SourceMeta(BaseModel):
    source_id: str
    type: SourceType
    title: str
    origin: str  # filename or URL
    status: SourceStatus = SourceStatus.PROCESSING
    summary: Optional[str] = None
    num_chunks: int = 0
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


    processing_method: Optional[Literal["captions", "whisper", "whisper_full_audio", "sarvam"]] = None


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    citations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    session_id: str
    message: str
    mode: str = "qa"  


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str
    source_locator: str = ""


class QuizRequest(BaseModel):
    session_id: str
    num_questions: int = 5
    source_id: Optional[str] = None  # restrict quiz to one source if given