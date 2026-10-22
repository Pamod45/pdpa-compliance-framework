import React, { useEffect, useState } from "react";
import { download, summarise } from "./summary.js";
import { api, f2 } from "./api.js";

const when = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export function draftRows(ssp) {
  const s = ssp["system-security-plan"];
  const comps = Object.fromEntries(s["system-implementation"].components.map((c) => [c.uuid, c]));
  return s["control-implementation"]["implemented-requirements"].flatMap((ir) => ir.statements.flatMap((st) =>
    st["by-components"].map((b) => ({ control: ir["control-id"], statement: st["statement-id"], component: comps[b["component-uuid"]],
                                      description: b.description, remarks: b.remarks || "" }))));
}

function rebuild(ssp, rows, role) {
  const copy = JSON.parse(JSON.stringify(ssp));
  const s = copy["system-security-plan"];
  s["system-characteristics"].props = role ? [{ name: "pdpa-role", value: role }] : [];
  for (const ir of s["control-implementation"]["implemented-requirements"]) {
    for (const st of ir.statements) {
      st["by-components"] = rows.filter((r) => !r.removed && r.control === ir["control-id"] && r.statement === st["statement-id"])
        .map((r) => ({ ...r.raw, description: r.description, ...(r.remarks ? { remarks: r.remarks } : { remarks: undefined }) }));
    }
    ir.statements = ir.statements.filter((st) => st["by-components"].length > 0);
  }
  s["control-implementation"]["implemented-requirements"] = s["control-implementation"]["implemented-requirements"].filter((ir) => ir.statements.length > 0);
  return copy;
}

function Headline({ label, s }) {
  return (
    <div className="dh">
      <span className="small">{label}</span>
      <b>{s.counts.built}</b> <span className="small">of {s.duties.length} covered and built</span>
      <span className="hs a">A <b>{f2(s.averages.alignment)}</b></span> <span className="hs r">R <b>{f2(s.averages.realization)}</b></span>
    </div>
  );
}

function Result({ out, meta, sampleId, onOpenResult }) {
  const pv = out.provenance;
  const ssp0 = out.ssp["system-security-plan"];
  const name = ssp0["system-characteristics"]["system-name"];
  const start = draftRows(out.ssp).map((r, i) => ({ ...r, id: i, raw: ssp0["control-implementation"]["implemented-requirements"]
    .find((ir) => ir["control-id"] === r.control).statements.find((st) => st["statement-id"] === r.statement)["by-components"]
    .find((b) => b.description === r.description), removed: false }));
  const [rows, setRows] = useState(start);
  const [role, setRole] = useState((ssp0["system-characteristics"].props || []).find((p) => p.name === "pdpa-role")?.value || "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [scored, setScored] = useState(null);
  const edits = rows.filter((r, i) => r.removed || r.description !== start[i].description || r.remarks !== start[i].remarks).length
    + (role !== ((ssp0["system-characteristics"].props || []).find((p) => p.name === "pdpa-role")?.value || "") ? 1 : 0);
  const set = (id, patch) => setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  const edited = () => rebuild(out.ssp, rows, role);

  async function score() {
    setBusy(true); setErr(""); setScored(null);
    try {
      const ids = meta.clauses.map((c) => c.id).join(",");
      const fd = new FormData();
      fd.append("clause_ids", ids);
      fd.append("ssp", new Blob([JSON.stringify(edited())], { type: "application/json" }), `LLM draft (reviewed) - ${name}.json`);
      fd.append("draft_provenance", JSON.stringify({ ...pv, edits }));
      const res = await api.run(fd);
      let base = null;
      if (sampleId === "fleettrack") {
        const bf = new FormData();
        bf.append("clause_ids", ids); bf.append("use_sample", "true"); bf.append("dont_save", "true");
        base = await api.run(bf);
      }
      setScored({ res, base });
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <section className="draft-out">
      <div className="row-head"><h2>Review the draft: {name}</h2>
        <button className="ghost" onClick={() => download(`draft_ssp_${name.replace(/\W+/g, "_").toLowerCase()}.json`, JSON.stringify(edited(), null, 2), "application/json")}>Download OSCAL JSON</button></div>
      <p className="small">Drafted by {pv.model_version || pv.model} on {when(pv.generated_utc)} from "{pv.source}"{out.cached ? " (stored draft, no new model call)" : ""}. The draft passed PCEF's SSP parser. Check each statement against the document: correct the text, mark gaps, or remove statements the document does not support. Then score it.</p>
      {out.warnings.length > 0 && (
        <div className="note"><b>Checks on the draft</b><ul>{out.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>)}
      <label className="draft-role">PDPA role of the organisation{" "}
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">Not stated</option><option value="controller">Controller</option>
          <option value="processor">Processor</option><option value="controller,processor">Controller and processor</option>
        </select></label>
      <table className="ctable draft-edit"><thead><tr><th>Control part</th><th>Implementation text (editable)</th><th>Gap</th><th /></tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.id} className={r.removed ? "removed" : ""}>
            <td><b>{r.statement}</b><div className="small">{r.component?.title}</div></td>
            <td><textarea rows={3} value={r.description} disabled={r.removed} onChange={(e) => set(r.id, { description: e.target.value })} aria-label={`Text for ${r.statement}`} /></td>
            <td><label className="small"><input type="checkbox" checked={/known gap/i.test(r.remarks)} disabled={r.removed}
                  onChange={(e) => set(r.id, { remarks: e.target.checked ? "KNOWN GAP" : "" })} /> known gap</label></td>
            <td><button className="link" onClick={() => set(r.id, { removed: !r.removed })}>{r.removed ? "Restore" : "Remove"}</button></td>
          </tr>))}</tbody></table>
      <div className="row-actions">
        <button className="primary" disabled={busy || rows.every((r) => r.removed)} onClick={score}>{busy ? "Scoring..." : "Score this draft"}</button>
        <span className="small">{edits === 0 ? "No changes yet." : `${edits} change${edits === 1 ? "" : "s"} made.`} The result is labelled as LLM-drafted and reviewed by you.</span>
      </div>
      {err && <p className="alert">{err}</p>}
      {scored && (() => {
        const sd = summarise(scored.res), sb = scored.base && summarise(scored.base);
        return (
          <div className="draft-scored">
            <h3>Scored with the frozen scorer</h3>
            <Headline label="LLM draft, reviewed" s={sd} />
            {sb && <Headline label="Hand-written FleetTrack plan" s={sb} />}
            {sb && <p className="small">Both use the same scorer and clauses. Differences come from what the draft says, so they show how much an LLM draft from a short prose overview captures compared with the full hand-written plan.</p>}
            <button className="primary" onClick={() => onOpenResult(scored.res)}>Open the full results</button>
          </div>);
      })()}
    </section>
  );
}

