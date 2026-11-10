// Record the Osprey mission simulation from headless Edge via CDP screencast.
// usage: node capture_sim.mjs <outdir> <seconds>
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";

const OUT = process.argv[2]; const SECS = +process.argv[3] || 60;
mkdirSync(OUT, { recursive: true });
const PORT = 9333;
const edge = spawn("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", [
  "--headless=new", `--remote-debugging-port=${PORT}`, "--window-size=1920,1080",
  "--force-device-scale-factor=1", "--hide-scrollbars", "--mute-audio", "--no-first-run",
  "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist",
  `--user-data-dir=${OUT}/profile`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let tab;
for (let i = 0; i < 50 && !tab; i++) {
  await sleep(200);
  try { tab = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find((t) => t.type === "page"); } catch {}
}
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map(); const frames = [];
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
  if (m.method === "Page.screencastFrame") {
    const { data, metadata, sessionId } = m.params;
    const n = frames.length; const f = `${OUT}/f${String(n).padStart(5, "0")}.jpg`;
    writeFileSync(f, Buffer.from(data, "base64"));
    frames.push({ f, t: metadata.timestamp });
    send("Page.screencastFrameAck", { sessionId });
  }
};
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }))?.result?.value;

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: "http://127.0.0.1:8087/" });
await sleep(6000); // load three.js + fixture
console.log("webgl:", await evalJs(`!!document.querySelector('#viewport canvas')`));
// clean run for voice-over: no auto explainer cards
await evalJs(`(()=>{const g=document.getElementById('guided'); if(g.checked){g.click()} return g.checked})()`);
await send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
await sleep(1500);
await evalJs(`document.getElementById('play').click()`);
const t0 = Date.now();
while (Date.now() - t0 < SECS * 1000) {
  await sleep(1000);
  const st = await evalJs(`document.getElementById('time').textContent+' '+document.getElementById('mission-state').textContent`);
  process.stdout.write(`\r${((Date.now() - t0) / 1000).toFixed(0)}s ${st} frames=${frames.length}   `);
}
await send("Page.stopScreencast");
writeFileSync(`${OUT}/frames.json`, JSON.stringify(frames));
console.log(`\n${frames.length} frames`);
ws.close(); edge.kill();
process.exit(0);
