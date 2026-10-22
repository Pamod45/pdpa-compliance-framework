import React from "react";
import { TERMS } from "./Term.jsx";

// Reference topics on how PCEF works. Parameter values come from the frozen config served by /api/meta.

const n = (x) => (typeof x === "number" ? String(+x.toFixed(4)) : String(x));

function Formula({ children }) {
  return <div className="formula" role="math">{children}</div>;
}

function WalkLink({ stage, onWalk, children }) {
  return onWalk ? <p className="walk-link"><button className="link" onClick={() => onWalk(stage)}>{children || `See it worked out: stage ${stage} of How scoring works`}</button></p> : null;
}

export function ClauseToDuties({ onWalk }) {
  return (
    <>
      <p>A legal clause is long and mixes several duties, conditions and exceptions. Before any scoring, each PDPA clause in PCEF was read by hand and broken into <b>units</b>, stored as a <b>clause profile</b>. This is done once; every plan is compared against the same profiles.</p>
      <table className="lt">
        <thead><tr><th>Part of a unit</th><th>What it records</th><th>Example (s.10)</th></tr></thead>
        <tbody>
          <tr><td>Who</td><td>The party the duty falls on: controller, processor or public authority</td><td>controller</td></tr>
          <tr><td>How strict</td><td>shall, shall not, may, deemed or conditional</td><td>shall</td></tr>
          <tr><td>Action and object</td><td>What must be done, and to what</td><td>ensure integrity and confidentiality … of personal data</td></tr>
          <tr><td>Elements</td><td>The things the duty requires, each tagged as a process, outcome, quality, condition or time limit</td><td>prevents unauthorised processing (outcome); appropriate technical measures in place (process)</td></tr>
          <tr><td>Keywords</td><td>Words from the clause that describe the duty</td><td>encryption, access controls, integrity</td></tr>
          <tr><td>Control hints</td><td>The NIST controls that could satisfy the duty, chosen by the annotator</td><td>AC-3, SC-8, SC-13, SC-28</td></tr>
          <tr><td>Conditions</td><td>When the duty applies, such as "a personal data breach has occurred"</td><td>none</td></tr>
        </tbody>
      </table>
      <p>Units also have a <b>type</b>. Obligations, preconditions and deferred duties are scored as duties. Triggers, exemptions and reclassifications are not: they say when something applies or stops applying, not what to build. An element the Act leaves to later rules (for example the time limit for breach notification) is marked as not specified in the Act.</p>
      <WalkLink stage={2} onWalk={onWalk} />
    </>
  );
}

export function PlanNormalised({ meta, onWalk }) {
  const k = meta.constants;
  return (
    <>
      <p>NIST SP 800-53 writes each control as a statement with numbered parts. PCEF splits every control into its smallest parts, called <b>rows</b> (for example AC-2 has rows ac-2_smt.a, ac-2_smt.b and so on). The plan's implementation text is then attached to the row it was written for.</p>
      <table className="lt">
        <thead><tr><th>Row status</th><th>Meaning</th><th>Effect on Realization</th></tr></thead>
        <tbody>
          <tr><td>implemented</td><td>The plan has text written for this row</td><td>Scored from that text</td></tr>
          <tr><td>inherited</td><td>No text for this row, but the plan wrote text for a parent statement</td><td>Scored from the parent's text, then multiplied by {n(k.inheritance_discount)}</td></tr>
          <tr><td>absent</td><td>The plan says nothing for this row or its parents</td><td>Counts 0</td></tr>
          <tr><td>not applicable</td><td>The plan declares the row not applicable</td><td>Left out of the average</td></tr>
        </tbody>
      </table>
      <p>General text written once for a whole control is weaker evidence than text written for each part, which is why inherited text earns less.</p>
      <WalkLink stage={2} onWalk={onWalk} />
    </>
  );
}

