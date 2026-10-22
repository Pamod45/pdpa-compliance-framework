import React, { useEffect, useState } from "react";
import { api, f2, f3 } from "./api.js";
import { GUIDE, STATUS } from "./summary.js";
import Term from "./Term.jsx";

const STAGES = ["Validate inputs", "Parse and normalise", "Propose pairs", "Apply the gates", "Compute the measures", "Combine into two scores", "Report"];
const SOURCE = {
  explicit_hint: "named for this duty in the clause profile",
  family_hint: "listed in the plan, in the same family as a named control",
};
const MEASURE = { coverage: "Coverage", relatedness: "Relatedness", directionality: "Directionality", strength: "Strength match" };

const short = (s, n = 220) => (s && s.length > n ? s.slice(0, n).trimEnd() + " ..." : s || "");
const statusOf = (t) => (t.alignment < GUIDE ? "weak" : (t.realization ?? 0) >= GUIDE ? "built" : "paper");

function Flow({ from, to, fromTitle, toTitle }) {
  return (
    <div className="wt-flow">
      <div className="wt-box"><h4>{fromTitle}</h4>{from}</div>
      <div className="wt-arrow" aria-hidden="true">→</div>
      <div className="wt-box out"><h4>{toTitle}</h4>{to}</div>
    </div>
  );
}

function Inputs({ w, c }) {
  const p = w.provenance;
  const fp = (k) => p.inputs_sha256[k].slice(0, 12);
  return (
    <>
      <p className="wt-lede">Nothing is scored yet. PCEF checks that the three inputs can be read and records a fingerprint of each, so the run can be repeated exactly.</p>
      <div className="wt-cards">
        <div className="wt-card law"><h4>The law</h4><p>PDPA clause profiles: {w.clauses_loaded} clauses, annotated by hand.</p>
          <p className="small">This case: <b>{c.clause.id.replace("PDPA-s", "s.")}</b> {c.clause.title}</p><code>{fp("profiles")}</code></div>
        <div className="wt-card cat"><h4>The catalog</h4><p>NIST SP 800-53 Rev 5 security and privacy controls.</p>
          <p className="small">This case: <b>{c.pair.control_id.toUpperCase()}</b> {c.pair.control_title}</p><code>{fp("catalog")}</code></div>
        <div className="wt-card ssp"><h4>The plan</h4><p>{w.ssp.name} OSCAL SSP: {w.ssp.controls} controls described, {w.ssp.components} components.</p>
          <p className="small">Declares <code>pdpa-role = {w.ssp.role}</code></p><code>{fp("ssp")}</code></div>
      </div>
      <ul className="wt-checks">
        <li>The plan is OSCAL JSON with a <code>system-security-plan</code>.</li>
        <li>Every control the plan names exists in the catalog.</li>
        <li>The plan's PDPA role is read: {w.ssp.roles.join(" and ")}.</li>
        <li>Scorer {p.config_status}, text model {p.embedder.model_id.split("/").pop()}.</li>
      </ul>
    </>
  );
}

function Parse({ c }) {
  const u = c.unit;
  const rows = c.pair.context.catalog_rows;
  const r = c.realization.rows;
  const entry = JSON.stringify(c.ssp_entry, (k, v) => (k === "uuid" || k === "component-uuid" ? undefined : typeof v === "string" ? short(v, 140) : v), 2);
  return (
    <>
      <p className="wt-lede">Both sides are turned into the same shape before anything is compared: the law into duties, the plan into catalog rows with the plan's text attached.</p>
      <Flow fromTitle={`Law text, ${c.clause.id.replace("PDPA-s", "section ")}`} toTitle={`Duty ${u.unit_id}`}
        from={<p className="wt-law">{short(c.clause.text, 520)}</p>}
        to={<dl className="wt-duty">
          <dt>Who</dt><dd>{u.actor}</dd>
          <dt>Must ({u.modality})</dt><dd>{u.action}</dd>
          <dt>About</dt><dd>{u.object}</dd>
          <dt>Elements</dt><dd><ul>{u.attributes.map((a) => <li key={a.attr_id}>{a.name}
            <span className="chip">{a.kind}</span>{!a.specified_in_act && <span className="chip warn">left to later rules</span>}</li>)}</ul></dd>
          <dt>Keywords</dt><dd className="wt-kw">{u.keywords.map((k) => <span key={k}>{k}</span>)}</dd>
        </dl>} />
      <p className="small">The duty is written once, by hand, when the clause profile is made. Every plan is compared against the same duty.</p>
      <Flow fromTitle={`Plan entry for ${c.pair.control_id.toUpperCase()}`} toTitle="Catalog rows with the plan's text"
        from={<pre className="code wt-json">{entry}</pre>}
        to={<table className="wt-rows"><thead><tr><th>Row</th><th>NIST text</th><th>Plan text</th></tr></thead>
          <tbody>{rows.map((row) => {
            const st = r[row.id]?.status || "absent";
            return <tr key={row.id}><td className="rid">{row.id}</td><td>{short(row.text, 120)}</td>
              <td><span className={"chip st-" + st}>{st === "implemented" ? "own text" : st === "inherited" ? "parent's text" : "no text"}</span>
                {st === "inherited" && <span className="small"> from {r[row.id].source}</span>}</td></tr>;
          })}</tbody></table>} />
      <p className="small">NIST splits a control into numbered rows. The plan's description is attached to the row it was written for; a row with no text of its own takes its parent's text. At this stage nothing is judged: a row can have text that says the control is not built, and that is dealt with when Realization is scored.</p>
    </>
  );
}

