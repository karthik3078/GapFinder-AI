import React, { useState } from "react";
import { Activity, AlertCircle, ArrowRight, CheckCircle2, FlaskConical, LoaderCircle, Shield } from "lucide-react";
import { api } from "../api";
import { Button } from "./Common";

export function Login({ onLogin, health }) {
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("student@demo.com");
  const [password, setPassword] = useState("demo123");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const endpoint = register ? "/auth/register" : "/auth/login";
      const payload = {
        email: email.trim(),
        password,
        ...(register ? { name: name.trim() } : {}),
      };
      const user = await api(endpoint, {
        method: "POST",
        body: payload,
      });
      onLogin(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function fillDemo() {
    setEmail("student@demo.com");
    setPassword("demo123");
    setRegister(false);
    setError("");
  }

  return (
    <div className="login-container">
      <div className="login-panel">
        <div className="login-brand">
          <div className="brand-logo">
            <Activity size={22} />
          </div>
          <span className="brand-title">GapFinder AI</span>
        </div>

        <div className="login-header">
          <h2>{register ? "Create an account" : "Sign in to your account"}</h2>
          <p>Adaptive diagnostic learning and evidence-grounded revision</p>
        </div>

        <form onSubmit={submit} className="login-form">
          {register && (
            <div className="form-group">
              <label htmlFor="name">Full Name</label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={80}
                placeholder="Student Name"
                className="input-field"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="student@demo.com"
              className="input-field"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              required
              minLength={register ? 8 : 1}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="input-field"
            />
          </div>

          {error && (
            <div className="form-alert error-alert" role="alert">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button type="submit" disabled={busy} className="w-full">
            {busy ? (
              <>
                <LoaderCircle size={16} className="spin" />
                <span>Processing...</span>
              </>
            ) : register ? (
              "Create account"
            ) : (
              "Sign in"
            )}
          </Button>

          <div className="login-toggle">
            <button
              type="button"
              className="link-button"
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
            >
              {register ? "Already have an account? Sign in" : "Need an account? Register"}
            </button>
          </div>
        </form>

        <div className="demo-credentials-card">
          <div className="demo-card-header">
            <FlaskConical size={16} className="text-indigo-600" />
            <span className="font-semibold text-slate-800">Demo Account</span>
          </div>
          <div className="demo-creds-row">
            <span>Email: <code>student@demo.com</code></span>
            <span>Password: <code>demo123</code></span>
          </div>
          <div className="demo-card-footer">
            <span className="text-xs text-slate-500">
              {health?.mode === "live" ? "Live Gemini AI mode" : "Offline deterministic demo mode"}
            </span>
            <button type="button" onClick={fillDemo} className="btn-demo-fill">
              Fill demo credentials
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
