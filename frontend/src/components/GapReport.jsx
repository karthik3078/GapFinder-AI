import React, { useState } from "react";
import {
  Activity,
  AlertCircle,
  BookOpen,
  Brain,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Filter,
  RefreshCw,
  Search,
  Sparkles,
  Target,
} from "lucide-react";
import {
  Badge,
  Button,
  CitationsList,
  EmptyState,
  MetricCard,
  percent,
  STATUS_LABELS,
} from "./Common";

export function GapReport({
  data,
  beginQuiz,
  retest,
  openSource,
  busy,
  setPage,
}) {
  const [filter, setFilter] = useState("all");
  const [expandedTopic, setExpandedTopic] = useState(null);

  const gaps = data.gaps || [];
  const counts = {
    weak: gaps.filter((g) => g.status === "weak").length,
    medium: gaps.filter((g) => g.status === "medium").length,
    strong: gaps.filter((g) => g.status === "strong").length,
    not_assessed: gaps.filter((g) => g.status === "not_assessed").length,
  };

  const assessedGaps = gaps.filter((g) => g.accuracy != null);
  const averageMastery = assessedGaps.length
    ? assessedGaps.reduce((sum, g) => sum + g.accuracy, 0) / assessedGaps.length
    : null;

  const filteredGaps = gaps.filter(
    (g) => filter === "all" || g.status === filter
  );

  return (
    <div className="page-container">
      <div className="section-header">
        <div>
          <h1 className="section-title">Gap report</h1>
          <p className="section-desc">
            Evidence-grounded topic mastery based strictly on submitted answers
          </p>
        </div>
        <div className="section-actions">
          <Button
            icon={Brain}
            disabled={!!busy || !data.topics.length}
            onClick={() => beginQuiz([])}
          >
            Take diagnostic
          </Button>
          <Button
            secondary
            icon={CalendarDays}
            disabled={!gaps.length}
            onClick={() => setPage("plan")}
          >
            Revision plan
          </Button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="metrics-grid">
        <MetricCard
          label="Assessed Mastery"
          value={percent(averageMastery)}
          note={
            assessedGaps.length
              ? `Calculated from ${assessedGaps.length} of ${gaps.length} topics`
              : "No diagnostic attempts submitted yet"
          }
          icon={Target}
        />
        <MetricCard
          label="Needs Work (<50%)"
          value={counts.weak}
          note="Demonstrated knowledge gaps"
          status="weak"
          icon={AlertCircle}
        />
        <MetricCard
          label="Medium (50–79%)"
          value={counts.medium}
          note="Partial understanding"
          status="medium"
          icon={Activity}
        />
        <MetricCard
          label="Strong (≥80%)"
          value={counts.strong}
          note="Consistently demonstrated"
          status="strong"
          icon={CheckCircle2}
        />
        <MetricCard
          label="Not assessed"
          value={counts.not_assessed}
          note="Requires diagnostic evaluation"
          status="not_assessed"
          icon={Search}
        />
      </div>

      {/* Diagnosis List Card */}
      <div className="card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Topic diagnosis</h2>
            <p className="card-subheading">
              Ranked by revision priority (lowest score + highest exam weight)
            </p>
          </div>
          <div className="filter-pill-group" role="group" aria-label="Filter topics">
            <button
              type="button"
              className={`filter-pill ${filter === "all" ? "filter-pill-active" : ""}`}
              onClick={() => setFilter("all")}
            >
              All ({gaps.length})
            </button>
            {Object.entries(STATUS_LABELS).map(([statusKey, label]) => (
              <button
                key={statusKey}
                type="button"
                className={`filter-pill ${filter === statusKey ? "filter-pill-active" : ""}`}
                onClick={() => setFilter(statusKey)}
              >
                {label} ({counts[statusKey] || 0})
              </button>
            ))}
          </div>
        </div>

        {!gaps.length ? (
          <EmptyState
            icon={BookOpen}
            title="No topics indexed yet"
            description="Upload course materials and build the syllabus topic map to generate the diagnosis."
          >
            <Button secondary onClick={() => setPage("materials")}>
              Go to Materials
            </Button>
          </EmptyState>
        ) : !filteredGaps.length ? (
          <EmptyState
            icon={Filter}
            title="No topics in this category"
            description="Select another filter above to inspect topics."
          />
        ) : (
          <div className="topic-diagnosis-list">
            {filteredGaps.map((topic) => {
              const isExpanded = expandedTopic === topic.id;
              const hasReviewPoints =
                topic.review_points && topic.review_points.length > 0;

              return (
                <article key={topic.id} className="topic-diagnosis-item">
                  <div className="topic-main-col">
                    <div className="topic-header-row">
                      <h3 className="topic-name">{topic.name}</h3>
                      <Badge status={topic.status} />
                      {topic.high_weight_unassessed && (
                        <span className="priority-pill">
                          High exam weight · Unassessed
                        </span>
                      )}
                    </div>

                    <p className="topic-reason">{topic.reason}</p>

                    <div className="topic-tags">
                      <span className="tag">
                        Exam weight: <strong>{percent(topic.weight)}</strong>
                      </span>
                      <span className="tag">
                        Questions: <strong>{topic.assessed_questions || 0}</strong>
                      </span>
                      {topic.limited_evidence && topic.assessed_questions > 0 && (
                        <span className="tag tag-warning">Limited evidence</span>
                      )}
                    </div>

                    {hasReviewPoints && (
                      <div className="review-points-wrap">
                        <button
                          type="button"
                          className="toggle-review-btn"
                          onClick={() =>
                            setExpandedTopic(isExpanded ? null : topic.id)
                          }
                        >
                          <span>Feedback & review details</span>
                          <ChevronDown
                            size={14}
                            className={`transform transition-transform ${
                              isExpanded ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {isExpanded && (
                          <ul className="review-points-list">
                            {topic.review_points.map((point, idx) => (
                              <li key={idx}>{point}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    <CitationsList
                      citations={topic.citations}
                      onOpen={openSource}
                    />
                  </div>

                  <div className="topic-score-col">
                    <div className="score-box">
                      <div className="score-percentage">
                        {percent(topic.accuracy)}
                      </div>
                      <div className="score-label">
                        {topic.accuracy == null ? "Untested" : "Accuracy"}
                      </div>
                    </div>

                    <div className="score-bar-track">
                      <div
                        className={`score-bar-fill score-${topic.status}`}
                        style={{
                          width: `${Math.max(4, (topic.accuracy || 0) * 100)}%`,
                        }}
                      />
                    </div>

                    <Button
                      secondary
                      disabled={!!busy}
                      onClick={() => retest(topic.id)}
                      className="w-full text-xs py-1.5"
                    >
                      {topic.accuracy == null ? "Assess topic" : "Retest topic"}
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
