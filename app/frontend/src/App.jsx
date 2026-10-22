import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import Explore from "./Explore.jsx";
import Panel from "./Panel.jsx";
import HowItWorks from "./HowItWorks.jsx";
import Learn from "./Learn.jsx";
import Landing from "./Landing.jsx";
import Account from "./Account.jsx";
import History from "./History.jsx";
import Compare from "./Compare.jsx";
import Privacy from "./Privacy.jsx";
import Admin from "./Admin.jsx";
import Draft from "./Draft.jsx";

const VIEWS = [
  { id: "home", label: "Home" },
  { id: "explore", label: "Explore an SSP" },
  { id: "draft", label: "Draft an SSP" },
  { id: "how", label: "How scoring works" },
  { id: "learn", label: "Learn the basics" },
  { id: "panel", label: "Expert panel" },
];

export default function App() {
  const [view, setView] = useState("home");
  const [start, setStart] = useState(null);      // how Explore was opened: "sample" | "upload" | null
  const [topic, setTopic] = useState("read");
  const [visit, setVisit] = useState(0);         // a fresh Explore each time it is opened
  const [opened, setOpened] = useState(null);    // a saved run to show in Explore
  const [comparing, setComparing] = useState(null);
  const go = (v, how = null, run = null) => { setStart(how); setOpened(run); setView(v); setVisit((n) => n + 1); window.scrollTo(0, 0); };
  const [present, setPresent] = useState(() => {
    try { return new URLSearchParams(window.location.search).has("present") || window.localStorage.getItem("pcef.present") === "1"; }
    catch { return false; }
  });
  useEffect(() => {
    document.documentElement.classList.toggle("present", present);
    try { window.localStorage.setItem("pcef.present", present ? "1" : "0"); } catch { /* storage unavailable */ }
  }, [present]);
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const refreshMe = () => api.me().then((r) => { setUser(r.email); setIsAdmin(!!r.admin); }).catch(() => {});
  useEffect(() => { refreshMe(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
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
          {[...VIEWS.slice(0, 3), ...(user ? [{ id: "history", label: "My runs" }] : []), ...VIEWS.slice(3)]
            .filter((v) => v.id !== "panel" || (meta && meta.panel_available && (!meta.panel_restricted || isAdmin)))
            .concat(isAdmin ? [{ id: "admin", label: "Admin" }] : []).map((v) => (
            <button key={v.id} data-nav={v.id} className={"nav-item" + (view === v.id ? " on" : "")} onClick={() => go(v.id)}>{v.label}</button>
          ))}
          <button className="nav-item tour-link" onClick={() => go("explore", "tour")} disabled={!meta}>Take the tour</button>
          <button data-nav="account" className={"nav-item account-link" + (view === "account" ? " on" : "")} onClick={() => go("account")}>
            {user ? <><span className="small">Signed in as</span> {user}</> : "Sign in"}</button>
          <button className="nav-item present-toggle" aria-pressed={present} onClick={() => setPresent(!present)}>
            <span className="switch" aria-hidden="true" />Presenter mode</button>
          <button data-nav="privacy" className={"nav-item privacy-link" + (view === "privacy" ? " on" : "")} onClick={() => go("privacy")}>Privacy</button>
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
                                     onLearn={(t) => { setTopic(t); go("learn"); }} onTour={() => go("explore", "tour")} />}
        {meta && view === "explore" && <Explore key={visit} meta={meta} start={start} initial={opened} user={user} onSignIn={() => go("account")} onPrivacy={() => go("privacy")} />}
        {meta && view === "panel" && <Panel meta={meta} />}
        {view === "how" && <HowItWorks meta={meta} onSample={() => go("explore", "sample")} />}
        {view === "history" && <History user={user} onOpen={(r, asReport) => go("explore", asReport ? "report" : null, r)} onSignIn={() => go("account")}
                                              onCompare={(ids) => { setComparing(ids); go("compare"); }} />}
        {view === "compare" && comparing && <Compare ids={comparing} onBack={() => go("history")} />}
        {view === "account" && <Account user={user} onUser={(u) => { setUser(u); refreshMe(); if (u) go("home"); }} onPrivacy={() => go("privacy")} />}
        {view === "admin" && isAdmin && <Admin onPanel={() => go("panel")} />}
        {view === "draft" && <Draft key={String(user)} meta={meta} onOpenResult={(r) => go("explore", null, r)} />}
        {view === "privacy" && <Privacy meta={meta} user={user} onAccount={() => go("account")} />}
        {view === "learn" && <Learn key={topic} start={topic} onSample={meta ? () => go("explore", "sample") : undefined} />}
      </main>
    </div>
  );
}
