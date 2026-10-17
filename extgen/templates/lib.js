// Shared telemetry library (instrumentation layer of the lab extensions).
// Credential VALUES are never logged: only a salted-free short SHA-256 id.
var AG = { buf: [], sid: null, comp: null, cseq: 0 };
var MODS = (typeof MODS === 'undefined') ? {} : MODS;
const TELE_URL = 'http://localhost:5001/telemetry';

async function agHash(s) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return Array.from(new Uint8Array(d)).slice(0, 6).map(b => b.toString(16).padStart(2, '0')).join('');
}
function agEmit(ev) {
  AG.buf.push(Object.assign({
    session_id: AG.sid, extension_id: self.AG_CFG.ext_id,
    ts: performance.timeOrigin + performance.now(), cseq: AG.cseq++
  }, ev));
}
async function agFlush() {
  if (!AG.buf.length) return;
  const body = JSON.stringify(AG.buf); AG.buf = [];
  try { await fetch(TELE_URL, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body }); }
  catch (e) { console.warn('telemetry flush failed', e); }
}
const agSleep = ms => new Promise(r => setTimeout(r, ms));
