import React, { useState } from "react";
import { api } from "./api.js";

function DeleteAccount({ onDeleted }) {
  const [open, setOpen] = useState(false);
  const [pw, setPw] = useState("");
  const [sure, setSure] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  if (!open) return <button className="ghost danger" onClick={() => setOpen(true)}>Delete my account and data</button>;
  return (
    <form className="auth-form danger-zone" onSubmit={async (e) => {
      e.preventDefault(); setBusy(true); setErr("");
      try { await api.deleteAccount(pw); onDeleted(); } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
    }}>
      <p><b>This deletes your email, sign-in sessions and every saved run.</b> It cannot be undone. Download your data first if you want a copy.</p>
      <label>Your password<input type="password" autoComplete="current-password" required value={pw} onChange={(e) => setPw(e.target.value)} /></label>
      <label className="check"><input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} /> I understand this cannot be undone</label>
      {err && <p className="alert" role="alert">{err}</p>}
      <div className="row-actions">
        <button className="primary danger" disabled={busy || !sure}>{busy ? "Deleting..." : "Delete everything"}</button>
        <button type="button" className="link" onClick={() => { setOpen(false); setPw(""); setSure(false); setErr(""); }}>Cancel</button>
      </div>
    </form>
  );
}

export default function Account({ user, onUser, onPrivacy }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const r = await (mode === "login" ? api.login : api.signup)({ email, password });
      setPassword(""); onUser(r.email);
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  }

  if (user) {
    return (
      <div className="account">
        <header className="page-head"><h1>Your account</h1><p>Signed in as <b>{user}</b>.</p></header>
        <button className="ghost" onClick={async () => { await api.logout().catch(() => {}); onUser(null); }}>Sign out</button>
        <section className="acct-data">
          <h2>Your data</h2>
          <p>See what is stored and for how long in <button className="link" onClick={onPrivacy}>Privacy</button>.</p>
          <div className="row-actions">
            <a className="button ghost" href="/api/runs/export" download="pcef_my_data.json">Download my data</a>
          </div>
          <DeleteAccount onDeleted={() => onUser(null)} />
        </section>
      </div>
    );
  }

  const signup = mode === "signup";
  return (
    <div className="account">
      <header className="page-head"><h1>{signup ? "Create an account" : "Sign in"}</h1>
        <p>Signing in is optional. Scoring works the same with or without an account.</p></header>
      <form className="auth-form" onSubmit={submit}>
        <div className="auth-tabs" role="tablist">
          <button type="button" role="tab" aria-selected={!signup} className={!signup ? "on" : ""} onClick={() => { setMode("login"); setErr(""); }}>Sign in</button>
          <button type="button" role="tab" aria-selected={signup} className={signup ? "on" : ""} onClick={() => { setMode("signup"); setErr(""); }}>Create account</button>
        </div>
        <label>Email
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>Password
          <input type="password" autoComplete={signup ? "new-password" : "current-password"} required minLength={signup ? 10 : undefined}
                 value={password} onChange={(e) => setPassword(e.target.value)} />
          {signup && <span className="small">At least 10 characters. A short sentence works well.</span>}
        </label>
        {err && <p className="alert" role="alert">{err}</p>}
        <button className="primary" disabled={busy}>{busy ? "Please wait..." : signup ? "Create account" : "Sign in"}</button>
        <p className="small">Your password is stored only as a one-way hash, and you stay signed in for up to 14 days on this browser. Runs you score while signed in are saved; see <button type="button" className="link" onClick={onPrivacy}>Privacy</button>.</p>
      </form>
    </div>
  );
}
