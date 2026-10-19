const WAKING = "The PCEF server could not be reached. If it was idle it may be waking up, which takes about a minute. Try again shortly.";

async function req(url, opts) {
  let r;
  try { r = await fetch(url, opts); } catch { throw Object.assign(new Error(WAKING), { retry: true }); }
  const body = await r.json().catch(() => ({}));
  if (r.ok) return body;
  if ([502, 503, 504].includes(r.status)) throw Object.assign(new Error(WAKING), { retry: true });
  const detail = typeof body.detail === "string" ? body.detail : "";
  throw new Error(detail || `The server could not complete the request (error ${r.status}).`);
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
