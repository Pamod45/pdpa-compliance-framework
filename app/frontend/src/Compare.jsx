import React, { useEffect, useState } from "react";
import { api, f2, f3 } from "./api.js";
import { STATUS } from "./summary.js";

const when = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

function Delta({ d, fmt = f3 }) {
  if (d === undefined || d === null) return <span className="delta none">-</span>;
  const cls = d > 0.0005 ? "up" : d < -0.0005 ? "down" : "same";
  return <span className={"delta " + cls}>{cls === "same" ? "no change" : `${d > 0 ? "+" : ""}${fmt(d)}`}</span>;
}

function Stat({ label, b, a, fmt = f2, cls }) {
  const d = a !== null && b !== null ? a - b : null;
  return (
    <div className={"cstat " + (cls || "")}>
      <span>{label}</span>
      <b>{fmt(b)} → {fmt(a)}</b>
      {d !== null && <Delta d={d} fmt={fmt === f2 ? f3 : fmt} />}
    </div>
  );
}

const cell = (side) => (side.status === "scored"
  ? <>A {f2(side.alignment)} · R {f2(side.realization)}</>
  : <span className="muted">{side.status === "absent" ? "not proposed" : side.status}</span>);

export default function Compare({ ids, onBack }) {
  const [c, setC] = useState(null);
  const [err, setErr] = useState("");
  const [all, setAll] = useState(false);
  useEffect(() => { api.compareRuns(ids[0], ids[1]).then(setC).catch((e) => setErr(e.message)); }, [ids]);
  if (err) return <div className="compare"><p className="alert">{err}</p><button className="ghost" onClick={onBack}>Back to My runs</button></div>;
  if (!c) return <p className="muted"><span className="spinner" aria-hidden="true" />Comparing...</p>;
  const sb = c.summary.before, sa = c.summary.after;
  const changed = c.pairs.filter((p) => p.changed);
  const shown = all ? c.pairs : changed;
  return (
    <div className="compare">
      <header className="page-head"><h1>Compare two runs</h1>
        <p>The older run is shown as before, the newer one as after. Realization reads the plan's text, so most changes between versions of a plan show up there; Alignment reads the law and the NIST catalog.</p></header>
      <button className="link" onClick={onBack}>← Back to My runs</button>
      <div className="cruns">
        <div><span className="small">Before</span><h3>{c.before.name}</h3><p className="small">{c.before.ssp_name} · {when(c.before.created_utc)}</p></div>
        <div className="arrow" aria-hidden="true">→</div>
        <div><span className="small">After</span><h3>{c.after.name}</h3><p className="small">{c.after.ssp_name} · {when(c.after.created_utc)}</p></div>
      </div>
      {!c.same_scorer && <p className="alert">These runs used different scorer versions or text models, so differences may come from the scorer rather than the plan.</p>}
      {!c.same_clauses && <p className="note">These runs checked different clauses. Only duties in both runs can be compared directly.</p>}

      <div className="cstats">
        <Stat label="Duties covered and built" b={sb.built} a={sa.built} fmt={(x) => `${x}`} cls="built" />
        <Stat label="Average Alignment" b={sb.avg_alignment} a={sa.avg_alignment} cls="a" />
        <Stat label="Average Realization" b={sb.avg_realization} a={sa.avg_realization} cls="r" />
      </div>

      <section>
        <h2>Duties that changed group</h2>
        {c.duties.length === 0 ? <p className="small">No duty moved to a different group.</p> : (
          <table className="ctable"><thead><tr><th>Duty</th><th>Before</th><th>After</th></tr></thead><tbody>
            {c.duties.map((d) => (
              <tr key={d.unit_id}><td><b>{d.unit_id}</b> <span className="small">{d.obligation}</span></td>
                <td><span className={"dot s-" + d.before} /> {d.before ? STATUS[d.before].label : "not checked"}</td>
                <td><span className={"dot s-" + d.after} /> {d.after ? STATUS[d.after].label : "not checked"}</td></tr>))}
          </tbody></table>)}
      </section>

      <section>
        <div className="row-head"><h2>Pairs</h2>
          <label className="small"><input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} /> Show unchanged pairs too ({c.unchanged})</label></div>
        {shown.length === 0 ? <p className="small">No pair changed.</p> : (
          <table className="ctable"><thead><tr><th>Duty × control</th><th>Before</th><th>After</th><th>Change in A</th><th>Change in R</th></tr></thead><tbody>
            {shown.map((p) => (
              <tr key={p.unit_id + p.control_id} className={p.changed ? "" : "same"}>
                <td><b>{p.unit_id}</b> × <b>{p.control_id.toUpperCase()}</b> <span className="small">{p.title}</span></td>
                <td>{cell(p.before)}</td><td>{cell(p.after)}</td>
                <td><Delta d={p.d_alignment} /></td><td><Delta d={p.d_realization} /></td></tr>))}
          </tbody></table>)}
      </section>
    </div>
  );
}