export function TextModel({ meta }) {
  return (
    <>
      <p>Two measures need to know whether two pieces of text mean similar things, even when they use different words. PCEF uses a sentence-embedding model, <b>{meta.embedder.split("/").pop()}</b>, pinned to revision <code>{String(meta.revision).slice(0, 12)}</code>.</p>
      <p>The model turns a piece of text into a list of 768 numbers, called an <b>embedding</b>. Texts with similar meaning get lists that point in similar directions. The closeness of two lists is their <b>cosine similarity</b>: 1 means the same direction, 0 means unrelated.</p>
      <Formula>cosine(a, b) = (a · b) / (|a| × |b|)</Formula>
      <p>A worked example with three numbers instead of 768: a = (0.6, 0.8, 0) and b = (0.8, 0.6, 0) both have length 1, so cosine = 0.6×0.8 + 0.8×0.6 + 0×0 = 0.48 + 0.48 = <b>0.96</b>, very similar.</p>
      <p>It is a fixed model, not a chat model: it produces no text and has no randomness, so the same input always gives the same numbers. Pinning the revision keeps results reproducible. A simple TF-IDF word-count model is used as a stand-in for tests only; its scores are never reported.</p>
      <p className="small">Measured limit: the model reacts to shared compliance wording, so clearly unrelated controls can still score about 0.3 to 0.5.</p>
    </>
  );
}

export function PairingGates({ meta, onWalk }) {
  return (
    <>
      <p><b>Pairing.</b> Each duty is paired only with controls that could satisfy it, so unrelated controls are never compared:</p>
      <ul>
        <li><b>Named controls</b>: the controls in the duty's control hints. A named control the plan never mentions is still paired; its Realization of 0 is the finding.</li>
        <li><b>Same-family controls</b>: any control the plan lists in the same family as a named one (for example AC-2 when AC-3 is named).</li>
      </ul>
      <p>A duty with no usable hint gets no pairs and is reported as having no control proposed.</p>
      <p><b>Gates.</b> Two checks decide whether a pair is scored at all. A pair that fails is <b>dropped and shown as excluded</b>, not given a low score, because a low score would wrongly suggest a weak control rather than an irrelevant one.</p>
      <ul>
        <li><b>Applicability</b>: the duty's party (controller or processor) must be one of the roles the plan declares in its pdpa-role property. If the plan declares no role, the pair passes with a note: PCEF never drops a pair on an assumption. Conditions such as "when a breach occurs" are noted, and the duty is assessed as readiness.</li>
        <li><b>Relatedness floor</b>: if the duty and the control's closest row have a cosine below <b>{n(meta.constants.relatedness_floor)}</b>, the pair is dropped as unrelated.</li>
      </ul>
      <WalkLink stage={3} onWalk={onWalk}>See pairing worked out: stage 3 of How scoring works</WalkLink>
      <WalkLink stage={4} onWalk={onWalk}>See the gates worked out: stage 4 of How scoring works</WalkLink>
    </>
  );
}