function Pairs({ c }) {
  return (
    <>
      <p className="wt-lede">Each duty is paired with the controls that could satisfy it. Only these pairs are scored, so a control that has nothing to do with the duty is never compared with it.</p>
      <div className="wt-pairs">
        <div className="wt-box"><h4>Duty {c.unit.unit_id}</h4><p>{c.unit.action}</p>
          <p className="small">Clause profile points to: {c.unit.control_hints.map((h) => h.candidate_controls.map((x) => x.toUpperCase()).join(", ")).join("; ")}</p></div>
        <div className="wt-arrow" aria-hidden="true">→</div>
        <ul className="wt-cands">{c.candidates.map((p) => (
          <li key={p.control_id} className={p.control_id === c.pair.control_id ? "on" : ""}>
            <b>{p.control_id.toUpperCase()}</b> {p.title}
            <span className="small">{SOURCE[p.source] || p.source}</span>
            {p.control_id === c.pair.control_id && <span className="chip">followed here</span>}
          </li>))}</ul>
      </div>
    </>
  );
}

function Gates({ c, w, meta }) {
  const g = c.pair.gates;
  const rel = c.pair.relatedness.value, floor = meta.constants.relatedness_floor;
  return (
    <>
      <p className="wt-lede">Two checks decide whether the pair is scored at all. A pair that fails a check is dropped and shown as excluded, not given a low score.</p>
      <div className="wt-gates">
        <div className={"wt-gate " + (g.applicability.passed ? "pass" : "fail")}>
          <h4>1. Does the duty apply to this organisation?</h4>
          <p>The duty is for a <b>{c.unit.actor}</b>. The plan declares <b>{w.ssp.roles.join(" and ")}</b>.</p>
          <p className="verdict">{g.applicability.passed ? "Applies: scored" : "Does not apply: dropped"}</p>
          {g.applicability.flags.map((f) => <p key={f} className="note">Noted: {f}</p>)}
          <p className="small wt-if">If the plan declared only <b>processor</b>, {c.role_check_other.passed ? "the duty would still apply" : `this pair would be dropped, because the duty is for a ${c.unit.actor}`}.</p>
        </div>
        <div className={"wt-gate " + (g.relatedness_floor.passed ? "pass" : "fail")}>
          <h4>2. Are the texts related at all?</h4>
          <p>Relatedness {f3(rel)} against a floor of {floor}.</p>
          <div className="wt-bar"><span style={{ width: `${rel * 100}%` }} /><i style={{ left: `${floor * 100}%` }} title={`floor ${floor}`} /></div>
          <p className="verdict">{g.relatedness_floor.passed ? "Above the floor: scored" : "Below the floor: dropped"}</p>
          <p className="small">A loose safety net for pairs suggested only by control family.</p>
        </div>
      </div>
    </>
  );
}

