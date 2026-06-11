import React, { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import SourcePanel from "./components/SourcePanel.jsx";
import QuizModal from "./components/QuizModal.jsx";
import { createSession } from "./api";

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [sources, setSources] = useState([]);
  const [busy, setBusy] = useState(false);
  const [quizOpen, setQuizOpen] = useState(false);
  const [initError, setInitError] = useState("");

  useEffect(() => {
    createSession()
      .then((data) => setSessionId(data.session_id))
      .catch((e) => setInitError(e.message));
  }, []);

  const hasReadySources = sources.some((s) => s.status === "ready");

  if (initError) {
    return (
      <div className="app-error">
        <h1>Could not connect to backend</h1>
        <p>{initError}</p>
        <p>Make sure the FastAPI server is running on port 8000.</p>
      </div>
    );
  }

  if (!sessionId) {
    return <div className="app-loading">Starting session…</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Samasocial — Multi-Source AI Learning Assistant</h1>
        <span className="session-pill">Session: {sessionId.slice(0, 8)}</span>
      </header>

      <main className="app-main">
        <SourcePanel sessionId={sessionId} sources={sources} setSources={setSources} busy={busy} setBusy={setBusy} />
        <ChatPanel sessionId={sessionId} hasReadySources={hasReadySources} onOpenQuiz={() => setQuizOpen(true)} />
      </main>

      {quizOpen && <QuizModal sessionId={sessionId} sources={sources} onClose={() => setQuizOpen(false)} />}
    </div>
  );
}
