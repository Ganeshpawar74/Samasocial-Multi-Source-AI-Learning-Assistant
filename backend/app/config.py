"""
Centralized application configuration.
All environment-driven settings live here so the rest of the codebase
never reads os.environ directly.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM provider (Mistral AI) ---
    mistral_api_key: str = ""
    mistral_chat_model: str = "mistral-small-latest"
    mistral_temperature: float = 0.2

    # --- Embeddings (local / free, runs on CPU via sentence-transformers) ---
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # --- Chunking ---
    chunk_size_tokens: int = 350
    chunk_overlap_tokens: int = 60
    top_k_chunks: int = 5

    # --- Sessions ---
    session_ttl_minutes: int = 120

    # --- CORS ---
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- YouTube transcription ---
    # "captions"     -> use youtube-transcript-api (fast, requires existing captions)
    # "whisper_audio" -> always download full audio with yt-dlp and transcribe
    #                    locally with openai-whisper (slow, but works on any
    #                    video regardless of caption availability/language)
    youtube_transcription_mode: str = "whisper_audio"

    # Kept for backwards compatibility with the old captions->whisper fallback path.
    youtube_whisper_fallback_enabled: bool = True

    # Local Whisper model size used for full-audio transcription
    # (tiny / base / small / medium / large)
    whisper_model: str = "small"

    # Deprecated alias, kept so existing .env files using the old name keep working.
    whisper_model_size: str = "base"

    # Length (in minutes) of each audio chunk sent to Whisper
    whisper_chunk_minutes: int = 10

    # --- Sarvam AI (Hindi / Hinglish STT + English translation) ---
    # Get a free key at https://dashboard.sarvam.ai/
    sarvam_api_key: str = ""
    sarvam_stt_model: str = "saaras:v2.5"


@lru_cache
def get_settings() -> Settings:
    return Settings()