function Measures({ c, meta }) {
  const p = c.pair, k = meta.constants;
  const [lo, hi] = p.coverage_detail.ramp;
  const atts = Object.values(p.coverage_detail.attributes);
  const d = p.directionality_detail;
  const fw = k.feature_weights;
  return (
    <>
      <p className="wt-lede"><Term k="alignment">Alignment</Term> measures read only the law and the NIST text. <Term k="realization">Realization</Term> reads only the plan's text. Neither side sees the other.</p>
      <div className="wt-measures">
        <section className="wt-m a">
          <h4><Term k="relatedness">Relatedness</Term> = {f3(p.measures.relatedness)}</h4>
          <p className="small">The text model compares the duty (with its keywords) with each NIST row; the closest row counts.</p>
          <ul className="wt-mini">{Object.entries(p.relatedness.per_row).map(([id, v]) => <li key={id}><span className="rid">{id}</span>{f3(v)}{id === p.relatedness.best_row && " ← closest"}</li>)}</ul>
        </section>
        <section className="wt-m a">
          <h4><Term k="coverage">Coverage</Term> = {f3(p.measures.coverage)}</h4>
          <p className="small">Each required element is matched to its closest NIST row. At or below {lo} counts 0, at or above {hi} counts 1, in between it rises in a straight line.</p>
          <table className="wt-calc"><tbody>{atts.map((a) => (
            <tr key={a.name}><td>{short(a.name, 60)}</td><td>{f3(a.best)}</td>
              <td className="arith">{a.best <= lo ? `≤ ${lo} → 0` : a.best >= hi ? `≥ ${hi} → 1` : `(${f3(a.best)} − ${lo}) / (${hi} − ${lo}) = ${f3(a.score)}`}</td></tr>))}
            <tr className="total"><td colSpan={2}>Average of {atts.length}</td><td className="arith">({atts.map((a) => f3(a.score)).join(" + ")}) / {atts.length} = {f3(p.measures.coverage)}</td></tr>
          </tbody></table>
        </section>
        <section className="wt-m a">
          <h4><Term k="directionality">Directionality</Term> = {f3(p.measures.directionality)}</h4>
          <p className="small">The duty is <b>{d.unit_orientation}</b>, the control is <b>{d.control_orientation}</b>. The published table gives {f3(d.cell)} for this combination{d.level_mismatch ? `, then × 0.8 because the control works at ${d.impl_level} level` : ""}.</p>
          <p className="small"><Term k="strength">Strength match</Term> is computed ({f3(p.measures.strength)}) but carries no weight in v1.1.</p>
        </section>
        <section className="wt-m r">
          <h4><Term k="realization">Realization</Term> features, row by row</h4>
          <table className="wt-calc"><thead><tr><th>Row</th><th>Features × weights</th><th>Row score</th></tr></thead><tbody>
            {Object.entries(c.realization.rows).map(([id, row]) => {
              const b = (row.by_components || []).reduce((x, y) => (y.score > (x?.score ?? -1) ? y : x), null);
              if (!b) return <tr key={id}><td className="rid">{id}</td><td>no plan text for this row</td><td>{row.score === null ? "not counted" : f3(row.score)}</td></tr>;
              const sum = Object.keys(fw).map((f) => `${f2(b.features[f])}×${fw[f]}`).join(" + ");
              return (
                <tr key={id}><td className="rid">{id}</td>
                  <td className="arith">{sum} = {f3(b.uncapped)}
                    {b.capped && <><br />says "{b.negation_hits.join('", "')}" → capped at {k.declared_gap_cap}</>}
                    {row.status === "inherited" && <><br />inherited from {row.source} → × {k.inheritance_discount}</>}</td>
                  <td>{f3(row.score)}</td></tr>);
            })}
          </tbody></table>
          <p className="small">Features: <Term k="specificity">specificity</Term>, <Term k="concrete_artefacts">concrete artefacts</Term>, <Term k="set_parameters">set parameters</Term>, <Term k="operational_component">operational component</Term>, <Term k="commitment">commitment</Term>.</p>
        </section>
      </div>
    </>
  );
}

function MiniMap({ cases, on }) {
  const S = 220, pad = 26, x = (v) => pad + v * (S - pad * 1.5), y = (v) => S - pad - v * (S - pad * 1.5);
  return (
    <svg className="wt-map" viewBox={`0 0 ${S} ${S}`} role="img" aria-label="The two pairs placed by Alignment (across) and Realization (up)">
      <rect x={x(0)} y={y(1)} width={x(1) - x(0)} height={y(0) - y(1)} className="field" />
      <line x1={x(0.5)} x2={x(0.5)} y1={y(0)} y2={y(1)} className="guide" /><line x1={x(0)} x2={x(1)} y1={y(0.5)} y2={y(0.5)} className="guide" />
      <text x={(x(0) + x(1)) / 2} y={S - 4} className="axis" textAnchor="middle">Alignment</text>
      <text transform={`translate(10 ${(y(0) + y(1)) / 2}) rotate(-90)`} className="axis" textAnchor="middle">Realization</text>
      {cases.map((c, i) => <g key={i} className={"pt" + (i === on ? " on" : "")}>
        <circle cx={x(c.pair.tuple.alignment)} cy={y(c.pair.tuple.realization ?? 0)} r={i === on ? 7 : 5} />
        <text x={x(c.pair.tuple.alignment) + 9} y={y(c.pair.tuple.realization ?? 0) + 4} className="tick">{c.pair.control_id.toUpperCase()}</text></g>)}
    </svg>
  );
}

