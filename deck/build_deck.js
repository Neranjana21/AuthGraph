// AuthGraph deck. All metrics come from data.json (generated from results/*.json by make_data.py).
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const fa = require("react-icons/fa");
const path = require("path");
const D = require("./data.json");
const { applyTheme } = require("C:/Users/Neranjana/.claude/skills/synced/49cf4089-9927-4cc7-a9d1-5a1cf191f4dc_104e9aae-66c2-49b9-a36a-8acd7d6f0605/pptx/scripts/apply_theme.js");

const THEME = {
  name: "AuthGraph Dark", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "E5ECF4", lt1: "0A1220", dk2: "8B9BB4", lt2: "0F1B2D",
            accent1: "22B8CF", accent2: "34D399", accent3: "F2C14E", accent4: "FF5C5C", accent5: "A78BFA", accent6: "F59E0B",
            hlink: "22B8CF", folHlink: "A78BFA" },
};
const HEX = { teal: "22B8CF", green: "34D399", amber: "F2C14E", red: "FF5C5C", purple: "A78BFA", blue: "3B82F6", grey: "8B9BB4",
              text: "E5ECF4", muted: "8B9BB4", grid: "22314A", card: "0F1B2D", bg: "0A1220" };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                       // 13.33 x 7.5 in
pres.author = "Neranjana"; pres.title = "AuthGraph: authentication-aware graph learning for credential flows in browser extensions";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.33, H = 7.5, MX = 0.6;
const IMG = (f) => path.join(__dirname, "img", f);

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "COVER", background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.9, w: 6.6, h: 1.3, fontSize: 60, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.3, w: 6.2, h: 1.6, fontSize: 22, color: C.text2, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: 12.1, h: 0.95, fontSize: 32, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "AuthGraph · credential-flow detection in browser extensions", options: { x: MX, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: C.text2, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.55, h: 0.3, color: C.text2, fontSize: 10, align: "right" },
});

// ------------------------------------------------------------------ helpers
const f3 = (x) => x.toFixed(3), f2 = (x) => x.toFixed(2), pct = (x, d = 0) => (x * 100).toFixed(d) + "%";
const M = D.main, U = D.unseen.heldout_wasm_flows, ORDER = D.order;
const SHORT = { "Rule R1 (co-occurrence)": "Rule R1", "Rule R2 (taint)": "Rule R2", "RF (counts)": "RF (counts)", "RF (counts+reachability)": "RF (+reach.)",
                "MLP (counts)": "MLP", "GCN": "GCN", "GraphSAGE": "GraphSAGE", "R-GCN": "R-GCN" };
const MCOL = { "Rule R1 (co-occurrence)": "8B9BB4", "Rule R2 (taint)": "6B7A91", "RF (counts)": "F2C14E", "RF (counts+reachability)": "F59E0B",
               "MLP (counts)": "E879F9", "GCN": "3B82F6", "GraphSAGE": "22B8CF", "R-GCN": "A78BFA" };
const sizes = {};
async function loadSizes() { for (const f of require("fs").readdirSync(path.join(__dirname, "img"))) { const m = await sharp(IMG(f)).metadata(); sizes[f] = m.width / m.height; } }
const icons = {};
async function icon(name, color) {
  const svg = renderToStaticMarkup(React.createElement(fa[name], { color: "#" + color, size: 256 }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}
function title(s, text) { s.addText(text, { placeholder: "title" }); }
function card(s, x, y, w, h, name, fill) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.12, fill: { color: fill || C.background2 }, line: { color: C.text2, transparency: 75, width: 0.75 }, objectName: name || "card" });
}
function fitImg(s, file, x, y, maxW, maxH, name, align = "center") {      // keep aspect ratio inside a box, rounded look via thin border
  const ar = sizes[file]; let w = maxW, h = w / ar; if (h > maxH) { h = maxH; w = h * ar; }
  const ox = align === "center" ? x + (maxW - w) / 2 : x;
  s.addImage({ path: IMG(file), x: ox, y: y + (maxH - h) / 2, w, h, objectName: name || file, altText: name || file });
  s.addShape(pres.ShapeType.roundRect, { x: ox, y: y + (maxH - h) / 2, w, h, rectRadius: 0.06, fill: { type: "none" }, line: { color: C.text2, transparency: 70, width: 0.75 }, objectName: "frame" });
  return { w, h, x: ox, y: y + (maxH - h) / 2 };
}
function stat(s, x, y, w, h, value, label, color, fs) {
  card(s, x, y, w, h, "stat");
  s.addText(value, { x: x + 0.2, y: y + 0.15, w: w - 0.4, h: h * 0.45, fontSize: fs || 38, bold: true, color, align: "left", valign: "middle", margin: 0, isTextBox: true });
  s.addText(label, { x: x + 0.2, y: y + h * 0.55, w: w - 0.4, h: h * 0.4, fontSize: 14, color: C.text1, align: "left", valign: "top", margin: 0, isTextBox: true });
}
function bullets(s, items, x, y, w, h, opt = {}) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1 } })),
    { x, y, w, h, fontSize: opt.size || 16, color: C.text1, valign: "top", paraSpaceAfter: opt.gap || 8, margin: 0, isTextBox: true });
}
function heading(s, text, x, y, w, color) { s.addText(text, { x, y, w, h: 0.35, fontSize: 13, bold: true, color: color || C.accent1, charSpacing: 2, margin: 0, isTextBox: true }); }
function chip(s, x, y, w, text, color, fg) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h: 0.62, rectRadius: 0.1, fill: { color }, line: { color, width: 0 }, objectName: "chip" });
  s.addText(text, { x, y, w, h: 0.62, fontSize: 13, bold: true, color: fg || HEX.bg, align: "center", valign: "middle", margin: 0.04, isTextBox: true });
}
function arrow(s, x, y, w, color) { s.addShape(pres.ShapeType.line, { x, y, w, h: 0, line: { color: color || C.text2, width: 2, endArrowType: "triangle" }, objectName: "arrow" }); }
const chartBase = () => ({
  catAxisLabelColor: "C3CedB", valAxisLabelColor: "C3CedB", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", titleFontFace: "+mn-lt",
  valGridLine: { color: HEX.grid, size: 0.5 }, catGridLine: { style: "none" }, valAxisLineShow: false, catAxisLineShow: true,
  dataLabelColor: HEX.text, dataLabelFontSize: 11, legendColor: "C3CedB", legendFontSize: 12,
});

