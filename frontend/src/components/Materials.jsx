import React, { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  FileText,
  FlaskConical,
  FolderOpen,
  UploadCloud,
} from "lucide-react";
import { Button, EmptyState, SectionHeader } from "./Common";
import { api } from "../api";

export function Materials({ data, run, endpoint, busy, setPage, demo }) {
  const [kind, setKind] = useState("syllabus");
  const [file, setFile] = useState(null);
  const [fileKey, setFileKey] = useState(0);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;

    await run("Extracting and vector-indexing material", async () => {
      const body = new FormData();
      body.append("file", file);
      body.append("kind", kind);
      await api(endpoint("documents"), { method: "POST", body });
      setFile(null);
      setFileKey((k) => k + 1);
    });
  }

  const documents = data.documents || [];

  return (
    <div className="page-container">
      <SectionHeader
        title="Materials"
        description="Course syllabus, lecture notes, textbooks, and past exam papers"
      />

      <div className="materials-layout-grid">
        {/* Upload Card */}
        <form onSubmit={handleUpload} className="card upload-card">
          <div className="card-header-bar">
            <div>
              <h2 className="card-heading">Add course document</h2>
              <p className="card-subheading">
                Upload text or searchable PDF files (up to 10 MB)
              </p>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="material-kind">Document category</label>
            <select
              id="material-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              className="select-field"
            >
              <option value="syllabus">Syllabus · Defines topic hierarchy</option>
              <option value="material">Notes / Textbook · Grounds diagnostics & tutor</option>
              <option value="past_paper">Past Paper · Estimates exam weights</option>
            </select>
          </div>

          <label className="dropzone-area">
            <UploadCloud size={32} className="text-slate-400" />
            <span className="dropzone-prompt">
              {file ? file.name : "Choose a PDF or TXT file to upload"}
            </span>
            <span className="dropzone-sub">
              Text PDFs with embedded fonts or UTF-8 text files
            </span>
            <input
              key={fileKey}
              type="file"
              accept=".pdf,.txt"
              onChange={(e) => setFile(e.target.files[0])}
              required
              className="sr-only"
            />
          </label>

          <div className="mt-4 flex items-center justify-between">
            <Button
              type="submit"
              icon={UploadCloud}
              disabled={!!busy || !file}
            >
              Upload and index
            </Button>
            {documents.length > 0 && (
              <Button
                secondary
                icon={BookOpen}
                onClick={() => setPage("topics")}
              >
                Go to Topic map
              </Button>
            )}
          </div>
        </form>

        {/* Guidelines / Overview Card */}
        <div className="card guidance-card">
          <div className="card-header-bar">
            <h2 className="card-heading">Processing pipeline</h2>
          </div>
          <ul className="guidance-list">
            <li>
              <strong>Syllabus files:</strong> Structured with Markdown headings (<code># Unit</code>, <code>## Topic</code>) or numbered outlines. Used by the topic builder to establish evaluation targets.
            </li>
            <li>
              <strong>Notes and textbooks:</strong> Chunked with overlap and tagged with filename, page numbers, and section headings for precise source attribution.
            </li>
            <li>
              <strong>Exam papers:</strong> Numbered questions and optional marks (e.g. <code>[5 marks]</code>) are parsed and mapped via vector similarity to leaf topics.
            </li>
            <li>
              <strong>Security quarantine:</strong> Prompt injection patterns and system instruction overrides are automatically detected, quarantined, and excluded from AI contexts.
            </li>
          </ul>
        </div>
      </div>

      {/* Document Library Card */}
      <div className="card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Indexed documents</h2>
            <p className="card-subheading">
              {documents.length} {documents.length === 1 ? "document" : "documents"} in this course repository
            </p>
          </div>
        </div>

        {!documents.length ? (
          <EmptyState
            icon={FolderOpen}
            title="No documents uploaded yet"
            description="Upload your syllabus and materials above, or load the pre-configured biology demo course to explore immediately."
          >
            <Button secondary icon={FlaskConical} disabled={!!busy} onClick={demo}>
              Load sample biology course
            </Button>
          </EmptyState>
        ) : (
          <div className="document-list">
            {documents.map((doc) => (
              <div key={doc.id} className="document-item">
                <div className="document-icon-wrap">
                  <FileText size={20} className="text-indigo-600" />
                </div>
                <div className="document-details">
                  <span className="document-filename">{doc.filename}</span>
                  <div className="document-meta">
                    <span className="document-kind-pill">{doc.kind.replace("_", " ")}</span>
                    <span>
                      {doc.pages} {doc.pages === 1 ? "page" : "pages"}
                    </span>
                  </div>
                  {doc.warnings && doc.warnings.length > 0 && (
                    <div className="document-warnings">
                      {doc.warnings.map((w, idx) => (
                        <div key={idx} className="warning-text">
                          <AlertTriangle size={13} className="shrink-0" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="document-status">
                  <CheckCircle2 size={16} className="text-emerald-600" />
                  <span>Indexed</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
