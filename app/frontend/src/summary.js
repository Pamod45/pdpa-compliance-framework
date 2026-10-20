// Reading layer over one run. The 0.5 cut is a reading guide for sorting units, not part of PCEF's method.
export const GUIDE = 0.5;
export const NON_DUTY = new Set(["trigger", "exemption", "reclassification"]);
export const STATUS = {
  built:    { label: "Covered and built", hint: "The best-fitting control covers the duty on paper and the plan shows it built." },
  paper:    { label: "Covered on paper, not built", hint: "A fitting control exists in the catalog, but the plan does not show it implemented." },
  weak:     { label: "Weak fit only", hint: "No proposed control covers this duty well on paper." },
  none:     { label: "No control proposed", hint: "The clause annotation names no NIST control for this duty." },
  excluded: { label: "Excluded by a check", hint: "Every proposed pair was dropped by an applicability or relevance check." },
  notscored:{ label: "Not scored", hint: "The annotation marks this unit as represented but not scored." },
  nonduty:  { label: "Condition or exemption", hint: "A trigger, exemption or status change, not a duty to implement." },
};
export const ORDER = ["built", "paper", "weak", "none", "excluded", "notscored"];
export const key = (p) => `${p.unit_id}|${p.control_id}`;

export function summarise(res) {
  const byUnit = {};
  for (const p of res.pairs) (byUnit[p.unit_id] ||= []).push(p);
  const units = res.units.map((u) => {
    const ps = byUnit[u.unit_id] || [];
    const scored = ps.filter((p) => p.status === "scored").sort((a, b) => b.tuple.alignment - a.tuple.alignment);
    let status;
    if (NON_DUTY.has(u.unit_type)) status = "nonduty";
    else if (!u.scored) status = "notscored";
    else if (ps.length === 0) status = "none";
    else if (scored.length === 0) status = "excluded";
    else {
      const b = scored[0];
      status = b.tuple.alignment < GUIDE ? "weak" : (b.tuple.realization ?? 0) >= GUIDE ? "built" : "paper";
    }
    return { ...u, status, pairs: scored, excluded: ps.filter((p) => p.status !== "scored"), best: scored[0] || null };
  });
  const duties = units.filter((u) => u.status !== "nonduty");
  const counts = Object.fromEntries(ORDER.map((s) => [s, duties.filter((u) => u.status === s).length]));
  // Two separate averages over duties that have a scored control, each taken at its best-fitting control.
  const judged = duties.filter((u) => u.best);
  const mean = (f) => (judged.length ? judged.reduce((a, u) => a + f(u.best.tuple), 0) / judged.length : null);
  const averages = { n: judged.length, alignment: mean((t) => t.alignment), realization: mean((t) => t.realization ?? 0) };
  const clauses = [];
  for (const u of units) {
    let c = clauses.find((x) => x.clause_id === u.clause_id);
    if (!c) clauses.push((c = { clause_id: u.clause_id, title: u.clause_title, units: [] }));
    c.units.push(u);
  }
  const gaps = res.pairs.filter((p) => p.status === "scored" && p.tuple.alignment >= GUIDE && (p.tuple.realization ?? 0) < GUIDE)
    .sort((a, b) => (b.tuple.alignment - (b.tuple.realization ?? 0)) - (a.tuple.alignment - (a.tuple.realization ?? 0)))
    .map((p) => {
      const rows = res.realization[p.control_id]?.rows || {};
      const text = Object.fromEntries(p.context.catalog_rows.map((r) => [r.id, r.text]));
      return { ...p,
        missing: Object.entries(rows).filter(([, r]) => r.status === "absent").map(([id]) => ({ id, text: text[id] || "" })),
        capped: Object.values(rows).some((r) => (r.by_components || []).some((b) => b.capped)) };
    });
  const controls = Object.entries(res.realization).map(([cid, r]) => {
    const ps = res.pairs.filter((p) => p.control_id === cid && p.status === "scored");
    const st = {};
    Object.values(r.rows).forEach((row) => (st[row.status] = (st[row.status] || 0) + 1));
    return { control_id: cid, title: ps[0]?.control_title || ps[0]?.context?.control_title || "", value: r.value, statuses: st,
             rows: r.rows, clauses: [...new Set(ps.map((p) => p.context.clause_id))], pairs: ps, ctx: ps[0]?.context };
  }).sort((a, b) => (a.value ?? 0) - (b.value ?? 0));
  return { units, duties, counts, averages, clauses, gaps, controls };
}

export function toCSV(res) {
  const cols = ["clause_id", "unit_id", "control_id", "control_title", "pair_source", "status", "excluded_by",
                "relatedness", "coverage", "directionality", "strength", "alignment", "realization"];
  const esc = (v) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const rows = res.pairs.map((p) => [p.clause_id, p.unit_id, p.control_id, p.control_title, p.pair_source, p.status, p.excluded_by || "",
    p.relatedness?.value, p.measures?.coverage, p.measures?.directionality, p.measures?.strength, p.tuple?.alignment, p.tuple?.realization]);
  return [cols, ...rows].map((r) => r.map(esc).join(",")).join("\n");
}

export function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
