"use client";

import { LogIn, LogOut, Shield } from "lucide-react";
import { useState } from "react";
import { login, logout } from "../lib/api";

export default function LoginPanel({ user, onUser }) {
  const [username, setUsername] = useState("admin_demo");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await login(username, password);
      onUser(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    await logout();
    onUser(null);
  }

  if (user) {
    return (
      <div className="login-panel compact">
        <div className="user-chip">
          <Shield size={18} />
          <span>
            <strong>{user.username}</strong>
            <small>{user.role} · {user.firm_id || "public"}</small>
          </span>
        </div>
        <button className="icon-button" type="button" onClick={signOut} aria-label="Sign out">
          <LogOut size={18} />
        </button>
      </div>
    );
  }

  return (
    <form className="login-panel" onSubmit={submit}>
      <label>
        <span>Username</span>
        <input value={username} onChange={(event) => setUsername(event.target.value)} />
      </label>
      <label>
        <span>Password</span>
        <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
      </label>
      {error && <p className="form-error">{error}</p>}
      <button className="primary-button" disabled={busy} type="submit">
        <LogIn size={18} />
        {busy ? "Signing in" : "Sign in"}
      </button>
    </form>
  );
}

