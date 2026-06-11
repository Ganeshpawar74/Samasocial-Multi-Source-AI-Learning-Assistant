# Samasocial — Multi-Source AI Learning Assistant

🚀 A powerful web-based AI learning platform that ingests **PDFs, PPTX slides, YouTube videos, and webpages**, indexes them with semantic embeddings, and answers questions **strictly grounded** in that content — with intelligent citations, real-time streaming responses, multi-language support, session memory, and interactive quiz generation.

---

## ✨ Key Features

| Feature | Implementation | Status |
|---|---|---|
| 📄 **Multi-Source Input** | PDF, PPTX, YouTube, Webpage | ✅ Full Support |
| 🎯 **Semantic Search & Retrieval** | FAISS vector store with top-k retrieval | ✅ Optimized |
| 🔗 **Smart Source Citations** | Automatic locators (page, slide, timestamp) | ✅ Context-Aware |
| 📡 **Streaming Responses** | Server-Sent Events (SSE) for real-time output | ✅ Low Latency |
| 💾 **Session Memory** | Per-session chat history & knowledge base | ✅ In-Memory |
| 🌍 **Multilingual Support** | Hindi/Hinglish STT via Sarvam AI | ✅ Live |
| 🧠 **Smart Question Detection** | Out-of-scope graceful handling | ✅ Enforced |
| 🎓 **Interactive Quiz Mode** | AI-generated MCQ assessments | ✅ JSON Mode |
| 🏷️ **Source Management** | Visual badges with summaries & status | ✅ Real-time |
| ⚡ **Local Embeddings** | CPU-friendly, no rate limits | ✅ Cost-Effective |

---

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│     React Frontend (Vite)        │
│  - Session Management            │
│  - Source Upload & Management    │
│  - Streaming Chat UI             │
│  - Quiz Interface                │
└────────────┬────────────────────┘
             │ (HTTP/SSE)
             ↓
