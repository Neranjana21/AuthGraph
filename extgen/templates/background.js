// MV3 service worker (classic). Executes steps delegated by the content script.
importScripts(__IMPORTS__);
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.ag) return;
  (async () => {
    AG.sid = msg.sid; AG.comp = 'service_worker';
    const before = new Set(Object.keys(msg.vars));
    await agStep(msg.step, msg.vars, 'service_worker', msg.idx);
    const out = {};
    if (msg.step.out && msg.vars[msg.step.out]) out[msg.step.out] = msg.vars[msg.step.out];
    if (Object.keys(out).length) {
      agEmit({ event_type: 'message', component: 'service_worker', module: 'background.js',
        to_component: 'content_script', api: 'sendResponse', step_idx: msg.idx,
        tags: agTags(out, Object.keys(out)) });
    }
    await agFlush();
    sendResponse({ vars: out });
  })();
  return true;
});
