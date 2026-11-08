// Osprey coordinator display. Holds its own snapshot and ages it locally; the only input is the
// gateway WebSocket (FR-10). History never overwrites newer current state (FR-07).
"use strict";

const LINK_TIMEOUT_MS = 1500;
const VIDEO_STALE_S = 1.5;
const NODES = ["ship", "A", "B"];
const NODE_COLORS = { ship: "#0b3d91", A: "#1d64d8", B: "#7a5af8" };

let ws = null, lastMsg = 0, linkUp = false, connectStarted = 0;
let snap = null;            // latest state from the ground processor
let offset = 0;             // server_ts - local time (s), from the latest state
let selectedCandidate = null;
const pending = new Map();  // command_id -> {cmd, el}
const timeline = new Map(); // event_id -> event
const feeds = {};           // node -> {live, liveTs, liveHeader, grab, grabTs}
let endArmedUntil = 0;
let historyAt = null;

const $ = (s) => document.querySelector(s);
const nowS = () => Date.now() / 1000 + offset;
const fmtTime = (ts) => new Date(ts * 1000).toLocaleTimeString([], { hour12: false });
const fmtAge = (s) => (s < 60 ? s.toFixed(1) + " s" : Math.floor(s / 60) + " min " + Math.floor(s % 60) + " s");

// ------------------------------------------------------------------ connection
function connect() {
  connectStarted = performance.now();
  try { ws && ws.close(); } catch (e) {}
  ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
  ws.binaryType = "arraybuffer";
  ws.onmessage = onMessage;
  ws.onclose = () => { ws = null; };
}

function watchdog() {
  const t = performance.now();
  const up = lastMsg && t - lastMsg < LINK_TIMEOUT_MS;
  if (up !== linkUp) {
    linkUp = up;
    document.body.classList.toggle("linklost", !up && !!snap);
  }
  if (!up) {
    // a connection that delivers nothing is treated as dead; start a fresh one (snapshot first)
    if (!ws || ws.readyState !== WebSocket.OPEN || t - connectStarted > LINK_TIMEOUT_MS) {
      if (t - connectStarted > 1000) connect();
    }
  }
}

function onMessage(ev) {
  lastMsg = performance.now();
  if (typeof ev.data !== "string") return onFrame(ev.data);
  const m = JSON.parse(ev.data);
  if (m.type === "state") {
    offset = m.server_ts - Date.now() / 1000;
    snap = m;
  } else if (m.type === "hb") {
    offset = m.server_ts - Date.now() / 1000;
  } else if (m.type === "events") {
    for (const e of m.events) addTimeline(e, false);
  } else if (m.type === "history") {
    // backlog: timeline only, never current state
    for (const e of m.events) addTimeline(e, true);
    historyAt = Date.now();
    if (!m.events.length) return;
    addTimeline({ event_id: "hist:" + historyAt, type: "history", capture_ts: nowS(), n: m.events.length }, false);
  } else if (m.type === "ack") {
    const p = pending.get(m.command_id);
    pending.delete(m.command_id);
    if (p && p.el) p.el.classList.remove("pending");
    toast((m.ok ? "✓ " : "✗ ") + m.message);
  }
}

async function onFrame(buf) {
  const dv = new DataView(buf);
  const n = dv.getUint32(0, true);
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, n)));
  const blob = new Blob([new Uint8Array(buf, 4 + n)], { type: "image/jpeg" });
  let bmp;
  try { bmp = await createImageBitmap(blob); } catch (e) { return; }
  const f = feeds[header.node_id] || (feeds[header.node_id] = {});
  if (f.liveHeader && header.capture_ts < f.liveHeader.capture_ts) return; // never rewind
  f.live = bmp; f.liveHeader = header; f.liveAt = performance.now();
  if (header.node_id === "ship" || header.boxes.some((b) => b.state === "tracking" || b.state === "candidate")) {
    f.grab = bmp; f.grabHeader = header;
  }
}

