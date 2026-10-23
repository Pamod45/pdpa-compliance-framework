import React, { useEffect, useMemo, useRef, useState } from "react";
import { api, f3 } from "./api.js";
import { AlignmentTrace, Inputs, RealizationTrace } from "./Trace.jsx";
import { GUIDE, download, key, summarise, toCSV } from "./summary.js";
import { ClauseControls, Controls, Gaps, Overview } from "./Views.jsx";
import Report from "./Report.jsx";
import DraftNote from "./DraftNote.jsx";
import { startTour, tourSeen } from "./tour.js";
import Term from "./Term.jsx";

function TupleMap({ pairs, selected, onSelect }) {
  const W = 420, H = 420, pad = 44;
  const x = (v) => pad + v * (W - pad * 1.5), y = (v) => H - pad - v * (H - pad * 1.5);
  return (
    <figure className="map">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Each clause-control pair placed by Alignment (across) and Realization (up)">
        <rect x={x(0)} y={y(1)} width={x(1) - x(0)} height={y(0) - y(1)} className="field" />
        <line x1={x(0.5)} x2={x(0.5)} y1={y(0)} y2={y(1)} className="guide" />
        <line x1={x(0)} x2={x(1)} y1={y(0.5)} y2={y(0.5)} className="guide" />
        <text x={x(0.98)} y={y(0.97)} className="ql" textAnchor="end">Covered on paper and built</text>
        <text x={x(0.98)} y={y(0.03)} className="ql" textAnchor="end">Covered on paper, not built</text>
        <text x={x(0.02)} y={y(0.97)} className="ql">Built, weak fit to the law</text>
        <text x={x(0.02)} y={y(0.03)} className="ql">Weak fit, not built</text>
        {[0, 0.5, 1].map((t) => <g key={t}>
          <text x={x(t)} y={y(0) + 18} className="tick" textAnchor="middle">{t}</text>
          <text x={x(0) - 10} y={y(t) + 4} className="tick" textAnchor="end">{t}</text></g>)}
        <text x={(x(0) + x(1)) / 2} y={H - 6} className="axis" textAnchor="middle">Alignment: control covers the law on paper</text>
        <text transform={`translate(12 ${(y(0) + y(1)) / 2}) rotate(-90)`} className="axis" textAnchor="middle">Realization: SSP shows it built</text>
        {pairs.map((p) => {
          const key = `${p.unit_id}|${p.control_id}`, on = selected === key;
          return (
            <g key={key} className={"pt" + (on ? " on" : "")} onClick={() => onSelect(key)} tabIndex={0}
               onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(key)} role="button"
               aria-label={`${key}: alignment ${f3(p.tuple.alignment)}, realization ${f3(p.tuple.realization)}`}>
              <circle cx={x(p.tuple.alignment)} cy={y(p.tuple.realization ?? 0)} r={on ? 8 : 5.5} />
              <title>{key}</title>
            </g>);
        })}
      </svg>
      <figcaption>The cross at 0.5 is a reading guide, not a pass mark. PCEF keeps both numbers and never merges them into one score.</figcaption>
    </figure>
  );
}