function Combine({ c, w, ci }) {
  const p = c.pair, ew = p.effective_weights;
  const terms = Object.keys(ew).map((k) => ({ k, w: ew[k], m: p.measures[k] }));
  const counted = Object.values(c.realization.rows).filter((r) => r.score !== null);
  return (
    <>
      <p className="wt-lede">The measures become two numbers. They are kept side by side and never merged, because they answer different questions.</p>
      <div className="wt-combine">
        <div className="wt-box a"><h4><Term k="alignment">Alignment</Term> = {f3(p.tuple.alignment)}</h4>
          <p className="arith">{terms.map((t) => `${f3(t.w)} × ${f3(t.m)}`).join(" + ")} = {f3(p.tuple.alignment)}</p>
          <p className="small">Weighted sum of {terms.map((t) => MEASURE[t.k]).join(", ")}. The weights are frozen in the config and rescaled to add up to 1 because Strength match carries no weight.</p></div>
        <div className="wt-box r"><h4><Term k="realization">Realization</Term> = {f3(c.realization.value)}</h4>
          <p className="arith">({counted.map((r) => f3(r.score)).join(" + ")}) / {counted.length} = {f3(c.realization.value)}</p>
          <p className="small">The average of the row scores. Rows the plan never mentions count 0.</p></div>
        <MiniMap cases={w.cases} on={ci} />
      </div>
    </>
  );
}

function Report({ c, onSample }) {
  const s = statusOf(c.pair.tuple);
  return (
    <>
      <p className="wt-lede">In the results, each duty is shown with its best-fitting control and sorted with 0.5 as a reading guide on both scores. It is a guide for reading, not a pass mark.</p>
      <div className={"wt-verdict s-" + s}>
        <b>{STATUS[s].label}</b>
        <span>Alignment {f2(c.pair.tuple.alignment)} · Realization {f2(c.pair.tuple.realization)}</span>
        <p>{STATUS[s].hint}{s === "paper" && " Here the plan itself says the control is not implemented, which is exactly what the low Realization reflects."}</p>
      </div>
      <p>Every number on these screens is available for every pair in the results: open a pair and its trace shows the same inputs, measures and arithmetic.</p>
      {onSample && <button className="primary" onClick={onSample}>See all results for the sample</button>}
    </>
  );
}

export default function Walkthrough({ meta, onSample, startStage = 1 }) {
  const [w, setW] = useState(null);
  const [err, setErr] = useState("");
  const [ci, setCi] = useState(0);
  const [st, setSt] = useState(Math.min(Math.max(startStage - 1, 0), 6));
  useEffect(() => { api.walkthrough().then(setW).catch((e) => setErr(e.message)); }, []);
  if (err) return <p className="alert">{err}</p>;
  if (!w) return <p className="muted"><span className="spinner" aria-hidden="true" />Running the sample for the walkthrough...</p>;
  const c = w.cases[ci];
  const body = [<Inputs w={w} c={c} />, <Parse c={c} />, <Pairs c={c} />, <Gates c={c} w={w} meta={meta} />,
                <Measures c={c} meta={meta} />, <Combine c={c} w={w} ci={ci} />, <Report c={c} onSample={onSample} />][st];
  return (
    <section className="walk" aria-label="Walkthrough of the seven stages">
      <div className="wt-head">
        <h2>Follow one duty and two controls through the seven stages</h2>
        <div className="wt-cases" role="tablist">{w.cases.map((k, i) => (
          <button key={i} role="tab" aria-selected={ci === i} className={"wt-case" + (ci === i ? " on" : "")} onClick={() => setCi(i)}>
            <b>{k.clause.id.replace("PDPA-s", "s.")} × {k.pair.control_id.toUpperCase()}</b>
            <span>{k.pair.control_title}</span></button>))}</div>
      </div>
      <ol className="wt-steps">{STAGES.map((t, i) => (
        <li key={t}><button className={(i === st ? "on" : "") + (i < st ? " done" : "")} onClick={() => setSt(i)} aria-current={i === st ? "step" : undefined}>
          <span>{i + 1}</span>{t}</button></li>))}</ol>
      <div className="wt-body"><h3>{st + 1}. {STAGES[st]}</h3>{body}</div>
      <div className="wt-nav">
        <button className="ghost" disabled={st === 0} onClick={() => setSt(st - 1)}>Back</button>
        <span className="small">Stage {st + 1} of {STAGES.length}</span>
        <button className="primary" disabled={st === STAGES.length - 1} onClick={() => setSt(st + 1)}>Next stage</button>
      </div>
    </section>
  );
}
