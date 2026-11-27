import React from "react";
import { AlertTriangle, FileText, X } from "lucide-react";

export function SourceModal({ source, onClose }) {
  if (!source) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="source-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="source-modal-header">
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-indigo-600 shrink-0" />
            <div>
              <h2 id="source-modal-title" className="source-modal-title">
                {source.filename || "Source Document"}
              </h2>
              <p className="source-modal-subtitle">
                Page {source.page || 1} {source.section ? `· Section: ${source.section}` : ""}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="btn-icon"
            onClick={onClose}
            aria-label="Close source preview"
            autoFocus
          >
            <X size={18} />
          </button>
        </div>

        {source.quarantined && (
          <div className="source-quarantine-warning">
            <AlertTriangle size={16} className="shrink-0" />
            <span>
              This excerpt contains instruction-like patterns and was quarantined. It is excluded from AI context.
            </span>
          </div>
        )}

        <div className="source-modal-body">
          <pre className="source-text">{source.text}</pre>
        </div>

        <div className="source-modal-footer">
          <span className="text-xs text-slate-500">
            Chunk ID: <code>{source.chunk_id || "N/A"}</code>
          </span>
          <button type="button" className="btn btn-secondary text-xs py-1.5 px-3" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