function RunBar({ meta, onResult, start, wantSample }) {
  const [file, setFile] = useState(null);
  const [chosen, setChosen] = useState(new Set(meta.clauses.map((c) => c.id)));
  const [busy, setBusy] = useState(false);
  const [secs, setSecs] = useState(0);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!busy) return undefined;
    const t0 = Date.now(), id = setInterval(() => setSecs(Math.floor((Date.now() - t0) / 1000)), 500);
    return () => clearInterval(id);
  }, [busy]);
  const input = useRef();
  useEffect(() => { if (wantSample && !busy && start !== "tour") { setFile(null); go(true); } }, [wantSample]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (start === "sample" || start === "tour") go();
    if (start === "upload") input.current?.click();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  const toggle = (id) => { const s = new Set(chosen); s.has(id) ? s.delete(id) : s.add(id); setChosen(s); };
  async function go(sample = false) {
    setBusy(true); setErr(""); setSecs(0);
    const fd = new FormData();
    fd.append("clause_ids", [...chosen].join(","));
    if (file && sample !== true) fd.append("ssp", file); else fd.append("use_sample", "true");
    const t0 = Date.now();
    try { const r = await api.run(fd); onResult(r, (Date.now() - t0) / 1000); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  return (
    <section className="runbar">
      <div className="drop" onClick={() => input.current.click()}
           onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}>
        <input ref={input} type="file" accept=".json,application/json" hidden onChange={(e) => setFile(e.target.files[0])} />
        <strong>{file ? file.name : "FleetTrack sample SSP"}</strong>
        <span>{file ? "Click to choose a different file" : "Drop an OSCAL SSP (JSON) here, or click to choose one. Leave empty to use the sample."}</span>
        {file && <button className="link" onClick={(e) => { e.stopPropagation(); setFile(null); }}>Use the sample instead</button>}
      </div>
      <div className="clauses">
        <div className="clauses-head"><span>PDPA clauses to check</span>
          <button className="link" onClick={() => setChosen(new Set(meta.clauses.map((c) => c.id)))}>All</button>
          <button className="link" onClick={() => setChosen(new Set())}>None</button></div>
        <div className="chips">
          {meta.clauses.map((c) => (
            <button key={c.id} className={"cl" + (chosen.has(c.id) ? " on" : "")} aria-pressed={chosen.has(c.id)} onClick={() => toggle(c.id)} title={c.title}>
              <b>{c.id.replace("PDPA-s", "s.")}</b> {c.title}</button>))}
        </div>
      </div>
      <div className="go">
        <button className="primary" disabled={busy || chosen.size === 0} onClick={go}>{busy ? "Scoring..." : `Score ${chosen.size} clause${chosen.size === 1 ? "" : "s"}`}</button>
        {busy && (
          <p className="progress" role="status">
            <span className="spinner" aria-hidden="true" />
            Scoring {chosen.size} clause{chosen.size === 1 ? "" : "s"} on {file ? file.name : "the FleetTrack sample"} · {secs} s
            {secs >= 15 && <span className="small"> A new plan takes about a minute: every duty is compared with every candidate control.</span>}
          </p>)}
        {err && <p className="alert">{err}</p>}
      </div>
    </section>
  );
}

const TABS = [["overview", "Overview"], ["clauses", "Clause to controls"], ["gaps", "Gaps"], ["controls", "Controls"], ["map", "Map"]];

// Plain-language reading of one pair for the person acting on it. Uses the overview's reading guide.
function Reading({ pick, r }) {
  const a = pick.tuple.alignment, rv = pick.tuple.realization ?? 0;
  const declared = !!r && Object.values(r.rows).some((v) => (v.by_components || []).some((b) => (b.negation_hits || []).length > 0));
  const fit = a >= GUIDE, shown = rv >= GUIDE;
  let means, todo;
  if (!fit) {
    means = "This control only partly matches what the duty asks for.";
    todo = "Look at the other controls listed for this duty. This one is not the main way to meet it.";
  } else if (shown) {
    means = "The right kind of control for this duty, and your plan shows it built.";
    todo = "Nothing to fix here. Keep the evidence your plan points to ready for an audit.";
  } else if (declared) {
    means = "The right kind of control for this duty, but your plan says it is not done yet.";
    todo = "Build it, then update the plan. Until then this control cannot be used to show the duty is met.";
  } else {
    means = "The right kind of control for this duty, but your plan does not show it built.";
    todo = "Build it, or describe what is already in place: name the component, files, settings and how it works.";
  }
  return (
    <section className="reading" aria-label="What this means">
      <div className="reading-chips">
        <span className={"rchip " + (fit ? "ok" : "low")}>{fit ? "Right kind of control" : "Weak fit to the duty"}</span>
        <span className={"rchip " + (shown ? "ok" : "low")}>{shown ? "Shown built in the plan" : declared ? "Plan says not done yet" : "Not shown built in the plan"}</span>
      </div>
      <p><b>What this means:</b> {means}</p>
      <p><b>What to do:</b> {todo}</p>
      <p className="small">Read at {GUIDE} on each score. This is a reading guide, not a pass mark.</p>
    </section>
  );
}

function Drawer({ pick, res, meta, onClose }) {
  if (!pick) return null;
  return (
    <div className="drawer-wrap" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label="Pair trace" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose} aria-label="Close">Close</button>
        <h2>{pick.unit_id} &times; {pick.control_id.toUpperCase()}</h2>
        <p className="tuple"><span className="a"><Term k="alignment">Alignment</Term> {f3(pick.tuple.alignment)}</span><span className="r"><Term k="realization">Realization</Term> {f3(pick.tuple.realization)}</span></p>
        <Reading pick={pick} r={res.realization[pick.control_id]} />
        {pick.gates.applicability.flags.length > 0 && <p className="note">Assumptions the applicability check made: {pick.gates.applicability.flags.join("; ")}.</p>}
        <Inputs ctx={pick.context} />
        <AlignmentTrace p={pick} constants={meta.constants} />
        <RealizationTrace r={res.realization[pick.control_id]} constants={meta.constants} />
      </aside>
    </div>
  );
}

// How the three inputs connect: the NIST control sits between the law and the plan.
function Bridge() {
  return (
    <figure className="bridge" aria-label="How PCEF connects the law, the NIST standard and your plan">
      <div className="bnode law"><span className="btag">The law · built in</span><b>PDPA duty</b><span>s.10: keep personal data confidential and intact</span></div>
      <div className="barrow a"><span>Alignment</span><small>Is this the right control for the duty?</small></div>
      <div className="bnode nist"><span className="btag">The bridge · built in</span><b>NIST SP 800-53 control</b><span>AC-3 Access Enforcement</span></div>
      <div className="barrow r"><span>Realization</span><small>Does the plan show it built?</small></div>
      <div className="bnode plan"><span className="btag">You provide</span><b>Your security plan (SSP)</b><span>Every request checks the user's role and company before returning data</span></div>
      <figcaption className="small">The law and your plan are never compared directly. Each duty is linked to standard NIST controls, and your plan is checked against those controls.</figcaption>
    </figure>
  );
}

