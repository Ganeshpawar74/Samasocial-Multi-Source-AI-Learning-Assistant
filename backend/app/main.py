"""
Application entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import chat, sources

settings = get_settings()

app = FastAPI(
    title="Samasocial Multi-Source AI Learning Assistant",
    description="Task 1 - Full-Stack AI Feature Build",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
