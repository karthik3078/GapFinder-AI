import React, { useEffect, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Circle,
  Clock,
  HelpCircle,
  MessageCircle,
  RefreshCw,
} from "lucide-react";
import { Badge, Button, EmptyState, SectionHeader } from "./Common";
import { api } from "../api";

export function RevisionPlan({
  data,
  run,
  endpoint,
  busy,
  retest,
  openTutor,
}) {
  const [days, setDays] = useState(5);
  const [minutes, setMinutes] = useState(60);

  const plan = data.plan;

  useEffect(() => {
    if (plan) {
      setDays(plan.days);
      setMinutes(plan.minutes_per_day);
    }
  }, [plan?.id]);

  const handleCreate = (e) => {
    e.preventDefault();
    run("Building revision plan based on priority gaps", () =>
      api(endpoint("plan"), {
        method: "POST",
        body: { days: Number(days), minutes_per_day: Number(minutes) },
      })
    );
  };

  const toggleTask = (taskId, currentlyCompleted) => {
    run("Updating task status", () =>
      api(endpoint(`plan/${plan.id}`), {
        method: "PATCH",
        body: {
          task_id: taskId,
          completed: !currentlyCompleted,
        },
      })
    );
  };

  return (
    <div className="page-container">
      <SectionHeader
        title="Revision plan"
        description="Time-bounded revision schedule prioritized by knowledge gaps and exam weights"
      />

      {/* Time Budget Card */}
      <form onSubmit={handleCreate} className="card budget-form-card">
        <div className="budget-form-header">
          <div>
            <h2 className="card-heading">Study time budget</h2>
            <p className="card-subheading">
              Set your available timeframe to generate or update the daily schedule
            </p>
          </div>
          <Button
            type="submit"
            icon={CalendarDays}
            disabled={!!busy || !data.topics.length}
          >
            {plan ? "Update plan" : "Generate plan"}
          </Button>
        </div>

        <div className="budget-inputs-row">
          <div className="form-group flex-1">
            <label htmlFor="plan-days">Days available</label>
            <input
              id="plan-days"
              type="number"
              min={1}
              max={30}
              value={days}
              onChange={(e) => setDays(e.target.value)}
              required
              className="input-field"
            />
          </div>

          <div className="form-group flex-1">
            <label htmlFor="plan-minutes">Minutes per day</label>
            <input
              id="plan-minutes"
              type="number"
              min={10}
              max={480}
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              required
              className="input-field"
            />
          </div>
        </div>
      </form>

      {!plan ? (
        <EmptyState
          icon={CalendarDays}
          title="No revision plan generated"
          description="Configure your study budget above to generate an adaptive revision schedule."
        />
      ) : (
        <div className="card">
          <div className="card-header-bar">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="card-heading">
                  {plan.days}-day schedule
                </h2>
                <span className="version-pill">Version {plan.version}</span>
              </div>
              <p className="card-subheading">{plan.reason}</p>
            </div>
            <div className="text-xs text-slate-500 flex items-center gap-1">
              <Clock size={14} />
              <span>{plan.minutes_per_day} min / day target</span>
            </div>
          </div>

          <div className="schedule-day-grid">
            {plan.schedule.map((day) => (
              <section key={day.day} className="day-card">
                <div className="day-header">
                  <span className="day-title">Day {String(day.day).padStart(2, "0")}</span>
                  <span className="day-time">
                    {day.minutes} min <span className="text-slate-400">/ {plan.minutes_per_day} min</span>
                  </span>
                </div>

                <div className="day-tasks-list">
                  {day.tasks.map((task) => {
                    const isDone = (plan.completed || []).includes(task.id);

                    return (
                      <div
                        key={task.id}
                        className={`task-row ${isDone ? "task-row-done" : ""}`}
                      >
                        <button
                          type="button"
                          className="task-checkbox"
                          disabled={!!busy}
                          onClick={() => toggleTask(task.id, isDone)}
                          aria-label={`${isDone ? "Unmark" : "Complete"} task ${task.topic}`}
                        >
                          {isDone ? (
                            <CheckCircle2 size={18} className="text-emerald-600" />
                          ) : (
                            <Circle size={18} className="text-slate-400" />
                          )}
                        </button>

                        <div className="task-content">
                          <div className="task-top-row">
                            <span className="task-topic-name">{task.topic}</span>
                            <span className="task-minutes">{task.minutes} min</span>
                          </div>

                          <p className="task-action-text">{task.action}</p>

                          <div className="task-meta-row">
                            <Badge status={task.status} />

                            {task.topic_id && (
                              <div className="task-action-links">
                                <button
                                  type="button"
                                  className="task-action-link"
                                  onClick={() => openTutor(task.topic_id)}
                                >
                                  <MessageCircle size={13} />
                                  <span>Review with tutor</span>
                                </button>
                                <button
                                  type="button"
                                  className="task-action-link"
                                  disabled={!!busy}
                                  onClick={() => retest(task.topic_id)}
                                >
                                  <RefreshCw size={13} />
                                  <span>Retest</span>
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {day.free_minutes > 0 && (
                  <div className="day-free-time">
                    {day.free_minutes} min unallocated (rest or additional review)
                  </div>
                )}
              </section>
            ))}
          </div>

          <div className="card-info-footer">
            <span className="font-semibold text-slate-700">Allocation policy:</span>{" "}
            Priority = (1 − latest topic score) × exam weight. Unassessed topics use 0.75 × weight to schedule initial diagnostics. Marking tasks complete tracks progress without falsely inflating mastery.
          </div>
        </div>
      )}
    </div>
  );
}
