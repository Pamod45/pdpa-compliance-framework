import React from "react";
import { f2, f3 } from "./api.js";
import { GUIDE, ORDER, STATUS, key } from "./summary.js";

export function StatusBar({ counts, total }) {
  return (
    <div className="sbar" role="img" aria-label={ORDER.map((s) => `${STATUS[s].label}: ${counts[s]}`).join(", ")}>
      {ORDER.filter((s) => counts[s] > 0).map((s) => (
        <span key={s} className={"seg s-" + s} style={{ flexGrow: counts[s] }} title={`${STATUS[s].label}: ${counts[s]} of ${total}`} />))}
    </div>
  );
}

export function Legend({ counts, total }) {
  return (
    <ul className="legend">
      {ORDER.map((s) => (
        <li key={s} className={counts[s] === 0 ? "zero" : ""}>
          <span className={"sw s-" + s} /><b>{counts[s]}</b> <span>{STATUS[s].label}</span>
          <small>{STATUS[s].hint}</small></li>))}
    </ul>
  );
}

const TupleChip = ({ p, onOpen }) => (
  <button className="tchip" onClick={() => onOpen(key(p))} title="Open the full trace">
    <b>{p.control_id.toUpperCase()}</b> <span className="muted">{p.control_title}</span>
    <span className="ta">A {f2(p.tuple.alignment)}</span><span className="tr">R {f2(p.tuple.realization)}</span>
  </button>
);

export function Overview({ s, onOpen, onTab }) {
  const total = s.duties.length;
  return (
    <div className="overview">
      <section className="ov-head">
        <div>
          <h2>{total} duties checked across {s.clauses.length} clause{s.clauses.length === 1 ? "" : "s"}</h2>
          <p className="small">Each duty is judged by its best-fitting control (highest Alignment). Sorting uses {GUIDE} as a reading guide on both scores; it is not a pass mark, and PCEF never merges the two scores into one.</p>
        </div>
        <StatusBar counts={s.counts} total={total} />
        <Legend counts={s.counts} total={total} />
      </section>
      <section>
        <div className="row-head"><h3>By clause</h3>
          {s.gaps.length > 0 && <button className="link" onClick={() => onTab("gaps")}>See the {s.gaps.length} gaps to close</button>}</div>
        <div className="clause-cards">
          {s.clauses.map((c) => {
            const duties = c.units.filter((u) => u.status !== "nonduty");
            const cnt = Object.fromEntries(ORDER.map((k) => [k, duties.filter((u) => u.status === k).length]));
            return (
              <article key={c.clause_id} className="ccard">
                <header><h4>{c.clause_id.replace("PDPA-s", "Section ")}</h4><p>{c.title}</p></header>
                <StatusBar counts={cnt} total={duties.length} />
                <ul className="units">
                  {c.units.map((u) => (
                    <li key={u.unit_id} className={"unit s-" + u.status}>
                      <span className={"dot s-" + u.status} title={STATUS[u.status].label} />
                      <span className="uo">{u.obligation}</span>
                      <span className="us">{STATUS[u.status].label}{u.best ? <> via <button className="link" onClick={() => onOpen(key(u.best))}>{u.best.control_id.toUpperCase()}</button></> : null}</span>
                    </li>))}
                </ul>
              </article>);
          })}
        </div>
      </section>
    </div>
  );
}

export function ClauseControls({ s, onOpen }) {
  return (
    <div className="cc">
      <p className="small">Every duty with the controls proposed for it, best fit first. A = Alignment (covers the law on paper), R = Realization (the plan shows it built).</p>
      {s.clauses.map((c) => (
        <section key={c.clause_id} className="cc-clause">
          <h3>{c.clause_id.replace("PDPA-s", "Section ")}: {c.title}</h3>
          {c.units.map((u) => (
            <div key={u.unit_id} className="cc-unit">
              <div className="cc-u"><span className={"dot s-" + u.status} /><b>{u.unit_id}</b> {u.obligation}<span className="muted"> ({STATUS[u.status].label})</span></div>
              <div className="cc-ctl">
                {u.pairs.map((p) => <TupleChip key={key(p)} p={p} onOpen={onOpen} />)}
                {u.excluded.map((p) => <span key={key(p)} className="tchip off">{p.control_id.toUpperCase()} excluded: {p.excluded_by.replace("_", " ")}</span>)}
                {u.pairs.length + u.excluded.length === 0 && <span className="muted small">{u.status === "nonduty" ? "Not a duty, so no control is expected." : "No control proposed."}</span>}
              </div>
            </div>))}
        </section>))}
    </div>
  );
}

export function Gaps({ s, onOpen }) {
  if (s.gaps.length === 0) return <div className="empty"><h3>No gaps at the reading guide</h3><p>No pair has Alignment of at least {GUIDE} with Realization below {GUIDE}.</p></div>;
  return (
    <div className="gaps">
      <p className="small">Pairs where a control covers the law on paper (Alignment at least {GUIDE}) but the plan does not show it built (Realization below {GUIDE}). Largest gap first. The missing rows are the catalog statements the plan never addresses.</p>
      <ol className="gap-list">
        {s.gaps.map((p) => {
          return (
            <li key={key(p)} className="gap">
              <div className="gap-head">
                <button className="link strong" onClick={() => onOpen(key(p))}>{p.control_id.toUpperCase()}: {p.control_title}</button>
                <span className="muted">for {p.unit_id} ({p.context.clause_id.replace("PDPA-s", "s.")})</span>
                <span className="gapnum"><span className="ta">A {f2(p.tuple.alignment)}</span><span className="tr">R {f2(p.tuple.realization)}</span></span>
              </div>
              <p className="small">{p.context.obligation}</p>
              {p.missing.length > 0 && (
                <details><summary>{p.missing.length} catalog row{p.missing.length === 1 ? "" : "s"} the plan never addresses</summary>
                  <ul className="miss">{p.missing.map((r) => <li key={r.id}><span className="rid">{r.id}</span>{r.text}</li>)}</ul></details>)}
              {p.capped && <p className="flag-text small">The plan itself says this control is not done.</p>}
            </li>);
        })}
      </ol>
    </div>
  );
}

export function Controls({ s, onOpen }) {
  return (
    <table className="ctable">
      <thead><tr><th>Control</th><th>Realization</th><th>Catalog rows</th><th>Duties that depend on it</th></tr></thead>
      <tbody>
        {s.controls.map((c) => (
          <tr key={c.control_id}>
            <td><b>{c.control_id.toUpperCase()}</b> <span className="muted">{c.title}</span></td>
            <td><span className="bar r" style={{ "--v": c.value ?? 0 }} />{f3(c.value)}</td>
            <td className="small">{Object.entries(c.statuses).map(([k, v]) => `${v} ${k}`).join(", ")}</td>
            <td>{c.pairs.length === 0 ? <span className="muted">none scored</span> :
              c.pairs.map((p, i) => <React.Fragment key={key(p)}>{i > 0 && ", "}<button className="link" onClick={() => onOpen(key(p))}>{p.unit_id}</button></React.Fragment>)}</td>
          </tr>))}
      </tbody>
    </table>
  );
}