// ------------------------------------------------------------------ commands
function send(cmd, args, el) {
  const command_id = cmd + "-" + Math.random().toString(36).slice(2, 10);
  if (!ws || ws.readyState !== WebSocket.OPEN || !linkUp) { toast("✗ link down — command not sent"); return; }
  pending.set(command_id, { cmd, el });
  if (el) el.classList.add("pending");
  ws.send(JSON.stringify({ type: "command", command_id, cmd, args: args || {} }));
  toast("… " + cmd.replace("_", " "));
  setTimeout(() => { if (pending.has(command_id)) { pending.delete(command_id); el && el.classList.remove("pending"); toast("✗ no ack for " + cmd); } }, 4000);
}
let toastTimer = null;
function toast(t) { $("#toast").textContent = t; clearTimeout(toastTimer); toastTimer = setTimeout(() => ($("#toast").textContent = ""), 5000); }

const tileCandidate = (node) => {
  const cs = (snap && snap.nodes[node] ? snap.nodes[node].candidates : []);
  return cs.find((c) => c.candidate_id === selectedCandidate) || [...cs].sort((a, b) => b.confidence - a.confidence)[0];
};
document.querySelectorAll(".tile").forEach((tile) => {
  const node = tile.dataset.node;
  const c = tile.querySelector(".btn-confirm"), r = tile.querySelector(".btn-reject");
  if (c) c.onclick = (e) => { const k = tileCandidate(node); if (k) send("confirm", { candidate_id: k.candidate_id }, e.target); };
  if (r) r.onclick = (e) => { const k = tileCandidate(node); if (k) send("reject", { candidate_id: k.candidate_id }, e.target); };
});
$("#btn-follow").onclick = (e) => send(snap && snap.follow_enabled ? "stop_follow" : "resume_follow", {}, e.target);
$("#btn-end").onclick = (e) => {
  if (Date.now() < endArmedUntil) { endArmedUntil = 0; send("end_incident", {}, e.target); }
  else { endArmedUntil = Date.now() + 3000; toast("Click End incident again to confirm"); }
};
document.querySelectorAll("#drawer button[data-cmd]").forEach((b) =>
  (b.onclick = () => send(b.dataset.cmd, b.dataset.args ? JSON.parse(b.dataset.args) : {}, b)));
document.addEventListener("keydown", (e) => { if (e.key === "d" || e.key === "D") $("#drawer").classList.toggle("hidden"); });

function allCandidates() {
  if (!snap) return [];
  return NODES.flatMap((n) => (snap.nodes[n] ? snap.nodes[n].candidates : []));
}
function currentCandidate() {
  const cs = allCandidates();
  return cs.find((c) => c.candidate_id === selectedCandidate) || cs.sort((a, b) => b.confidence - a.confidence)[0];
}

// tile click: select a candidate box
document.querySelectorAll(".tile canvas").forEach((cv) => {
  cv.onclick = (e) => {
    const node = cv.closest(".tile").dataset.node, f = feeds[node];
    if (!f || !f.liveHeader) return;
    const r = cv.getBoundingClientRect();
    const fit = fitRect(cv, f.live);
    const x = ((e.clientX - r.left) * (cv.width / r.width) - fit.x) / fit.w;
    const y = ((e.clientY - r.top) * (cv.height / r.height) - fit.y) / fit.h;
    const hit = f.liveHeader.boxes.find((b) => b.candidate_id && x >= b.bbox[0] && x <= b.bbox[2] && y >= b.bbox[1] && y <= b.bbox[3]);
    if (hit) { selectedCandidate = hit.candidate_id; toast("Selected candidate on " + node); }
  };
});

// ------------------------------------------------------------------ timeline
const TL_TYPES = { dispatch: "rover launched", handoff: "fix → rover", mob: "MOB", confirm: "confirmed", associated: "associated",
  reacquired: "reacquired", lost: "visual lost", input_lost: "video lost", input_restored: "video back", end: "ended",
  stop_follow: "follow stopped", resume_follow: "follow resumed", reject: "rejected", session_restart: "source restart", history: "history" };
const TL_COLORS = { mob: "#d92d20", observation: "#f97066", confirm: "#12804a", associated: "#12804a", reacquired: "#12804a",
  dispatch: "#1d64d8", handoff: "#1d64d8", lost: "#b54708", input_lost: "#b54708", end: "#0b3d91" };
