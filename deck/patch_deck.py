"""One-off edits applied to build_deck.js after visual QA (kept for traceability)."""
p = open('prep_images.py', encoding='utf-8').read()
p = p.replace('crop("06a_explainability", 495, 1290, "c_explain_graph", w=1500, x1=1990)', 'crop("06a_explainability", 488, 1485, "c_explain_graph", w=1500, x1=1842)')
open('prep_images.py', 'w', encoding='utf-8').write(p)

s = open('build_deck.js', encoding='utf-8').read()


def rep(old, new):
    global s
    assert old in s, "NOT FOUND: " + old[:70]
    s = s.replace(old, new, 1)


# stat(): optional font size so long values fit (slide 7 '288/288')
rep('function stat(s, x, y, w, h, value, label, color, sub) {', 'function stat(s, x, y, w, h, value, label, color, fs) {')
rep('fontSize: 38, bold: true, color, align: "left", valign: "middle", margin: 0, isTextBox: true });\n  s.addText(label',
    'fontSize: fs || 38, bold: true, color, align: "left", valign: "middle", margin: 0, isTextBox: true });\n  s.addText(label')
rep('stat(s, MX + 4.3, 1.5, 2.0, 1.45, "288/288", "benign / suspicious", HEX.green);', 'stat(s, MX + 4.3, 1.5, 2.0, 1.45, "288 / 288", "benign / suspicious", HEX.green, 26);')
# slide 1: bigger hero
rep('fitImg(s, "c_graph.jpg", 7.55, 1.75, 5.2, 3.9, "cover-hero");', 'fitImg(s, "c_graph.jpg", 6.95, 1.6, 5.85, 4.2, "cover-hero");')
# slide 8: graph-only crop, larger
rep('const gimg = fitImg(s, "c_graph.jpg", MX, 1.5, 8.1, 5.2, "graph-screenshot");', 'const gimg = fitImg(s, "c_graph_only.jpg", MX, 1.5, 8.1, 5.25, "graph-screenshot");')
# slide 12: shorter heading so it never wraps
rep('heading(s, "SESSIONS WHERE TAINT IS LOST IN WASM", 8.75, 1.65, 3.8, HEX.amber);', 'heading(s, "TAINT LOST INSIDE WASM", 8.75, 1.65, 3.8, HEX.amber);')
# params: truncate like the dashboard does
rep('Math.round(r.params).toLocaleString("en-US")', 'Math.floor(r.params).toLocaleString("en-US")')
# fill empty space: larger body text on sparse slides
rep('], MX + 0.3, 2.15, 6.3, 4.4, { size: 15, gap: 10 });', '], MX + 0.3, 2.15, 6.3, 4.4, { size: 16, gap: 12 });')
rep('s.addText(t, { x: x + 0.3, y: y + 1.05, w: 5.35, h: 1.1, fontSize: 15, color: C.text2', 's.addText(t, { x: x + 0.3, y: y + 1.05, w: 5.35, h: 1.1, fontSize: 16, color: C.text2')
rep('s.addText(t, { x: x + 0.12, y: 3.85, w: bw - 0.24, h: 1.6, fontSize: 12, color: C.text2', 's.addText(t, { x: x + 0.12, y: 3.85, w: bw - 0.24, h: 1.6, fontSize: 13, color: C.text2')
rep('bullets(s, items, x + 0.3, 2.3, 3.4, 4.3, { size: 14, gap: 9 });', 'bullets(s, items, x + 0.3, 2.3, 3.4, 4.3, { size: 16, gap: 12 });')
rep('MX + 0.3, 2.15, 5.45, 4.5, { size: 14, gap: 8 });\n  card(s, 6.7, 1.5, 6.0, 5.25, "next")', 'MX + 0.3, 2.15, 5.45, 4.5, { size: 16, gap: 11 });\n  card(s, 6.7, 1.5, 6.0, 5.25, "next")')
rep('7.0, 2.15, 5.45, 4.5, { size: 14, gap: 8 });\n  s.addNotes("LIMITATIONS', '7.0, 2.15, 5.45, 4.5, { size: 16, gap: 11 });\n  s.addNotes("LIMITATIONS')

# ---- slide 15: graph-only screenshot + native verdict card and path chips
a = s.index('  title(s, "Explainability: the path that triggered the verdict");')
b = s.index('  s.addNotes("EXPLAINABILITY')
new15 = '''  title(s, "Explainability: the path that triggered the verdict");
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
'''
s = s[:a] + new15 + s[b:]

# ---- appendix B / C: clean dark figures instead of dashboard crops
a = s.index('  title(s, "Appendix B: ROC and precision-recall curves");')
b = s.index('  s.addNotes("APPENDIX B.')
s = s[:a] + '''  title(s, "Appendix B: ROC and precision-recall curves");
  fitImg(s, "roc_curves.png", MX, 1.5, 5.95, 5.25, "roc"); fitImg(s, "pr_curves.png", 6.75, 1.5, 5.95, 5.25, "pr");
''' + s[b:]
a = s.index('  title(s, "Appendix C: confusion matrices, training curves and latency");')
b = s.index('  s.addNotes("APPENDIX C.')
s = s[:a] + '''  title(s, "Appendix C: confusion matrices, training curves and latency");
  fitImg(s, "confusion_matrices.png", MX, 1.4, 12.1, 2.25, "confusion");
  fitImg(s, "training_curves.png", MX, 3.8, 6.4, 3.0, "training"); fitImg(s, "latency.png", 7.2, 3.8, 5.5, 3.0, "latency");
''' + s[b:]

# ---- appendix D: native, legible tables
a = s.index('  title(s, "Appendix D: confidence calibration in detail");')
b = s.index('  s.addNotes("APPENDIX D.')
s = s[:a] + '''  title(s, "Appendix D: confidence calibration in detail");
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
''' + s[b:]
open('build_deck.js', 'w', encoding='utf-8').write(s)
print("edited")
