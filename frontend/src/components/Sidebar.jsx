import React from "react";
import {
  Activity,
  BookOpen,
  Brain,
  CalendarDays,
  FolderOpen,
  LogOut,
  MessageCircle,
  Target,
  TrendingUp,
} from "lucide-react";

export const NAV_ITEMS = [
  { id: "gaps", label: "Gap report", icon: Target },
  { id: "quiz", label: "Diagnostic", icon: Brain },
  { id: "plan", label: "Revision plan", icon: CalendarDays },
  { id: "topics", label: "Topic map", icon: BookOpen },
  { id: "materials", label: "Materials", icon: FolderOpen },
  { id: "progress", label: "Progress", icon: TrendingUp },
  { id: "tutor", label: "Tutor", icon: MessageCircle },
];

export function Sidebar({ page, setPage, pendingQuiz, user, onLogout }) {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <Activity size={20} />
        </div>
        <span className="brand-text">GapFinder AI</span>
      </div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const isActive = page === id;
          const hasPending = id === "quiz" && !!pendingQuiz;
          return (
            <button
              key={id}
              type="button"
              className={`nav-link ${isActive ? "nav-link-active" : ""}`}
              onClick={() => setPage(id)}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon size={18} className="nav-icon" />
              <span className="nav-label">{label}</span>
              {hasPending && (
                <span className="nav-badge" title="Diagnostic in progress">
                  Active
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar" aria-hidden="true">
            {user?.name ? user.name[0].toUpperCase() : "U"}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.name || "Student"}</span>
            <span className="user-email">{user?.email || ""}</span>
          </div>
          <button
            type="button"
            className="btn-logout"
            onClick={onLogout}
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
