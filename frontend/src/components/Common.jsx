import React from "react";
import { BookOpen, FileText } from "lucide-react";

export const STATUS_LABELS = {
  weak: "Weak",
  medium: "Medium",
  strong: "Strong",
  not_assessed: "Not assessed",
};

export function percent(n) {
  if (n == null) return "—";
  return `${Math.round(n * 100)}%`;
}

export function Button({
  children,
  icon: Icon,
  secondary = false,
  className = "",
  type = "button",
  disabled = false,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={`btn ${secondary ? "btn-secondary" : "btn-primary"} ${className}`}
      {...props}
    >
      {Icon && <Icon size={16} className="shrink-0" />}
      <span>{children}</span>
    </button>
  );
}

export function Badge({ status }) {
  const label = STATUS_LABELS[status] || status;
  return <span className={`status-badge status-${status}`}>{label}</span>;
}

export function SectionHeader({ title, description, action }) {
  return (
    <div className="section-header">
      <div>
        <h1 className="section-title">{title}</h1>
        {description && <p className="section-desc">{description}</p>}
      </div>
      {action && <div className="section-action">{action}</div>}
    </div>
  );
}

export function MetricCard({ icon: Icon, value, label, note, status }) {
  return (
    <div className={`metric-card ${status ? `border-${status}` : ""}`}>
      <div className="metric-header">
        <span className="metric-label">{label}</span>
        {Icon && <Icon size={18} className="metric-icon" />}
      </div>
      <div className="metric-value">{value}</div>
      {note && <div className="metric-note">{note}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon = BookOpen, title, description, children }) {
  return (
    <div className="empty-state">
      <div className="empty-icon-wrap">
        <Icon size={24} />
      </div>
      <h3 className="empty-title">{title}</h3>
      {description && <p className="empty-desc">{description}</p>}
      {children && <div className="empty-actions">{children}</div>}
    </div>
  );
}

export function CitationsList({ citations = [], onOpen, locked = false }) {
  if (!citations || !citations.length) return null;
  return (
    <div className="citations-list">
      {citations.map((c, i) => (
        <button
          type="button"
          className="citation-pill"
          key={(c.chunk_id || "") + i}
          disabled={locked}
          onClick={() => onOpen && onOpen(c)}
          title={
            locked
              ? "Source preview available after submission"
              : `View source: ${c.filename || "file"} (p. ${c.page || 1})`
          }
        >
          <FileText size={12} className="shrink-0" />
          <span>
            {c.filename || "Source"} · p. {c.page || 1}
          </span>
        </button>
      ))}
    </div>
  );
}

export function ModeIndicator({ health }) {
  const isLive = health?.mode === "live";
  return (
    <div className={`mode-badge ${isLive ? "mode-live" : "mode-demo"}`} title={health?.notice || ""}>
      <span className="mode-dot" />
      <span className="mode-text">
        {isLive ? `Live AI (${health?.generation_model || "Gemini"})` : "Offline Demo (Local)"}
      </span>
    </div>
  );
}
