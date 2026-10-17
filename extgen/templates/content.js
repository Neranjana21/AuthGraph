// Content script: drives the scenario program for the session named in the page URL.
(async function () {
  const cfg = self.AG_CFG;
  const params = new URLSearchParams(location.search);
  if (params.get('ext') !== cfg.ext_id) return;           // other loaded extensions stay idle
  AG.sid = params.get('sid'); AG.comp = 'content_script';
  agEmit({ event_type: 'session_start', component: 'content_script', module: 'content.js', page_origin: location.origin });
  const vars = {};
  for (const [i, step] of cfg.steps.entries()) {
    if (step.p !== undefined && Math.random() > step.p) continue;     // optional distractor
    if (step.delay) await agSleep(step.delay * (0.5 + Math.random()));
    if (step.where === 'bg') {
      const sub = {};
      for (const n of (step.in || [])) if (vars[n]) sub[n] = vars[n];
      agEmit({ event_type: 'message', component: 'content_script', module: 'content.js',
        to_component: 'service_worker', api: 'chrome.runtime.sendMessage', step_idx: i,
        tags: agTags(sub, Object.keys(sub)) });
      await agFlush();
      const resp = await chrome.runtime.sendMessage({ ag: 1, sid: AG.sid, step, idx: i, vars: sub });
      if (resp && resp.vars) Object.assign(vars, resp.vars);
    } else {
      await agStep(step, vars, 'content_script', i);
    }
    await agFlush();
  }
  agEmit({ event_type: 'session_end', component: 'content_script', module: 'content.js' });
  await agFlush();
})();
