import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  FlaskConical,
  LoaderCircle,
  Plus,
  X,
} from "lucide-react";
import { api } from "./api";
import "./styles.css";

import { Button, EmptyState } from "./components/Common";
import { Login } from "./components/Login";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { SourceModal } from "./components/SourceModal";
import { GapReport } from "./components/GapReport";
import { Diagnostic } from "./components/Diagnostic";
import { RevisionPlan } from "./components/RevisionPlan";
import { TopicMap } from "./components/TopicMap";
import { Materials } from "./components/Materials";
import { Progress } from "./components/Progress";
import { Tutor } from "./components/Tutor";

const emptyData = {
  documents: [],
  topics: [],
  gaps: [],
  papers: [],
  quizzes: [],
  progress: {
    history: [],
    attempts: 0,
    assessed_topics: 0,
    total_topics: 0,
    strong_topics: 0,
  },
  plan: null,
  messages: [],
};

function App() {
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [booting, setBooting] = useState(true);

  const [courses, setCourses] = useState([]);
  const [course, setCourse] = useState("");
  const [page, setPage] = useState("gaps");

  const [data, setData] = useState(emptyData);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [newName, setNewName] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [source, setSource] = useState(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const [quiz, setQuiz] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [tutorTopic, setTutorTopic] = useState("");
  const [drafts, setDrafts] = useState({});

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [page, course, quiz?.id, quiz?.status]);

  useEffect(() => {
    if (!source) return;
    const close = (e) => {
      if (e.key === "Escape") setSource(null);
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [source]);

  useEffect(() => {
    Promise.all([
      api("/health").then(setHealth),
      api("/auth/me")
        .then(setUser)
        .catch(() => {}),
    ])
      .catch((e) => setError(e.message))
      .finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    if (user) {
      api("/courses")
        .then((items) => {
          setCourses(items);
          if (items.length > 0 && !course) {
            setCourse(items[0].id);
          }
        })
        .catch((e) => setError(e.message));
    }
  }, [user]);

  useEffect(() => {
    if (!course) {
      setData(emptyData);
      return;
    }
    let alive = true;
    setLoading(true);
    const paths = [
      "documents",
      "topics",
      "gaps",
      "papers",
      "quizzes",
      "progress",
      "plan",
      "tutor",
    ];
    Promise.all(paths.map((p) => api(`/courses/${course}/${p}`)))
      .then((values) => {
        if (alive) {
          setData(
            Object.fromEntries(
              paths.map((p, i) => [p === "tutor" ? "messages" : p, values[i]])
            )
          );
        }
      })
      .catch((e) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [course, refresh]);

  useEffect(() => {
    setQuiz(null);
    setSelectedTopics([]);
    setSource(null);
    setData(emptyData);
  }, [course]);

  async function run(label, fn) {
    if (busy) return;
    setBusy(label);
    setError("");
    setNotice("");
    try {
      const result = await fn();
      setRefresh((x) => x + 1);
      return result;
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setBusy("");
    }
  }

  const endpoint = (path) => `/courses/${course}/${path}`;

  async function demo() {
    await run("Loading sample biology materials", async () => {
      const result = await api("/demo/load", { method: "POST" });
      const updatedCourses = await api("/courses");
      setCourses(updatedCourses);
      setCourse(result.id);
      setNotice(result.notice);
      setPage("gaps");
    });
  }

  async function addCourse(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    await run("Creating course", async () => {
      const c = await api("/courses", {
        method: "POST",
        body: { name: newName.trim() },
      });
      const updatedCourses = await api("/courses");
      setCourses(updatedCourses);
      setCourse(c.id);
      setNewName("");
      setShowNew(false);
      setPage("materials");
    });
  }

  const openSource = (c) =>
    run("Fetching source excerpt", async () =>
      setSource(await api(endpoint(`sources/${c.chunk_id}`)))
    );

  const beginQuiz = (ids = selectedTopics) =>
    run("Generating cited questions from indexed material", async () => {
      const q = await api(endpoint("quizzes"), {
        method: "POST",
        body: { topic_ids: ids, per_topic: 2 },
      });
      setQuiz(q);
      setPage("quiz");
    });

  const openTutor = (id) => {
    setTutorTopic(id);
    setPage("tutor");
  };

  const logout = () =>
    run("Signing out", async () => {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setCourse("");
      setCourses([]);
      setDrafts({});
    });

  const retest = (id) => {
    setSelectedTopics([id]);
    beginQuiz([id]);
  };

  const resume = (id) =>
    run("Loading diagnostic assessment", async () => {
      setQuiz(await api(endpoint(`quizzes/${id}`)));
      setPage("quiz");
    });

  const pending = data.quizzes.find((q) => q.status === "ready");

  if (booting) {
    return (
      <div className="boot-screen">
        <LoaderCircle size={28} className="spin text-indigo-600" />
        <span className="text-sm font-medium text-slate-600">
          Initializing GapFinder AI workspace...
        </span>
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <Login onLogin={setUser} health={health} />
        {error && (
          <div className="login-error-toast" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </>
    );
  }

  return (
    <div className="app-shell">
      <div
        className={`sidebar-overlay ${mobileNavOpen ? "open" : ""}`}
        onClick={() => setMobileNavOpen(false)}
      />

      <div className={`sidebar-container ${mobileNavOpen ? "open" : ""}`}>
        <Sidebar
          page={page}
          setPage={(p) => {
            setPage(p);
            setMobileNavOpen(false);
          }}
          pendingQuiz={pending}
          user={user}
          onLogout={logout}
        />
      </div>

      <div className="main-shell">
        <Header
          page={page}
          courses={courses}
          course={course}
          setCourse={setCourse}
          busy={busy}
          showNewCourse={showNew}
          setShowNewCourse={setShowNew}
          newName={newName}
          setNewName={setNewName}
          onAddCourse={addCourse}
          health={health}
          onLoadDemo={demo}
          mobileNavOpen={mobileNavOpen}
          setMobileNavOpen={setMobileNavOpen}
        />

        <main className="main-content" aria-busy={!!busy || loading}>
          {error && (
            <div className="alert-banner alert-danger" role="alert">
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className="shrink-0" />
                <span>{error}</span>
              </div>
              <button
                type="button"
                className="btn-icon"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X size={15} />
              </button>
            </div>
          )}

          {notice && (
            <div className="alert-banner alert-success" role="status">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="shrink-0" />
                <span>{notice}</span>
              </div>
              <button
                type="button"
                className="btn-icon"
                onClick={() => setNotice("")}
                aria-label="Dismiss notification"
              >
                <X size={15} />
              </button>
            </div>
          )}

          {busy && (
            <div className="busy-toast" role="status">
              <LoaderCircle size={15} className="spin" />
              <span>{busy}...</span>
            </div>
          )}

          {!course ? (
            <div className="page-container">
              <div className="card welcome-card">
                <div className="welcome-inner">
                  <h1 className="welcome-title">Welcome to GapFinder AI</h1>
                  <p className="welcome-desc">
                    An evidence-grounded diagnostic learning system that indexes
                    your syllabus, notes, and past exams to discover knowledge
                    gaps and build adaptive revision plans.
                  </p>

                  <div className="welcome-actions">
                    <Button
                      icon={FlaskConical}
                      disabled={!!busy}
                      onClick={demo}
                    >
                      Load sample biology course
                    </Button>
                    <Button
                      secondary
                      icon={Plus}
                      disabled={!!busy}
                      onClick={() => setShowNew(true)}
                    >
                      Create custom course
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ) : loading && !data.topics.length && !data.documents.length ? (
            <div className="page-container">
              <EmptyState
                icon={LoaderCircle}
                title="Loading course workspace..."
              />
            </div>
          ) : (
            <>
              {page === "gaps" && (
                <GapReport
                  data={data}
                  beginQuiz={beginQuiz}
                  retest={retest}
                  openSource={openSource}
                  busy={busy}
                  setPage={setPage}
                />
              )}
              {page === "quiz" && (
                <Diagnostic
                  quiz={quiz}
                  setQuiz={setQuiz}
                  data={data}
                  run={run}
                  endpoint={endpoint}
                  busy={busy}
                  selectedTopics={selectedTopics}
                  setSelectedTopics={setSelectedTopics}
                  beginQuiz={beginQuiz}
                  resume={resume}
                  openSource={openSource}
                  setPage={setPage}
                  pending={pending}
                  drafts={drafts}
                  setDrafts={setDrafts}
                />
              )}
              {page === "plan" && (
                <RevisionPlan
                  data={data}
                  run={run}
                  endpoint={endpoint}
                  busy={busy}
                  retest={retest}
                  openTutor={openTutor}
                />
              )}
              {page === "topics" && (
                <TopicMap
                  data={data}
                  run={run}
                  endpoint={endpoint}
                  busy={busy}
                  openSource={openSource}
                />
              )}
              {page === "materials" && (
                <Materials
                  data={data}
                  run={run}
                  endpoint={endpoint}
                  busy={busy}
                  setPage={setPage}
                  demo={demo}
                />
              )}
              {page === "progress" && (
                <Progress
                  data={data}
                  beginQuiz={beginQuiz}
                  resume={resume}
                  busy={busy}
                  setPage={setPage}
                />
              )}
              {page === "tutor" && (
                <Tutor
                  data={data}
                  run={run}
                  endpoint={endpoint}
                  busy={busy}
                  openSource={openSource}
                  pending={pending}
                  resume={resume}
                  topic={tutorTopic}
                  setTopic={setTutorTopic}
                />
              )}
            </>
          )}
        </main>
      </div>

      <SourceModal source={source} onClose={() => setSource(null)} />
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