export default function Explore({ meta, start, initial, user, onSignIn, onPrivacy }) {
  const [res, setRes] = useState(initial);
  const [took, setTook] = useState(0);
  const [sel, setSel] = useState(null);
  const [tab, setTab] = useState("overview");
  const [report, setReport] = useState(start === "report" && !!initial);
  const [wantTour, setWantTour] = useState(start === "tour");
  const [showInvite, setShowInvite] = useState(start !== "tour" && !initial && !tourSeen());
  const s = useMemo(() => (res ? summarise(res) : null), [res]);
  const scored = useMemo(() => (res ? res.pairs.filter((p) => p.status === "scored") : []), [res]);
  const pick = scored.find((p) => key(p) === sel) || null;
  useEffect(() => {
    const esc = (e) => e.key === "Escape" && setSel(null);
    window.addEventListener("keydown", esc); return () => window.removeEventListener("keydown", esc);
  }, []);
  useEffect(() => {
    if (!wantTour || !res) return;
    setWantTour(false); setShowInvite(false);
    const first = (s.gaps[0] || scored[0]);
    setTimeout(() => startTour({     // after the result has rendered
      openPair: () => first && setSel(key(first)),
      closePair: () => setSel(null),
      setTab,
    }), 300);
  }, [wantTour, res]);  // eslint-disable-line react-hooks/exhaustive-deps
  if (report && res) return <Report res={res} s={s} onClose={() => setReport(false)} />;
  const stamp = res ? res.ssp_name.replace(/\W+/g, "_").toLowerCase() : "";
  return (
    <div className="explore">
      <header className="page-head">
        <h1>Check a security plan against the PDPA</h1>
        <p>Upload your System Security Plan and choose the clauses. You get a summary of which legal duties your controls cover and how far your plan shows them built, then every detail behind it.</p>
        {user && <p className="small save-note">Signed in: runs you score are saved to My runs, including the plan text they quote. <button className="link" onClick={onPrivacy}>Privacy</button></p>}
      </header>
      <Bridge />
      {showInvite && (
        <div className="invite">
          <span><b>New here?</b> A one-minute tour runs the sample and explains each part of the result.</span>
          <button className="primary" onClick={() => { setShowInvite(false); setWantTour(true); }}>Take the tour</button>
          <button className="link" onClick={() => setShowInvite(false)}>Not now</button>
        </div>)}
      <RunBar meta={meta} start={start} wantSample={wantTour && !res} onResult={(r, t) => { setRes(r); setTook(t); setSel(null); setTab("overview"); }} />
      {res && (
        <>
          {res.draft && <DraftNote d={res.draft} />}
          <div className="result-bar">
            <p className="runinfo">{res.ssp_name}: {scored.length} pairs scored{initial === res && res.saved_run && !res.draft ? `. Reopened from My runs: ${res.saved_run.name}` : initial === res ? "" : ` in ${took < 1 ? "under a second" : `${Math.round(took)} s`}`}. Scorer {res.provenance.config_status}.
              {res.saved_run?.id && initial !== res && <span className="saved"> Saved to My runs.</span>}
              {res.saved_run && !res.saved_run.id && <span className="saved warn"> {res.saved_run.note}</span>}
              {!user && <> <button className="link" onClick={onSignIn}>Sign in</button> to keep a history of your runs.</>}</p>
            <div className="exports">
              <button className="primary" onClick={() => setReport(true)}>Open report</button>
              <button className="ghost" onClick={() => download(`pcef_${stamp}.csv`, toCSV(res), "text/csv")}>Download CSV</button>
              <button className="ghost" onClick={() => download(`pcef_${stamp}.json`, JSON.stringify(res, null, 2), "application/json")}>Download JSON</button>
            </div>
          </div>
          <div className="tabs" role="tablist">
            {TABS.map(([id, label]) => (
              <button key={id} role="tab" aria-selected={tab === id} className={"tab" + (tab === id ? " on" : "")} onClick={() => setTab(id)}>
                {label}{id === "gaps" && s.gaps.length ? <span className="count">{s.gaps.length}</span> : null}</button>))}
          </div>
          <div className="tabpanel">
            {tab === "overview" && <Overview s={s} onOpen={setSel} onTab={setTab} />}
            {tab === "clauses" && <ClauseControls s={s} onOpen={setSel} />}
            {tab === "gaps" && <Gaps s={s} onOpen={setSel} />}
            {tab === "controls" && <Controls s={s} onOpen={setSel} />}
            {tab === "map" && <div className="mapview"><TupleMap pairs={scored} selected={sel} onSelect={setSel} />
              <p className="small">Click a point to open its trace.</p></div>}
          </div>
          <Drawer pick={pick} res={res} meta={meta} onClose={() => setSel(null)} />
        </>
      )}
    </div>
  );
}
