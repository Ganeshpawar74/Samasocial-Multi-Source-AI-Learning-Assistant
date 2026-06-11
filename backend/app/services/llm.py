"""
Thin wrapper around the Mistral AI chat API.

Centralizing this here means:
  - Prompt templates live in one place
  - The rest of the app doesn't depend on the mistralai SDK directly
  - Swapping providers later (e.g. to a HF-hosted model) only touches this file
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

from mistralai.async_client import MistralAsyncClient
from mistralai.models.chat_completion import ChatMessage as MistralChatMessage

from app.config import get_settings
from app.schemas import Chunk

_settings = get_settings()


def _get_client() -> MistralAsyncClient:
    if not _settings.mistral_api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Add it to your .env file. "
        )
    return MistralAsyncClient(api_key=_settings.mistral_api_key)


SYSTEM_PROMPT_QA = """You are an AI Learning Assistant for Samasocial, a social learning platform.

You answer questions STRICTLY using the provided CONTEXT, which consists of excerpts
from the user's uploaded documents, slides, web pages, and/or video transcripts.

Rules:
1. Only use information present in the CONTEXT below. Do not use outside knowledge.
2. If the CONTEXT does not contain enough information to answer, say so clearly and
   politely - do NOT make up an answer. Suggest what kind of source might help instead.
3. When you use information from a chunk, mention its source label in your answer
   in parentheses, e.g. "(Source: Slide 4)" or "(Source: at 03:22)".
4. Keep answers clear and well-structured. Use short paragraphs or bullet points.
"""

SYSTEM_PROMPT_SIMPLE = SYSTEM_PROMPT_QA + """
The user has asked for a SIMPLE explanation. Explain the concept in plain,
beginner-friendly language, using an analogy or example if it helps, while
still grounding the explanation in the CONTEXT and citing sources.
"""

SYSTEM_PROMPT_SUMMARY = """You are an AI Learning Assistant. Summarize the following content
from a single source in 3-5 concise sentences, capturing the main topics and key takeaways.
Do not add information that isn't in the text. Do not mention "the text" or "the document" -
write the summary as standalone content."""

SYSTEM_PROMPT_QUIZ = """You are an AI Learning Assistant generating a multiple-choice quiz
based STRICTLY on the provided CONTEXT.

Return ONLY valid JSON (no markdown fences, no extra commentary) matching this schema:
{
  "questions": [
    {
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_index": 0,
      "explanation": "string - why this answer is correct, referencing the context",
      "source_locator": "string - the source label this question is based on"
    }
  ]
}

Generate exactly the requested number of questions. Each question must have exactly
4 options and test understanding of a different part of the context where possible."""


def _build_context_block(chunks: list[Chunk], source_titles: dict[str, str]) -> str:
    parts = []
    for chunk in chunks:
        title = source_titles.get(chunk.source_id, "Unknown source")
        parts.append(f"[Source: {title} | {chunk.locator}]\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


async def stream_chat_completion(
    *,
    history: list[dict],
    user_message: str,
    retrieved_chunks: list[Chunk],
    source_titles: dict[str, str],
    mode: str = "qa",
) -> AsyncGenerator[str, None]:
    """
    Streams the assistant's reply token-by-token.

    `history` is a list of {"role": "user"|"assistant", "content": str}
    representing prior turns in the session (session memory).
    """
    client = _get_client()

    if not retrieved_chunks:
        context_block = "(No relevant content was found in the loaded sources for this question.)"
    else:
        context_block = _build_context_block(retrieved_chunks, source_titles)

    system_prompt = SYSTEM_PROMPT_SIMPLE if mode == "simple" else SYSTEM_PROMPT_QA

    messages = [MistralChatMessage(role="system", content=system_prompt)]
    for turn in history[-10:]:  # cap context window growth
        messages.append(MistralChatMessage(role=turn["role"], content=turn["content"]))

    messages.append(
        MistralChatMessage(
            role="user",
            content=f"CONTEXT:\n{context_block}\n\nQUESTION:\n{user_message}",
        )
    )

    async for chunk in client.chat_stream(
        model=_settings.mistral_chat_model,
        messages=messages,
        temperature=_settings.mistral_temperature,
    ):
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def generate_summary(text: str, max_chars: int = 6000) -> str:
    client = _get_client()
    truncated = text[:max_chars]

    messages = [
        MistralChatMessage(role="system", content=SYSTEM_PROMPT_SUMMARY),
        MistralChatMessage(role="user", content=truncated),
    ]
    response = await client.chat(
        model=_settings.mistral_chat_model,
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


async def generate_quiz(chunks: list[Chunk], source_titles: dict[str, str], num_questions: int) -> list[dict]:
    client = _get_client()
    context_block = _build_context_block(chunks, source_titles)

    messages = [
        MistralChatMessage(role="system", content=SYSTEM_PROMPT_QUIZ),
        MistralChatMessage(
            role="user",
            content=f"Generate {num_questions} questions from this context:\n\n{context_block}",
        ),
    ]
    response = await client.chat(
        model=_settings.mistral_chat_model,
        messages=messages,
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON for quiz: {exc}") from exc

    questions = data.get("questions", [])
    if not questions:
        raise ValueError("LLM returned no quiz questions.")
    return questions
