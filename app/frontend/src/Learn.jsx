import React, { useState } from "react";

const TOPICS = [
  { id: "read", title: "How to read the results", body: (
    <>
      <p>Every pair of a legal duty and a security control gets two numbers between 0 and 1, and they are never added together.</p>
      <p><b>Alignment</b> asks: if this control were fully built, would it cover the duty? It compares the law's text with NIST's description of the control, and never looks at your plan.</p>
      <p><b>Realization</b> asks: does your plan show this control built? It reads only your plan's implementation text, row by row.</p>
      <p>The useful readings come from the two together. High Alignment with low Realization means the right control exists but your plan does not show it done, which is a gap to close. Low Alignment with high Realization means you built something well, but it is not what this duty asks for.</p>
    </>) },
  { id: "pdpa", title: "What is the PDPA?", body: (
    <>
      <p>Sri Lanka's Personal Data Protection Act No. 9 of 2022 sets out how organisations must handle personal data: on what basis they may process it, for what purposes, how long they keep it, how they secure it, and what they must do when a breach happens.</p>
      <p>PCEF works with a selected set of its clauses. Each clause was broken by hand into duties (who must do what, under which conditions), and each duty lists the elements it requires.</p>
    </>) },
  { id: "nist", title: "What is NIST SP 800-53?", body: (
    <>
      <p>NIST Special Publication 800-53 Revision 5 is a catalog of security and privacy controls published by the US National Institute of Standards and Technology. Controls are grouped into families, such as AC (access control), IR (incident response) and PT (PII processing and transparency).</p>
      <p>Each control is written as a statement with numbered parts, for example AC-2a, AC-2b. PCEF treats each smallest part as a row and checks your plan row by row.</p>
    </>) },
  { id: "ssp", title: "What is an SSP and OSCAL?", body: (
    <>
      <p>A System Security Plan (SSP) describes a system and explains how each security control is implemented in it.</p>
      <p>OSCAL (Open Security Controls Assessment Language) is NIST's machine-readable format for this kind of document, in JSON, XML or YAML. PCEF reads OSCAL SSPs in JSON. The parts it uses look like this:</p>
      <pre className="code">{`{
  "system-security-plan": {
    "system-characteristics": { "system-name": "FleetTrack", "props": [ ... ] },
    "control-implementation": {
      "implemented-requirements": [
        { "control-id": "ac-3",
          "statements": [
            { "statement-id": "ac-3_smt",
              "by-components": [
                { "description": "Every request is checked against the user's role ..." }
              ] } ] } ] } } }`}</pre>
      <p>The <i>description</i> text is what Realization reads. A control your SSP does not list scores 0, because the plan gives no evidence it is built.</p>
    </>) },
  { id: "legal", title: "Is this a legal opinion?", body: (
    <>
      <p>No. PCEF is decision support. It shows how well a plan's controls line up with the duties in the law, and how far the plan describes them as built. It cannot see your actual systems, only what the plan says, and it does not decide whether an organisation complies with the law. Use it to find where to look, then check with a qualified person.</p>
    </>) },
];

export default function Learn({ start = "read" }) {
  const [open, setOpen] = useState(start);
  return (
    <div className="learn">
      <header className="page-head"><h1>Learn the basics</h1><p>Short answers to what the results mean and what the documents are.</p></header>
      <div className="learn-grid">
        <nav className="learn-nav" aria-label="Topics">
          {TOPICS.map((t) => <button key={t.id} className={"nav-item light" + (open === t.id ? " on" : "")} onClick={() => setOpen(t.id)}>{t.title}</button>)}
        </nav>
        <article className="learn-body">{TOPICS.filter((t) => t.id === open).map((t) => <div key={t.id}><h2>{t.title}</h2>{t.body}</div>)}</article>
      </div>
    </div>
  );
}
