async function req(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || `Request failed (${r.status})`);
  return body;
}
export const api = {
  meta: () => req("/api/meta"),
  run: (form) => req("/api/run", { method: "POST", body: form }),
  panelItems: () => req("/api/panel/items"),
  panelProgress: (expert) => req(`/api/panel/progress?expert=${encodeURIComponent(expert)}`),
  panelSave: (rec) => req("/api/panel/response", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(rec) }),
};
export const f3 = (x) => (x === null || x === undefined ? "n/a" : Number(x).toFixed(3));
export const f2 = (x) => (x === null || x === undefined ? "n/a" : Number(x).toFixed(2));
