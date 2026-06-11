import React, { useRef, useState } from "react";
import { addUrlSource, removeSource, uploadFileSource } from "../api";

const TYPE_LABELS = {
  pdf: "PDF",
  pptx: "Slides",
  youtube: "YouTube",
  webpage: "Webpage",
};

const TYPE_ICONS = {
  pdf: "📄",
  pptx: "📊",
  youtube: "▶️",
  webpage: "🌐",
};

export default function SourcePanel({ sessionId, sources, setSources, busy, setBusy }) {
  const pdfInputRef = useRef(null);
  const pptxInputRef = useRef(null);
  const [urlInput, setUrlInput] = useState("");
  const [urlType, setUrlType] = useState("youtube");
  const [error, setError] = useState("");

  const upsertSource = (meta) => {
    setSources((prev) => {
      const others = prev.filter((s) => s.source_id !== meta.source_id);
      return [...others, meta];
    });
  };

  const handleFile = async (kind, file) => {
    if (!file) return;
    setError("");
    setBusy(true);

    // Optimistic placeholder badge
    const placeholderId = `pending-${Date.now()}`;
    upsertSource({
      source_id: placeholderId,
      type: kind,
      title: file.name,
      origin: file.name,
      status: "processing",
    });

    try {
      const meta = await uploadFileSource(kind, sessionId, file);
      setSources((prev) => prev.filter((s) => s.source_id !== placeholderId).concat(meta));
      if (meta.status === "failed") setError(meta.error || "Failed to process file.");
    } catch (e) {
      setSources((prev) => prev.filter((s) => s.source_id !== placeholderId));
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleUrlSubmit = async (e) => {
    e.preventDefault();
    if (!urlInput.trim()) return;
    setError("");
    setBusy(true);

    const placeholderId = `pending-${Date.now()}`;
    upsertSource({
      source_id: placeholderId,
      type: urlType,
      title: urlInput,
      origin: urlInput,
      status: "processing",
    });

    try {
      const meta = await addUrlSource(urlType, sessionId, urlInput.trim());
      setSources((prev) => prev.filter((s) => s.source_id !== placeholderId).concat(meta));
      if (meta.status === "failed") setError(meta.error || "Failed to process URL.");
      else setUrlInput("");
    } catch (e) {
      setSources((prev) => prev.filter((s) => s.source_id !== placeholderId));
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (sourceId) => {
    setSources((prev) => prev.filter((s) => s.source_id !== sourceId));
    try {
      await removeSource(sessionId, sourceId);
    } catch {
      /* best-effort */
    }
  };

  return (
    <div className="source-panel">
      <h2>Knowledge Sources</h2>
      <p className="hint">Add one or more sources, then ask questions grounded in their content.</p>

      <div className="upload-row">
        <button disabled={busy} onClick={() => pdfInputRef.current?.click()}>
          📄 Upload PDF
        </button>
        <input
          ref={pdfInputRef}
          type="file"
          accept="application/pdf"
          hidden
          onChange={(e) => handleFile("pdf", e.target.files[0])}
        />

        <button disabled={busy} onClick={() => pptxInputRef.current?.click()}>
          📊 Upload PPTX
        </button>
        <input
          ref={pptxInputRef}
          type="file"
          accept=".pptx"
          hidden
          onChange={(e) => handleFile("pptx", e.target.files[0])}
        />
      </div>

      <form className="url-row" onSubmit={handleUrlSubmit}>
        <select value={urlType} onChange={(e) => setUrlType(e.target.value)} disabled={busy}>
          <option value="youtube">YouTube URL</option>
          <option value="webpage">Webpage URL</option>
        </select>
        <input
          type="url"
          placeholder={urlType === "youtube" ? "https://youtube.com/watch?v=..." : "https://example.com/article"}
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          disabled={busy}
          required
        />
        <button type="submit" disabled={busy}>
          Add
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      <div className="source-list">
        {sources.length === 0 && <p className="empty">No sources loaded yet.</p>}
        {sources.map((s) => (
          <div className={`source-badge ${s.status}`} key={s.source_id}>
            <div className="badge-header">
              <span className="badge-icon">{TYPE_ICONS[s.type] || "📁"}</span>
              <span className="badge-title" title={s.title}>
                {s.title}
              </span>
              <button className="remove-btn" onClick={() => handleRemove(s.source_id)} title="Remove source">
                ✕
              </button>
            </div>
            <div className="badge-meta">
              <span className="badge-type">{TYPE_LABELS[s.type] || s.type}</span>
              {s.status === "processing" && <span className="badge-status processing">Processing…</span>}
              {s.status === "ready" && <span className="badge-status ready">Ready · {s.num_chunks} chunks</span>}
              {s.status === "failed" && <span className="badge-status failed">Failed</span>}
            </div>
            {s.status === "ready" && s.summary && <p className="badge-summary">{s.summary}</p>}
            {s.status === "failed" && s.error && <p className="badge-error">{s.error}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
