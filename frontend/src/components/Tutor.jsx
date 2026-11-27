import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Brain,
  MessageCircle,
  Search,
  Send,
  Sparkles,
} from "lucide-react";
import { Button, CitationsList, EmptyState, SectionHeader } from "./Common";
import { api } from "../api";

export function Tutor({
  data,
  run,
  endpoint,
  busy,
  openSource,
  pending,
  resume,
  topic,
  setTopic,
}) {
  const [message, setMessage] = useState("");

  const leaves = (data.topics || []).filter((t) => t.is_leaf);
  const messages = data.messages || [];

  useEffect(() => {
    if (!leaves.some((t) => t.id === topic) && leaves.length > 0) {
      setTopic(leaves[0].id);
    }
  }, [data.topics]);

  async function handleSend(e) {
    e.preventDefault();
    if (!message.trim() || !topic) return;

    await run("Retrieving evidence and formulating grounded explanation", async () => {
      await api(endpoint("tutor"), {
        method: "POST",
        body: { topic_id: topic, message: message.trim() },
      });
      setMessage("");
    });
  }

  return (
    <div className="page-container">
      <SectionHeader
        title="Tutor"
        description="Grounded explanations derived strictly from your uploaded course notes"
      />

      {pending && (
        <div className="alert-banner alert-warning">
          <div className="flex items-center gap-3">
            <Brain size={20} className="text-amber-600 shrink-0" />
            <div>
              <strong className="block text-slate-800 font-semibold">
                Tutor paused during active diagnostic
              </strong>
              <span className="text-slate-600 text-sm">
                Submit or discard your open diagnostic quiz before querying the tutor.
              </span>
            </div>
          </div>
          <Button
            onClick={() => resume(pending.id)}
            disabled={!!busy}
            className="text-xs py-1.5 px-3"
          >
            Resume diagnostic
          </Button>
        </div>
      )}

      <div className="tutor-grid">
        {/* Topic Selector & Guidelines */}
        <aside className="card tutor-sidebar-card">
          <div className="card-header-bar">
            <h2 className="card-heading">Subject scope</h2>
          </div>

          <div className="form-group">
            <label htmlFor="tutor-topic-select">Focus topic</label>
            <select
              id="tutor-topic-select"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={!!pending}
              className="select-field"
            >
              {!leaves.length && <option value="">No leaf topics available</option>}
              {leaves.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          <div className="tutor-instructions">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
              Provenance rules
            </h3>
            <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
              <li>
                Responses are synthesized from retrieved chunks for the selected topic.
              </li>
              <li>
                If your course notes do not contain sufficient evidence, the tutor will explicitly decline rather than hallucinate.
              </li>
              <li>
                Click on the source pills below any answer to inspect the exact underlying text chunk.
              </li>
            </ul>
          </div>
        </aside>

        {/* Chat / Conversation Area */}
        <div className="card tutor-chat-card">
          <div className="chat-messages-area">
            {!messages.length ? (
              <EmptyState
                icon={MessageCircle}
                title="No tutor queries yet"
                description="Select a topic on the left and ask a question grounded in your course materials."
              />
            ) : (
              <div className="chat-thread">
                {messages.map((m) => (
                  <div key={m.id} className="chat-exchange">
                    <div className="chat-bubble chat-user">
                      <span className="chat-sender">You</span>
                      <p className="chat-text">{m.question}</p>
                    </div>

                    <div className="chat-bubble chat-assistant">
                      <div className="chat-assistant-header">
                        <span className="chat-sender flex items-center gap-1.5">
                          <Sparkles size={14} className="text-indigo-600" />
                          <span>GapFinder Tutor</span>
                        </span>
                        {m.response?.insufficient_evidence && (
                          <span className="evidence-needed-pill">
                            Evidence needed
                          </span>
                        )}
                      </div>

                      <p className="chat-text">{m.response?.answer}</p>

                      {m.response?.citations && (
                        <div className="chat-citations">
                          <CitationsList
                            citations={m.response.citations}
                            onOpen={openSource}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="chat-input-bar">
            <label htmlFor="tutor-input-msg" className="sr-only">
              Ask a question about this topic
            </label>
            <input
              id="tutor-input-msg"
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={
                pending
                  ? "Tutor is paused while a diagnostic is in progress..."
                  : "Ask a question about this topic..."
              }
              disabled={!!pending || !topic}
              required
              minLength={3}
              maxLength={2000}
              className="input-field flex-1"
            />
            <Button
              type="submit"
              icon={Send}
              disabled={!!busy || !!pending || !topic || message.trim().length < 3}
            >
              Ask
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