function addTimeline(e, isHistory) {
  if (!TL_TYPES[e.type] && !(e.type === "observation" && e.kind === "candidate")) return;
  if (timeline.has(e.event_id)) return;
  timeline.set(e.event_id, { ...e, history: isHistory });
  renderTimeline();
}
function renderTimeline() {
  const evs = [...timeline.values()].sort((a, b) => a.capture_ts - b.capture_ts).slice(-8);
  const n = evs.length, span = 90;
  const pos = (i) => (n <= 1 ? 4 : 4 + (i * (span - 4)) / (n - 1));
  const items = evs.map((e, i) => {
    const label = e.type === "observation" ? `candidate ${e.node_id}` :
      e.type === "history" ? `history +${e.n}` : `${TL_TYPES[e.type]}${e.node_id && !["mob", "dispatch", "handoff"].includes(e.type) ? " " + e.node_id : ""}`;
    const c = TL_COLORS[e.type] || "#98a2b3";
    const quiet = !TL_COLORS[e.type] ? " quiet" : "";
    return `<div class="ev ${i % 2 ? "dn" : "up"}${e.history ? " history" : ""}${quiet}" style="left:${pos(i)}%;--c:${c}" title="${fmtTime(e.capture_ts)} ${label}${e.reason ? " — " + e.reason : ""}"><i></i><b>${label} <small>${fmtTime(e.capture_ts)}</small></b></div>`;
  }).join("");
  const now = n ? `<div class="ev now ${n % 2 ? "dn" : "up"}" style="left:97%"><i></i><b>now</b></div>` : `<div class="ev now dn quiet" style="left:50%"><i></i><b>no events yet</b></div>`;
  $("#timeline").innerHTML = `<div class="axis"></div>${n ? '<div class="fill" style="width:97%"></div>' : ""}${items}${now}`;
}
renderTimeline();

// ------------------------------------------------------------------ chart
const map = L.map("chart", { zoomControl: true, attributionControl: true }).setView([42.35, -70.8], 17);
// Esri Light Gray canvas: keyless, minimal, so the markers carry the picture
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 20, maxNativeZoom: 16, attribution: "Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors" }).addTo(map);
L.control.scale({ imperial: false, position: "bottomright" }).addTo(map);
const SIM = '<span class="badge">SIM</span>';
const layers = {
  hull90: L.polygon([], { color: "#f79009", weight: 1.5, fillColor: "#f79009", fillOpacity: 0.08, dashArray: "5 5" }).addTo(map),
  hull50: L.polygon([], { color: "#f79009", weight: 2, fillColor: "#f79009", fillOpacity: 0.18 }).addTo(map),
  ship: L.circleMarker([0, 0], { radius: 9, color: "#fff", fillColor: "#0b3d91", fillOpacity: 1, weight: 3 }).addTo(map)
    .bindTooltip("Ship " + SIM, { permanent: true, direction: "right", className: "mk-label", offset: [10, 0] }),
  mob: L.marker([0, 0], { icon: L.divIcon({ className: "", html: '<div class="mob-x">✕</div>' }) }),
  sight: {}, cand: {},
};
let mapCentered = false, lastIncident = null, userMovedAt = 0;
map.on("dragstart zoomstart", (e) => { if (!autoFitting) userMovedAt = Date.now(); });
let autoFitting = false;
function autoFit() {
  if (!snap || Date.now() - userMovedAt < 15000) return;
  const pts = [[snap.ship.lat, snap.ship.lon]];
  const inc = snap.incident;
  if (inc && inc.mob_location) pts.push([inc.mob_location.lat, inc.mob_location.lon]);
  for (const n of ["A", "B"]) { const la = snap.nodes[n] && snap.nodes[n].last_accepted; if (la && la.location) pts.push([la.location.lat, la.location.lon]); }
  for (const c of allCandidates()) if (c.location) pts.push([c.location.lat, c.location.lon]);
  if (snap.drift) pts.push(...snap.drift.hull90);
  const b = L.latLngBounds(pts);
  const view = map.getBounds().pad(-0.1);
  const want = Math.min(18, map.getBoundsZoom(b.pad(0.3)));
  if (!view.contains(b) || want - map.getZoom() >= 1) {
    autoFitting = true;
    map.fitBounds(b.pad(0.25), { maxZoom: 18, animate: true });
    setTimeout(() => (autoFitting = false), 600);
  }
}
setInterval(autoFit, 2000);

