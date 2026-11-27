import React from "react";
import { ChevronRight, FlaskConical, Menu, Plus, X } from "lucide-react";
import { ModeIndicator } from "./Common";
import { NAV_ITEMS } from "./Sidebar";

export function Header({
  page,
  courses,
  course,
  setCourse,
  busy,
  showNewCourse,
  setShowNewCourse,
  newName,
  setNewName,
  onAddCourse,
  health,
  onLoadDemo,
  mobileNavOpen,
  setMobileNavOpen,
}) {
  const currentNav = NAV_ITEMS.find((n) => n.id === page);

  return (
    <header className="app-header">
      <div className="header-left">
        <button
          type="button"
          className="mobile-nav-toggle"
          onClick={() => setMobileNavOpen(!mobileNavOpen)}
          aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
        >
          {mobileNavOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <div className="header-breadcrumbs">
          <span className="breadcrumb-root">Course</span>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <span className="breadcrumb-current">{currentNav?.label || "Workspace"}</span>
        </div>
      </div>

      <div className="header-right">
        <div className="course-selector-wrap">
          <label htmlFor="course-select" className="sr-only">
            Select Course
          </label>
          <select
            id="course-select"
            value={course}
            disabled={!!busy}
            onChange={(e) => setCourse(e.target.value)}
            className="course-select"
          >
            {!courses.length && <option value="">No courses yet</option>}
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <button
            type="button"
            className="btn-icon"
            onClick={() => setShowNewCourse(!showNewCourse)}
            title="Create new course"
            aria-label="Create new course"
          >
            <Plus size={16} />
          </button>
        </div>

        {courses.length === 0 && (
          <button
            type="button"
            className="btn-demo-quick"
            onClick={onLoadDemo}
            disabled={!!busy}
          >
            <FlaskConical size={14} />
            <span>Load Demo</span>
          </button>
        )}

        <ModeIndicator health={health} />
      </div>

      {showNewCourse && (
        <div className="new-course-dropdown">
          <form onSubmit={onAddCourse} className="new-course-form">
            <label htmlFor="new-course-name" className="text-xs font-medium text-slate-700">
              New Course Name
            </label>
            <div className="flex gap-2">
              <input
                id="new-course-name"
                type="text"
                required
                maxLength={120}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g., Biology Foundations"
                className="input-field text-sm py-1.5 flex-1"
                autoFocus
              />
              <button type="submit" disabled={!newName.trim() || !!busy} className="btn btn-primary py-1.5 px-3 text-sm">
                Create
              </button>
              <button
                type="button"
                className="btn btn-secondary py-1.5 px-2 text-sm"
                onClick={() => setShowNewCourse(false)}
              >
                <X size={16} />
              </button>
            </div>
          </form>
        </div>
      )}
    </header>
  );
}
