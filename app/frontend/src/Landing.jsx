import React from "react";

const STEPS = [
  { n: "1", title: "Your security plan", body: "An OSCAL System Security Plan (SSP) that says how each security control is implemented." },
  { n: "2", title: "Duties meet controls", body: "Each PDPA duty is paired with the NIST SP 800-53 controls that could satisfy it." },
  { n: "3", title: "Two scores per pair", body: "Alignment and Realization, each between 0 and 1, kept side by side and never merged." },
];

const READINGS = [
  { tone: "a", title: "Alignment", body: "Does the control, as NIST writes it, address the legal duty on paper? Your plan is not read here." },
  { tone: "r", title: "Realization", body: "Does your plan show the control actually built? Only your implementation text is read here." },
  { tone: "t", title: "Trace", body: "Every number opens to the law text, the catalog rows and the plan text it came from." },
];

export default function Landing({ meta, onSample, onUpload, onLearn }) {
  const clauses = meta ? meta.clauses.length : null;
  return (
    <div className="landing">
      <section className="hero">
        <img src="/pcef-logo.svg" alt="PCEF - PDPA Compliance Evaluation Framework" className="hero-logo" width="311" height="72" />
        <h1>See how well a security plan supports Sri Lanka's PDPA</h1>
        <p className="lede">
          PCEF reads a System Security Plan and scores each pairing of a PDPA duty with a NIST security control:
          how well the control fits the law, and how far the plan shows it built. Every score can be traced back to its sources.
        </p>
        <div className="hero-actions">
          <button className="primary big" onClick={onSample} disabled={!meta}>Try the FleetTrack sample</button>
          <button className="ghost big" onClick={onUpload} disabled={!meta}>Upload your own SSP</button>
        </div>
        <p className="small">
          {meta
            ? `${clauses} PDPA clauses ready · NIST SP 800-53 Rev 5 · scorer ${meta.config_status}`
            : "Loading the text model. The first start can take a minute."}
          {" · "}<button className="link" onClick={() => onLearn("ssp")}>What is an SSP?</button>
        </p>
      </section>

      <section className="steps" aria-label="How it works">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.n}>
            <div className="step">
              <span className="step-n">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
            {i < STEPS.length - 1 && <span className="step-arrow" aria-hidden="true">→</span>}
          </React.Fragment>
        ))}
      </section>

      <section className="readings" aria-label="What you will see">
        {READINGS.map((r) => (
          <div key={r.title} className={"reading " + r.tone}>
            <h3>{r.title}</h3>
            <p>{r.body}</p>
          </div>
        ))}
      </section>

      <p className="disclaimer">
        Evidence-based scoring of security controls against PDPA duties. It reads only what the plan says and is not legal advice.{" "}
        <button className="link" onClick={() => onLearn("legal")}>Why?</button>
      </p>
    </div>
  );
}
