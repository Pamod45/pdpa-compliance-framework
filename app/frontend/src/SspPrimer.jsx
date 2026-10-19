import React from "react";

// A trimmed excerpt of the FleetTrack sample SSP; each marker links to a note below.
const LINES = [
  { t: "{" },
  { t: '  "system-security-plan": {' },
  { t: '    "system-characteristics": {' },
  { t: '      "system-name": "FleetTrack",' },
  { t: '      "props": [ { "name": "pdpa-role", "value": "processor,controller" } ]', m: 1 },
  { t: "    }," },
  { t: '    "control-implementation": {' },
  { t: '      "implemented-requirements": [' },
  { t: '        { "control-id": "au-2",', m: 2 },
  { t: '          "statements": [' },
  { t: '            { "statement-id": "au-2_smt",', m: 3 },
  { t: '              "by-components": [' },
  { t: '                { "description": "write_audit_log() (app/audit.py) writes an', m: 4 },
  { t: "                   audit_log row (actor, action, resource_type, resource_id," },
  { t: "                   timestamp) inside the same DB transaction as the change it" },
  { t: "                   records ... Verified: create+update+delete on one driver" },
  { t: '                   produced exactly 3 audit_log rows.",' },
  { t: '                  "remarks": "..." }', m: 5 },
  { t: "              ] } ] }" },
  { t: "      ] } } }" },
];

const NOTES = [
  { m: 1, title: "The organisation's PDPA role",
    body: "Some PDPA duties apply only to a controller or only to a processor. PCEF reads the pdpa-role property to decide which duties apply. If it is missing, every duty is kept and the run is flagged, so nothing is dropped on a guess." },
  { m: 2, title: "Which control is claimed",
    body: "Each implemented requirement names one NIST SP 800-53 control, written in lower case (au-2, ac-3, si-12). A control that is not listed here scores 0 for Realization, because the plan gives no evidence it is built." },
  { m: 3, title: "Which part of the control",
    body: "NIST controls have numbered parts (au-2_smt.a, au-2_smt.b). A plan can describe each part, or describe the whole control once. When a part has no text of its own, PCEF uses the parent's text but halves the score it earns, because general text is weaker evidence." },
  { m: 4, title: "The implementation text",
    body: "This is what Realization reads. It rewards a specific description (about 40 words or more), concrete artefacts such as file names, versions, time periods and named mechanisms (TLS, bcrypt), set parameter values, and a component that is operational. It never reads the law." },
  { m: 5, title: "Remarks",
    body: "Remarks are read with the description. A plain statement that the control is not implemented, planned or a known gap caps Realization at 0.2: writing about a gap is not evidence the control exists." },
];

const CHECKS = [
  "A JSON file with a top-level \"system-security-plan\" object.",
  "Controls listed under control-implementation → implemented-requirements, with NIST SP 800-53 Rev 5 control ids.",
  "Each control (or each of its parts) has a by-components description that says how it is built.",
  "Optional but useful: a pdpa-role property (controller, processor, or both) in system-characteristics.",
];

export default function SspPrimer({ onSample }) {
  return (
    <div className="primer">
      <p>
        A <b>System Security Plan (SSP)</b> describes a system and explains how each security control is put in place in it.
        <b> OSCAL</b> (Open Security Controls Assessment Language) is NIST's machine-readable format for these plans. PCEF reads OSCAL SSPs in JSON.
      </p>
      <p>Here is a trimmed part of the FleetTrack sample. The numbered lines are the parts PCEF uses.</p>

      <div className="primer-grid">
        <pre className="code annotated" aria-label="Annotated OSCAL SSP excerpt"><div className="ln-wrap">
          {LINES.map((l, i) => (
            <div key={i} className={"ln" + (l.m ? " hl" : "")}>
              <span className="ln-m">{l.m ? <span className="marker">{l.m}</span> : ""}</span>
              <span className="ln-t">{l.t}</span>
            </div>
          ))}
        </div></pre>
        <ol className="primer-notes">
          {NOTES.map((n) => (
            <li key={n.m}>
              <span className="marker">{n.m}</span>
              <div><h3>{n.title}</h3><p>{n.body}</p></div>
            </li>
          ))}
        </ol>
      </div>

      <h3 className="primer-h">Will my SSP work?</h3>
      <ul className="checks">{CHECKS.map((c) => <li key={c}>{c}</li>)}</ul>

      <div className="primer-actions">
        <a className="button ghost" href="/api/sample-ssp" download="fleettrack_ssp.json">Download the sample SSP</a>
        {onSample && <button className="primary" onClick={onSample}>Score the sample now</button>}
      </div>
      <p className="small">FleetTrack is a small fleet-tracking system written for this project. Its plan includes some controls that are described but not built, so the results show both strong and weak cases.</p>
    </div>
  );
}
