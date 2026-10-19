import React, { useState } from "react";
import { f2, f3 } from "./api.js";
import Term from "./Term.jsx";

const MEASURE_LABEL = { coverage: "Coverage", relatedness: "Relatedness", directionality: "Directionality", strength: "Strength match" };

export function Explain({ title = "How this is calculated", children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={"explain" + (open ? " open" : "")}>
      <button className="explain-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Hide" : title}</button>
      {open && <div className="explain-body">{children}</div>}
    </div>
  );
}

export function Inputs({ ctx, compact }) {
  return (
    <section className="inputs">
      <div className="law">
        <h4>{ctx.clause_id.replace("PDPA-", "Section ")}{ctx.clause_title ? `: ${ctx.clause_title}` : ""}</h4>
        <blockquote className="law-text">{ctx.clause_text}</blockquote>
        <p className="obl"><span className="k">Obligation assessed</span> {ctx.obligation}</p>
        {ctx.attributes?.length > 0 && (
          <ul className="attrs">{ctx.attributes.map((a) => <li key={a}>{a}</li>)}</ul>
        )}
      </div>
      <div className="ctl">
        <h4>{ctx.control_id.toUpperCase()}: {ctx.control_title}</h4>
        <ol className="rows">{ctx.catalog_rows.map((r) => <li key={r.id}><span className="rid">{r.id}</span>{r.text}</li>)}</ol>
      </div>
      {!compact && (
        <div className="impl">
          <h4>What the SSP says</h4>
          {ctx.ssp_text.length === 0 ? <p className="flag-text">The SSP does not mention this control.</p> :
            ctx.ssp_text.map((s, i) => (
              <div key={i} className="ssp-stmt"><span className="rid">{s.statement}</span>{s.text}
                {s.remarks && <div className="remark">Remark: {s.remarks}</div>}</div>))}
        </div>
      )}
    </section>
  );
}

export function AlignmentTrace({ p, constants }) {
  const w = p.effective_weights || {};
  const terms = Object.keys(w).map((k) => ({ k, w: w[k], m: p.measures[k], c: w[k] * p.measures[k] }));
  const cov = p.coverage_detail || {};
  const d = p.directionality_detail || {};
  return (
    <section className="trace align">
      <header><h3><Term k="alignment">Alignment</Term> {f3(p.tuple.alignment)}</h3><p>Does the control, as NIST wrote it, cover this obligation? This never reads the SSP.</p></header>
      <table className="sum">
        <thead><tr><th>Measure</th><th>Score</th><th>Weight</th><th>Adds</th></tr></thead>
        <tbody>
          {terms.map((t) => <tr key={t.k}><td><Term k={t.k}>{MEASURE_LABEL[t.k]}</Term></td><td>{f3(t.m)}</td><td>&times; {f3(t.w)}</td><td>{f3(t.c)}</td></tr>)}
          <tr className="total"><td colSpan={3}>Alignment</td><td>{f3(terms.reduce((s, t) => s + t.c, 0))}</td></tr>
        </tbody>
      </table>
      {p.measures.strength !== null && p.measures.strength !== undefined && (
        <p className="note">Strength match was computed ({f3(p.measures.strength)}) but carries no weight in v1.1: it scored 1.000 on every pair, so it could not separate anything.</p>
      )}
      <Explain>
        <p>Each measure is a number from 0 to 1. Alignment is their weighted sum. The weights come from the frozen config (coverage {constants.alignment_weights.coverage}, relatedness {constants.alignment_weights.relatedness}, directionality {constants.alignment_weights.directionality}) and are rescaled to add up to 1 when a measure does not apply.</p>
      </Explain>

      <h4><Term k="relatedness">Relatedness</Term> {f3(p.measures.relatedness)}</h4>
      <p className="small">Cosine similarity between the obligation (with its keywords) and the closest catalog row, <b>{p.relatedness.best_row}</b>.</p>
      <Explain><p>Both texts are turned into vectors by the text model; cosine similarity measures how close their meaning is. The pair passes the relevance floor if this is at least {constants.relatedness_floor}. Measured limit: the model reacts to shared compliance wording, so unrelated controls can score 0.3 to 0.5.</p></Explain>

      <h4><Term k="coverage">Coverage</Term> {f3(p.measures.coverage)}</h4>
      {cov.attributes && (
        <table className="cov">
          <thead><tr><th>Element the obligation requires</th><th>Best match</th><th>Similarity</th><th>Counts as</th></tr></thead>
          <tbody>
            {Object.values(cov.attributes).map((a) => (
              <tr key={a.name}><td>{a.name}</td><td className="rid">{a.row}</td><td>{f3(a.best)}</td>
                <td><span className="meter"><span style={{ width: `${a.score * 100}%` }} /></span>{f2(a.score)}</td></tr>))}
          </tbody>
        </table>
      )}
      <Explain><p>Each element is matched to its most similar catalog row. Similarity at or below {constants.coverage_ramp[0]} counts 0, at or above {constants.coverage_ramp[1]} counts 1, and in between it rises in a straight line. Coverage is the average. Measured limit: elements that only point to another part of the law (for example "a Schedule I condition") score 0 against everything.</p></Explain>

      <h4><Term k="directionality">Directionality</Term> {f3(p.measures.directionality)}</h4>
      <p className="small">Obligation type <b>{d.unit_orientation}</b>, control type <b>{d.control_orientation}</b>{d.level_mismatch ? `, and the control works at ${d.impl_level} level where ${d.expected_level} is expected (x 0.8)` : ""}.</p>
      <Explain><p>A published table says how well each type of obligation fits each type of control (technical, procedural, governance, data governance). Same type gives 1.0.</p></Explain>
    </section>
  );
}

