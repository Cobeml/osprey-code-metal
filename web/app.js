// Osprey coordinator display. Holds its own snapshot and ages it locally; the only input is the
// gateway WebSocket (FR-10). History never overwrites newer current state (FR-07).
"use strict";

const LINK_TIMEOUT_MS = 1500;
const VIDEO_STALE_S = 1.5;
const NODES = ["ship", "A", "B"];
const NODE_COLORS = { ship: "#ffffff", A: "#58a6ff", B: "#d2a8ff" };

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

$("#btn-confirm").onclick = (e) => { const c = currentCandidate(); if (c) send("confirm", { candidate_id: c.candidate_id }, e.target); };
$("#btn-reject").onclick = (e) => { const c = currentCandidate(); if (c) send("reject", { candidate_id: c.candidate_id }, e.target); };
$("#btn-dispatch").onclick = (e) => send("dispatch", {}, e.target);
$("#btn-follow").onclick = (e) => send(snap && snap.follow_enabled ? "stop_follow" : "resume_follow", {}, e.target);
$("#btn-end").onclick = (e) => {
  if (Date.now() < endArmedUntil) { endArmedUntil = 0; send("end_incident", {}, e.target); }
  else { endArmedUntil = Date.now() + 3000; toast("Click END INCIDENT again to confirm"); }
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
    const node = cv.parentElement.dataset.node, f = feeds[node];
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
const TL_TYPES = { dispatch: "rover dispatched", mob: "MOB", confirm: "confirmed", associated: "associated", reacquired: "reacquired", lost: "visual lost",
  input_lost: "video lost", input_restored: "video back", end: "ended", stop_follow: "follow stopped",
  resume_follow: "follow resumed", reject: "rejected", session_restart: "source restart", history: "history" };
function addTimeline(e, isHistory) {
  if (!TL_TYPES[e.type] && !(e.type === "observation" && e.kind === "candidate")) return;
  if (timeline.has(e.event_id)) return;
  timeline.set(e.event_id, { ...e, history: isHistory });
  renderTimeline();
}
function renderTimeline() {
  const evs = [...timeline.values()].sort((a, b) => a.capture_ts - b.capture_ts).slice(-9);
  $("#timeline").innerHTML = evs.map((e) => {
    const label = e.type === "observation" ? `candidate ${e.node_id}` :
      e.type === "history" ? `history +${e.n}` : `${TL_TYPES[e.type]}${e.node_id && e.type !== "mob" ? " " + e.node_id : ""}`;
    return `<span class="chip ${e.type} ${e.history ? "history" : ""}" title="${e.reason || ""}">${fmtTime(e.capture_ts)} ${label}</span>`;
  }).join("");
}

// ------------------------------------------------------------------ chart
const map = L.map("chart", { zoomControl: true, attributionControl: true }).setView([42.35, -70.8], 17);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
L.control.scale({ imperial: false }).addTo(map);
const layers = {
  hull90: L.polygon([], { color: "#f2cc60", weight: 1, fillOpacity: 0.12, dashArray: "4 4" }).addTo(map),
  hull50: L.polygon([], { color: "#f2cc60", weight: 2, fillOpacity: 0.25 }).addTo(map),
  ship: L.circleMarker([0, 0], { radius: 9, color: "#fff", fillColor: "#30363d", fillOpacity: 1, weight: 3 }).addTo(map)
    .bindTooltip("Ship (simulated position)", { permanent: true, direction: "right", className: "mk-label" }),
  mob: L.marker([0, 0], { icon: L.divIcon({ className: "", html: '<div style="color:#ff4d4f;font:900 26px sans-serif;margin:-14px 0 0 -8px">✕</div>' }) }),
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
      timeline.clear();
      map.setView([inc.mob_location.lat, inc.mob_location.lon], 17);
    }
  } else layers.mob.remove();

  const d = snap.drift;
  setLatLngs(layers.hull90, d && d.hull90);
  setLatLngs(layers.hull50, d && d.hull50);
  const lab = $("#estimate-label");
  if (d) {
    lab.classList.remove("hidden");
    lab.innerHTML = `<b>ESTIMATE</b> — 50% / 90% drift area<br>${d.model}<br>Forcing: ${d.forcing}` +
      `<br>Seeded from ${d.seed_kind === "overboard" ? "overboard point" : "last sighting (" + d.seed_node + ")"} · ` +
      `scenario +${fmtAge(d.sim_elapsed_s)} (clock ${d.multiplier}× while no sighting is fresh)` +
      `<br>90% area ≈ ${(d.area90_m2 / 1e4).toFixed(2)} ha · not a calibrated probability`;
  } else lab.classList.add("hidden");

  for (const n of ["A", "B"]) {
    const ns = snap.nodes[n];
    const la = ns && ns.last_accepted;
    let m = layers.sight[n];
    if (la && la.location) {
      const age = t - la.capture_ts;
      const fresh = age <= 6.0;
      if (!m) {
        m = layers.sight[n] = L.circleMarker([0, 0], { radius: 8, weight: 3 }).addTo(map)
          .bindTooltip("", { permanent: true, direction: "top", className: "mk-label", offset: [0, -8] });
      }
      m.setLatLng([la.location.lat, la.location.lon]);
      m.setStyle({ color: NODE_COLORS[n], fillColor: fresh ? NODE_COLORS[n] : "#000", fillOpacity: fresh ? 0.9 : 0.3, dashArray: fresh ? null : "3 3" });
      m.setTooltipContent(`${n} last sighting · ${fmtAge(age)}${fresh ? "" : " (stale)"} · sim coords`);
    } else if (m) { m.remove(); delete layers.sight[n]; }
  }
  const cands = allCandidates();
  const keep = new Set(cands.map((c) => c.candidate_id));
  for (const [id, m] of Object.entries(layers.cand)) if (!keep.has(id)) { m.remove(); delete layers.cand[id]; }
  for (const c of cands) {
    if (!c.location) continue;
    let m = layers.cand[c.candidate_id];
    if (!m) {
      m = layers.cand[c.candidate_id] = L.circleMarker([0, 0], { radius: 11, color: "#ff7b72", weight: 3, fillOpacity: 0.2 }).addTo(map)
        .bindTooltip("", { permanent: true, direction: "bottom", className: "mk-label", offset: [0, 10] });
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
const BOX_COLORS = { tracking: "#3fb950", candidate: "#ff7b72", detection: "#8b949e", person: "#f2cc60", ball: "#7ee787" };

function drawBoxes(ctx, fit, header, dim) {
  for (const b of header.boxes) {
    const [x1, y1, x2, y2] = b.bbox;
    const sel = b.candidate_id && b.candidate_id === (currentCandidate() || {}).candidate_id;
    ctx.strokeStyle = BOX_COLORS[b.state] || "#fff";
    ctx.lineWidth = sel ? 5 : 3;
    ctx.globalAlpha = dim ? 0.6 : 1;
    ctx.strokeRect(fit.x + x1 * fit.w, fit.y + y1 * fit.h, (x2 - x1) * fit.w, (y2 - y1) * fit.h);
    ctx.fillStyle = ctx.strokeStyle;
    ctx.font = "bold 18px sans-serif";
    const lbl = (b.state === "person" || b.state === "ball") ? `${b.state}${b.z_m != null ? " " + b.z_m.toFixed(2) + " m" : ""}` : `${b.state} ${Math.round(b.confidence * 100)}%`;
    ctx.fillText(lbl, fit.x + x1 * fit.w, Math.max(18, fit.y + y1 * fit.h - 5));
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
    if (isRover && snap.dispatch && snap.dispatch.status === "arrived") pill = "ON SCENE";
    const SRC = { sim: "  [SIM]", file: "  [RECORDED FLIGHT]", usb: "  [LIVE FPV]" };
    if (ns) tile.querySelector(".name").textContent = (ns.label || node) + (SRC[ns.source] || "");
    let tg = tile.querySelector(".target");
    if (!tg) { tg = document.createElement("div"); tg.className = "target"; tile.appendChild(tg); }
    tg.textContent = ns && ns.target && node !== "ship" ? "target: " + (ns.target === "ball" ? "green ball" : ns.target) : "";
    const pe = tile.querySelector(".pill");
    pe.textContent = pill + (linkUp || !snap ? "" : " · as of link loss");
    pe.className = "pill " + pill.replace(" ", "_");
    tile.classList.toggle("sel", !!(ns && ns.candidates.length));

    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, cv.width, cv.height);
    let ageText = "";
    if (videoOk) {
      const fit = fitRect(cv, f.live);
      ctx.drawImage(f.live, fit.x, fit.y, fit.w, fit.h);
      drawBoxes(ctx, fit, f.liveHeader, false);
      if (node === "ship" && snap && snap.rail && snap.rail.row && f.liveHeader.source !== "sim") drawRail(ctx, fit);
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
        ctx.fillStyle = "rgba(0,0,0,.6)"; ctx.fillRect(0, fit.y, cv.width, 34);
        ctx.fillStyle = "#fff"; ctx.font = "bold 20px sans-serif";
        ctx.fillText("RETAINED GRAB", fit.x + 10, fit.y + 24);
      } else {
        ctx.fillStyle = "#8b949e"; ctx.font = "bold 26px sans-serif"; ctx.fillText("NO VIDEO", cv.width / 2 - 70, cv.height / 2);
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
  ctx.fillStyle = "rgba(0,0,0,.7)"; ctx.fillRect(x, y + h - 22, w, 22);
  ctx.fillStyle = "#fff"; ctx.font = "bold 14px sans-serif"; ctx.fillText("last sighting grab", x + 6, y + h - 6);
}

function drawRail(ctx, fit) {
  const y = fit.y + snap.rail.row * fit.h;
  ctx.strokeStyle = "#ffdc00"; ctx.lineWidth = 3; ctx.setLineDash([12, 8]);
  ctx.beginPath(); ctx.moveTo(fit.x, y); ctx.lineTo(fit.x + fit.w, y); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = "#ffdc00"; ctx.font = "bold 16px sans-serif"; ctx.fillText(`RAIL ${snap.rail.rail_m.toFixed(2)} m (depth)`, fit.x + 8, y - 6);
}

// ------------------------------------------------------------------ banner + controls
const PHASE_TEXT = { STANDBY: "DECK WATCH", OVERBOARD: "MAN OVERBOARD — searching", CANDIDATE: "MAN OVERBOARD — candidate",
  TRACKING: "MAN OVERBOARD — tracking", CONTACT_LOST: "CONTACT LOST — drift search", ENDED: "INCIDENT ENDED" };

function subtitle() {
  const t = nowS(), inc = snap.incident, p = snap.phase;
  const tracking = ["A", "B"].filter((n) => snap.nodes[n] && snap.nodes[n].has_target && !snap.nodes[n].lost);
  switch (p) {
    case "STANDBY": return snap.rail.armed ? "Deck camera is watching the rail line. Crew member on deck — trigger armed." : "Deck camera is watching the rail line.";
    case "OVERBOARD": return (inc.source === "shipcam" ? `Deck camera saw a person cross the rail at ${fmtTime(inc.mob_capture_ts)}.` : `Manual MOB at ${fmtTime(inc.mob_capture_ts)}.`) + " Drone searching the drift area.";
    case "CANDIDATE": { const c = currentCandidate(); return c ? `Scout ${c.node_id} sees a possible person (${c.reason}). Confirm or reject.` : "Candidate needs a decision."; }
    case "TRACKING": {
      if (!tracking.length) { const la = snap.last_accepted; return `All scouts lost visual — last fix ${fmtAge(t - la.capture_ts)} old, still fresh.`; }
      const names = tracking.map((n) => (snap.roles && n === snap.roles.rover ? "rover" : snap.roles && n === snap.roles.drone ? "drone" : "Scout " + n));
      const d = snap.dispatch;
      let extra = "";
      if (d && d.status === "arrived") extra = " Rover on scene.";
      else if (d && !tracking.includes(snap.roles.rover)) extra = ` Rover ${({ dispatched: "en route", driving: "en route" })[d.status] || d.status} (${d.plan.basis}).`;
      else if (!d && snap.roles && tracking.includes(snap.roles.drone)) extra = " Dispatch the rover to recover.";
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
  $("#phase-text").textContent = (PHASE_TEXT[snap.phase] || snap.phase) + (linkUp ? "" : " (last known)");
  $("#subtitle").textContent = subtitle();
  const inc = snap.incident;
  if (inc && !inc.ended) $("#inc-timer").textContent = "incident " + fmtAge(nowS() - inc.opened_ts).replace(" min ", ":").replace(" s", "");
  else $("#inc-timer").textContent = inc ? inc.incident_id : "";

  const active = inc && !inc.ended;
  const cands = allCandidates();
  $("#btn-confirm").classList.toggle("hidden", !(active && cands.length));
  $("#btn-reject").classList.toggle("hidden", !(active && cands.length));
  const rover = snap.roles ? snap.roles.rover : "B";
  const rv = snap.nodes[rover];
  $("#btn-dispatch").classList.toggle("hidden", !(active && snap.last_accepted && !snap.dispatch && !(rv && rv.has_target)));
  const fb = $("#btn-follow");
  fb.classList.toggle("hidden", !(active && rv && (rv.has_target || snap.dispatch)));
  fb.textContent = snap.follow_enabled ? "STOP FOLLOWING" : "RESUME FOLLOWING";
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
