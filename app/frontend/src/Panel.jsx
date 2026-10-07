import React, { useEffect, useRef, useState } from "react";
import { api, f2, f3 } from "./api.js";
import { AlignmentTrace, Explain, Inputs, RealizationTrace } from "./Trace.jsx";

const APP_NAME = { claude: "Claude", chatgpt: "ChatGPT", gemini: "Gemini" };
const DEFENSIBLE = [
  ["pcef", "PCEF's reading"], ["llms", "The LLMs' reading"], ["both", "Both about equally"],
  ["neither", "Neither"], ["cannot", "Cannot judge"],
];

function Rating({ label, help, value, onChange }) {
  return (
    <div className="rating">
      <label><span className="rl">{label}</span><span className="rh">{help}</span></label>
      <div className="rating-row">
        <input type="range" min="0" max="1" step="0.05" value={value ?? 0.5} aria-label={label}
               className={value === null ? "unset" : ""} onChange={(e) => onChange(Number(e.target.value))} />
        <output>{value === null ? "not set" : f2(value)}</output>
      </div>
      <div className="scale"><span>0 not at all</span><span>0.5 partly</span><span>1 fully</span></div>
    </div>
  );
}

function Item({ item, idx, total, expert, pack, meta, onSaved }) {
  const [a, setA] = useState(null), [r, setR] = useState(null), [conf, setConf] = useState("");
  const [note, setNote] = useState(""), [revealed, setRevealed] = useState(false);
  const [dA, setDA] = useState(""), [dR, setDR] = useState(""), [note2, setNote2] = useState("");
  const [err, setErr] = useState(""), [saving, setSaving] = useState(false);
  const t0 = useRef(Date.now()), tBlind = useRef(null);
  const canReveal = a !== null && r !== null && conf;
  const canSave = revealed && dA && dR;
  async function save() {
    setSaving(true); setErr("");
    try {
      await api.panelSave({ expert, pair: item.pair, pack_sha256: pack.sha256, blind_alignment: a, blind_realization: r,
        confidence: conf, blind_note: note, defensible_alignment: dA, defensible_realization: dR, reveal_note: note2,
        seconds_blind: tBlind.current });
      onSaved(item.pair);
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  }
  const P = item.pcef;
  return (
    <article className="pitem">
      <div className="progress" aria-label={`Pair ${idx + 1} of ${total}`}><span style={{ width: `${(idx / total) * 100}%` }} /></div>
      <p className="muted">Pair {idx + 1} of {total}</p>
      <Inputs ctx={item.context} />
      <section className={"blind" + (revealed ? " locked" : "")}>
        <h3>Your judgement</h3>
        <p className="small">Rate from the texts above before you see any scores.</p>
        <fieldset disabled={revealed}>
          <Rating label="Alignment" help="Does the control, as written in the catalog, address this obligation?" value={a} onChange={setA} />
          <Rating label="Realization" help="How fully does the SSP text show this control implemented?" value={r} onChange={setR} />
          <div className="conf"><span>How confident are you?</span>
            {["low", "medium", "high"].map((c) => <label key={c}><input type="radio" name="conf" checked={conf === c} onChange={() => setConf(c)} />{c}</label>)}</div>
          <textarea placeholder="Optional: why (one or two sentences)" value={note} onChange={(e) => setNote(e.target.value)} />
        </fieldset>
        {!revealed && <button className="primary" disabled={!canReveal} onClick={() => { tBlind.current = (Date.now() - t0.current) / 1000; setRevealed(true); }}>
          Lock my ratings and show the scores</button>}
      </section>
      {revealed && (
        <section className="reveal">
          <h3>How the scorers read this pair</h3>
          <table className="cmp">
            <thead><tr><th></th><th>Alignment</th><th>Realization</th><th>Spread across 3 runs</th></tr></thead>
            <tbody>
              <tr className="you"><td>You</td><td>{f2(a)}</td><td>{f2(r)}</td><td></td></tr>
              <tr className="pcef"><td>PCEF</td><td>{f3(P.tuple.alignment)}</td><td>{f3(P.tuple.realization)}</td><td>identical every run</td></tr>
              {Object.entries(item.llms).map(([k, m]) => (
                <tr key={k}><td>{APP_NAME[k] || k} <span className="muted">{m.model}</span></td><td>{f2(m.median_alignment)}</td><td>{f2(m.median_realization)}</td>
                  <td className="muted">{m.runs.map((x) => `${f2(x.alignment)}/${f2(x.realization)}`).join("  ")}</td></tr>))}
            </tbody>
          </table>
          <p className="small">LLM values are the median of 3 runs. The last column lists each run as alignment/realization.</p>
          <Explain title="Read the LLMs' reasons">
            {Object.entries(item.llms).map(([k, m]) => (
              <div key={k} className="why"><b>{APP_NAME[k] || k}</b>{m.runs.map((x) => <p key={x.run}>Run {x.run}: {x.rationale}</p>)}</div>))}
          </Explain>
          <Explain title="See how PCEF got its numbers">
            <AlignmentTrace p={P} constants={meta.constants} />
            <RealizationTrace r={P.realization} constants={meta.constants} />
          </Explain>
          <div className="defend">
            {[["Alignment", dA, setDA], ["Realization", dR, setDR]].map(([lab, v, set]) => (
              <fieldset key={lab}><legend>For {lab.toLowerCase()}, which reading is more defensible?</legend>
                {DEFENSIBLE.map(([id, txt]) => <label key={id}><input type="radio" name={lab} checked={v === id} onChange={() => set(id)} />{txt}</label>)}
              </fieldset>))}
            <textarea placeholder="Optional: what the scorers missed or got right" value={note2} onChange={(e) => setNote2(e.target.value)} />
          </div>
          {err && <p className="alert">{err}</p>}
          <button className="primary" disabled={!canSave || saving} onClick={save}>{saving ? "Saving..." : idx + 1 === total ? "Save and finish" : "Save and go to the next pair"}</button>
        </section>
      )}
    </article>
  );
}

export default function Panel({ meta }) {
  const [pack, setPack] = useState(null), [err, setErr] = useState("");
  const [expert, setExpert] = useState(""), [consent, setConsent] = useState(false), [started, setStarted] = useState(false);
  const [done, setDone] = useState([]);
  useEffect(() => { api.panelItems().then(setPack).catch((e) => setErr(e.message)); }, []);
  async function start() {
    const p = await api.panelProgress(expert.trim());
    setDone(p.done); setStarted(true);
  }
  if (err) return <div className="alert">{err}</div>;
  if (!pack) return <p className="muted">Loading the panel pack.</p>;
  const todo = pack.items.filter((i) => !done.includes(i.pair));
  if (!started) return (
    <div className="panel-start">
      <header className="page-head"><h1>Expert panel</h1>
        <p>You will see {pack.items.length} pairs of a PDPA obligation and a NIST control, with the implementation text from a sample System Security Plan. For each one, give your own rating first. Then the scores from PCEF and three LLMs are shown, and you say which reading you find more defensible.</p></header>
      <ul className="facts">
        <li>About 3 to 5 minutes per pair. You can stop and come back; finished pairs are skipped.</li>
        <li>Your ratings are saved under a code only, never your name.</li>
        <li>There are no right answers. Disagreeing with every scorer is useful data.</li>
      </ul>
      <label className="field">Participant code <input value={expert} onChange={(e) => setExpert(e.target.value)} placeholder="for example E1" /></label>
      <label className="check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />I agree that my anonymised ratings and comments are recorded for this study.</label>
      <button className="primary" disabled={!expert.trim() || !consent} onClick={start}>Start</button>
      <p className="small muted">Pack {pack.version}, fingerprint {pack.sha256}, scorer {pack.pcef_config}.</p>
    </div>
  );
  if (todo.length === 0) return (
    <div className="panel-done"><h1>All {pack.items.length} pairs are done</h1><p>Thank you. Your answers are saved in <code>outputs/panel/responses.jsonl</code> under code {expert}.</p></div>);
  const item = todo[0];
  return <Item key={item.pair} item={item} idx={pack.items.length - todo.length} total={pack.items.length}
               expert={expert.trim()} pack={pack} meta={meta} onSaved={(pid) => { setDone([...done, pid]); window.scrollTo(0, 0); }} />;
}
