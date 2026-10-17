MODS['__NAME__'] = {
  b64: s => btoa(unescape(encodeURIComponent(s))),
  rot: s => s.replace(/[a-zA-Z]/g, ch => { const b = ch <= 'Z' ? 65 : 97; return String.fromCharCode((ch.charCodeAt(0) - b + 13) % 26 + b); }),
  hex: s => Array.from(new TextEncoder().encode(s)).map(b => b.toString(16).padStart(2, '0')).join(''),
  rev: s => s.split('').reverse().join(''),
  fmt: s => JSON.stringify({ d: s }),
};