export default function Draft({ meta, onOpenResult, onSignIn }) {
  const [status, setStatus] = useState(null);
  const [samples, setSamples] = useState([]);
  const [pick, setPick] = useState(null);
  const [own, setOwn] = useState("");
  const [consent, setConsent] = useState(false);
  const [out, setOut] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.draftStatus().then(setStatus).catch((e) => setErr(e.message));
    api.draftSamples().then((s) => { setSamples(s); setPick(s[0]?.id || null); }).catch(() => {});
  }, []);
  const [lastSample, setLastSample] = useState(null);
  async function run(body) {
    setBusy(true); setErr(""); setOut(null); setLastSample(body.text ? null : body.sample_id);
    try { setOut(await api.draft(body)); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  const sample = samples.find((s) => s.id === pick);
  return (
    <div className="draft">
      <header className="page-head"><h1>Draft an SSP from a document <span className="chip">beta</span></h1>
        <p>An LLM (Google Gemini) reads a prose description of a system and drafts an OSCAL System Security Plan from it. The draft is checked against the NIST catalog and PCEF's SSP parser. The LLM never scores anything: scoring stays with the frozen scorer.</p></header>
      <p className="pv-warn small">This site uses Gemini's free tier, where Google may use what is sent to improve its products and people may review it. Anyone can draft the sample document below. Signed-in users can draft their own documents, a few a day, after confirming each time. Do not send confidential documents.</p>
      {status && !status.configured && <p className="alert">Drafting is not set up on this server yet.</p>}

      <section className="draft-in">
        <h2>Sample document</h2>
        <div className="draft-pick">{samples.map((s) => (
          <button key={s.id} className={"wt-case" + (pick === s.id ? " on" : "")} onClick={() => setPick(s.id)}><b>{s.title}</b></button>))}</div>
        {sample && <pre className="draft-doc">{sample.text}</pre>}
        <div className="row-actions">
          <button className="primary" disabled={busy || !status?.configured || !sample} onClick={() => run({ sample_id: pick })}>
            {busy ? "Drafting..." : "Draft an SSP from this document"}</button>
          {status?.is_admin && <button className="link" disabled={busy} onClick={() => run({ sample_id: pick, regenerate: true })}>Redraft (admin)</button>}
        </div>
      </section>

      <section className="draft-in">
        <h2>Your own document</h2>
        {status && !status.signed_in && (
          <p>Sign in to draft an SSP from your own technical document. <button className="link strong" onClick={onSignIn}>Sign in or create an account</button></p>)}
        {status?.signed_in && !status.can_draft_own_text && <p className="small">Drafting your own documents is limited to site admins on this server.</p>}
        {status?.can_draft_own_text && (
          <>
            <textarea className="draft-text" rows={8} value={own} maxLength={20000} onChange={(e) => setOwn(e.target.value)}
                      placeholder="Paste a technical description of your system: its parts, how access, logging, encryption, retention and incidents are handled, and any known gaps." />
            <label className="consent"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              I understand this text is sent to Google's Gemini API on the free tier, where Google may use it to improve its products and people may review it. It contains nothing confidential or personal.</label>
            <div className="row-actions">
              <button className="primary" disabled={busy || !own.trim() || !consent || !status.configured}
                      onClick={async () => { await run({ text: own, consent: true }); setConsent(false); api.draftStatus().then(setStatus).catch(() => {}); }}>Draft from this text</button>
              <span className="small">{own.length.toLocaleString()} / 20,000 characters
                {status.drafts_left_today !== null && ` · ${status.drafts_left_today} draft${status.drafts_left_today === 1 ? "" : "s"} left today`}</span>
            </div>
          </>)}
      </section>

      {busy && <p className="progress"><span className="spinner" aria-hidden="true" />Asking the model and checking its draft. This can take up to a minute.</p>}
      {err && <p className="alert">{err}</p>}
      {out && meta && <Result key={out.provenance.generated_utc} out={out} meta={meta} sampleId={lastSample} onOpenResult={onOpenResult} />}
    </div>
  );
}
