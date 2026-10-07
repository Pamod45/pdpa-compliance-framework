import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import Explore from "./Explore.jsx";
import Panel from "./Panel.jsx";
import HowItWorks from "./HowItWorks.jsx";
import Learn from "./Learn.jsx";

const VIEWS = [
  { id: "explore", label: "Explore an SSP" },
  { id: "how", label: "How scoring works" },
  { id: "learn", label: "Learn the basics" },
  { id: "panel", label: "Expert panel" },
];

export default function App() {
  const [view, setView] = useState("explore");
  const [meta, setMeta] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.meta().then(setMeta).catch((e) => setErr(e.message)); }, []);
  return (
    <div className="shell">
      <aside className="side no-print">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true"><span /><span /></div>
          <div>
            <div className="brand-name">PCEF</div>
            <div className="brand-sub">PDPA clauses traced to NIST controls and SSP evidence</div>
          </div>
        </div>
        <nav aria-label="Sections">
          {VIEWS.map((v) => (
            <button key={v.id} className={"nav-item" + (view === v.id ? " on" : "")} onClick={() => setView(v.id)}>{v.label}</button>
          ))}
        </nav>
        {meta && (
          <dl className="prov">
            <dt>Scorer</dt><dd>{meta.config_status}</dd>
            <dt>Text model</dt><dd>{meta.embedder.split("/").pop()}</dd>
            <dt>Law</dt><dd>Sri Lanka PDPA No. 9 of 2022</dd>
            <dt>Catalog</dt><dd>NIST SP 800-53 Rev 5</dd>
          </dl>
        )}
      </aside>
      <main className="main">
        {err && <div className="alert">The server did not answer: {err}. Start it with <code>python -m app.server</code>.</div>}
        {!meta && !err && <p className="muted">Loading the text model. The first start can take a minute.</p>}
        {meta && view === "explore" && <Explore meta={meta} />}
        {meta && view === "panel" && <Panel meta={meta} />}
        {view === "how" && <HowItWorks />}
        {view === "learn" && <Learn />}
      </main>
    </div>
  );
}