function setLatLngs(poly, pts) { poly.setLatLngs(pts && pts.length ? pts : []); }
let lastHulls = null, collapse = null, fixLabelTimer = null;
const COLLAPSE_MS = 1400;
function animateCollapse(t) {
  if (!collapse) return;
  const k = Math.min(1, (t - collapse.t0) / COLLAPSE_MS), e = 1 - Math.pow(1 - k, 3);
  const [ty, tx] = collapse.to;
  const lerp = (pts) => pts.map(([y, x]) => [y + (ty - y) * e, x + (tx - x) * e]);
  setLatLngs(layers.hull90, lerp(collapse.from.h90));
  setLatLngs(layers.hull50, lerp(collapse.from.h50));
  if (k < 1) requestAnimationFrame(animateCollapse);
  else { collapse = null; setLatLngs(layers.hull90, null); setLatLngs(layers.hull50, null); }
}

function renderChart() {
  if (!snap) return;
  const t = nowS();
  const ship = [snap.ship.lat, snap.ship.lon];
  layers.ship.setLatLng(ship);
  if (!mapCentered) { map.setView(ship, 17); mapCentered = true; }
  const inc = snap.incident;
  if (inc && inc.mob_location) {
    layers.mob.setLatLng([inc.mob_location.lat, inc.mob_location.lon]).addTo(map);
    if (lastIncident !== inc.incident_id) {
      lastIncident = inc.incident_id;
      // drop only other incidents' events; this incident's MOB/launch may already be in
      for (const [k, e] of timeline) if (e.incident_id && e.incident_id !== inc.incident_id) timeline.delete(k);
      renderTimeline();
      map.setView([inc.mob_location.lat, inc.mob_location.lon], 17);
    }
  } else layers.mob.remove();

  const d = snap.drift;
  const lab = $("#estimate-label");
  if (d) {
    collapse = null;
    clearTimeout(fixLabelTimer); fixLabelTimer = null;
    lastHulls = { h50: d.hull50, h90: d.hull90 };
    setLatLngs(layers.hull90, d.hull90);
    setLatLngs(layers.hull50, d.hull50);
    lab.classList.remove("hidden");
    lab.innerHTML = `<h4>Drift search area <span class="badge">ESTIMATE</span></h4><dl>` +
      `<dt>Model</dt><dd>${d.model}</dd><dt>Forcing</dt><dd>${d.forcing}</dd>` +
      `<dt>Seeded from</dt><dd>${d.seed_kind === "overboard" ? "Overboard point" : "Last sighting (" + d.seed_node + ")"}</dd>` +
      `<dt>Scenario</dt><dd>+${fmtAge(d.sim_elapsed_s)} · clock ${d.multiplier}×</dd>` +
      `<dt>90 % area</dt><dd>≈ ${(d.area90_m2 / 1e4).toFixed(2)} ha <span class="grow">▲ growing</span></dd></dl>` +
      `<div class="fine">50 % / 90 % contours · grows while no sighting is fresh · not a calibrated probability</div>`;
  } else if (lastHulls && snap.last_accepted && snap.last_accepted.location && inc && !inc.ended) {
    // a fresh sighting replaced the estimate: shrink the area onto the fix instead of blinking it out
    const la = snap.last_accepted;
    collapse = { t0: performance.now(), to: [la.location.lat, la.location.lon], from: lastHulls, node: la.node_id };
    lastHulls = null;
    requestAnimationFrame(animateCollapse);
    lab.classList.remove("hidden");
    lab.innerHTML = `<h4>Position fixed <span class="badge real">SIGHTING</span></h4>` +
      `<div class="fine"><span class="fix">Drift area collapsed to Scout ${la.node_id}'s sighting.</span> ` +
      `${snap.dispatch && snap.dispatch.handoff ? "Fix sent to the rover. " : ""}Coordinates simulated (no GPS).</div>`;
    clearTimeout(fixLabelTimer);
    fixLabelTimer = setTimeout(() => { fixLabelTimer = null; if (!snap.drift) lab.classList.add("hidden"); }, 6000);
  } else if (!collapse) {
    setLatLngs(layers.hull90, null); setLatLngs(layers.hull50, null);
    if (!fixLabelTimer) lab.classList.add("hidden");
  }

  for (const n of ["A", "B"]) {
    const ns = snap.nodes[n];
    const la = ns && ns.last_accepted;
    let m = layers.sight[n];
    if (la && la.location) {
      const age = t - la.capture_ts;
      const fresh = age <= 6.0;
      if (!m) {
        const dir = n === "A" ? "top" : "bottom";
        m = layers.sight[n] = L.circleMarker([0, 0], { radius: 8, weight: 3 }).addTo(map)
          .bindTooltip("", { permanent: true, direction: dir, className: "mk-label", offset: [0, dir === "top" ? -10 : 10] });
      }
      m.setLatLng([la.location.lat, la.location.lon]);
      m.setStyle({ color: fresh ? "#fff" : NODE_COLORS[n], fillColor: fresh ? NODE_COLORS[n] : "#fff", fillOpacity: 1, dashArray: fresh ? null : "3 3" });
      m.setTooltipContent(`${n} · last sighting ${fmtAge(age)}${fresh ? "" : " (stale)"} ${SIM}`);
    } else if (m) { m.remove(); delete layers.sight[n]; }
  }
  const cands = allCandidates();
  const keep = new Set(cands.map((c) => c.candidate_id));
  for (const [id, m] of Object.entries(layers.cand)) if (!keep.has(id)) { m.remove(); delete layers.cand[id]; }
  for (const c of cands) {
    if (!c.location) continue;
    let m = layers.cand[c.candidate_id];
    if (!m) {
      m = layers.cand[c.candidate_id] = L.circleMarker([0, 0], { radius: 13, color: "#d92d20", weight: 3, fillOpacity: 0.12 }).addTo(map)
        .bindTooltip("", { permanent: true, direction: "bottom", className: "mk-label cand", offset: [0, 12] });
      m.on("click", () => { selectedCandidate = c.candidate_id; toast("Selected candidate on " + c.node_id); });
    }
    m.setLatLng([c.location.lat, c.location.lon]);
    m.setTooltipContent(`CANDIDATE ${c.node_id}${c.distance_m != null ? " · " + c.distance_m.toFixed(0) + " m" : ""}`);
  }
}