export function AlignmentMeasures({ meta, onWalk }) {
  const k = meta.constants;
  const w = k.alignment_weights;
  const live = Object.entries(w).filter(([, v]) => v > 0);
  const total = live.reduce((s, [, v]) => s + v, 0);
  const [lo, hi] = k.coverage_ramp;
  const kinds = ["technical", "procedural", "governance", "data_governance"];
  return (
    <>
      <p><b>Alignment</b> asks whether the control, as NIST writes it, covers the duty on paper. It reads the law and the catalog only, never the plan. It is a weighted sum of measures, each between 0 and 1.</p>
      <div className="mcards">
        <section className="mcard"><h3>Relatedness</h3>
          <p>How close in meaning the duty is to the control's closest row. The duty is represented by its action, object and keywords.</p>
          <Formula>Relatedness = max over rows of cosine(duty, row)</Formula></section>
        <section className="mcard"><h3>Coverage</h3>
          <p>How many of the duty's required elements the control addresses. Each element is matched to its closest row, and its similarity s is turned into a score:</p>
          <Formula>score(s) = 0 if s ≤ {n(lo)};  1 if s ≥ {n(hi)};  (s − {n(lo)}) / ({n(hi)} − {n(lo)}) in between<br />Coverage = average of the element scores</Formula>
          <p className="small">Example from the method-of-record run, with the real text model (s.10 × AC-3): similarity 0.4017 gives (0.4017 − 0.25) / 0.20 = 0.759. The four elements score 1.000, 0.759, 0.706 and 0.596, so Coverage = 3.061 / 4 = 0.765.</p></section>
        <section className="mcard wide"><h3>Directionality</h3>
          <p>Whether the duty and the control are the same kind. Each side is classed as technical, procedural, governance or data governance, and a published table gives the fit. If the control works at a different level than expected (system or organisation), the value is multiplied by {n(k.level_mismatch_factor)}.</p>
          <div className="tscroll"><table className="lt small-t"><thead><tr><th>duty \ control</th>{kinds.map((c) => <th key={c}>{c.replace("_", " ")}</th>)}</tr></thead>
            <tbody>{kinds.map((r) => <tr key={r}><td>{r.replace("_", " ")}</td>{kinds.map((c) => <td key={c}>{n(k.compatibility[r][c])}</td>)}</tr>)}</tbody></table></div></section>
        <section className="mcard"><h3>Strength match</h3>
          <p>Whether the control is worded as firmly as the duty. The duty demands {Object.entries(k.modality_strength).filter(([, v]) => v !== null).map(([m, v]) => `${m.replace("_", " ")} = ${n(v)}`).join(", ")}; the control's firmness is the share of its rows without softening words such as "as needed".</p>
          <Formula>Strength match = 1 − |demanded − control firmness|</Formula>
          <p className="small">Weight {n(w.strength)} in v1.1: it scored 1.000 on every applicable pair in the evaluation, so it could not tell pairs apart. It is still computed and shown.</p></section>
      </div>
      <p><b>Combining them.</b> Weights in the frozen config: {Object.entries(w).map(([m, v]) => `${m} ${n(v)}`).join(", ")}. Weights of measures that do not apply are dropped and the rest are rescaled to add up to 1:</p>
      <Formula>Alignment = Σ wᵢ · mᵢ / Σ wᵢ   ({live.map(([m, v]) => `${m} ${n(v)}/${n(total)} = ${(v / total).toFixed(4)}`).join(", ")})</Formula>
      <p className="small">Example from the method-of-record run (s.10 × AC-3): 0.4118 × 0.765 + 0.2941 × 0.539 + 0.2941 × 1.000 = 0.315 + 0.159 + 0.294 = 0.768.</p>
      <WalkLink stage={5} onWalk={onWalk} />
    </>
  );
}

export function RealizationTopic({ meta, onWalk }) {
  const k = meta.constants;
  const fw = k.feature_weights;
  const label = { specificity: "Specificity", concrete_artefacts: "Concrete artefacts", set_parameters: "Set parameters", operational_component: "Operational component", commitment: "Commitment" };
  const rule = {
    specificity: `words ÷ ${k.specificity_full_words}, full marks at ${k.specificity_full_words} words`,
    concrete_artefacts: `distinct named details ÷ ${k.artefacts_full_count}: file names, versions, time periods, code names, mechanisms such as TLS`,
    set_parameters: "1 if the plan fills in the control's own settings, else 0",
    operational_component: "1 if the component doing the work is operational, else 0",
    commitment: `1 unless the text says ${k.negation_cues.map((c) => `"${c}"`).join(", ")}`,
  };
  return (
    <>
      <p><b>Realization</b> asks whether the plan shows the control built. It reads only the plan's text, row by row, never the law.</p>
      <table className="lt"><thead><tr><th>Feature</th><th>Weight</th><th>How it is scored (0 to 1)</th></tr></thead>
        <tbody>{Object.entries(fw).map(([f, v]) => <tr key={f}><td>{label[f] || f}</td><td>{n(v)}</td><td>{rule[f]}</td></tr>)}</tbody></table>
      <Formula>text score = Σ weight × feature<br />if the text declares a gap: text score = min(text score, {n(k.declared_gap_cap)})<br />row score = best text score among the plan's components for that row (× {n(k.inheritance_discount)} if inherited)<br />Realization = average of row scores (absent rows count 0, not-applicable rows are left out)</Formula>
      <p className="small">Examples from the method-of-record run: AC-3's text scores 0.3 + 0.3 + 0 + 0.1 + 0.2 = 0.9 on its single row, so Realization = 0.900. SC-28's text would score 0.3 × 1 + 0.3 × 0.67 + 0 + 0.1 + 0 = 0.600, but it says "not implemented", so it is capped at 0.200.</p>
      <p className="small">Measured limit: Realization rewards text that looks specific, so generic filler, or real text attached to the wrong control, still scores fairly well.</p>
      <WalkLink stage={5} onWalk={onWalk} />
    </>
  );
}