export function RealizationTrace({ r, constants }) {
  if (!r) return null;
  const rows = Object.entries(r.rows);
  const counted = rows.filter(([, v]) => v.score !== null);
  const sum = counted.reduce((s, [, v]) => s + v.score, 0);
  const fw = constants.feature_weights;
  return (
    <section className="trace real">
      <header><h3><Term k="realization">Realization</Term> {f3(r.value)}</h3><p>How fully does the SSP describe implementing this control? This never reads the law.</p></header>
      <ol className="rrows">
        {rows.map(([id, v]) => {
          const best = v.by_components?.reduce((a, b) => (b.score > (a?.score ?? -1) ? b : a), null);
          return (
            <li key={id} className={"rrow st-" + v.status}>
              <div className="rrow-head"><span className="rid">{id}</span><span className="chip">{v.status}</span><span className="rscore">{v.score === null ? "not counted" : f3(v.score)}</span></div>
              {best && (
                <div className="feat">
                  {Object.entries(fw).map(([k, wt]) => (
                    <span key={k} className="fterm"><Term k={k}>{k.replace("_", " ")}</Term> {f2(best.features[k])} &times; {wt}</span>))}
                  <span className="fterm eq">= {f3(best.uncapped ?? best.score)}</span>
                  {best.capped && <span className="fterm flag">says "{best.negation_hits.join('", "')}": capped at {constants.declared_gap_cap}</span>}
                  {v.status === "inherited" && <span className="fterm">written at parent level: &times; {constants.inheritance_discount}</span>}
                </div>
              )}
            </li>);
        })}
      </ol>
      <p className="mean">Control score = {counted.length <= 6
        ? <>({counted.map(([, v]) => f3(v.score)).join(" + ")}) / {counted.length}</>
        : <>sum of {counted.length} row scores {f3(sum)} / {counted.length}</>} = <b>{f3(r.value)}</b></p>
      <Explain>
        <p>Each catalog row gets a score. Rows the SSP never mentions count 0. Where the SSP describes a row, the text is scored on how specific it is (length up to 40 words), concrete details (files, versions, named mechanisms), set parameters, whether the component is operational, and whether it avoids saying the work is not done. Text that declares a gap is capped at {constants.declared_gap_cap}. Text written at the parent statement and inherited by a row is multiplied by {constants.inheritance_discount}. The control score is the average over rows.</p>
        <p>Measured limits: generic filler and text describing a different control still score fairly well, because the scorer reads how specific text looks, not whether it is about this control.</p>
      </Explain>
    </section>
  );
}