// ------------------------------------------------------------------ feeds
function fitRect(cv, img) {
  const iw = img ? img.width : 640, ih = img ? img.height : 400;
  const s = Math.min(cv.width / iw, cv.height / ih);
  return { x: (cv.width - iw * s) / 2, y: (cv.height - ih * s) / 2, w: iw * s, h: ih * s };
}
const BOX_COLORS = { tracking: "#32d583", candidate: "#f97066", detection: "#98a2b3", person: "#fdb022", ball: "#32d583",
  decoy: "#b42318", "ball?": "#98a2b3" };
const CANVAS_FONT = "Inter, -apple-system, sans-serif";

function drawBoxes(ctx, fit, header, dim) {
  for (const b of header.boxes) {
    const [x1, y1, x2, y2] = b.bbox;
    const sel = b.candidate_id && b.candidate_id === (currentCandidate() || {}).candidate_id;
    const col = BOX_COLORS[b.state] || "#fff";
    const bx = fit.x + x1 * fit.w, by = fit.y + y1 * fit.h;
    ctx.strokeStyle = col;
    ctx.lineWidth = sel ? 5 : 3;
    ctx.globalAlpha = dim ? 0.6 : 1;
    ctx.beginPath(); ctx.roundRect(bx, by, (x2 - x1) * fit.w, (y2 - y1) * fit.h, 6); ctx.stroke();
    const lbl = (b.state === "person" || b.state === "ball") ? `${b.state}${b.z_m != null ? " " + b.z_m.toFixed(2) + " m" : ""}`
      : b.state === "decoy" ? "red · decoy" : `${b.state} ${Math.round(b.confidence * 100)}%`;
    ctx.font = `700 17px ${CANVAS_FONT}`;
    const tw = ctx.measureText(lbl).width, ly = Math.max(0, by - 26);
    ctx.fillStyle = col; ctx.beginPath(); ctx.roundRect(bx - 1.5, ly, tw + 14, 24, 5); ctx.fill();
    ctx.fillStyle = (b.state === "candidate" || b.state === "decoy") ? "#fff" : "#06281a";
    ctx.fillText(lbl, bx + 5.5, ly + 17);
    ctx.globalAlpha = 1;
  }
}

