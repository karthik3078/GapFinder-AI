import React, { useState } from "react";
import {
  Activity,
  BookOpen,
  Brain,
  CheckCircle2,
  TrendingUp,
} from "lucide-react";
import {
  Button,
  EmptyState,
  MetricCard,
  percent,
  SectionHeader,
} from "./Common";

export function Progress({ data, beginQuiz, resume, busy, setPage }) {
  const p = data.progress || {
    attempts: 0,
    assessed_topics: 0,
    total_topics: 0,
    strong_topics: 0,
    history: [],
  };

  const [topicFilter, setTopicFilter] = useState("all");
  const leaves = (data.topics || []).filter((t) => t.is_leaf);

  const history = (p.history || [])
    .map((h) => ({
      ...h,
      shownScore:
        topicFilter === "all"
          ? h.score
          : h.topics?.find((t) => t.id === topicFilter)?.score,
    }))
    .filter((h) => h.shownScore != null);

  return (
    <div className="page-container">
      <SectionHeader
        title="Progress"
        description="Historical assessment records and verified diagnostic scores over time"
        action={
          <Button
            icon={Brain}
            disabled={!!busy || !data.topics.length}
            onClick={() => beginQuiz([])}
          >
            New diagnostic
          </Button>
        }
      />

      {/* Real Stored Metrics */}
      <div className="metrics-grid">
        <MetricCard
          label="Submitted Attempts"
          value={p.attempts}
          note="Only submitted evaluations are recorded"
          icon={Brain}
        />
        <MetricCard
          label="Syllabus Coverage"
          value={`${p.assessed_topics} / ${p.total_topics}`}
          note="Topics assessed at least once"
          icon={BookOpen}
        />
        <MetricCard
          label="Mastered Topics (≥80%)"
          value={p.strong_topics}
          note="Based on latest diagnostic submission"
          status="strong"
          icon={CheckCircle2}
        />
      </div>

      {/* Attempt History Chart */}
      <div className="card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Diagnostic score history</h2>
            <p className="card-subheading">
              Select an attempt below to review questions, answers, and rubric grading
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="topic-history-filter" className="text-xs text-slate-600 font-medium">
              Filter by topic:
            </label>
            <select
              id="topic-history-filter"
              value={topicFilter}
              onChange={(e) => setTopicFilter(e.target.value)}
              className="select-field text-xs py-1"
            >
              <option value="all">Overall attempt score</option>
              {leaves.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {!history.length ? (
          <EmptyState
            icon={Activity}
            title="No diagnostic history available"
            description="Take and submit a diagnostic quiz to record your first verified assessment scores."
          >
            <Button
              disabled={!!busy || !data.topics.length}
              onClick={() => beginQuiz([])}
            >
              Take diagnostic
            </Button>
          </EmptyState>
        ) : (
          <div className="history-chart-wrap">
            <div className="history-bars-row">
              {history.map((h) => {
                const heightPercent = Math.max(8, Math.round(h.shownScore * 100));
                return (
                  <button
                    key={h.id}
                    type="button"
                    onClick={() => resume(h.id)}
                    className="history-bar-btn"
                    title={`Attempt ${h.attempt}: ${percent(h.shownScore)} earned credit. Click to review.`}
                  >
                    <div className="history-bar-value">{percent(h.shownScore)}</div>
                    <div className="history-bar-track">
                      <div
                        className="history-bar-fill"
                        style={{ height: `${heightPercent}%` }}
                      />
                    </div>
                    <div className="history-bar-label">
                      Attempt {h.attempt}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="card-info-footer">
          <span className="font-semibold text-slate-700">Verification integrity:</span>{" "}
          Scores reflect deterministic MCQ matching and evidence-based short-answer grading. Topic accuracy automatically updates with each new attempt.
        </div>
      </div>
    </div>
  );
}
