import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import Explore from "./Explore.jsx";
import Panel from "./Panel.jsx";
import HowItWorks from "./HowItWorks.jsx";
import Learn from "./Learn.jsx";
import Landing from "./Landing.jsx";

const VIEWS = [
  { id: "home", label: "Home" },
  { id: "explore", label: "Explore an SSP" },
  { id: "how", label: "How scoring works" },
  { id: "learn", label: "Learn the basics" },
  { id: "panel", label: "Expert panel" },
];

export default function App() {
  const [view, setView] = useState("home");
  const [start, setStart] = useState(null);      // how Explore was opened: "sample" | "upload" | null
  const [topic, setTopic] = useState("read");
  const go = (v, how = null) => { setStart(how); setView(v); window.scrollTo(0, 0); };
  const [meta, setMeta] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.meta().then(setMeta).catch((e) => setErr(e.message)); }, []);
  return (
    <div className="shell">
      <aside className="side no-print">
        <div className="brand">
          <img className="brand-mark" src="/pcef-mark.svg" alt="" width="40" height="40" />
          <div>
            <div className="brand-name">PCEF</div>
            <div className="brand-sub">PDPA Compliance Evaluation Framework</div>
          </div>
        </div>
        <nav aria-label="Sections">
          {VIEWS.map((v) => (
            <button key={v.id} className={"nav-item" + (view === v.id ? " on" : "")} onClick={() => go(v.id)}>{v.label}</button>
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
        {!meta && !err && view !== "home" && <p className="muted">Loading the text model. The first start can take a minute.</p>}
        {view === "home" && <Landing meta={meta} onSample={() => go("explore", "sample")} onUpload={() => go("explore", "upload")}
                                     onLearn={(t) => { setTopic(t); go("learn"); }} />}
        {meta && view === "explore" && <Explore meta={meta} start={start} />}
        {meta && view === "panel" && <Panel meta={meta} />}
        {view === "how" && <HowItWorks />}
        {view === "learn" && <Learn key={topic} start={topic} onSample={meta ? () => go("explore", "sample") : undefined} />}
      </main>
    </div>
  );
}
