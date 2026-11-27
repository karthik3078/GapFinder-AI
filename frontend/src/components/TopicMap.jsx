import React from "react";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  FileText,
  HelpCircle,
  RefreshCw,
} from "lucide-react";
import {
  Badge,
  Button,
  CitationsList,
  EmptyState,
  percent,
  SectionHeader,
} from "./Common";
import { api } from "../api";

export function TopicMap({ data, run, endpoint, busy, openSource }) {
  const build = () =>
    run("Extracting syllabus topic hierarchy", () =>
      api(endpoint("topics/build"), { method: "POST" })
    );

  const map = () =>
    run("Mapping past-paper questions against topics", () =>
      api(endpoint("papers/map"), { method: "POST" })
    );

  const leaves = (data.topics || []).filter((t) => t.is_leaf);
  const topics = data.topics || [];
  const papers = data.papers || [];

  return (
    <div className="page-container">
      <SectionHeader
        title="Topic map"
        description="Syllabus hierarchy, topic weights, and past-paper question mappings"
        action={
          <div className="flex gap-2">
            <Button
              icon={RefreshCw}
              disabled={!!busy}
              onClick={build}
            >
              {topics.length ? "Refresh topic map" : "Build topic map"}
            </Button>
            <Button
              secondary
              icon={RefreshCw}
              disabled={!!busy || !topics.length}
              onClick={map}
            >
              Map exam questions
            </Button>
          </div>
        }
      />

      {/* Syllabus Tree Card */}
      <div className="card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Syllabus hierarchy</h2>
            <p className="card-subheading">
              {topics.length} topics ({leaves.length} leaf topics evaluated in diagnostics)
            </p>
          </div>
        </div>

        {!topics.length ? (
          <EmptyState
            icon={BookOpen}
            title="No topics built yet"
            description="Upload a syllabus document in Materials, then click 'Build topic map'."
          />
        ) : (
          <div className="syllabus-tree">
            {topics.map((topic) => {
              const depth = Math.min(4, (topic.path || "").split(" / ").length - 1);
              return (
                <div
                  key={topic.id}
                  className={`tree-node ${topic.is_leaf ? "tree-node-leaf" : "tree-node-unit"}`}
                  style={{ paddingLeft: `${depth * 20 + 12}px` }}
                >
                  <BookOpen
                    size={topic.is_leaf ? 15 : 18}
                    className={topic.is_leaf ? "text-slate-400 shrink-0" : "text-indigo-600 shrink-0"}
                  />
                  <div className="tree-node-info">
                    <span className="tree-node-name">{topic.name}</span>
                    <CitationsList citations={topic.citations} onOpen={openSource} />
                  </div>

                  <div className="tree-node-metrics">
                    <span className="tree-node-weight">
                      {percent(topic.weight)} weight
                    </span>
                    <span className="tree-node-frequency">
                      {topic.frequency || 0} mapped {topic.frequency === 1 ? "question" : "questions"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Past Paper Questions Mapping */}
      <div className="card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Exam question mappings</h2>
            <p className="card-subheading">
              Vector retrieval matches past-paper questions to syllabus topics to calculate weightings
            </p>
          </div>
          <span className="text-xs text-slate-500 font-medium">
            {papers.length} questions mapped
          </span>
        </div>

        {!papers.length ? (
          <EmptyState
            icon={FileText}
            title="No exam questions mapped"
            description="Upload past exam papers in Materials and click 'Map exam questions' to link questions to topics."
          />
        ) : (
          <div className="paper-questions-grid">
            {papers.map((paper) => (
              <article key={paper.id} className="paper-question-card">
                <div className="paper-card-top">
                  <span className="marks-badge">{paper.marks} marks</span>
                  <span
                    className={`status-badge ${
                      paper.review_needed ? "status-medium" : "status-strong"
                    }`}
                  >
                    {paper.review_needed ? "Review needed" : "Confirmed"}
                  </span>
                </div>

                <p className="paper-question-text">{paper.text}</p>

                {paper.citation && (
                  <CitationsList
                    citations={[paper.citation]}
                    onOpen={openSource}
                  />
                )}

                <div className="paper-card-controls">
                  <div className="form-group flex-1">
                    <label htmlFor={`map-${paper.id}`} className="text-xs text-slate-600">
                      Mapped leaf topic
                    </label>
                    <select
                      id={`map-${paper.id}`}
                      value={paper.topic_id || ""}
                      disabled={!!busy}
                      onChange={(e) =>
                        run("Updating question mapping", () =>
                          api(endpoint(`papers/${paper.id}`), {
                            method: "PATCH",
                            body: { topic_id: e.target.value },
                          })
                        )
                      }
                      className="select-field text-xs py-1.5"
                    >
                      <option value="" disabled>
                        Select topic
                      </option>
                      {leaves.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="paper-card-footer">
                    <span className="text-xs text-slate-500">
                      Confidence: {percent(paper.confidence)}
                    </span>
                    {paper.review_needed && paper.topic_id && (
                      <button
                        type="button"
                        className="btn btn-secondary text-xs py-1 px-2.5"
                        disabled={!!busy}
                        onClick={() =>
                          run("Confirming mapping match", () =>
                            api(endpoint(`papers/${paper.id}`), {
                              method: "PATCH",
                              body: { topic_id: paper.topic_id },
                            })
                          )
                        }
                      >
                        Confirm match
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        <div className="card-info-footer">
          <span className="font-semibold text-slate-700">Exam weight calculation:</span>{" "}
          Weights incorporate confirmed past-paper marks with Laplace smoothing (+1 smoothing mark per leaf topic) so unseen topics remain eligible for revision.
        </div>
      </div>
    </div>
  );
}