function renderFeeds() {
  const t = nowS();
  for (const tile of document.querySelectorAll(".tile")) {
    const node = tile.dataset.node, cv = tile.querySelector("canvas"), ctx = cv.getContext("2d");
    const ns = snap && snap.nodes[node], f = feeds[node] || {};
    const liveAge = f.liveHeader ? t - f.liveHeader.capture_ts : Infinity;
    const videoOk = linkUp && f.live && liveAge < VIDEO_STALE_S;
    let pill = ns ? ns.pill : "NO VIDEO";
    if (!videoOk && pill !== "CONTACT LOST") pill = "NO VIDEO";
    const isRover = snap && snap.roles && node === snap.roles.rover;
    if (isRover && snap.dispatch && ns && !ns.has_target && pill !== "CANDIDATE" && pill !== "NO VIDEO")
      pill = ({ dispatched: "EN ROUTE", driving: "EN ROUTE", searching: "SEARCHING", approaching: "APPROACHING" })[snap.dispatch.status] || snap.dispatch.status.toUpperCase();
    let pillNote = "";
    if (isRover && snap.dispatch && snap.dispatch.status === "arrived") {
      pill = "ON SCENE";
      const ob = snap.dispatch.onboard;
      if (ob && (ob.label || ob.color)) pillNote = ` · ${ob.label || ob.color} confirmed onboard`;
    }
    const SRC = { sim: ["SIM", ""], file: ["RECORDED", ""], usb: ["LIVE FPV", "real"], aurora: ["AURORA", "real"], ws: ["LIVE", "real"], uvc: ["LIVE", "real"] };
    if (ns) {
      const role = node === "ship" ? "Ship deck cam" : snap.roles && node === snap.roles.rover ? `Rover ${node}` : snap.roles && node === snap.roles.drone ? `Drone ${node}` : `Scout ${node}`;
      tile.querySelector(".name").textContent = role;
      const lb = ns.label || "";
      tile.querySelector(".sub").textContent = node === "ship" ? (ns.source === "aurora" ? "Aurora stereo depth" : "stereo depth camera") : lb.includes("·") ? lb.split("·").slice(1).join("·").trim() : lb;
      const sb = tile.querySelector(".src"), sv = SRC[ns.source] || [String(ns.source || "").toUpperCase(), ""];
      sb.textContent = sv[0]; sb.className = "src badge " + sv[1];
    }
    const vid = tile.querySelector(".video");
    let tg = vid.querySelector(".target");
    if (!tg) { tg = document.createElement("div"); tg.className = "target"; vid.appendChild(tg); }
    tg.textContent = ns && ns.target && node !== "ship" ? "target: " + (ns.target === "ball" ? "green ball" : ns.target.replace("+", " + ")) : "";
    const pe = tile.querySelector(".pill");
    pe.textContent = pill + pillNote + (linkUp || !snap ? "" : " · as of link loss");
    pe.className = "pill " + pill.replace(" ", "_");
    const hasCand = !!(ns && ns.candidates.length && snap.incident && !snap.incident.ended);
    tile.classList.toggle("sel", hasCand);
    const q = tile.querySelector(".decide .q");
    if (q && hasCand) { const k = tileCandidate(node); q.textContent = `Possible person · ${k.reason}${k.distance_m != null ? " · " + k.distance_m.toFixed(0) + " m from last fix" : ""}`; }

    ctx.fillStyle = "#0b1520"; ctx.fillRect(0, 0, cv.width, cv.height);
    let ageText = "";
    if (videoOk) {
      const fit = fitRect(cv, f.live);
      ctx.drawImage(f.live, fit.x, fit.y, fit.w, fit.h);
      drawBoxes(ctx, fit, f.liveHeader, false);
      if (node === "ship" && snap && snap.rail && snap.rail.row && f.liveHeader.source !== "sim") drawRail(ctx, fit);
      if (node === "ship" && snap && snap.rail && f.liveHeader.source !== "sim") {
        const txt = snap.rail.trigger_enabled ? `rail ${snap.rail.rail_m.toFixed(2)} m · auto-MOB ${snap.rail.armed ? "ARMED" : "on"}` : "auto-MOB off · rail not calibrated";
        ctx.font = "bold 16px sans-serif"; const w = ctx.measureText(txt).width + 14;
        ctx.fillStyle = "rgba(0,0,0,.65)"; ctx.fillRect(cv.width - w - 8, cv.height - 30, w, 24);
        ctx.fillStyle = snap.rail.trigger_enabled ? "#f2cc60" : "#c9d1d9"; ctx.fillText(txt, cv.width - w - 1, cv.height - 12);
      }
      if (ns && ns.lost && ns.last_accepted) {
        ageText = `visual lost · last seen ${fmtAge(t - ns.last_accepted.capture_ts)} ago`;
        if (f.grab) drawInset(ctx, cv, f.grab, f.grabHeader);
      }
    } else {
      const img = f.grab || f.live, hdr = f.grabHeader || f.liveHeader;
      if (img) {
        const fit = fitRect(cv, img);
        ctx.globalAlpha = 0.55; ctx.drawImage(img, fit.x, fit.y, fit.w, fit.h); ctx.globalAlpha = 1;
        drawBoxes(ctx, fit, hdr, true);
        ctx.fillStyle = "rgba(15,29,46,.75)"; ctx.beginPath(); ctx.roundRect(fit.x + 10, fit.y + 10, 170, 30, 6); ctx.fill();
        ctx.fillStyle = "#fff"; ctx.font = `700 15px ${CANVAS_FONT}`;
        ctx.fillText("RETAINED GRAB", fit.x + 22, fit.y + 30);
      } else {
        ctx.textAlign = "center";
        ctx.fillStyle = "#5b6b7f"; ctx.font = `700 22px ${CANVAS_FONT}`; ctx.fillText("NO VIDEO", cv.width / 2, cv.height / 2);
        ctx.font = `500 14px ${CANVAS_FONT}`; ctx.fillText("waiting for frames from this node", cv.width / 2, cv.height / 2 + 26);
        ctx.textAlign = "start";
      }
      const seen = ns && ns.last_accepted ? ns.last_accepted.capture_ts : f.liveHeader ? f.liveHeader.capture_ts : null;
      ageText = seen ? `${ns && ns.last_accepted ? "person" : "video"} last seen ${fmtAge(t - seen)} ago` : "";
    }
    tile.querySelector(".age").textContent = ageText;
  }
}

