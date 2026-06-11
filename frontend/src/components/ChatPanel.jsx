import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { streamChat } from "../api";

export default function ChatPanel({ sessionId, hasReadySources, onOpenQuiz }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("qa");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const handleSend = async (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    if (!hasReadySources) {
      setError("Add at least one source and wait for it to finish processing before asking questions.");
      return;
    }

    setError("");
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "", citations: [] }]);
    setStreaming(true);

    let assistantText = "";

    await streamChat({
      sessionId,
      message: text,
      mode,
      onToken: (token) => {
        assistantText += token;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], content: assistantText };
          return next;
        });
      },
      onDone: (citations) => {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], citations };
          return next;
        });
        setStreaming(false);
      },
      onError: (msg) => {
        setError(msg);
        setMessages((prev) => prev.slice(0, -1)); // drop empty assistant bubble
        setStreaming(false);
      },
    });
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>AI Learning Assistant</h2>
        <div className="chat-controls">
          <label className="mode-toggle">
            <input
              type="checkbox"
              checked={mode === "simple"}
              onChange={(e) => setMode(e.target.checked ? "simple" : "qa")}
            />
            Explain simply
          </label>
          <button className="quiz-btn" onClick={onOpenQuiz} disabled={!hasReadySources}>
            🧠 Quiz me
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>👋 Add a source on the left, then ask a question about it here.</p>
            <p className="chat-empty-examples">
              Try: <em>"Summarize this in simple terms"</em> or <em>"What does the video say about X?"</em>
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div className={`message ${m.role}`} key={i}>
            <div className="message-bubble">
              <ReactMarkdown>{m.content || (streaming && i === messages.length - 1 ? "▍" : "")}</ReactMarkdown>
            </div>
            {m.role === "assistant" && m.citations?.length > 0 && (
              <div className="citations">
                {m.citations.map((c, idx) => (
                  <span className="citation-chip" key={idx}>
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Ask a question about your sources…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming}
        />
        <button type="submit" disabled={streaming || !input.trim()}>
          {streaming ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
