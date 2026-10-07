import React from "react";

const STAGES = [
  ["Read the law", "Each PDPA clause is broken into obligation units: who must do what, under which conditions, and the elements the duty requires. This is done once, by hand, and stored as a clause profile."],
  ["Read the catalog and the plan", "The NIST SP 800-53 Rev 5 catalog is split into its smallest statements (rows). The System Security Plan's implementation text is attached to those rows; text written at a parent statement is passed down to its rows and marked as inherited."],
  ["Propose pairs", "Each obligation unit is paired with the controls its profile points to, plus every control the plan lists in the same family."],
  ["Check the pair is valid", "A pair is dropped, not scored low, if the obligation does not apply to this kind of organisation or if the texts are clearly unrelated."],
  ["Score Alignment", "Relatedness, Coverage and Directionality, all read from the law and the catalog only. Alignment answers: would this control cover the duty if it were built?"],
  ["Score Realization", "Read from the plan's text only: how specific, concrete and complete the implementation description is, row by row."],
  ["Report both numbers", "Every pair keeps two numbers. A high Alignment with a low Realization means the right control exists on paper but the plan does not show it built."],
];

export default function HowItWorks() {
  return (
    <div className="how">
      <header className="page-head"><h1>How scoring works</h1>
        <p>PCEF scores how well a security plan meets a privacy law, in two separate parts that are never merged. Every step is a fixed rule, so the same input always gives the same output.</p></header>
      <ol className="stages">{STAGES.map(([t, d]) => <li key={t}><h3>{t}</h3><p>{d}</p></li>)}</ol>
      <section className="limits">
        <h2>What the evaluation found it cannot do</h2>
        <ul>
          <li>The text model reacts to shared compliance wording, so clearly unrelated controls can still score 0.3 to 0.5 on Relatedness.</li>
          <li>Realization rewards text that looks specific. Generic filler, or real text attached to the wrong control, still scores fairly well. Three fixes were tested; none passed all checks, so the frozen v1.1 scorer is used.</li>
          <li>Coverage scores 0 on elements that only point to another part of the law, such as "a Schedule I condition".</li>
        </ul>
      </section>
    </div>
  );
}
