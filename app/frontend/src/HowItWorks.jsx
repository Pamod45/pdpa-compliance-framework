import React from "react";
import Walkthrough from "./Walkthrough.jsx";

export default function HowItWorks({ meta, onSample }) {
  return (
    <div className="how">
      <header className="page-head"><h1>How scoring works</h1>
        <p>PCEF scores how well a security plan meets a privacy law, in two separate parts that are never merged. Every step is a fixed rule, so the same input always gives the same output.</p></header>
      {meta ? <Walkthrough meta={meta} onSample={onSample} /> : <p className="muted">Loading the text model. The first start can take a minute.</p>}
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
