import React, { useEffect, useState } from "react";
import { api } from "./api.js";

const when = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "never");
const kb = (b) => (b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`);

export default function Admin({ onPanel }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const load = () => api.adminUsers().then(setData).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  async function remove(u) {
    if (!window.confirm(`Delete ${u.email} with their ${u.runs} saved run(s)? This cannot be undone.`)) return;
    try { await api.adminDeleteUser(u.id); load(); } catch (e) { setErr(e.message); }
  }
  return (
    <div className="admin">
      <header className="page-head"><h1>Admin</h1><p>Accounts on this site and what they store. Admins are set by the PCEF_ADMIN_EMAILS setting on the server.</p></header>
      {err && <p className="alert">{err}</p>}
      {data && (
        <>
          <div className="cstats">
            <div className="cstat"><span>Accounts</span><b>{data.totals.users}</b></div>
            <div className="cstat"><span>Saved runs</span><b>{data.totals.runs}</b></div>
            <div className="cstat"><span>Stored (compressed)</span><b>{kb(data.totals.stored_bytes)}</b></div>
          </div>
          <div className="row-actions"><button className="ghost" onClick={onPanel}>Open the expert panel</button></div>
          <table className="ctable">
            <thead><tr><th>Email</th><th>Created</th><th>Saved runs</th><th>Last run</th><th>Stored</th><th /></tr></thead>
            <tbody>{data.users.map((u) => (
              <tr key={u.id}>
                <td>{u.email}{u.admin && <span className="chip"> admin</span>}</td><td>{when(u.created_utc)}</td>
                <td>{u.runs}</td><td>{when(u.last_run_utc)}</td><td>{kb(u.stored_bytes)}</td>
                <td>{!u.admin && <button className="ghost danger" onClick={() => remove(u)}>Delete</button>}</td>
              </tr>))}</tbody>
          </table>
        </>
      )}
    </div>
  );
}