function drawInset(ctx, cv, img, hdr) {
  const w = cv.width * 0.34, h = w * img.height / img.width, x = cv.width - w - 8, y = 8;
  ctx.drawImage(img, x, y, w, h);
  drawBoxes(ctx, { x, y, w, h }, hdr, false);
  ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h);
  ctx.fillStyle = "rgba(15,29,46,.8)"; ctx.fillRect(x, y + h - 22, w, 22);
  ctx.fillStyle = "#fff"; ctx.font = `600 13px ${CANVAS_FONT}`; ctx.fillText("last sighting grab", x + 6, y + h - 6);
}

function drawRail(ctx, fit) {
  const y = fit.y + snap.rail.row * fit.h;
  ctx.strokeStyle = "#fdb022"; ctx.lineWidth = 3; ctx.setLineDash([12, 8]);
  ctx.beginPath(); ctx.moveTo(fit.x, y); ctx.lineTo(fit.x + fit.w, y); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = "#fdb022"; ctx.font = `700 15px ${CANVAS_FONT}`; ctx.fillText(`RAIL ${snap.rail.rail_m.toFixed(2)} m (depth)`, fit.x + 8, y - 6);
}

// ------------------------------------------------------------------ banner + controls
const PHASE_TEXT = { STANDBY: "DECK WATCH", OVERBOARD: "MAN OVERBOARD — searching", CANDIDATE: "MAN OVERBOARD — candidate",
  TRACKING: "MAN OVERBOARD — tracking", CONTACT_LOST: "CONTACT LOST — drift search", ENDED: "INCIDENT ENDED" };

