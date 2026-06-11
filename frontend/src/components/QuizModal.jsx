import React, { useState } from "react";
import { generateQuiz } from "../api";

export default function QuizModal({ sessionId, sources, onClose }) {
  const [numQuestions, setNumQuestions] = useState(5);
  const [sourceId, setSourceId] = useState("");
  const [questions, setQuestions] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const readySources = sources.filter((s) => s.status === "ready");

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setQuestions(null);
    setAnswers({});
    setSubmitted(false);
    try {
      const data = await generateQuiz(sessionId, numQuestions, sourceId || null);
      setQuestions(data.questions);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const score = questions
    ? questions.reduce((acc, q, i) => acc + (answers[i] === q.correct_index ? 1 : 0), 0)
    : 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🧠 Quiz Mode</h2>
          <button className="remove-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        {!questions && (
          <div className="quiz-setup">
            <label>
              Number of questions:
              <input
                type="number"
                min={1}
                max={10}
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
              />
            </label>
            <label>
              Source:
              <select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
                <option value="">All sources</option>
                {readySources.map((s) => (
                  <option key={s.source_id} value={s.source_id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </label>
            <button onClick={handleGenerate} disabled={loading}>
              {loading ? "Generating…" : "Generate Quiz"}
            </button>
            {error && <div className="error-banner">{error}</div>}
          </div>
        )}

        {questions && (
          <div className="quiz-body">
            {questions.map((q, i) => (
              <div className="quiz-question" key={i}>
                <p className="quiz-question-text">
                  {i + 1}. {q.question}
                </p>
                <div className="quiz-options">
                  {q.options.map((opt, oi) => {
                    const isSelected = answers[i] === oi;
                    const isCorrect = oi === q.correct_index;
                    let cls = "quiz-option";
                    if (submitted) {
                      if (isCorrect) cls += " correct";
                      else if (isSelected) cls += " incorrect";
                    } else if (isSelected) {
                      cls += " selected";
                    }
                    return (
                      <button
                        key={oi}
                        className={cls}
                        disabled={submitted}
                        onClick={() => setAnswers((prev) => ({ ...prev, [i]: oi }))}
                      >
                        {opt}
                      </button>
                    );
                  })}
                </div>
                {submitted && (
                  <p className="quiz-explanation">
                    {q.explanation} <span className="quiz-source">({q.source_locator})</span>
                  </p>
                )}
              </div>
            ))}

            <div className="quiz-footer">
              {!submitted ? (
                <button onClick={() => setSubmitted(true)} disabled={Object.keys(answers).length < questions.length}>
                  Submit Answers
                </button>
              ) : (
                <>
                  <p className="quiz-score">
                    Score: {score} / {questions.length}
                  </p>
                  <button onClick={handleGenerate}>New Quiz</button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
