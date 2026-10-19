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
  const [tries, setTries] = useState(0);
  useEffect(() => {          // keep asking while the server wakes up, for about three minutes
    let stop = false, n = 0;
    const ask = () => api.meta().then((m) => !stop && setMeta(m)).catch((e) => {
      if (stop) return;
      n += 1; setTries(n);
      if (e.retry && n < 36) setTimeout(ask, 5000); else setErr(e.message);
    });
    ask();
    return () => { stop = true; };
  }, []);
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
        {err && <div className="alert">{err}</div>}
        {!meta && !err && (tries > 0
          ? <div className="waking" role="status"><span className="spinner" aria-hidden="true" />Waking up the server and loading the text model. This takes about a minute after a quiet period.</div>
          : view !== "home" && <p className="muted">Loading the text model. The first start can take a minute.</p>)}
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
