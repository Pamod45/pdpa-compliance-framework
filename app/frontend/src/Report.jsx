import React from "react";
import { f2, f3 } from "./api.js";
import { GUIDE, ORDER, STATUS } from "./summary.js";
import { Legend, StatusBar } from "./Views.jsx";
import DraftNote from "./DraftNote.jsx";

export default function Report({ res, s, onClose }) {
  const pv = res.provenance;
  const when = new Date(pv.run_at_utc).toLocaleString();
  return (
    <div className="report">
      <div className="report-tools no-print">
        <button className="primary" onClick={() => window.print()}>Print or save as PDF</button>
        <button className="link" onClick={onClose}>Back to the results</button>
      </div>
      <header className="rp-head">
        <img className="rp-logo" src="/pcef-logo.svg" alt="PCEF - PDPA Compliance Evaluation Framework" width="233" height="54" />
        <h1>PDPA compliance evidence report</h1>
        <p>{res.ssp_name}, scored {when}{res.saved_run?.name ? ` · saved as "${res.saved_run.name}"` : ""}</p>
        {res.draft && <DraftNote d={res.draft} />}
        <p className="rp-disclaimer">Decision support, not a legal opinion. PCEF shows how well a security plan's controls match the duties in Sri Lanka's Personal Data Protection Act No. 9 of 2022, and how far the plan shows them implemented. It does not decide whether an organisation complies with the law.</p>
      </header>

      <section className="rp-sec">
        <h2>Summary</h2>
        <p>{s.duties.length} duties across {s.clauses.length} clauses. Each duty is judged by its best-fitting control; {GUIDE} is used as a reading guide on both scores.</p>
        <div className="rp-headline">
          <div><b>{s.counts.built}</b> of {s.duties.length} duties covered and built</div>
          {s.averages.n > 0 && <>
            <div>Average Alignment <b>{f2(s.averages.alignment)}</b></div>
            <div>Average Realization <b>{f2(s.averages.realization)}</b></div>
          </>}
        </div>
        {s.averages.n > 0 && <p className="small">Averages over the {s.averages.n} duties that have a scored control, each at its best-fitting control. Two separate averages, not a compliance rating.</p>}
        <StatusBar counts={s.counts} total={s.duties.length} />
        <Legend counts={s.counts} total={s.duties.length} />
      </section>

      <section className="rp-sec">
        <h2>Duties by clause</h2>
        <table className="rp-t">
          <thead><tr><th>Duty</th><th>Status</th><th>Best-fitting control</th><th>Alignment</th><th>Realization</th></tr></thead>
          <tbody>
            {s.clauses.map((c) => (
              <React.Fragment key={c.clause_id}>
                <tr className="rp-clause"><td colSpan={5}>{c.clause_id.replace("PDPA-s", "Section ")}: {c.title}</td></tr>
                {c.units.map((u) => (
                  <tr key={u.unit_id}>
                    <td><b>{u.unit_id}</b> {u.obligation}</td><td>{STATUS[u.status].label}</td>
                    <td>{u.best ? `${u.best.control_id.toUpperCase()} ${u.best.control_title}` : ""}</td>
                    <td>{u.best ? f3(u.best.tuple.alignment) : ""}</td><td>{u.best ? f3(u.best.tuple.realization) : ""}</td>
                  </tr>))}
              </React.Fragment>))}
          </tbody>
        </table>
      </section>

      <section className="rp-sec">
        <h2>Gaps to close</h2>
        {s.gaps.length === 0 ? <p>No control covers a duty on paper while the plan leaves it unbuilt, at the reading guide.</p> : (
          <table className="rp-t">
            <thead><tr><th>Control</th><th>For duty</th><th>Alignment</th><th>Realization</th><th>Rows the plan never addresses</th></tr></thead>
            <tbody>{s.gaps.map((p) => (
              <tr key={`${p.unit_id}|${p.control_id}`}>
                <td><b>{p.control_id.toUpperCase()}</b> {p.control_title}</td><td>{p.unit_id}</td>
                <td>{f3(p.tuple.alignment)}</td><td>{f3(p.tuple.realization)}{p.capped ? " (plan says not done)" : ""}</td>
                <td className="small">{p.missing.map((r) => r.id).join(", ") || "none"}</td></tr>))}</tbody>
          </table>)}
      </section>

      <section className="rp-sec">
        <h2>Controls</h2>
        <table className="rp-t">
          <thead><tr><th>Control</th><th>Realization</th><th>Catalog rows</th><th>Clauses that depend on it</th></tr></thead>
          <tbody>{s.controls.map((c) => (
            <tr key={c.control_id}><td><b>{c.control_id.toUpperCase()}</b> {c.title}</td><td>{f3(c.value)}</td>
              <td className="small">{Object.entries(c.statuses).map(([k, v]) => `${v} ${k}`).join(", ")}</td>
              <td>{c.clauses.map((x) => x.replace("PDPA-s", "s.")).join(", ")}</td></tr>))}</tbody>
        </table>
      </section>

      {(res.stage3.unanchored_units.length > 0 || res.pairs.some((p) => p.status !== "scored")) && (
        <section className="rp-sec">
          <h2>Not assessed</h2>
          {res.stage3.unanchored_units.length > 0 && <p>No control proposed: {res.stage3.unanchored_units.join(", ")}.</p>}
          {res.pairs.filter((p) => p.status !== "scored").map((p) => (
            <p key={`${p.unit_id}|${p.control_id}`}>{p.unit_id} with {p.control_id.toUpperCase()}: excluded by the {p.excluded_by.replace("_", " ")} check.</p>))}
        </section>)}

      <section className="rp-sec rp-stamp">
        <h2>Reproducibility</h2>
        <dl>
          <dt>Scorer</dt><dd>PCEF, {pv.config_status} (config fingerprint {pv.config_sha256.pcef_params.slice(0, 12)})</dd>
          <dt>Text model</dt><dd>{pv.embedder.model_id} at revision {String(pv.embedder.revision).slice(0, 12)}</dd>
          <dt>Inputs</dt><dd>SSP {pv.inputs_sha256.ssp.slice(0, 12)}, clause profiles {pv.inputs_sha256.profiles.slice(0, 12)}, catalog {pv.inputs_sha256.catalog.slice(0, 12)}</dd>
          <dt>System role</dt><dd>{pv.system_roles.roles ? pv.system_roles.roles.join(" and ") : "not declared"} ({pv.system_roles.source})</dd>
          <dt>Same input</dt><dd>Gives the same report every time.</dd>
          <dt>Report printed</dt><dd>{new Date().toLocaleString()}</dd>
        </dl>
      </section>
    </div>
  );
}
