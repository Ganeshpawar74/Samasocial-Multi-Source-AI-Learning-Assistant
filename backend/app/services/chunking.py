"""
Token-aware text chunking with overlap.

We use tiktoken purely as a fast, deterministic tokenizer for *length
measurement* (it does not need to match the LLM's actual tokenizer
exactly - it just needs to produce consistent, reasonably-sized chunks).
"""
from __future__ import annotations

import re
import uuid

import tiktoken

from app.config import get_settings
from app.schemas import Chunk

_settings = get_settings()
_encoding = tiktoken.get_encoding("cl100k_base")


def _split_into_paragraphs(text: str) -> list[str]:
    # Normalize whitespace, split on blank lines / sentence boundaries as fallback
    paragraphs = re.split(r"\n\s*\n", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    return paragraphs


def chunk_text(
    text: str,
    source_id: str,
    locator_prefix: str = "",
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    Split `text` into overlapping chunks of roughly `chunk_size` tokens.

    Strategy: greedily pack paragraphs into a chunk until the token budget
    is exceeded, then start a new chunk that re-includes the last
    `overlap` tokens of context for continuity.
    """
    chunk_size = chunk_size or _settings.chunk_size_tokens
    overlap = overlap or _settings.chunk_overlap_tokens

    paragraphs = _split_into_paragraphs(text)
    if not paragraphs:
        return []

    chunks: list[Chunk] = []
    current_tokens: list[int] = []

    def flush(idx: int):
        if not current_tokens:
            return
        chunk_str = _encoding.decode(current_tokens).strip()
        if chunk_str:
            locator = f"{locator_prefix} (part {idx})" if locator_prefix else f"part {idx}"
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    source_id=source_id,
                    text=chunk_str,
                    locator=locator,
                )
            )

    part_idx = 1
    for para in paragraphs:
        para_tokens = _encoding.encode(para + "\n\n")
        if current_tokens and len(current_tokens) + len(para_tokens) > chunk_size:
            flush(part_idx)
            part_idx += 1
            # carry over overlap from the end of the previous chunk
            current_tokens = current_tokens[-overlap:] if overlap > 0 else []

        # If a single paragraph is itself larger than chunk_size, hard-split it
        if len(para_tokens) > chunk_size:
            for i in range(0, len(para_tokens), chunk_size - overlap):
                window = para_tokens[i : i + chunk_size]
                current_tokens.extend(window)
                if len(current_tokens) >= chunk_size:
                    flush(part_idx)
                    part_idx += 1
                    current_tokens = current_tokens[-overlap:] if overlap > 0 else []
        else:
            current_tokens.extend(para_tokens)

    flush(part_idx)
    return chunks


def chunk_slides(slides: list[dict], source_id: str) -> list[Chunk]:
    """
    slides: [{"slide_number": int, "text": str}]
    One chunk per slide (slides are usually small and self-contained),
    but very long slides are further split by chunk_text.
    """
    chunks: list[Chunk] = []
    for slide in slides:
        text = slide["text"].strip()
        if not text:
            continue
        locator = f"Slide {slide['slide_number']}"
        sub_chunks = chunk_text(text, source_id, locator_prefix=locator)
        if len(sub_chunks) == 1:
            sub_chunks[0].locator = locator
        chunks.extend(sub_chunks)
    return chunks


def chunk_transcript_segments(segments: list[dict], source_id: str, window_seconds: int = 60) -> list[Chunk]:
    """
    segments: [{"start": float, "duration": float, "text": str}]  (youtube_transcript_api format)
    Groups transcript segments into ~window_seconds windows so each chunk
    can cite a timestamp like "at 3:22".
    """
    if not segments:
        return []

    chunks: list[Chunk] = []
    bucket_text: list[str] = []
    bucket_start = segments[0]["start"]

    def fmt_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    for seg in segments:
        if seg["start"] - bucket_start > window_seconds and bucket_text:
            text = " ".join(bucket_text).strip()
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    source_id=source_id,
                    text=text,
                    locator=f"at {fmt_time(bucket_start)}",
                )
            )
            bucket_text = []
            bucket_start = seg["start"]
        bucket_text.append(seg["text"])

    if bucket_text:
        text = " ".join(bucket_text).strip()
        chunks.append(
            Chunk(
                chunk_id=str(uuid.uuid4()),
                source_id=source_id,
                text=text,
                locator=f"at {fmt_time(bucket_start)}",
            )
        )

    return chunks