(async () => {
  await loadSizes();
  const I = {};
  for (const [k, n, c] of [["shield", "FaShieldAlt", HEX.teal], ["puzzle", "FaPuzzlePiece", HEX.teal], ["key", "FaKey", HEX.amber], ["net", "FaNetworkWired", HEX.teal],
    ["db", "FaDatabase", HEX.teal], ["graph", "FaProjectDiagram", HEX.teal], ["lock", "FaLock", HEX.green], ["globe", "FaGlobe", HEX.teal], ["flask", "FaFlask", HEX.purple],
    ["check", "FaCheckCircle", HEX.green], ["warn", "FaExclamationTriangle", HEX.amber], ["scale", "FaBalanceScale", HEX.teal], ["search", "FaSearch", HEX.teal],
    ["bolt", "FaBolt", HEX.amber], ["cookie", "FaCookieBite", HEX.amber], ["chip", "FaMicrochip", HEX.purple]]) I[k] = await icon(n, c);
  const ic = (s, k, x, y, sz = 0.5) => s.addImage({ data: I[k], x, y, w: sz, h: sz, altText: k, objectName: "icon-" + k });

  // ================================================================ 1 COVER
  pres.addSection({ title: "Context" });
  let s = pres.addSlide({ masterName: "COVER", sectionTitle: "Context" });
  s.addText("AuthGraph", { placeholder: "title" });
  s.addText("Authentication-aware graph learning to detect unauthorized credential flows in browser extensions", { placeholder: "body" });
  s.addText("Controlled-lab prototype  ·  real Chromium  ·  576 sessions  ·  144 extensions", { x: 0.8, y: 5.2, w: 6.4, h: 0.4, fontSize: 14, color: C.accent1, margin: 0, isTextBox: true });
  s.addText("Presented by Neranjana", { x: 0.8, y: 5.7, w: 6.4, h: 0.4, fontSize: 14, color: C.text2, margin: 0, isTextBox: true });
  fitImg(s, "c_graph.jpg", 6.95, 1.6, 5.85, 4.2, "cover-hero");
  s.addNotes("OPENING (20 s). Browser extensions can legitimately read cookies and page data, so the security question is not 'is a credential read?' but 'where does it go?'. " +
    "This project builds a controlled lab that produces real browser telemetry, turns it into an authentication-aware graph, and tests whether graph neural networks detect unauthorized credential flows — including flows that pass through WebAssembly. " +
    "The picture is the actual output of the system: a session graph with the suspicious credential-to-sink path highlighted in red. Everything runs on localhost with synthetic credentials.");

  // ================================================================ 2 PROBLEM
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Context" });
  title(s, "A session cookie is one API call away");
  s.addText("Extensions legitimately read cookies, storage and pages. The question is where the credential goes, not whether it is read.",
    { x: MX, y: 1.3, w: 12.1, h: 0.7, fontSize: 18, color: C.text2, margin: 0, isTextBox: true });
  const rows = [
    { y: 2.35, col: HEX.green, tag: "AUTHORIZED  ·  BENIGN", chips: [["Extension", HEX.blue], ["chrome.cookies.get", "5EEAD4"], ["Session credential", "FB923C"], ["POST request", HEX.purple], ["api.lab.localhost\n(approved)", HEX.green]] },
    { y: 4.35, col: HEX.red, tag: "UNAUTHORIZED  ·  SUSPICIOUS", chips: [["Extension", HEX.blue], ["chrome.cookies.get", "5EEAD4"], ["Session credential", "FB923C"], ["JS / WebAssembly", "E879F9"], ["sink-a.lab.localhost\n(unapproved)", HEX.red]] },
  ];
  for (const r of rows) {
    card(s, MX, r.y, 12.1, 1.75, "flow-card");
    s.addText(r.tag, { x: MX + 0.3, y: r.y + 0.12, w: 6, h: 0.3, fontSize: 12, bold: true, color: r.col, charSpacing: 2, margin: 0, isTextBox: true });
    const cw = 1.95, gap = 0.5; let x = MX + 0.3;
    r.chips.forEach(([t, c], i) => { chip(s, x, r.y + 0.65, cw, t, c); x += cw; if (i < r.chips.length - 1) { arrow(s, x + 0.05, r.y + 0.96, gap - 0.1, r.col); x += gap; } });
  }
  s.addText("Same API calls, same credential. Only the destination and the data flow differ, so API-level rules are not enough.",
    { x: MX, y: 6.3, w: 12.1, h: 0.5, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addNotes("PROBLEM (60 s). Top row is a perfectly legitimate extension: it reads the session cookie and sends it to the approved API. Bottom row reads the same cookie through the same API, " +
    "but routes it through JavaScript or a WebAssembly module and sends it to a destination that is not approved. A detector that only looks at 'cookie API was called' cannot tell these apart. " +
    "That is why the project models the whole flow as a graph and also builds hard negatives into the dataset — benign sessions that read credentials and use approved APIs.");

  // ================================================================ 3 SUMMARY
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Context" });
  title(s, "What we found, in four numbers");
  const cw4 = 2.9, gx = 0.17;
  const cards4 = [
    [String(D.dataset.sessions_completed), "real browser sessions from 144 generated MV3 extensions in 12 scenarios; 0 credential leaks", HEX.teal],
    [f3(U["GraphSAGE"].recall), `GraphSAGE recall on Wasm flows never seen in training. Taint rule ${f3(U["Rule R2 (taint)"].recall)}, flat models ${f2(U["MLP (counts)"].recall)}–${f2(U["RF (counts+reachability)"].recall)}`, HEX.green],
    [f3(U["R-GCN"].recall), "R-GCN, our proposed heterogeneous model, on the same test. It lost, and we report it", HEX.purple],
    ["≥99.3%", "top-band confidence: the 95% lower bound of accuracy observed on held-out data. Never 100%", HEX.amber],
  ];
  cards4.forEach(([v, l, c], i) => stat(s, MX + i * (cw4 + gx), 1.5, cw4, 2.6, v, l, c));
  card(s, MX, 4.4, 12.1, 2.25, "takeaway");
  heading(s, "THE MESSAGE", MX + 0.35, 4.6, 4);
  s.addText([
    { text: "Graph structure helps exactly where instrumentation is incomplete: when taint is lost inside WebAssembly, the graph still exposes the flow.", options: { breakLine: true } },
    { text: "But the relation-typed R-GCN did not beat plain GraphSAGE on this small synthetic dataset. The honest result is the useful one.", options: {} },
  ], { x: MX + 0.35, y: 5.0, w: 11.4, h: 1.5, fontSize: 18, color: C.text1, paraSpaceAfter: 10, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("EXECUTIVE SUMMARY (60 s). Four numbers carry the story. First, the evidence base: 576 real browser sessions, no credential value ever stored. " +
    "Second, the research moment: with Wasm-involving flows removed from training, GraphSAGE still catches 93% of them, while a taint rule catches 65% and flat count-based models catch 62 to 69%. " +
    "Third, the honest negative result: our proposed R-GCN reached only 0.45. Fourth, the confidence score: we never print 100%; we quote the lower bound of what was actually observed. " +
    "Caveat to state out loud: this is synthetic data from a controlled lab, so it demonstrates the method, not real-world prevalence.");

  // ================================================================ 4 POSITIONING
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Context" });
  title(s, "Positioning: a narrow claim on top of strong prior work");
  card(s, MX, 1.5, 6.9, 5.2, "prior");
  heading(s, "PRIOR WORK (CHECKED BY SEARCH)", MX + 0.3, 1.7, 6);
  bullets(s, [
    "DoubleX (ACM CCS 2021): static Extension Dependence Graph for vulnerable data flows; 154,484 Chrome extensions.",
    "Arcanum (USENIX Security 2024): dynamic taint tracking of page content to network sinks in modern extensions.",
    "Heterogeneous-graph GNNs for malware behaviour graphs already exist (e.g. MalSage; title seen in search only).",
    "Wasm–JS collaborative attacks on Chrome extensions (Electronics; title seen, not yet read in full).",
  ], MX + 0.3, 2.15, 6.3, 4.4, { size: 16, gap: 12 });
  card(s, 7.75, 1.5, 4.95, 2.9, "claim");
  heading(s, "OUR CLAIM", 8.05, 1.7, 4, HEX.green);
  s.addText("An authentication-aware heterogeneous graph of runtime behaviour, with GNN detection of credential flows, compared with rules, flat ML and homogeneous GNNs under extension-level and unseen-flow splits.",
    { x: 8.05, y: 2.1, w: 4.4, h: 2.2, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  card(s, 7.75, 4.55, 4.95, 2.15, "not-claim");
  heading(s, "WE DO NOT CLAIM", 8.05, 4.7, 4, HEX.amber);
  bullets(s, ["the first extension graph or detector", "the first GNN in browser security", "any result on real-world extensions (NOT YET MEASURED)"], 8.05, 5.1, 4.4, 1.5, { size: 14, gap: 5 });
  s.addNotes("POSITIONING (60 s). Be explicit about what is not new. DoubleX and Arcanum are the closest prior art: one static, one dynamic. Graph-based malware detection with heterogeneous GNNs is established. " +
    "What this project adds is narrower and testable: an authentication-aware graph representation and a controlled comparison against baselines, specifically under unseen flow patterns and with taint lost across the Wasm boundary. " +
    "Two references (MalSage, the Electronics Wasm paper) were found through search snippets; they should be read in full before a formal citation. Say that if asked.");

  // ================================================================ 5 SAFETY
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Context" });
  title(s, "A safe lab: nothing leaves localhost");
  const safe = [
    ["globe", "Localhost only", "App on :5000, collector and sink hosts on *.lab.localhost:5001 and 127.0.0.1. No external network."],
    ["lock", "Synthetic credentials", "Fresh random cookie and JWT per login. Telemetry stores only a hashed ID, never a value."],
    ["flask", "Controlled behaviours", "Proof-of-concept extensions exist only to produce labelled telemetry. No persistence, no real malware."],
    ["scale", "Label by design", "Suspicious = credential-derived data sent to an unapproved destination. Fixed by scenario, not by a detector."],
  ];
  safe.forEach(([k, h, t], i) => {
    const x = MX + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 2.55;
    card(s, x, y, 5.95, 2.3, "safe-card"); ic(s, k, x + 0.3, y + 0.3, 0.55);
    s.addText(h, { x: x + 1.05, y: y + 0.3, w: 4.6, h: 0.55, fontSize: 20, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    s.addText(t, { x: x + 0.3, y: y + 1.05, w: 5.35, h: 1.1, fontSize: 16, color: C.text2, valign: "top", margin: 0, isTextBox: true });
  });
  s.addNotes("THREAT MODEL AND SAFETY (45 s). All 'attacks' are controlled proof-of-concept behaviours inside an isolated browser profile against a local Flask app. " +
    "No real user, site, cookie or token is ever involved, and the collector stores only body length and a short hash. " +
    "We verified this: a search for the token strings in all 7,258 telemetry events found zero. The ground-truth label is a property of the scenario design, which matters for how we interpret the rule baselines later.");

  // ================================================================ 6 ARCHITECTURE
  pres.addSection({ title: "Method" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  title(s, "System: from a real browser event to an explained verdict");
  const stages = [
    ["db", "Controlled lab", "Flask auth app with synthetic cookie/JWT; collector and sink hosts", HEX.teal],
    ["puzzle", "Real Chromium", "Generated MV3 extensions use chrome.cookies, storage, DOM, fetch and WebAssembly", HEX.blue],
    ["net", "Telemetry JSONL", "Hashed credential IDs; server-log cross-check of every request", HEX.amber],
    ["graph", "Heterogeneous graph", "11 node types, 17 relations; taint edges kept separable", HEX.green],
    ["chip", "Detectors", "Rules, RF, MLP, GCN, GraphSAGE, R-GCN; 10-model ensembles", HEX.purple],
    ["search", "Explanation", "Occlusion importance and the highlighted credential-to-sink path", HEX.red],
  ];
  const bw = 1.82, bg = 0.236;
  stages.forEach(([k, h, t, c], i) => {
    const x = MX + i * (bw + bg);
    card(s, x, 2.0, bw, 3.55, "stage");
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.51, y: 2.25, w: 0.8, h: 0.8, fill: { color: c, transparency: 80 }, line: { color: c, width: 1.25 }, objectName: "icon-bg" });
    ic(s, k, x + 0.66, 2.4, 0.5);
    s.addText(h, { x: x + 0.1, y: 3.2, w: bw - 0.2, h: 0.6, fontSize: 15, bold: true, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(t, { x: x + 0.12, y: 3.85, w: bw - 0.24, h: 1.6, fontSize: 13, color: C.text2, align: "center", valign: "top", margin: 0, isTextBox: true });
    if (i < stages.length - 1) arrow(s, x + bw + 0.03, 3.78, bg - 0.06, C.text2);
  });
  s.addText("Everything on localhost  ·  synthetic credentials only  ·  graph + verdict + path shown live in the dashboard",
    { x: MX, y: 6.0, w: 12.1, h: 0.4, fontSize: 15, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  s.addNotes("ARCHITECTURE (60 s). Walk left to right. The lab generates extensions; each one is a real Manifest V3 extension loaded into Chromium via Playwright, performing real chrome.cookies, storage, DOM, fetch and WebAssembly calls. " +
    "Telemetry is written as JSONL with hashed credential IDs, and every request is cross-checked against a server-side log. A graph builder converts each session into a typed graph; detectors score it; an occlusion explainer returns the path. " +
    "Honest limitation to mention: the telemetry is self-reported by instrumented lab extensions, not captured at browser level the way Arcanum does.");

  // ================================================================ 7 DATASET
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  title(s, "Dataset: 576 real sessions, hard negatives included");
  stat(s, MX, 1.5, 2.0, 1.45, "576", "sessions", HEX.teal); stat(s, MX + 2.15, 1.5, 2.0, 1.45, "144", "extensions", HEX.teal);
  stat(s, MX + 4.3, 1.5, 2.0, 1.45, "288 / 288", "benign / suspicious", HEX.green, 26); stat(s, MX + 6.45, 1.5, 2.0, 1.45, "7,258", "events captured", HEX.amber);
  card(s, MX, 3.15, 8.45, 3.55, "integrity");
  heading(s, "INTEGRITY CHECKS (EVERY RUN)", MX + 0.3, 3.3, 6);
  const chk = [["0", "credential-value leaks in any event"], ["0", "events failing the schema"], ["0", "duplicate events"], ["576 / 576", "sessions where telemetry matches the server log"]];
  chk.forEach(([v, l], i) => {
    const y = 3.8 + i * 0.7; ic(s, "check", MX + 0.3, y + 0.04, 0.4);
    s.addText(v, { x: MX + 0.9, y, w: 1.7, h: 0.5, fontSize: 22, bold: true, color: HEX.green, valign: "middle", margin: 0, isTextBox: true });
    s.addText(l, { x: MX + 2.65, y, w: 5.6, h: 0.5, fontSize: 16, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  });
  const trow = (a, b, c) => [{ text: a, options: { color: c, bold: true } }, { text: b, options: { color: HEX.text } }];
  const fam = [["B1", "DOM only"], ["B2", "storage settings"], ["B3", "approved API"], ["B4", "authenticated call to approved API (hard negative)"], ["B5", "credential read + unrelated analytics (hard negative)"], ["B6", "benign WebAssembly"],
    ["S1", "direct credential to sink"], ["S2", "via 1–3 JS hops"], ["S3", "via WebAssembly"], ["S4", "content script ↔ service worker"], ["S5", "staged through storage"], ["S6", "chunked to a raw-IP sink"]];
  s.addTable(fam.map(([a, b]) => trow(a, b, a[0] === "B" ? HEX.green : HEX.red)),
    { x: 9.25, y: 1.5, w: 3.45, colW: [0.55, 2.9], fontSize: 11, border: { type: "none" }, fill: { color: C.background2 }, valign: "middle", rowH: 0.4, margin: [0.03, 0.08, 0.03, 0.08] });
  s.addText("Wasm output loses its taint tag with probability 0.5 (a design choice modelling a JS-level tracker). Result: 254 suspicious sessions have taint visible at the sink, 34 have it lost.",
    { x: 9.25, y: 6.4, w: 3.45, h: 0.55, fontSize: 10, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("DATASET (60 s). 12 scenario families, 12 generated extensions each, 4 sessions per extension, all run in real Chromium. Six benign families and six controlled-suspicious families. " +
    "Two benign families are deliberate hard negatives: B4 reads a credential and sends it to the approved API, B5 reads a credential but sends only unrelated data to an analytics host. " +
    "The integrity panel is measured: no credential value in any event, no schema failures, and the number of requests in telemetry equals the server log in every session. " +
    "One design choice you must disclose: with probability 0.5 the Wasm output loses its taint tag, modelling a JS-level tracker that cannot see inside Wasm. That gives 34 taint-lost suspicious sessions.");

  // ================================================================ 8 GRAPH
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  title(s, "An authentication-aware graph of each session");
  const gimg = fitImg(s, "c_graph_only.jpg", MX, 1.5, 8.1, 5.25, "graph-screenshot");
  card(s, 9.0, 1.5, 3.7, 5.2, "graph-facts");
  heading(s, "REPRESENTATION", 9.3, 1.7, 3.2);
  bullets(s, [`11 node types: extension, content script, service worker, JS, Wasm, API, credential, storage, request, domain, page`,
    "17 relations, including flows_cred and carries (taint) that can be ablated",
    `Mean ${D.dataset.nodes_mean.toFixed(1)} nodes and ${D.dataset.edges_mean.toFixed(1)} edges per session`,
    "No names or scenario labels used as features"], 9.3, 2.15, 3.2, 4.4, { size: 14, gap: 8 });
  s.addNotes("GRAPH (60 s). Each session becomes a heterogeneous graph: components such as the content script and service worker, JavaScript and Wasm modules, browser APIs, credentials, storage objects, requests and destination domains. " +
    "Orange is the credential; the red path is what the explainer highlights: credential to request to an unapproved domain. " +
    "Taint information is represented by two dedicated relations, flows_cred and carries, so we can remove them in an ablation and see how much the structure alone contributes. " +
    "Domain nodes only carry 'approved' and 'is an IP'; no extension names, module names or scenario labels leak into the features.");

  // ================================================================ 9 PROTOCOL
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  title(s, "Experimental protocol: built to avoid fooling ourselves");
  const cols = [
    ["DETECTORS", HEX.teal, ["Rule R1: credential accessed AND unapproved request", "Rule R2: unapproved request carrying a credential taint tag", "Random Forest and MLP on count features", "GCN, GraphSAGE, R-GCN in plain PyTorch", "10-model ensembles for the dashboard scores"]],
    ["SPLITS", HEX.green, ["Extension-level: all sessions of an extension stay in one split", "5 split seeds, mean ± std", "Unseen flow: hold out Wasm families (S3 + S5) entirely", "Leave-one-family-out for S1 to S6"]],
    ["RIGOR", HEX.amber, ["Validation-only tuning, identical grid for all GNNs", "Test sets never used for any choice", "Threshold 0.5, not tuned", "Every run logged; the untuned v1 run is kept", "NumPy Random Forest (a local policy blocked sklearn's tree module)"]],
  ];
  cols.forEach(([h, c, items], i) => {
    const x = MX + i * 4.1; card(s, x, 1.5, 3.9, 5.2, "protocol");
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 1.75, w: 0.18, h: 0.18, fill: { color: c }, line: { color: c, width: 0 }, objectName: "dot" });
    s.addText(h, { x: x + 0.6, y: 1.65, w: 3, h: 0.4, fontSize: 14, bold: true, color: c, charSpacing: 2, valign: "middle", margin: 0, isTextBox: true });
    bullets(s, items, x + 0.3, 2.3, 3.4, 4.3, { size: 16, gap: 12 });
  });
  s.addNotes("PROTOCOL (60 s). Three rules guard against self-deception. First, no leakage: the split is by extension, so no extension appears in both train and test, and unseen-flow tests withhold whole scenario families. " +
    "Second, fair tuning: all three GNNs get the same validation-only grid; the test sets are never touched. Third, nothing hidden: every run is in experiments.csv and the first untuned run is kept alongside the tuned one. " +
    "Disclose: scikit-learn's tree module was blocked by a local Windows policy, so the Random Forest is a small NumPy implementation; we did not bypass the policy. Std over five splits understates uncertainty because test sets overlap across seeds.");

  // ================================================================ 10 STANDARD SPLIT
  pres.addSection({ title: "Results" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  title(s, "Standard split: easy when taint is visible");
  s.addChart(pres.charts.BAR, [{ name: "F1", labels: ORDER.map((m) => SHORT[m]), values: ORDER.map((m) => +M[m].f1.toFixed(3)) }],
    { ...chartBase(), x: MX, y: 1.45, w: 8.2, h: 5.3, barDir: "col", chartColors: ORDER.map((m) => MCOL[m]), showValue: true, dataLabelFormatCode: "0.000", dataLabelPosition: "outEnd",
      valAxisMinVal: 0.8, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0.00", showLegend: false, barGapWidthPct: 45,
      showTitle: true, title: "F1 on held-out extensions (mean of 5 splits; axis starts at 0.80)", titleColor: "C3CedB", titleFontSize: 13 });
  card(s, 9.1, 1.45, 3.6, 5.3, "std-notes");
  heading(s, "HOW TO READ THIS", 9.4, 1.65, 3);
  bullets(s, [`RF and MLP on simple counts already reach F1 ${f2(M["RF (counts)"].f1)} and ${f2(M["MLP (counts)"].f1)}`,
    `GraphSAGE is best: F1 ${f3(M["GraphSAGE"].f1)}, ROC-AUC ${f3(M["GraphSAGE"].roc_auc)}`,
    `Rule R1 flags ${pct(M["Rule R1 (co-occurrence)"].fpr, 1)} of benign sessions`,
    `R-GCN is lowest of the learned models: ${f3(M["R-GCN"].f1)}`,
    "This split does not separate the methods, so the unseen-flow test matters"], 9.4, 2.1, 3.1, 4.5, { size: 14, gap: 8 });
  s.addNotes("RESULT 1 (60 s). On the standard extension-level split, almost everything works, because when taint is visible the task is nearly trivial: even a Random Forest on counts gets 0.98. " +
    "GraphSAGE is the best learned model at 0.988. Rule R1, the 'credential plus unapproved request' co-occurrence rule, gets perfect recall but flags 16.7% of benign sessions. " +
    "R-GCN trails at 0.904. The honest reading: this split does not discriminate between methods. That is why the next two slides, unseen flows and taint-lost sessions, are the informative tests. " +
    "Note the axis starts at 0.80 to make differences visible; say so.");

  // ================================================================ 11 UNSEEN WASM
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  title(s, "Never-seen Wasm flows: graph structure still detects them");
  const ucats = ORDER.map((m) => SHORT[m]);
  s.addChart(pres.charts.BAR, [
    { name: "Recall on never-seen flows", labels: ucats, values: ORDER.map((m) => +U[m].recall.toFixed(3)) },
    { name: "False-positive rate", labels: ucats, values: ORDER.map((m) => +U[m].fpr.toFixed(3)) }],
    { ...chartBase(), x: MX, y: 1.45, w: 8.4, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.teal, HEX.red], showValue: true, dataLabelFormatCode: "0.00",
      dataLabelPosition: "outEnd", dataLabelFontSize: 10, valAxisMinVal: 0, valAxisMaxVal: 1.1, valAxisMajorUnit: 0.25, valAxisLabelFormatCode: "0.00", showLegend: true, legendPos: "b", barGapWidthPct: 40,
      showTitle: true, title: "Wasm flows (S3 + S5) removed from training; mean of 5 splits", titleColor: "C3CedB", titleFontSize: 13 });
  card(s, 9.3, 1.45, 3.4, 5.3, "unseen-notes");
  heading(s, "THE RESEARCH MOMENT", 9.55, 1.65, 3, HEX.green);
  s.addText(f3(U["GraphSAGE"].recall), { x: 9.55, y: 2.05, w: 3, h: 0.9, fontSize: 52, bold: true, color: HEX.teal, margin: 0, valign: "middle", isTextBox: true });
  s.addText(`GraphSAGE recall at ${pct(U["GraphSAGE"].fpr, 1)} false positives`, { x: 9.55, y: 2.95, w: 3, h: 0.6, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  bullets(s, [`Taint rule R2: ${f3(U["Rule R2 (taint)"].recall)}, because taint is lost inside Wasm`, `Flat models: ${f2(U["MLP (counts)"].recall)}–${f2(U["RF (counts+reachability)"].recall)}`,
    `Rule R1 reaches ${f2(U["Rule R1 (co-occurrence)"].recall)} recall but with ${pct(U["Rule R1 (co-occurrence)"].fpr, 1)} false positives`, `R-GCN: ${f3(U["R-GCN"].recall)}`],
    9.55, 3.7, 3.0, 3.0, { size: 13, gap: 6 });
  s.addNotes("RESULT 2 — THE RESEARCH MOMENT (90 s). We removed every Wasm-involving suspicious family, S3 and S5, from training. The test is 96 never-seen suspicious sessions plus 48 benign ones from unseen extensions. " +
    "GraphSAGE still detects 93% at a 3.7% false-positive rate. The taint rule only reaches 65%, because the taint tag is lost inside Wasm. Flat count-based models reach 62 to 69%. " +
    "Rule R1 has perfect recall but only because it flags every session that touches a credential and an unapproved host, which is why its false-positive rate is 16.7%. " +
    "Then, unprompted: our proposed R-GCN reached only 0.45. Do not oversell the 0.93: this is one synthetic distribution and five overlapping splits.");

  // ================================================================ 12 LOFO + TAINT LOST
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  title(s, "Leave-one-family-out, and the taint-lost sessions");
  const S3 = D.unseen.loso_S3_cred_wasm_sink, S5 = D.unseen.loso_S5_staged_multi_component;
  const mods = ["Rule R2 (taint)", "RF (counts)", "MLP (counts)", "GCN", "GraphSAGE", "R-GCN"];
  s.addChart(pres.charts.BAR, [
    { name: "Leave out S3 (credential via Wasm)", labels: mods.map((m) => SHORT[m]), values: mods.map((m) => +S3[m].recall.toFixed(3)) },
    { name: "Leave out S5 (staged multi-component)", labels: mods.map((m) => SHORT[m]), values: mods.map((m) => +S5[m].recall.toFixed(3)) }],
    { ...chartBase(), x: MX, y: 1.45, w: 7.6, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.purple, HEX.amber], showValue: true, dataLabelFormatCode: "0.00", dataLabelPosition: "outEnd",
      dataLabelFontSize: 10, valAxisMinVal: 0, valAxisMaxVal: 1.1, valAxisMajorUnit: 0.25, valAxisLabelFormatCode: "0.00", showLegend: true, legendPos: "b", barGapWidthPct: 40,
      showTitle: true, title: "Recall on the held-out suspicious family (mean of 5 splits)", titleColor: "C3CedB", titleFontSize: 13 });
  const V = D.taint_visibility;
  card(s, 8.45, 1.45, 4.25, 5.3, "taint-lost");
  heading(s, "TAINT LOST INSIDE WASM", 8.75, 1.65, 3.8, HEX.amber);
  s.addText(`n = ${V["Rule R2 (taint)"].n_lost} suspicious test sessions`, { x: 8.75, y: 2.0, w: 3.7, h: 0.35, fontSize: 13, color: C.text2, margin: 0, isTextBox: true });
  const tl = [["Rule R2 (taint)", HEX.red], ["RF (counts)", HEX.amber], ["GraphSAGE", HEX.teal], ["R-GCN", HEX.purple]];
  tl.forEach(([m, c], i) => {
    const y = 2.5 + i * 0.85;
    s.addText(pct(V[m].lost), { x: 8.75, y, w: 1.55, h: 0.7, fontSize: 30, bold: true, color: c, margin: 0, valign: "middle", isTextBox: true });
    s.addText(m.replace(" (taint)", " (taint rule)"), { x: 10.35, y, w: 2.2, h: 0.7, fontSize: 14, color: C.text1, margin: 0, valign: "middle", isTextBox: true });
  });
  s.addText("Detection rate on these sessions. A taint rule cannot see them at all.", { x: 8.75, y: 6.0, w: 3.7, h: 0.6, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("RESULT 3 (60 s). Leaving out only S3 (credential via Wasm) or only S5 (staged across components) tells the same story: GraphSAGE generalises, the taint rule and flat models are less reliable, and R-GCN struggles. " +
    "The right panel is the sharpest evidence for why a graph helps: in the 25 test sessions where taint was lost inside Wasm, Rule R2 detects none by construction, while GraphSAGE detects all of them. " +
    "Caveat: part of that advantage may be dataset regularities, such as a credential connected to an unapproved domain in a small graph, which real extensions would not respect.");

  // ================================================================ 13 ABLATION
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  title(s, "Ablation: which information actually matters");
  const A = D.ablation, amodes = [["full", "Full graph"], ["no_auth", "− auth nodes"], ["no_jswasm", "− JS/Wasm nodes"], ["no_dest", "− destinations"], ["no_taint", "− taint edges"]];
  const am = ["GraphSAGE", "RF (counts)", "R-GCN"];
  s.addChart(pres.charts.BAR, am.map((m) => ({ name: m, labels: amodes.map((a) => a[1]), values: amodes.map((a) => +A[a[0]][m].toFixed(3)) })),
    { ...chartBase(), x: MX, y: 1.45, w: 8.3, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.teal, HEX.amber, HEX.purple], showValue: true, dataLabelFormatCode: "0.00", dataLabelPosition: "outEnd",
      dataLabelFontSize: 10, valAxisMinVal: 0.75, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0.00", showLegend: true, legendPos: "b", barGapWidthPct: 40,
      showTitle: true, title: "F1 after removing information (mean of 5 splits; axis starts at 0.75)", titleColor: "C3CedB", titleFontSize: 13 });
  card(s, 9.2, 1.45, 3.5, 5.3, "abl-notes");
  heading(s, "WHAT THE DATA SAY", 9.5, 1.65, 3);
  bullets(s, [`Destinations matter most: GraphSAGE F1 ${f3(A.full.GraphSAGE)} → ${f3(A.no_dest.GraphSAGE)}`, `Auth nodes next: → ${f3(A.no_auth.GraphSAGE)}`,
    `Taint edges help: → ${f3(A.no_taint.GraphSAGE)}, yet the structure alone keeps most of the signal`, `JS/Wasm nodes barely change GraphSAGE (${f3(A.no_jswasm.GraphSAGE)})`],
    9.5, 2.1, 3.0, 4.5, { size: 14, gap: 9 });
  s.addNotes("ABLATION (45 s). We removed one kind of information at a time and retrained everything. Removing destination information hurts the most, and removing credential nodes hurts next: the model genuinely uses the destination and the authentication context. " +
    "Taint edges help by about four F1 points for GraphSAGE, but without them it still reaches 0.948, so structure alone carries a lot. Removing the JS and Wasm nodes barely changes GraphSAGE. " +
    "Be careful to state that the y-axis starts at 0.75; all models are high on this standard split.");

  // ================================================================ 14 R-GCN NEGATIVE
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  title(s, "The honest negative: our proposed R-GCN lost");
  const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.teal, fill: { color: C.background2 }, align: "center" } });
  const cell = (t, c, b) => ({ text: t, options: { color: c || HEX.text, align: "center", bold: !!b } });
  s.addTable([
    [hdr(""), hdr("Parameters"), hdr("Standard split F1"), hdr("Unseen Wasm recall")],
    [cell("R-GCN, untuned (v1)", HEX.muted), cell("349,058", HEX.muted), cell("0.904", HEX.muted), cell("0.263", HEX.muted)],
    [cell("R-GCN, validation-tuned (v2)", HEX.purple, true), cell(M["R-GCN"].params.toLocaleString("en-US"), HEX.purple, true), cell(f3(M["R-GCN"].f1), HEX.purple, true), cell(f3(U["R-GCN"].recall), HEX.purple, true)],
    [cell("GraphSAGE", HEX.teal, true), cell(M["GraphSAGE"].params.toLocaleString("en-US"), HEX.teal, true), cell(f3(M["GraphSAGE"].f1), HEX.teal, true), cell(f3(U["GraphSAGE"].recall), HEX.teal, true)],
  ], { x: MX, y: 1.55, w: 12.1, colW: [4.0, 2.6, 2.7, 2.8], fontSize: 16, border: { type: "solid", color: "22314A", pt: 0.75 }, fill: { color: C.background2 }, rowH: 0.55, valign: "middle", margin: 0.08 });
  card(s, MX, 4.05, 5.9, 2.65, "why");
  heading(s, "HYPOTHESES (NOT YET TESTED)", MX + 0.3, 4.2, 5, HEX.amber);
  bullets(s, ["Under-converged: on 2 of 5 splits the best epoch was 10 and 21 with train loss near 0.2", "Per-relation weights may transfer poorly to unseen relation combinations with about 350 training graphs"],
    MX + 0.3, 4.65, 5.3, 2.0, { size: 14, gap: 8 });
  card(s, 6.8, 4.05, 5.9, 2.65, "what-we-did");
  heading(s, "WHAT WE DID NOT DO", 7.1, 4.2, 5, HEX.green);
  bullets(s, ["Tune anything on the test sets", "Hide the first run: results/v1_untuned/ is kept", "Move the goalposts: the unseen-flow headline is GraphSAGE"], 7.1, 4.65, 5.3, 2.0, { size: 14, gap: 8 });
  s.addNotes("NEGATIVE RESULT (60 s). We expected the heterogeneous R-GCN to win. It did not, in either run. The untuned version had 349 thousand parameters; after a validation-only search with basis decomposition it has 5.5 thousand, and it is still worse than GraphSAGE. " +
    "The diagnosis is a hypothesis, not a finding: on two of five splits it stopped at epoch 10 and 21 with training loss still near 0.2, and per-relation weights may not transfer to relation combinations never seen in training with only about 350 graphs. " +
    "We did not tune on the test data, we kept the untuned run, and we did not rewrite the story around the model we wished had won. That is the point of reporting it.");

  // ================================================================ 15 EXPLAINABILITY
  pres.addSection({ title: "Trust and demo" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Trust and demo" });
  title(s, "Explainability: the path that triggered the verdict");
  fitImg(s, "c_explain_graph.jpg", MX, 1.45, 6.6, 4.25, "explain-graph");
  card(s, 7.45, 1.45, 5.25, 1.75, "verdict-explain");
  s.addShape(pres.ShapeType.roundRect, { x: 7.45, y: 1.45, w: 0.12, h: 1.75, rectRadius: 0.06, fill: { color: HEX.red }, line: { color: HEX.red, width: 0 }, objectName: "verdict-edge" });
  s.addText("SUSPICIOUS", { x: 7.8, y: 1.55, w: 2.7, h: 0.6, fontSize: 28, bold: true, color: HEX.red, margin: 0, valign: "middle", isTextBox: true });
  s.addText("confidence ≥99.3%", { x: 10.2, y: 1.55, w: 2.35, h: 0.6, fontSize: 16, bold: true, color: C.text1, align: "right", margin: 0, valign: "middle", isTextBox: true });
  s.addText("550 of 550 held-out sessions in this score band were correct", { x: 7.8, y: 2.3, w: 4.75, h: 0.75, fontSize: 14, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  card(s, 7.45, 3.4, 5.25, 2.3, "path-explain");
  heading(s, "HIGHLIGHTED ATTACK PATH", 7.75, 3.55, 4.5, HEX.red);
  chip(s, 7.75, 4.05, 2.35, "jwt_localstorage:6c988e", "FB923C"); arrow(s, 10.13, 4.36, 0.3, HEX.red); chip(s, 10.45, 4.05, 1.95, "POST /b", HEX.purple);
  chip(s, 7.75, 4.95, 3.3, "stats.lab.localhost:5001", HEX.green);
  s.addText("credential → request → unapproved sink", { x: 11.15, y: 4.95, w: 1.5, h: 0.62, fontSize: 11, color: C.text2, margin: 0, valign: "middle", isTextBox: true });
  card(s, MX, 5.85, 12.1, 0.95, "how-explain");
  s.addText([{ text: "How it works. ", options: { bold: true, color: HEX.teal } },
    { text: "Remove one node or edge, re-score, and measure the drop in log-odds; the path is the highest-importance route from credential to domain. A saturated score falls back to a labelled structural path. ", options: {} },
    { text: "Faithfulness vs ground-truth paths: NOT YET MEASURED.", options: { color: HEX.amber, bold: true } }],
    { x: MX + 0.3, y: 5.9, w: 11.5, h: 0.85, fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("EXPLAINABILITY (60 s). The system does not just say 'suspicious'. It removes each node and edge in turn, re-scores the graph, and reports how much the log-odds fall. " +
    "The red path in the screenshot is the highest-importance route from the credential, through the POST request, to the unapproved sink. " +
    "Two honesty points: importance is occlusion on the model output, not attention weights; and when the score is saturated and no single removal matters, the dashboard shows a structural shortest path and says so. " +
    "We have not measured how faithful these explanations are against known ground-truth paths. That is future work.");

  // ================================================================ 16 CONFIDENCE
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Trust and demo" });
  title(s, "A confidence score you can believe");
  const cs = D.calibration;
  s.addChart(pres.charts.BAR, [
    { name: "Single model", labels: ["GraphSAGE", "R-GCN"], values: [+(cs["GraphSAGE"].single.frac_conf_ge_999 * 100).toFixed(0), +(cs["R-GCN"].single.frac_conf_ge_999 * 100).toFixed(0)] },
    { name: "10-model ensemble", labels: ["GraphSAGE", "R-GCN"], values: [+(cs["GraphSAGE"].ensemble.frac_conf_ge_999 * 100).toFixed(0), +(cs["R-GCN"].ensemble.frac_conf_ge_999 * 100).toFixed(0)] }],
    { ...chartBase(), x: MX, y: 1.5, w: 4.6, h: 3.4, barDir: "col", barGrouping: "clustered", chartColors: [HEX.grey, HEX.teal], showValue: true, dataLabelFormatCode: '0"%"', dataLabelPosition: "outEnd",
      valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"', showLegend: true, legendPos: "b", barGapWidthPct: 50,
      showTitle: true, title: "Sessions scoring ≥ 99.9%", titleColor: "C3CedB", titleFontSize: 13 });
  const th = (t) => ({ text: t, options: { bold: true, color: HEX.teal, align: "center", fill: { color: C.background2 } } });
  const td = (t, c) => ({ text: t, options: { color: c || HEX.text, align: "center" } });
  const crow = (arch, m, lab, col) => [td(arch, HEX.text), td(lab, col), td(f3(cs[arch][m].ece), col), td(f3(cs[arch][m].nll), col), td(f3(cs[arch][m].brier), col)];
  s.addTable([[th("Detector"), th("Model"), th("ECE"), th("Log-loss"), th("Brier")], crow("GraphSAGE", "single", "single", HEX.muted), crow("GraphSAGE", "ensemble", "ensemble", HEX.teal),
    crow("R-GCN", "single", "single", HEX.muted), crow("R-GCN", "ensemble", "ensemble", HEX.purple)],
    { x: MX, y: 5.05, w: 4.6, colW: [1.0, 0.95, 0.8, 1.0, 0.85], fontSize: 12, border: { type: "solid", color: "22314A", pt: 0.5 }, fill: { color: C.background2 }, rowH: 0.34, valign: "middle", margin: 0.04 });
  // the verdict card as the dashboard shows it
  card(s, 5.5, 1.5, 7.2, 2.35, "verdict-demo");
  s.addShape(pres.ShapeType.roundRect, { x: 5.5, y: 1.5, w: 0.12, h: 2.35, rectRadius: 0.06, fill: { color: HEX.red }, line: { color: HEX.red, width: 0 }, objectName: "verdict-edge" });
  s.addText("SUSPICIOUS", { x: 5.9, y: 1.65, w: 3.6, h: 0.6, fontSize: 30, bold: true, color: HEX.red, margin: 0, valign: "middle", isTextBox: true });
  s.addText("confidence ≥99.3%", { x: 9.3, y: 1.65, w: 3.2, h: 0.6, fontSize: 20, bold: true, color: C.text1, align: "right", margin: 0, valign: "middle", isTextBox: true });
  s.addText("Observed 100.0% correct (95% interval 99.3–100.0%): 550 of 550 held-out sessions in this score band.", { x: 5.9, y: 2.4, w: 6.6, h: 0.9, fontSize: 14, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  s.addText("The card quotes the 95% lower bound of observed accuracy. It never prints 100%.", { x: 5.9, y: 3.25, w: 6.6, h: 0.5, fontSize: 13, color: HEX.teal, margin: 0, valign: "top", isTextBox: true });
  card(s, 5.5, 4.05, 3.5, 2.75, "conf-how");
  heading(s, "HOW IT IS BUILT", 5.75, 4.2, 3);
  bullets(s, ["10 independently seeded models, scores averaged", "576 out-of-fold predictions from unseen extensions", "Bands pooled so a higher score never shows lower confidence"], 5.75, 4.6, 3.05, 2.1, { size: 12, gap: 5 });
  const wt = D.calibration_test["R-GCN_heldout_wasm_flows"];
  card(s, 9.2, 4.05, 3.5, 2.75, "conf-caveat");
  heading(s, "CAVEAT", 9.45, 4.2, 3, HEX.amber);
  s.addText(`On never-seen flows, R-GCN reports confidence of about ${pct(wt.mean_conf)} while being ${pct(wt.accuracy)} accurate (ECE ${f3(wt.ece)}). Its confidence is not trustworthy there; the dashboard warns.`,
    { x: 9.45, y: 4.6, w: 3.05, h: 2.1, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("CONFIDENCE (75 s). A raw softmax from one small network saturates near 100%, which is not believable. We tried temperature scaling, Platt scaling and binning on the single model, cross-fitted on 576 out-of-fold predictions, and none beat the raw scores. " +
    "What does help is an ensemble: averaging ten independently trained models lowers log-loss and Brier for both architectures, and the share of sessions scoring 99.9% or more drops from 90% to 69% for GraphSAGE and from 45% to 8% for R-GCN. ECE improves for GraphSAGE and is about the same for R-GCN. " +
    "The dashboard then quotes the 95% lower bound of the accuracy actually observed in the score band, so GraphSAGE's top band, 550 of 550 correct, reads 'at least 99.3%'. " +
    "State the caveat: on never-seen flow families R-GCN's confidence is badly off, ECE 0.287 at 61% accuracy, and bands come from the same synthetic dataset.");

  // ================================================================ 17 DEMO
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Trust and demo" });
  title(s, "Live demo: event to graph to verdict, in a real browser");
  const d1 = fitImg(s, "c_replay.jpg", MX, 1.5, 6.0, 3.65, "demo-replay");
  const d2 = fitImg(s, "c_live_wasm.jpg", 6.85, 1.5, 5.85, 3.65, "demo-live");
  s.addText("Session Replay: events arrive, the graph grows, the verdict appears when the session completes", { x: MX, y: 5.2, w: 6.0, h: 0.55, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  s.addText("Live Lab Run: a freshly generated extension in real Chromium, classified on the spot", { x: 6.85, y: 5.2, w: 5.85, h: 0.55, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  card(s, MX, 5.85, 12.1, 0.95, "demo-steps");
  s.addText([{ text: "3-minute path:  ", options: { bold: true, color: HEX.teal } }, { text: "1 benign authenticated call → BENIGN   2 Wasm exfiltration → SUSPICIOUS + path   3 unseen-flow chart   4 comparison table", options: {} }],
    { x: MX + 0.3, y: 5.9, w: 11.5, h: 0.85, fontSize: 15, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("DEMO (3 min). Open the dashboard. Step 1: Live Lab Run, scenario 1 'Authenticated API Call'. The system generates a brand-new extension, runs it in real Chromium, and shows BENIGN with no flagged path. " +
    "Step 2: scenario 3, 'Credential via WebAssembly', which shows SUSPICIOUS with the red credential-to-sink path and the confidence card. Step 3: Unseen-Flow and Ablation page for the research chart. Step 4: Model Comparison. " +
    "If a live run misses, say so; do not re-roll until it looks good. Session Replay is the fallback: press Play and watch the graph build and the verdict appear at the end. " +
    "While a session is still in progress the card says 'OBSERVING' with a provisional risk number; verdict and confidence appear only for complete sessions.");

  // ================================================================ 18 LIMITS + NEXT
  pres.addSection({ title: "Wrap-up" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wrap-up" });
  title(s, "Limitations, and what comes next");
  card(s, MX, 1.5, 6.0, 5.25, "limits"); heading(s, "LIMITATIONS", MX + 0.3, 1.7, 5, HEX.amber);
  bullets(s, ["Telemetry is self-reported by instrumented lab extensions, not captured at browser level", "A generator with a small step vocabulary, not real extensions", "Label defined by construction; the Wasm taint-drop rate (0.5) is our choice",
    "One dataset of 576 sessions; the 5 splits overlap", "No adaptive adversary", "Latency is offline CPU inference, not a deployed monitor"], MX + 0.3, 2.15, 5.45, 4.5, { size: 16, gap: 11 });
  card(s, 6.7, 1.5, 6.0, 5.25, "next"); heading(s, "NEXT STEPS (NOT IMPLEMENTED)", 7.0, 1.7, 5, HEX.green);
  bullets(s, ["Browser-level capture (CDP, Arcanum-style) instead of self-reporting", "A corpus of real extensions", "Adversarial and evasion evaluation", "Understand and fix R-GCN: longer training, edge-type regularisation", "Explanation faithfulness against known flows", "Streaming, real-time deployment"], 7.0, 2.15, 5.45, 4.5, { size: 16, gap: 11 });
  s.addNotes("LIMITATIONS AND NEXT STEPS (60 s). The biggest limitation is realism: our extensions are generated from a small vocabulary and report their own telemetry, so results demonstrate the method on a controlled distribution, not detection rates on real malware. " +
    "The Wasm taint-drop rate is a design parameter, not a measured property of real trackers. The next steps that would change the conclusions most are browser-level telemetry and real extensions, then an adversary who adapts to the detector.");

  // ================================================================ 19 CONCLUSION
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wrap-up" });
  title(s, "Conclusion");
  const cons = [
    ["bolt", "It works end to end", "Real browser events become an authentication-aware graph, a verdict, a confidence and an explained path, live."],
    ["graph", "Structure helps when instrumentation fails", `GraphSAGE caught ${pct(V["GraphSAGE"].lost)} of the taint-lost Wasm sessions and ${f3(U["GraphSAGE"].recall)} of never-seen Wasm flows. A taint rule caught none of the former.`],
    ["scale", "We report what lost", `R-GCN did not beat GraphSAGE (${f3(U["R-GCN"].recall)} vs ${f3(U["GraphSAGE"].recall)}). The untuned run, the failed calibrators and the limits are all documented.`],
  ];
  cons.forEach(([k, h, t], i) => {
    const y = 1.5 + i * 1.75; card(s, MX, y, 12.1, 1.55, "concl");
    s.addShape(pres.ShapeType.ellipse, { x: MX + 0.35, y: y + 0.4, w: 0.75, h: 0.75, fill: { color: HEX.teal, transparency: 82 }, line: { color: HEX.teal, width: 1.25 }, objectName: "icon-bg" });
    ic(s, k, MX + 0.5, y + 0.55, 0.45);
    s.addText(h, { x: MX + 1.4, y: y + 0.15, w: 10.4, h: 0.5, fontSize: 22, bold: true, color: C.text1, margin: 0, valign: "middle", isTextBox: true });
    s.addText(t, { x: MX + 1.4, y: y + 0.7, w: 10.4, h: 0.75, fontSize: 15, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  });
  s.addText("Everything shown is reproducible from the repository; every number comes from an executed run.", { x: MX, y: 6.75, w: 12.1, h: 0.3, fontSize: 13, color: HEX.teal, margin: 0, isTextBox: true });
  s.addNotes("CONCLUSION (45 s). Three sentences. One: the system works end to end in a real browser. Two: graph structure helps precisely where instrumentation fails, which is the Wasm boundary. " +
    "Three: we report what lost, and everything, including failures, is documented and reproducible. Then invite questions; the appendix has the full tables, ROC and PR curves, confusion matrices, training curves and calibration bands.");

  // ================================================================ APPENDIX
  pres.addSection({ title: "Appendix" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  title(s, "Appendix A: full results, extension-level split");
  const ah = ["Model", "Precision", "Recall", "F1", "ROC-AUC", "FPR", "Infer ms", "Train s", "Params"].map((t) => ({ text: t, options: { bold: true, color: HEX.teal, align: t === "Model" ? "left" : "center", fill: { color: C.background2 } } }));
  const arows = ORDER.map((m) => { const r = M[m], c = m === "GraphSAGE" ? HEX.teal : m === "R-GCN" ? HEX.purple : HEX.text;
    return [{ text: m, options: { color: c, bold: c !== HEX.text } }, ...[f3(r.precision), f3(r.recall), f3(r.f1), f3(r.roc_auc), f3(r.fpr), f3(r.infer_ms_per_graph), f2(r.train_s), Math.floor(r.params).toLocaleString("en-US")].map((t) => ({ text: t, options: { color: c, align: "center" } }))]; });
  s.addTable([ah, ...arows], { x: MX, y: 1.5, w: 12.1, colW: [2.9, 1.1, 1.0, 1.0, 1.1, 0.9, 1.2, 1.0, 1.0], fontSize: 13, border: { type: "solid", color: "22314A", pt: 0.5 }, fill: { color: C.background2 }, rowH: 0.45, valign: "middle", margin: 0.06 });
  s.addText("Mean over 5 extension-level splits, threshold 0.5. Inference is offline, per session graph, batch size 1, CPU; graph construction adds " + D.latency_build_ms.toFixed(3) + " ms. Params for RF are tree nodes.",
    { x: MX, y: 5.8, w: 12.1, h: 0.7, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("APPENDIX A. Full table behind slide 10. Latency is offline CPU inference, not a deployed real-time monitor.");

  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  title(s, "Appendix B: ROC and precision-recall curves");
  fitImg(s, "roc_curves.png", MX, 1.5, 5.95, 5.25, "roc"); fitImg(s, "pr_curves.png", 6.75, 1.5, 5.95, 5.25, "pr");
  s.addNotes("APPENDIX B. ROC and PR curves for split 0 on held-out test extensions.");

  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  title(s, "Appendix C: confusion matrices, training curves and latency");
  fitImg(s, "confusion_matrices.png", MX, 1.4, 12.1, 2.25, "confusion");
  fitImg(s, "training_curves.png", MX, 3.8, 6.4, 3.0, "training"); fitImg(s, "latency.png", 7.2, 3.8, 5.5, 3.0, "latency");
  s.addNotes("APPENDIX C. Confusion matrices (split 0), training and validation loss for the three GNNs, and inference latency per model.");

  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  title(s, "Appendix D: confidence calibration in detail");
  const dh = (t) => ({ text: t, options: { bold: true, color: HEX.teal, align: "center", fill: { color: C.background2 } } });
  const dc = (t, c) => ({ text: t, options: { color: c || HEX.text, align: "center" } });
  const bandRows = [];
  for (const arch of ["GraphSAGE", "R-GCN"]) for (const b of D.calibration[arch].bins)
    bandRows.push([dc(arch, arch === "GraphSAGE" ? HEX.teal : HEX.purple), dc(`${(b.lo * 100).toFixed(0)}–${(b.hi * 100).toFixed(0)}%`), dc(String(b.n)), dc(String(b.correct)), dc(f3(b.accuracy)), dc(f3(b.ci_lo))]);
  heading(s, "SCORE BANDS (ENSEMBLE, OUT-OF-FOLD)", MX, 1.45, 6);
  s.addTable([[dh("Detector"), dh("Score band"), dh("Sessions"), dh("Correct"), dh("Accuracy"), dh("95% lower")], ...bandRows],
    { x: MX, y: 1.85, w: 6.6, colW: [1.2, 1.2, 1.0, 1.0, 1.1, 1.1], fontSize: 12, border: { type: "solid", color: "22314A", pt: 0.5 }, fill: { color: C.background2 }, rowH: 0.36, valign: "middle", margin: 0.04 });
  const tRows = Object.entries(D.calibration_test).map(([k, t]) => [dc(k.replace("_heldout_wasm_flows", " · Wasm held out").replace("_extension_split", " · standard split"), k.startsWith("GraphSAGE") ? HEX.teal : HEX.purple),
    dc(String(t.n_test)), dc(f3(t.mean_conf)), dc(f3(t.accuracy)), dc(f3(t.ece), t.ece > 0.2 ? HEX.red : HEX.text)]);
  heading(s, "SAVED ENSEMBLES ON THEIR TEST SETS", 7.55, 1.45, 5.2);
  s.addTable([[dh("Detector · training"), dh("n"), dh("Mean conf."), dh("Accuracy"), dh("ECE")], ...tRows],
    { x: 7.55, y: 1.85, w: 5.15, colW: [2.15, 0.5, 0.95, 0.85, 0.7], fontSize: 12, border: { type: "solid", color: "22314A", pt: 0.5 }, fill: { color: C.background2 }, rowH: 0.5, valign: "middle", margin: 0.04 });
  s.addText("The verdict card quotes the 95% lower bound of the band accuracy. Adjacent bands are pooled so a higher score never shows a lower confidence. ECE above 0.2 means the confidence is not trustworthy for that detector under that shift.",
    { x: 7.55, y: 4.7, w: 5.15, h: 1.5, fontSize: 13, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("APPENDIX D. Single model versus ensemble, the pooled score bands with Wilson intervals, and the never-seen-flow calibration of the saved ensembles.");

  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  title(s, "Appendix E: reproducibility and what is not yet measured");
  card(s, MX, 1.5, 6.0, 5.25, "repro"); heading(s, "RUN IT", MX + 0.3, 1.7, 5);
  s.addText([{ text: "./setup.sh", options: { fontFace: "Consolas", color: HEX.teal, breakLine: true } }, { text: "./run_demo.sh", options: { fontFace: "Consolas", color: HEX.teal, breakLine: true } }, { text: " ", options: { breakLine: true } },
    { text: "streamlit run dashboard.py", options: { fontFace: "Consolas", color: HEX.teal, breakLine: true } }, { text: " ", options: { breakLine: true } },
    { text: "Dataset frozen (576 graphs); re-running the lab produces a new random sample. All runs are logged in experiments.csv; the untuned v1 run is kept.", options: { color: HEX.text } }],
    { x: MX + 0.3, y: 2.15, w: 5.4, h: 4.4, fontSize: 15, valign: "top", margin: 0, isTextBox: true });
  card(s, 6.7, 1.5, 6.0, 5.25, "unmeasured"); heading(s, "NOT YET MEASURED", 7.0, 1.7, 5, HEX.amber);
  bullets(s, ["Clean-machine end-to-end re-run", "Explanation faithfulness", "Real-extension corpus", "Adversarial evaluation", "Browser-level (non-self-reported) telemetry"], 7.0, 2.15, 5.4, 4.5, { size: 15, gap: 9 });
  s.addNotes("APPENDIX E. Reproducibility and the explicit list of things that were not measured.");

  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  title(s, "Appendix F: references");
  bullets(s, [
    "Fass, Somé, Backes, Stock. DoubleX: Statically Detecting Vulnerable Data Flows in Browser Extensions at Scale. ACM CCS 2021.",
    "Xie, Kasi Murali, Pearce, Li. Arcanum: Detecting and Evaluating the Privacy Risks of Browser Extensions on Web Pages and Web Content. USENIX Security 2024.",
    "I Spy with My Little Eye: Analysis and Detection of Spying Browser Extensions. arXiv:1612.00766.",
    "The Blind Spot of Extension Security: WebAssembly–JavaScript Collaborative Attacks on Chrome. Electronics, doi:10.3390/electronics15143049 (title only; read before citing).",
    "Kipf and Welling. Semi-Supervised Classification with Graph Convolutional Networks. ICLR 2017.",
    "Hamilton, Ying, Leskovec. Inductive Representation Learning on Large Graphs. NeurIPS 2017.",
    "Schlichtkrull et al. Modeling Relational Data with Graph Convolutional Networks. ESWC 2018.",
  ], MX, 1.5, 12.1, 5.2, { size: 15, gap: 11 });
  s.addNotes("APPENDIX F. References. The Electronics paper and MalSage were located via search snippets and should be read in full before a formal citation.");

  const out = path.join(__dirname, "AuthGraph_deck.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("written", out, "slides:", pres.slides.length);
})();
