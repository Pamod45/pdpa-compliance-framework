import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { download } from "./summary.js";

const when = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export function draftRows(ssp) {
  const s = ssp["system-security-plan"];
  const comps = Object.fromEntries(s["system-implementation"].components.map((c) => [c.uuid, c]));
  return s["control-implementation"]["implemented-requirements"].flatMap((ir) => ir.statements.flatMap((st) =>
    st["by-components"].map((b) => ({ control: ir["control-id"], statement: st["statement-id"], component: comps[b["component-uuid"]],
                                      description: b.description, remarks: b.remarks || "" }))));
}

function Result({ out }) {
  const rows = draftRows(out.ssp);
  const pv = out.provenance;
  const name = out.ssp["system-security-plan"]["system-characteristics"]["system-name"];
  return (
    <section className="draft-out">
      <div className="row-head"><h2>Draft SSP: {name}</h2>
        <button className="ghost" onClick={() => download(`draft_ssp_${name.replace(/\W+/g, "_").toLowerCase()}.json`, JSON.stringify(out.ssp, null, 2), "application/json")}>Download OSCAL JSON</button></div>
      <p className="small">Drafted by {pv.model_version || pv.model} on {when(pv.generated_utc)} from "{pv.source}"{out.cached ? " (stored draft, no new model call)" : ""}. The draft passed PCEF's SSP parser. It is a starting point to review, not a finished plan.</p>
      {out.warnings.length > 0 && (
        <div className="note"><b>Checks on the draft</b><ul>{out.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>)}
      <table className="ctable"><thead><tr><th>Control part</th><th>Component</th><th>Drafted implementation text</th></tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i}><td><b>{r.statement}</b></td><td className="small">{r.component?.title}{r.component?.status?.state !== "operational" ? " (not operational)" : ""}</td>
            <td>{r.description}{r.remarks && <span className="chip warn"> {r.remarks}</span>}</td></tr>))}</tbody></table>
    </section>
  );
}

export default function Draft() {
  const [status, setStatus] = useState(null);
  const [samples, setSamples] = useState([]);
  const [pick, setPick] = useState(null);
  const [own, setOwn] = useState("");
  const [out, setOut] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.draftStatus().then(setStatus).catch((e) => setErr(e.message));
    api.draftSamples().then((s) => { setSamples(s); setPick(s[0]?.id || null); }).catch(() => {});
  }, []);
  async function run(body) {
    setBusy(true); setErr(""); setOut(null);
    try { setOut(await api.draft(body)); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  const sample = samples.find((s) => s.id === pick);
  return (
    <div className="draft">
      <header className="page-head"><h1>Draft an SSP from a document <span className="chip">beta</span></h1>
        <p>An LLM (Google Gemini) reads a prose description of a system and drafts an OSCAL System Security Plan from it. The draft is checked against the NIST catalog and PCEF's SSP parser. The LLM never scores anything: scoring stays with the frozen scorer.</p></header>
      <p className="pv-warn small">Demo only. This site uses Gemini's free tier, where Google may use and review what is sent. So the public can draft only the sample document below; drafting your own text is limited to site admins. Do not use this for confidential plans.</p>
      {status && !status.configured && <p className="alert">Drafting is not set up on this server yet.</p>}

      <section className="draft-in">
        <h2>Sample document</h2>
        <div className="draft-pick">{samples.map((s) => (
          <button key={s.id} className={"wt-case" + (pick === s.id ? " on" : "")} onClick={() => setPick(s.id)}><b>{s.title}</b></button>))}</div>
        {sample && <pre className="draft-doc">{sample.text}</pre>}
        <div className="row-actions">
          <button className="primary" disabled={busy || !status?.configured || !sample} onClick={() => run({ sample_id: pick })}>
            {busy ? "Drafting..." : "Draft an SSP from this document"}</button>
          {status?.can_draft_own_text && <button className="link" disabled={busy} onClick={() => run({ sample_id: pick, regenerate: true })}>Redraft (admin)</button>}
        </div>
      </section>

      {status?.can_draft_own_text && (
        <section className="draft-in">
          <h2>Your own document (admin)</h2>
          <textarea className="draft-text" rows={8} value={own} maxLength={20000} onChange={(e) => setOwn(e.target.value)}
                    placeholder="Paste a technical description of a system. It is sent to Google's Gemini API." />
          <div className="row-actions">
            <button className="primary" disabled={busy || !own.trim() || !status.configured} onClick={() => run({ text: own })}>Draft from this text</button>
            <span className="small">{own.length.toLocaleString()} / 20,000 characters</span>
          </div>
        </section>)}

      {busy && <p className="progress"><span className="spinner" aria-hidden="true" />Asking the model and checking its draft. This can take up to a minute.</p>}
      {err && <p className="alert">{err}</p>}
      {out && <Result out={out} />}
    </div>
  );
}