┌─────────────────────────────────┐       ┌──────────────────────┐
│   FastAPI Backend (Python)       │◄─────►│  Multiple LLM Tiers  │
│                                  │       │  - Mistral AI        │
│ /api/sources/*                   │       │  - OpenAI (GPT)      │
│  ├─ PDF parser & chunker         │       │  - Groq (Llama)      │
│  ├─ PPTX parser & slide chunker  │       │  - Gemini            │
│  ├─ YouTube audio extraction     │       │  - HuggingFace       │
│  ├─ Webpage scraper & parser     │       └──────────────────────┘
│  └─ Vector embedding (sentence)  │
│      ─transformers)              │       ┌──────────────────────┐
│                                  │◄─────►│  Speech-to-Text      │
│ /api/chat/*                      │       │  - Sarvam AI (Hindi) │
│  ├─ Semantic search (FAISS)      │       │  - Whisper (Multilng)│
│  ├─ Streaming chat completion    │       │  - Faster-Whisper    │
│  └─ Quiz generation (JSON)       │       └──────────────────────┘
│                                  │
└─────────────────────────────────┘
```

### Design Philosophy

**Multi-Provider LLM Support**: The system supports multiple LLM providers simultaneously:
- **Mistral AI** (default, free tier) — fast, streaming-capable
- **OpenAI GPT** — powerful, versatile
- **Groq Llama** — ultra-fast inference
- **Google Gemini** — advanced reasoning
- **HuggingFace** — open-source models

**Local-First Embeddings**: Sentence-transformers runs locally on CPU with zero API calls for retrieval, ensuring:
- ✅ No rate limits
- ✅ Zero latency between chunks
- ✅ Complete privacy
- ✅ Minimal operational cost

**Multilingual Speech Processing**:
- **Sarvam AI**: Native Hindi/Hinglish support with automatic English translation
- **OpenAI Whisper**: Supports 99+ languages, with optional faster-whisper fallback
- Full audio download via `yt-dlp` for maximum accuracy on YouTube

**Intelligent Chunking**:
- **PDF**: Page-based with token-aware overlap (≈350 tokens, 60 overlap)
- **PPTX**: Slide-level with automatic large-slide splitting
- **YouTube**: 10-minute audio chunks → Whisper transcription → 60-second semantic windows
- **Webpages**: Boilerplate-stripped HTML → token-chunked

**Session Architecture**:
- Per-session FAISS IndexFlatIP (cosine similarity)
- Thread-safe in-memory storage with auto-cleanup
- Session TTL with background cleanup

---

## 🚀 Quick Start

### Prerequisites
- **Python** 3.10+ with pip
- **Node.js** 18+ with npm
- **FFmpeg** (for YouTube audio processing)
  - Windows: `winget install ffmpeg` or download from https://ffmpeg.org/download.html
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
- **API Keys** (at least one LLM provider):
  - Mistral AI: https://console.mistral.ai/ (free tier)
  - OpenAI: https://platform.openai.com/api-keys (optional)
  - Groq: https://console.groq.com (optional, free)
  - Google Gemini: https://ai.google.dev (optional, free)
  - Sarvam AI: https://dashboard.sarvam.ai/ (optional, for Hindi support)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
nano .env  # or open in your editor

# Start server
uvicorn app.main:app --reload --port 8000
```

✅ **First startup**: Downloads sentence-transformers embedding model (~80MB, cached thereafter)

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

✅ **Access**: http://localhost:3000 (automatically proxies `/api` to localhost:8000)

---

## 🔑 Environment Variables

### Core LLM Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `MISTRAL_API_KEY` | ❌ (one LLM required) | — | Mistral API key (https://console.mistral.ai) |
| `MISTRAL_CHAT_MODEL` | ❌ | `mistral-small-latest` | Mistral model choice |
| `MISTRAL_TEMPERATURE` | ❌ | `0.2` | Response creativity (0=deterministic, 1=creative) |
| `OPENAI_API_KEY` | ❌ (optional) | — | OpenAI API key for GPT models |
| `GROQ_API_KEY` | ❌ (optional) | — | Groq API key for Llama models |
| `GEMINI_API_KEY` | ❌ (optional) | — | Google Gemini API key |
| `HUGGINGFACEHUB_API_TOKEN` | ❌ (optional) | — | HuggingFace API token |

### Embedding & Retrieval

| Variable | Default | Purpose |
|---|---|---|
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `EMBEDDING_DIM` | `384` | Embedding vector dimension |
| `TOP_K_CHUNKS` | `5` | Chunks retrieved per query |
| `CHUNK_SIZE_TOKENS` | `350` | Target chunk size |
| `CHUNK_OVERLAP_TOKENS` | `60` | Overlap between chunks |

### YouTube Processing

| Variable | Default | Purpose |
|---|---|---|
| `YOUTUBE_TRANSCRIPTION_MODE` | `whisper_audio` | `"whisper_audio"` (full) or `"captions"` (fast) |
| `WHISPER_MODEL` | `small` | Model size: `tiny`, `base`, `small`, `medium`, `large` |
| `WHISPER_CHUNK_MINUTES` | `10` | Audio chunk duration for Whisper |
| `YOUTUBE_WHISPER_FALLBACK_ENABLED` | `true` | Fallback to faster-whisper if no captions |

### Multilingual Speech-to-Text

| Variable | Default | Purpose |
|---|---|---|
| `SARVAM_API_KEY` | — | Sarvam API key (https://dashboard.sarvam.ai) |
| `SARVAM_STT_MODEL` | `saaras:v2.5` | Sarvam model for Hindi/Hinglish transcription |

### Session & CORS

| Variable | Default | Purpose |
|---|---|---|
| `SESSION_TTL_MINUTES` | `120` | Session expiration time |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS-allowed origins |

---

## 📖 Usage Guide

### 1️⃣ Start a Session
- Opens automatically when you visit http://localhost:3000
- Session ID persists in browser memory (lost on page reload)

### 2️⃣ Add Knowledge Sources
Upload or link your learning material:

**Upload Files:**
- 📄 PDF documents (text-based)
- 📊 PowerPoint presentations

**Paste URLs:**
- 🎬 YouTube videos (audio transcribed locally)
- 🌐 Webpages (HTML parsed, boilerplate removed)

### 3️⃣ Monitor Processing
Each source shows a status badge:
- ⏳ **Processing** — Being ingested & embedded
- ✅ **Ready** — Indexed and AI-summarized
- ❌ **Failed** — Check error message

### 4️⃣ Ask Questions
- **Question**: Type in the chat box
- **Mode**: Toggle "Explain simply" for beginner-friendly answers
- **Response**: Streams in real-time with source citations

Example citations:
- `(Lecture Slides — Slide 4)`
- `(Intro Video — at 02:15)`
- `(Research Paper — Page 7)`

### 5️⃣ Generate Quizzes
Click **"🧠 Quiz me"** to:
- Generate 5 MCQ questions (or specify count)
- Optionally limit to one source
- Answer interactively
- See score & explanations

### 6️⃣ Remove Sources
Hover over a source badge → click ✕ to remove (rebuilds index)

---

## 🛠️ API Endpoints

### Sources
```
POST   /api/sources/pdf          → Upload PDF
POST   /api/sources/pptx         → Upload PowerPoint
POST   /api/sources/youtube      → Add YouTube URL
POST   /api/sources/webpage      → Add webpage URL
DELETE /api/sources/{sessionId}/{sourceId} → Remove source
```

### Chat
```
POST   /api/chat/session         → Create session
POST   /api/chat/stream          → Stream chat response (SSE)
POST   /api/chat/quiz            → Generate quiz
GET    /api/chat/{sessionId}/history → Get chat history
GET    /api/health               → Health check
```

---

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entrypoint
│   │   ├── config.py               # Settings & environment variables
│   │   ├── schemas.py              # Pydantic data models
│   │   ├── routers/
│   │   │   ├── sources.py          # Source upload endpoints
│   │   │   └── chat.py             # Chat & quiz endpoints
│   │   └── services/
│   │       ├── parsers.py          # PDF/PPTX/YouTube/webpage parsing
│   │       ├── chunking.py         # Text chunking strategies
│   │       ├── vector_store.py     # FAISS semantic search
│   │       ├── llm.py              # LLM provider abstractions
│   │       ├── session_store.py    # Session management
│   │       └── utils.py            # Helper functions
│   ├── requirements.txt            # Python dependencies
│   └── .env                        # Environment configuration
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main React component
│   │   ├── api.js                  # Backend API client
│   │   ├── styles.css              # Global styles
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx       # Chat interface
│   │   │   ├── SourcePanel.jsx     # Source management
│   │   │   └── QuizModal.jsx       # Quiz UI
│   │   └── main.jsx                # React entry point
│   ├── package.json                # Node dependencies
│   ├── vite.config.js              # Vite dev server config
│   └── index.html                  # HTML template
│
└── README.md (this file)
```

---

## 💡 Advanced Configuration

### Switch LLM Provider

Edit `backend/app/services/llm.py`:
```python
# Use OpenAI instead of Mistral
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
```

All LLM calls are isolated in one file, making swaps simple.

### Tune Retrieval Quality

In `.env`:
```bash
# Adjust chunk size (more context per retrieval)
CHUNK_SIZE_TOKENS=500

# Adjust overlap (smoother transitions)
CHUNK_OVERLAP_TOKENS=100

# Retrieve more chunks per query
TOP_K_CHUNKS=10

# Sensitivity of semantic search
# (Managed via normalized inner product in FAISS)
```

### Enable Fast YouTube Captions Mode

```bash
YOUTUBE_TRANSCRIPTION_MODE=captions
YOUTUBE_WHISPER_FALLBACK_ENABLED=true
```

- ✅ Near-instant if captions exist
- ⏱️ Falls back to Whisper if missing
- 🎯 Best for videos with good captions

### Enable Hindi/Hinglish Support

```bash
SARVAM_API_KEY=sk_xxxx_xxxx
SARVAM_STT_MODEL=saaras:v2.5
```

Adds native support for Hindi and Hinglish speech-to-text with automatic English translation.

---

## ⚠️ Known Limitations & Future Work

### Current Limitations

- **In-Memory Sessions**: Lost on server restart. Production should use **Redis** (history) + **Supabase/pgvector** (vectors) as per brief's preferred stack.

- **YouTube Audio Processing** (`whisper_audio` mode): 
  - ⏳ Slow: full audio download + FFmpeg conversion + Whisper transcription
  - 💪 CPU-intensive, especially with larger Whisper models
  - ✅ Accurate even for videos with no/poor/auto-generated captions
  - 🌍 Works for any language Whisper supports
  - 💡 Use `captions` mode for faster processing when captions exist

- **Scanned PDFs**: Text-only extraction. OCR (e.g., `pytesseract`) needed for image-only PDFs.

- **Blocking Source Ingestion**: Upload blocks request. Should use background tasks + progress polling for large files.

- **FAISS Limitations**: Flat index doesn't support deletion, so removing a source rebuilds entire index.

### Planned Improvements

- [ ] Redis session backend with TTL
- [ ] Persistent vector database (Supabase pgvector)
- [ ] Async source processing with progress polling
- [ ] Document segmentation & OCR for scanned PDFs
- [ ] Multi-worker deployment with load balancing
- [ ] Document version control & audit logs
- [ ] Bulk source import from cloud storage
- [ ] Custom prompt templates per session
- [ ] Advanced analytics & usage tracking
- [ ] Multi-user collaboration features

---

## 🔧 Development

### Running Tests
```bash
cd backend
pytest tests/ -v
```

### Building for Production
```bash
# Backend
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker

# Frontend
cd frontend
npm run build
# Output in: frontend/dist/
```

### Debugging

**Backend Logs**:
```bash
uvicorn app.main:app --log-level debug
```

**Frontend Errors**:
- Open DevTools (F12) → Console tab
- Check Vite dev server terminal for build errors

---

## 📝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -am 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

---

## 📄 License

This project is part of the **Samasocial** learning platform initiative.

---

## 🆘 Support & Troubleshooting

### "MISTRAL_API_KEY is not set"
→ Create `.env` in `backend/` with `MISTRAL_API_KEY=your_key`

### "Session not found"
→ Create session first: visit frontend or call `POST /api/chat/session`

### "No processed sources available"
→ Upload a source and wait for badge to show **Ready**

### "FFmpeg not found"
→ Install FFmpeg:
- Windows: `winget install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### "CORS error from frontend"
→ Check `ALLOWED_ORIGINS` in `.env` includes your frontend URL

### Slow YouTube processing
→ Switch to `YOUTUBE_TRANSCRIPTION_MODE=captions` or use smaller `WHISPER_MODEL=tiny`

---

## 🚀 What's New in This Update

✨ **Multi-Provider LLM Support** — Now supports OpenAI, Groq, Gemini, and HuggingFace alongside Mistral  
🌍 **Multilingual Speech-to-Text** — Integrated Sarvam AI for Hindi/Hinglish transcription  
⚡ **Enhanced Configuration** — Comprehensive environment variables for fine-tuning  
📚 **Improved Documentation** — Complete API reference and troubleshooting guide  
🎯 **Better Architecture Docs** — Clear visualization of data flow and component interaction