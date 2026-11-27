import React from "react";
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  ChevronRight,
  FileText,
  HelpCircle,
  RefreshCw,
  Target,
  Trash2,
} from "lucide-react";
import {
  Button,
  CitationsList,
  EmptyState,
  percent,
  SectionHeader,
} from "./Common";
import { api } from "../api";

export function Diagnostic({
  quiz,
  setQuiz,
  data,
  run,
  endpoint,
  busy,
  selectedTopics,
  setSelectedTopics,
  beginQuiz,
  resume,
  openSource,
  setPage,
  pending,
  drafts,
  setDrafts,
}) {
  const leaves = (data.topics || []).filter((t) => t.is_leaf);

  // Draft management
  const answers =
    quiz?.status === "submitted" ? quiz.answers || {} : drafts[quiz?.id] || {};

  const setAnswers = (update) =>
    setDrafts((current) => ({
      ...current,
      [quiz.id]:
        typeof update === "function" ? update(current[quiz.id] || {}) : update,
    }));

  async function submit(e) {
    e.preventDefault();
    await run("Evaluating responses against source evidence", async () => {
      const res = await api(endpoint(`quizzes/${quiz.id}/submit`), {
        method: "POST",
        body: { answers },
      });
      setQuiz(res);
    });
  }

  // Pre-quiz topic selection screen
  if (!quiz) {
    return (
      <div className="page-container">
        <SectionHeader
          title="Diagnostic"
          description="Source-grounded questions targeting knowledge gaps and syllabus weights"
        />

        {pending && (
          <div className="alert-banner alert-info">
            <div className="flex items-center gap-3">
              <Brain size={20} className="text-indigo-600 shrink-0" />
              <div>
                <strong className="block text-slate-800 font-semibold">
                  Unfinished diagnostic in progress
                </strong>
                <span className="text-slate-600 text-sm">
                  You have an unsubmitted quiz waiting for your answers.
                </span>
              </div>
            </div>
            <Button
              onClick={() => resume(pending.id)}
              disabled={!!busy}
              className="text-xs py-1.5 px-3"
            >
              Resume diagnostic
            </Button>
          </div>
        )}

        <div className="card">
          <div className="card-header-bar">
            <div>
              <h2 className="card-heading">Select topics to assess</h2>
              <p className="card-subheading">
                Leave all unchecked for an adaptive selection of high-priority
                topics. Each topic includes one multiple-choice question and one
                short-answer question.
              </p>
            </div>
            {selectedTopics.length > 0 && (
              <button
                type="button"
                className="btn btn-secondary text-xs py-1 px-2.5"
                onClick={() => setSelectedTopics([])}
              >
                Clear selection ({selectedTopics.length})
              </button>
            )}
          </div>

          {!leaves.length ? (
            <EmptyState
              icon={Brain}
              title="No syllabus topics available"
              description="Build your syllabus topic map in Materials or Topic map before starting a diagnostic."
            >
              <Button secondary onClick={() => setPage("topics")}>
                Go to Topic map
              </Button>
            </EmptyState>
          ) : (
            <>
              <div className="topic-picker-grid">
                {leaves.map((topic) => {
                  const isChecked = selectedTopics.includes(topic.id);
                  return (
                    <label
                      key={topic.id}
                      className={`topic-picker-item ${
                        isChecked ? "topic-picker-checked" : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        disabled={
                          !!busy ||
                          (!isChecked && selectedTopics.length >= 8)
                        }
                        onChange={(e) => {
                          setSelectedTopics((prev) =>
                            e.target.checked
                              ? [...prev, topic.id]
                              : prev.filter((id) => id !== topic.id)
                          );
                        }}
                        className="checkbox-field"
                      />
                      <div className="topic-picker-info">
                        <span className="topic-picker-name">{topic.name}</span>
                        <span className="topic-picker-weight">
                          {percent(topic.weight)} exam weight
                        </span>
                      </div>
                    </label>
                  );
                })}
              </div>

              <div className="card-footer-actions">
                <Button
                  icon={Brain}
                  disabled={!!busy || !leaves.length}
                  onClick={() => beginQuiz(selectedTopics)}
                >
                  {selectedTopics.length > 0
                    ? `Start diagnostic (${selectedTopics.length} ${
                        selectedTopics.length === 1 ? "topic" : "topics"
                      })`
                    : "Start adaptive diagnostic"}
                </Button>
                <span className="text-xs text-slate-500">
                  Questions are generated directly from indexed course excerpts.
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  // Quiz active or submitted screen
  const isSubmitted = quiz.status === "submitted";
  const answeredCount = Object.values(answers).filter(
    (a) => typeof a === "string" && a.trim().length > 0
  ).length;

  return (
    <div className="page-container">
      <div className="section-header">
        <div>
          <h1 className="section-title">
            {isSubmitted ? "Diagnostic results" : "Diagnostic assessment"}
          </h1>
          <p className="section-desc">
            {isSubmitted
              ? `Overall earned credit: ${percent(quiz.score)} · Results reflected in Gap report`
              : `${quiz.questions.length} questions · Source citations unlocked upon submission`}
          </p>
        </div>
        <div className="section-actions">
          {isSubmitted ? (
            <div className="flex gap-2">
              <Button
                icon={Target}
                onClick={() => setPage("gaps")}
              >
                View gap report
              </Button>
              <Button
                secondary
                icon={RefreshCw}
                onClick={() => {
                  setQuiz(null);
                  setSelectedTopics([]);
                }}
              >
                New diagnostic
              </Button>
            </div>
          ) : (
            <span className="quiz-progress-counter">
              <strong>{answeredCount}</strong> / {quiz.questions.length} answered
            </span>
          )}
        </div>
      </div>

      {quiz.skipped && quiz.skipped.length > 0 && (
        <div className="alert-banner alert-warning">
          <AlertCircle size={16} className="shrink-0" />
          <span className="text-sm">
            Some topics were excluded due to insufficient evidence:{" "}
            {quiz.skipped.map((s) => `${s.topic} (${s.reason})`).join("; ")}
          </span>
        </div>
      )}

      <form onSubmit={submit} className="quiz-form">
        <div className="question-stack">
          {quiz.questions.map((q, idx) => {
            const result = quiz.results?.find((r) => r.question_id === q.id);
            const isAnswered = answers[q.id] != null && answers[q.id] !== "";

            return (
              <article key={q.id} className="card question-card">
                <div className="question-header">
                  <div className="question-number-badge">
                    Question {idx + 1}
                  </div>
                  <span className="question-topic-tag">
                    {q.topic_name} · {q.kind === "mcq" ? "Multiple Choice" : "Short Answer"}
                  </span>
                </div>

                <h3 className="question-prompt">{q.prompt}</h3>

                {/* Source badges (locked during test, unlocked post-submission) */}
                <CitationsList
                  citations={q.citations}
                  onOpen={openSource}
                  locked={!isSubmitted}
                />

                {/* Question Input */}
                {q.kind === "mcq" ? (
                  <fieldset
                    disabled={isSubmitted || !!busy}
                    className="options-grid"
                  >
                    <legend className="sr-only">Options for Question {idx + 1}</legend>
                    {q.options.map((option, optIdx) => {
                      const isSelected = answers[q.id] === String(optIdx);
                      const isCorrect = isSubmitted && result?.answer_index === optIdx;
                      const isWrongChoice =
                        isSubmitted && isSelected && result?.answer_index !== optIdx;

                      return (
                        <label
                          key={optIdx}
                          className={`mcq-option ${isSelected ? "mcq-option-selected" : ""} ${
                            isCorrect ? "mcq-option-correct" : ""
                          } ${isWrongChoice ? "mcq-option-wrong" : ""}`}
                        >
                          <input
                            type="radio"
                            name={q.id}
                            value={optIdx}
                            checked={isSelected}
                            onChange={(e) =>
                              setAnswers((prev) => ({
                                ...prev,
                                [q.id]: e.target.value,
                              }))
                            }
                            className="sr-only"
                          />
                          <span className="mcq-letter">{"ABCD"[optIdx]}</span>
                          <span className="mcq-text">{option}</span>
                          {isCorrect && (
                            <CheckCircle2 size={16} className="text-emerald-600 ml-auto shrink-0" />
                          )}
                        </label>
                      );
                    })}
                  </fieldset>
                ) : (
                  <div className="form-group mt-3">
                    <label htmlFor={`answer-${q.id}`} className="text-xs font-semibold text-slate-700">
                      Your answer:
                    </label>
                    <textarea
                      id={`answer-${q.id}`}
                      rows={3}
                      value={answers[q.id] || ""}
                      disabled={isSubmitted || !!busy}
                      maxLength={3000}
                      placeholder="Write your explanation based on your understanding..."
                      onChange={(e) =>
                        setAnswers((prev) => ({
                          ...prev,
                          [q.id]: e.target.value,
                        }))
                      }
                      className="input-field textarea-field"
                    />
                  </div>
                )}

                {/* Post-submission Result & Evidence Feedback */}
                {result && (
                  <div
                    className={`evaluation-box ${
                      result.score >= 0.8
                        ? "eval-high"
                        : result.score >= 0.5
                        ? "eval-med"
                        : "eval-low"
                    }`}
                  >
                    <div className="eval-header">
                      <span className="eval-score">
                        Score: {percent(result.score)}
                      </span>
                      <span className="eval-method">
                        Evaluated by: {result.method?.replaceAll("_", " ")}
                      </span>
                    </div>

                    <p className="eval-feedback">{result.feedback}</p>

                    {result.reference_answer && (
                      <div className="eval-section">
                        <strong>Reference answer:</strong>
                        <p>{result.reference_answer}</p>
                      </div>
                    )}

                    {result.rubric && result.rubric.length > 0 && (
                      <div className="eval-section">
                        <strong>Evaluation rubric:</strong>
                        <ul className="eval-rubric-list">
                          {result.rubric.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {result.citations && result.citations.length > 0 && (
                      <div className="eval-section">
                        <strong>Source citations:</strong>
                        <CitationsList
                          citations={result.citations}
                          onOpen={openSource}
                        />
                        {result.citations.map((c, cIdx) =>
                          c.quote ? (
                            <blockquote key={cIdx} className="eval-quote">
                              "{c.quote}"
                            </blockquote>
                          ) : null
                        )}
                      </div>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>

        {/* Action Bar */}
        <div className="quiz-action-bar">
          {isSubmitted ? (
            <div className="flex flex-wrap gap-3">
              <Button
                icon={Target}
                onClick={() => setPage("gaps")}
              >
                Go to Gap report
              </Button>
              <Button
                secondary
                icon={RefreshCw}
                onClick={() => {
                  setQuiz(null);
                  setSelectedTopics([]);
                }}
              >
                Choose another diagnostic
              </Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-4 w-full">
              <div className="flex items-center gap-3">
                <Button
                  type="submit"
                  icon={CheckCircle2}
                  disabled={!!busy}
                >
                  Submit diagnostic
                </Button>
                <span className="text-xs text-slate-500">
                  Unanswered questions receive zero credit.
                </span>
              </div>

              <button
                type="button"
                className="btn-danger-outline"
                disabled={!!busy}
                onClick={() =>
                  run("Discarding unsubmitted quiz", async () => {
                    await api(endpoint(`quizzes/${quiz.id}`), {
                      method: "DELETE",
                    });
                    setQuiz(null);
                  })
                }
              >
                <Trash2 size={15} />
                <span>Discard quiz</span>
              </button>
            </div>
          )}
        </div>
      </form>
    </div>
  );
}