export function FrozenSettings({ meta }) {
  return (
    <>
      <p>Every number on this site comes from one fixed set of settings: <b>{meta.config_status}</b>, configuration fingerprint <code>{meta.config_sha256}</code>, text model {meta.embedder.split("/").pop()} at revision <code>{String(meta.revision).slice(0, 12)}</code>.</p>
      <p><b>Why frozen.</b> The settings were fixed before the evaluation was run, so the results could not be tuned to look good. Changing any value would change the fingerprint, and results made under the old one would no longer count as this scorer's results.</p>
      <p><b>What was tried afterwards.</b> Two further design iterations targeted Realization's weakness: it rewards text that only looks specific. Iteration 2 weighted each piece of plan text by its similarity to the row it is attached to; iteration 3 used its similarity relative to the plan's other controls. Each was judged against checks written before it was scored. Neither passed all of them, so v1.1 stayed the method of record; both configurations are published alongside it.</p>
      <p><b>Reproducing a result.</b> Every run records its fingerprints, the model revision and a fingerprint of each input. The same inputs with the same settings give the same scores, which the reproducibility runs confirmed.</p>
    </>
  );
}

export function ReadingFAQ() {
  return (
    <dl className="faq">
      <dt>Why two scores and not one?</dt>
      <dd>They answer different questions. A control can fit the law perfectly but not be built (high Alignment, low Realization), or be built well but not fit the duty (the reverse). One merged number would hide which problem you have.</dd>
      <dt>Is the overview's average a compliance percentage?</dt>
      <dd>No. It is the average of the scores shown below it, over duties that have a scored control. It summarises evidence in a plan; it does not measure legal compliance.</dd>
      <dt>What does 0.5 mean?</dt>
      <dd>It is a reading guide used to sort duties into groups. It is not a pass mark, and PCEF does not treat 0.49 and 0.51 as different in kind.</dd>
      <dt>Why is a pair "excluded" instead of scored 0?</dt>
      <dd>A gate found that the duty does not apply to this organisation, or that the texts are unrelated. Scoring it 0 would suggest a weak control rather than an irrelevant one.</dd>
      <dt>Why does a control the plan never mentions get Realization 0?</dt>
      <dd>The duty points to it, and the plan gives no evidence that it is built. That silence is itself the finding.</dd>
      <dt>Can an LLM change the scores?</dt>
      <dd>No. The optional Draft an SSP feature uses an LLM to write a draft plan, which a person reviews. Scoring always uses the frozen scorer described here.</dd>
    </dl>
  );
}

const EXTRA = {
  duty: "One thing a clause requires a party to do, taken from the clause by hand.",
  element: "A part of a duty that must be met, such as an outcome or a time limit.",
  row: "The smallest numbered part of a NIST control, such as ac-2_smt.a.",
  pair: "One duty matched with one candidate control.",
  gate: "A check that drops a pair before scoring: applicability or the relatedness floor.",
  "relatedness floor": "The lowest similarity at which a pair is still considered related.",
  inheritance: "A row with no text of its own using its parent statement's text, at a discount.",
  "declared gap": "Plan text that says the control is not implemented or planned; it caps Realization.",
  embedding: "The list of numbers the text model turns a piece of text into.",
  "cosine similarity": "How closely two embeddings point the same way: 1 is the same, 0 unrelated.",
  "clause profile": "The hand-made structured version of a PDPA clause: its duties, elements and hints.",
  "config fingerprint": "A short code computed from the settings file; it changes if any setting changes.",
  OSCAL: "NIST's machine-readable format for security documents such as System Security Plans.",
  SSP: "System Security Plan: a document describing how each security control is put in place.",
};

export function Glossary() {
  const all = { ...Object.fromEntries(Object.entries(TERMS).map(([k, v]) => [k.replace("_", " "), v])), ...EXTRA };
  return (
    <dl className="glossary">
      {Object.keys(all).sort((a, b) => a.localeCompare(b)).map((k) => (
        <React.Fragment key={k}><dt>{k[0].toUpperCase() + k.slice(1)}</dt><dd>{all[k]}</dd></React.Fragment>))}
    </dl>
  );
}