function subtitle() {
  const t = nowS(), inc = snap.incident, p = snap.phase;
  const tracking = ["A", "B"].filter((n) => snap.nodes[n] && snap.nodes[n].has_target && !snap.nodes[n].lost);
  switch (p) {
    case "STANDBY":
      if (!snap.rail.trigger_enabled) return "Deck camera live with person detection. Rail not calibrated — auto-MOB off (manual MOB in the demo drawer).";
      return snap.rail.armed ? "Deck camera is watching the rail line. Crew member on deck — trigger armed." : "Deck camera is watching the rail line.";
    case "OVERBOARD": return (inc.source === "shipcam" ? `Deck camera saw a person cross the rail at ${fmtTime(inc.mob_capture_ts)}.` : `Manual MOB at ${fmtTime(inc.mob_capture_ts)}.`) + " Drone and rover launched — drone searching the drift area.";
    case "CANDIDATE": { const c = currentCandidate(); return c ? `Scout ${c.node_id} sees a possible person (${c.reason}). Confirm or reject.` : "Candidate needs a decision."; }
    case "TRACKING": {
      if (!tracking.length) { const la = snap.last_accepted; return `All scouts lost visual — last fix ${fmtAge(t - la.capture_ts)} old, still fresh.`; }
      const names = tracking.map((n) => (snap.roles && n === snap.roles.rover ? "rover" : snap.roles && n === snap.roles.drone ? "drone" : "Scout " + n));
      const d = snap.dispatch;
      let extra = "";
      if (d && d.status === "arrived") extra = " Rover on scene.";
      else if (d && !tracking.includes(snap.roles.rover)) extra = d.handoff ? ` Fix sent to rover — ${d.handoff.range_m} m at ${d.handoff.bearing_deg}°.` : ` Rover ${({ dispatched: "en route", driving: "en route" })[d.status] || d.status}.`;
      if (!snap.follow_enabled) extra += " Following stopped by coordinator.";
      const who = names.join(" + ");
      return who.charAt(0).toUpperCase() + who.slice(1) + " on the target." + extra;
    }
    case "CONTACT_LOST": { const la = snap.last_accepted; return `No scout has seen the person for ${fmtAge(t - la.capture_ts)}. Search area growing from the last sighting.`; }
    case "ENDED": return `Incident ended at ${fmtTime(inc.ended_ts)}. History preserved; deck watch re-armed.`;
  }
  return "";
}

function renderBanner() {
  const b = $("#banner");
  const lk = $("#link");
  lk.textContent = linkUp ? "LINK OK" : "LINK LOST";
  lk.className = "pill " + (linkUp ? "ok" : "bad");
  if (!snap) return;
  b.className = snap.phase;
  document.body.classList.remove("ph-STANDBY", "ph-OVERBOARD", "ph-CANDIDATE", "ph-TRACKING", "ph-CONTACT_LOST", "ph-ENDED");
  document.body.classList.add("ph-" + snap.phase);
  $("#clock").textContent = fmtTime(nowS());
  $("#phase-text").textContent = (PHASE_TEXT[snap.phase] || snap.phase) + (linkUp ? "" : " (last known)");
  $("#subtitle").textContent = subtitle();
  const inc = snap.incident;
  if (inc && !inc.ended) { const el = Math.max(0, nowS() - inc.opened_ts); $("#inc-timer").textContent = `${String(Math.floor(el / 60)).padStart(2, "0")}:${String(Math.floor(el % 60)).padStart(2, "0")}`; }
  else $("#inc-timer").textContent = inc ? "ended" : "—";

  const active = inc && !inc.ended;
  const rover = snap.roles ? snap.roles.rover : "B";
  const rv = snap.nodes[rover];
  const fb = $("#btn-follow");
  fb.classList.toggle("hidden", !(active && snap.last_accepted));
  fb.textContent = snap.follow_enabled ? "Stop following" : "Resume following";
  $("#btn-end").classList.toggle("hidden", !active);
  $("#btn-end").classList.toggle("armed", Date.now() < endArmedUntil);
  const st = NODES.map((n) => snap.nodes[n] ? `${n}: ${snap.nodes[n].source} ${snap.nodes[n].fps} fps clk=${snap.nodes[n].clock_quality}` : "").join("\n");
  $("#stats").textContent = st + `\ndrift ×${snap.scenario.multiplier}  hidden=${snap.scenario.hidden}`;
}

function frame() {
  watchdog();
  renderBanner();
  renderFeeds();
  requestAnimationFrame(frame);
}
setInterval(() => { if (snap) renderChart(); }, 250);
connect();
requestAnimationFrame(frame);
