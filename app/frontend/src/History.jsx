import React, { useEffect, useState } from "react";
import { api, f2 } from "./api.js";

const when = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

function RunRow({ r, onOpen, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(r.name);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const s = r.summary;

  async function act(fn) {
    setBusy(true); setErr("");
    try { await fn(); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  return (
    <li className="hrow">
      <div className="hmain">
        {editing ? (
          <form className="hrename" onSubmit={(e) => { e.preventDefault(); act(async () => { await api.renameRun(r.id, name); setEditing(false); onChanged(); }); }}>
            <input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} aria-label="Run name" autoFocus />
            <button className="primary" disabled={busy}>Save</button>
            <button type="button" className="link" onClick={() => { setName(r.name); setEditing(false); }}>Cancel</button>
          </form>
        ) : <h3>{r.name}</h3>}
        <p className="small">{r.ssp_name} · {r.clause_ids.length} clause{r.clause_ids.length === 1 ? "" : "s"} · {when(r.created_utc)} · scorer {r.config_status}</p>
        {err && <p className="alert">{err}</p>}
      </div>
      <div className="hstats">
        <span className="hs built"><b>{s.built}</b> of {s.duties} covered and built</span>
        <span className="hs a">A <b>{f2(s.avg_alignment)}</b></span>
        <span className="hs r">R <b>{f2(s.avg_realization)}</b></span>
      </div>
      <div className="hactions">
        <button className="primary" disabled={busy} onClick={() => act(async () => onOpen(await api.getRun(r.id)))}>Open</button>
        <button className="ghost" disabled={busy} onClick={() => setEditing(true)}>Rename</button>
        <button className="ghost danger" disabled={busy}
                onClick={() => window.confirm(`Delete "${r.name}"? This cannot be undone.`) && act(async () => { await api.deleteRun(r.id); onChanged(); })}>Delete</button>
      </div>
    </li>
  );
}

export default function History({ user, onOpen, onSignIn }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const load = () => api.runs().then(setData).catch((e) => setErr(e.message));
  useEffect(() => { if (user) load(); }, [user]);  // eslint-disable-line react-hooks/exhaustive-deps

  if (!user) {
    return (
      <div className="history">
        <header className="page-head"><h1>My runs</h1><p>Sign in and every run you score is kept here, so you can come back to it later.</p></header>
        <button className="primary" onClick={onSignIn}>Sign in or create an account</button>
      </div>
    );
  }
  return (
    <div className="history">
      <header className="page-head"><h1>My runs</h1>
        <p>Every run you score while signed in is saved here with its scorer version, so it can be reopened exactly as it was.</p></header>
      {err && <p className="alert">{err}</p>}
      {!data && !err && <p className="muted">Loading your runs...</p>}
      {data && data.runs.length === 0 && <div className="empty"><h3>No saved runs yet</h3><p>Score a plan in Explore and it will appear here.</p></div>}
      {data && data.runs.length > 0 && (
        <>
          <p className="small">{data.runs.length} of {data.limit} saved runs. A and R are the average Alignment and Realization over duties with a scored control.</p>
          <ul className="hlist">{data.runs.map((r) => <RunRow key={r.id} r={r} onOpen={onOpen} onChanged={load} />)}</ul>
        </>
      )}
    </div>
  );
}
