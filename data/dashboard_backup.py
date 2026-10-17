"""AuthGraph dashboard.  Run:  streamlit run dashboard.py"""
import json, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch, torch.nn.functional as F
import plotly.graph_objects as go
import streamlit as st

from authgraph.data import load_graphs, extension_split, batch_graphs
from authgraph.graph import RELS, N_FEAT, build_graph, load_events, APPROVED
from authgraph.models import RGCN, SAGE
from authgraph.explain import explain
from authgraph.rules import explain as rule_explain, RULES
from extgen.generate import FAMILIES

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="AuthGraph", layout="wide", page_icon="🕸️")

COL = {"extension": "#4C566A", "content_script": "#0072B2", "service_worker": "#56B4E9", "js_module": "#E69F00",
       "wasm_module": "#CC79A7", "browser_api": "#8FBCBB", "credential": "#D55E00", "storage_object": "#A3BE8C",
       "http_request": "#B48EAD", "domain": "#009E73", "page": "#BBBBBB"}
LAYER = {"extension": 0, "content_script": 1, "service_worker": 1, "page": 2, "browser_api": 2, "credential": 3,
         "js_module": 4, "wasm_module": 4, "storage_object": 4, "http_request": 5, "domain": 6}


@st.cache_data
def read_json(p):
    p = ROOT / p
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_resource
def graphs_and_events():
    g = load_graphs(ROOT / "data" / "graphs.pkl")
    return g, load_events(ROOT / "data" / "raw")


TUNED = json.loads((ROOT / "results" / "tuned_config.json").read_text()) if (ROOT / "results" / "tuned_config.json").exists() else {}


@st.cache_resource
def get_model(name):
    p = ROOT / "models" / name
    if not p.exists(): return None
    if name.startswith("R-GCN"):
        c = TUNED.get("RGCN", {"h": 64, "bases": 0}); m = RGCN(N_FEAT, RELS, c["h"], 3, c.get("bases", 0))
    else:
        m = SAGE(N_FEAT, TUNED.get("SAGE", {"h": 64})["h"])
    m.load_state_dict(torch.load(p)); m.eval(); return m


MODEL_FILES = {"GraphSAGE (best measured)": ("GraphSAGE_extension_split.pt", "GraphSAGE_heldout_wasm_flows.pt"),
               "R-GCN (proposed)": ("R-GCN_extension_split.pt", "R-GCN_heldout_wasm_flows.pt")}


def pick_model(label_key, unseen):
    """unseen=True -> model trained WITHOUT any Wasm-involving suspicious flow."""
    return get_model(MODEL_FILES[label_key][1 if unseen else 0])


def prob(model, g):
    with torch.no_grad():
        return F.softmax(model(batch_graphs([g])), 1)[0, 1].item()


def layout(g):
    layers = {}
    for i, t in enumerate(g["ntype"]): layers.setdefault(LAYER[t], []).append(i)
    pos = {}
    for l, ids in layers.items():
        for k, i in enumerate(ids): pos[i] = (l, (k - (len(ids) - 1) / 2) * -1.0)
    return pos


def draw_graph(g, exp=None, height=520):
    pos = layout(g)
    path_edges = set()
    if exp and exp["path"]["nodes"]:
        p = exp["path"]["nodes"]
        path_edges = {frozenset(e) for e in zip(p, p[1:])}
    fig = go.Figure()
    for r, es in g["edges"].items():
        for s, d in es:
            hot = frozenset((s, d)) in path_edges
            fig.add_annotation(x=pos[d][0], y=pos[d][1], ax=pos[s][0], ay=pos[s][1], xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=3, arrowsize=1.1, arrowwidth=3.2 if hot else 1,
                               arrowcolor="#D62728" if hot else "rgba(150,150,150,0.55)", standoff=9)
    nimp = exp["node_importance"] if exp else [0] * len(g["ntype"])
    onpath = set(exp["path"]["nodes"] or []) if exp else set()
    fig.add_trace(go.Scatter(
        x=[pos[i][0] for i in pos], y=[pos[i][1] for i in pos], mode="markers+text",
        text=[g["names"][i] if len(g["names"][i]) < 24 else g["names"][i][:22] + "…" for i in pos], textposition="bottom center",
        textfont=dict(size=10),
        marker=dict(size=[30 if i in onpath else 22 for i in pos], color=[COL[g["ntype"][i]] for i in pos],
                    line=dict(width=[4 if i in onpath else 1 for i in pos], color=["#D62728" if i in onpath else "white" for i in pos])),
        hovertext=[f"{g['ntype'][i]}: {g['names'][i]}<br>Δlog-odds={nimp[i]:+.2f}" for i in pos], hoverinfo="text"))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                      xaxis=dict(visible=False, range=[-0.5, 6.6]), yaxis=dict(visible=False), plot_bgcolor="rgba(0,0,0,0)")
    return fig


def legend():
    st.markdown(" ".join(f"<span style='color:{c}'>●</span> {t}" for t, c in COL.items()), unsafe_allow_html=True)


def events_df(evs):
    ev = sorted(evs, key=lambda e: (e["ts"], e.get("cseq", 0))); t0 = ev[0]["ts"]
    rows = []
    for e in ev:
        det = e.get("destination") or e.get("object") or e.get("script") or e.get("cred_type") or e.get("to_component") or ""
        tags = e.get("payload_tags") or e.get("in_tags") or e.get("tags") or e.get("out_tags") or []
        rows.append({"t (ms)": round(e["ts"] - t0, 1), "event": e["event_type"], "component": e.get("component", ""),
                     "api / module": e.get("api") or e.get("module") or "", "detail": det,
                     "credential taint": ",".join(t.split(":")[1][:6] for t in tags)})
    return pd.DataFrame(rows)


def verdict(p):
    return ("SUSPICIOUS", "#D62728", p) if p >= 0.5 else ("BENIGN", "#2CA02C", 1 - p)


def banner(p):
    v, c, conf = verdict(p)
    st.markdown(f"<div style='padding:10px 16px;border-left:8px solid {c};background:rgba(128,128,128,.1)'>"
                f"<span style='font-size:26px;color:{c};font-weight:700'>{v}</span> &nbsp; "
                f"risk score (P suspicious) = <b>{p*100:.1f}%</b> &nbsp;|&nbsp; confidence = <b>{conf*100:.1f}%</b></div>",
                unsafe_allow_html=True)


def path_text(g, exp):
    n = exp["path"]["nodes"]
    return "  →  ".join(g["names"][i] for i in n) + ("" if exp["path"].get("method") == "importance" else "  *(structural fallback: no single-edge removal changed the score)*") if n else "no credential→destination path with positive measured importance"


# =============================================================== sidebar
PAGES = ["1 · Overview", "2 · Session replay", "3 · Graph visualization", "4 · Model comparison",
         "5 · Confusion matrices", "6 · Explainability", "7 · Unseen-flow & ablation", "8 · Live lab run"]
page = st.sidebar.radio("AuthGraph", PAGES)
st.sidebar.caption("All data from a controlled local lab. Synthetic credentials only. Metrics are read from results/*.json (measured).")
if not (ROOT / "data" / "graphs.pkl").exists():
    st.error("No dataset yet. Run ./run_dataset.sh first."); st.stop()
graphs, events = graphs_and_events()
by_sid = {g["session_id"]: g for g in graphs}
MK = st.sidebar.radio("Model", list(MODEL_FILES))
model_full = pick_model(MK, False)
model_unseen = pick_model(MK, True)
test0 = {g["session_id"] for g in extension_split(graphs, 0)["test"]}

# =============================================================== 1 overview
if page == PAGES[0]:
    st.title("AuthGraph — authentication-aware graph detection in browser extensions")
    rep = read_json("results/dataset_report.json"); main = read_json("results/main.json")
    c = st.columns(6)
    c[0].metric("Sessions", rep["sessions_completed"]); c[1].metric("Graphs", rep["graphs"])
    c[2].metric("Extensions", rep["extensions"]); c[3].metric("Benign", rep["label_counts"]["benign"])
    c[4].metric("Suspicious", rep["label_counts"]["suspicious"])
    c[5].metric("Avg nodes / edges", f"{rep['nodes_mean']:.1f} / {rep['edges_mean']:.1f}")
    if main:
        st.subheader("Detection on held-out extensions (mean over 5 extension-level splits)")
        rows = []
        for m in ["Rule R1 (co-occurrence)", "Rule R2 (taint)", "GraphSAGE", "R-GCN"]:
            rs = [r for r in main if r["model"] == m]
            rows.append({"model": m, "detection rate (recall)": np.mean([r["recall"] for r in rs]),
                         "false positive rate": np.mean([r["fpr"] for r in rs]), "F1": np.mean([r["f1"] for r in rs])})
        st.dataframe(pd.DataFrame(rows).round(3), hide_index=True)
    st.subheader("Dataset QA")
    st.json({k: v for k, v in rep.items() if k not in ("graph_sizes", "graph_size_labels", "family_counts")})
    st.write("Scenario families:", rep["family_counts"])
    st.image(str(ROOT / "figures" / "graph_size_distribution.png")) if (ROOT / "figures" / "graph_size_distribution.png").exists() else None

# =============================================================== 2 replay
elif page == PAGES[1]:
    st.title("Session replay — events → graph → risk")
    fam = st.selectbox("Scenario family", FAMILIES, index=FAMILIES.index("S3_cred_wasm_sink"))
    cands = [g for g in graphs if g["family"] == fam and g["session_id"] in test0] or [g for g in graphs if g["family"] == fam]
    g0 = st.selectbox("Session (held-out test extensions first)", [g["session_id"] for g in cands])
    evs = sorted(events[g0], key=lambda e: (e["ts"], e.get("cseq", 0)))
    k = st.slider("Replay: events observed so far", 2, len(evs), len(evs))
    meta = {"session_id": g0, "extension_id": evs[0]["extension_id"], "family": fam, "label": by_sid[g0]["label"]}
    gk = build_graph(evs[:k], meta)
    left, right = st.columns([2, 3])
    left.dataframe(events_df(evs[:k]), height=520, hide_index=True)
    right.plotly_chart(draw_graph(gk), use_container_width=True); legend()
    if model_full:
        curve = [prob(model_full, build_graph(evs[:j], meta)) for j in range(2, len(evs) + 1)]
        banner(curve[k - 2])
        st.caption("Risk score as events arrive (selected model, offline replay of the recorded session)")
        st.line_chart(pd.DataFrame({"P(suspicious)": curve}, index=range(2, len(evs) + 1)))

# =============================================================== 3 graph
elif page == PAGES[2]:
    st.title("Graph visualization — suspicious path highlighted")
    fam = st.selectbox("Family", FAMILIES, index=FAMILIES.index("S5_staged_multi_component"))
    sid = st.selectbox("Session", [g["session_id"] for g in graphs if g["family"] == fam][:60])
    g = by_sid[sid]
    if model_full:
        exp = explain(model_full, g); banner(exp["prob"])
        st.plotly_chart(draw_graph(g, exp, 600), use_container_width=True); legend()
        st.markdown(f"**Highest-importance credential → destination path:** {path_text(g, exp)}")
        if g["session_id"] not in test0: st.caption("Note: this session's extension was in the training split of the saved model.")
    else:
        st.plotly_chart(draw_graph(g), use_container_width=True); st.warning("model not trained yet")

# =============================================================== 4 comparison
elif page == PAGES[3]:
    st.title("Model comparison (measured)")
    p = ROOT / "results" / "tables.md"
    if p.exists(): st.markdown(p.read_text(encoding="utf-8").split("## Unseen")[0].replace("# Measured results (auto-generated by evaluate.py)", ""))
    for f in ["model_comparison", "roc_curves", "pr_curves", "latency", "training_curves"]:
        if (ROOT / "figures" / f"{f}.png").exists(): st.image(str(ROOT / "figures" / f"{f}.png"))
    st.caption("Latency = offline per-session inference (batch size 1, CPU). Not a deployed real-time monitor.")

# =============================================================== 5 confusion
elif page == PAGES[4]:
    st.title("Confusion matrices (extension-level split 0, test extensions)")
    f = ROOT / "figures" / "confusion_matrices.png"
    st.image(str(f)) if f.exists() else st.warning("NOT YET MEASURED")

# =============================================================== 6 explain
elif page == PAGES[5]:
    st.title("Explainability — why was it flagged?")
    model = st.radio("Training data", ["all families (extension split)", "trained WITHOUT Wasm exfiltration flows"], horizontal=True)
    m = model_full if model.startswith("all") else model_unseen
    fam = st.selectbox("Family", FAMILIES, index=FAMILIES.index("S3_cred_wasm_sink"))
    sid = st.selectbox("Session", [g["session_id"] for g in graphs if g["family"] == fam][:60])
    g = by_sid[sid]
    if m is None: st.warning("model not trained yet"); st.stop()
    exp = explain(m, g); banner(exp["prob"])
    st.plotly_chart(draw_graph(g, exp, 520), use_container_width=True); legend()
    st.markdown(f"**Important path** ({len(exp['path']['nodes'] or [])} nodes): {path_text(g, exp)}")
    a, b = st.columns(2)
    nodes = sorted(((exp["node_importance"][i], g["ntype"][i], g["names"][i]) for i in range(len(g["ntype"]))), reverse=True)[:8]
    a.subheader("Node importance"); a.dataframe(pd.DataFrame(nodes, columns=["Δ log-odds if removed", "type", "node"]).round(3), hide_index=True)
    edges = sorted(exp["edge_importance"], key=lambda e: -e["importance"])[:8]
    b.subheader("Edge importance")
    b.dataframe(pd.DataFrame([{"Δ log-odds if removed": round(e["importance"], 3), "relation": e["rel"],
                               "edge": f"{g['names'][e['src']]} → {g['names'][e['dst']]}"} for e in edges]), hide_index=True)
    st.subheader("Rule-based explanation")
    for line in rule_explain(events[sid]) or ["no rule fired"]: st.write("•", line)
    st.caption("Importance = occlusion: log-odds(suspicious | full graph) − log-odds(suspicious | node/edge removed). Measured model outputs, not attention weights.")

# =============================================================== 7 unseen
elif page == PAGES[6]:
    st.title("Unseen-flow generalisation and ablation")
    t = (ROOT / "results" / "tables.md")
    if t.exists():
        txt = t.read_text(encoding="utf-8"); i = txt.find("## Unseen")
        st.markdown(txt[i:] if i >= 0 else "NOT YET MEASURED")
    for f in ["unseen_flow", "ablation"]:
        if (ROOT / "figures" / f"{f}.png").exists(): st.image(str(ROOT / "figures" / f"{f}.png"))

# =============================================================== 8 live
else:
    st.title("Live lab run — real browser, fresh extension")
    st.write("Generates a NEW extension (not in the dataset), loads it into Chromium, visits the controlled app, "
             "captures telemetry, builds the graph and classifies it. Localhost only; synthetic credentials.")
    fam = st.selectbox("Scenario", FAMILIES, index=FAMILIES.index("S3_cred_wasm_sink"))
    headed = st.checkbox("Show browser window", True)
    mname = st.radio("Training data", ["all families (extension split)", "trained WITHOUT Wasm exfiltration flows"], horizontal=True)
    if st.button("Run scenario"):
        with st.spinner("running browser session…"):
            cmd = [sys.executable, str(ROOT / "lab" / "live.py"), "--family", fam] + (["--headed"] if headed else [])
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0: st.error(r.stderr[-2000:]); st.stop()
        meta = json.loads(r.stdout.strip().splitlines()[-1])
        evs = load_events(ROOT / "data" / "live" / meta["session_id"])[meta["session_id"]]
        g = build_graph(evs, meta)
        m = model_full if mname.startswith("all") else model_unseen
        exp = explain(m, g)
        banner(exp["prob"]); st.caption(f"(ground-truth scenario label: {'suspicious' if meta['label'] else 'benign'}; telemetry events: {len(evs)})")
        st.plotly_chart(draw_graph(g, exp, 560), use_container_width=True); legend()
        st.markdown(f"**Important path:** {path_text(g, exp)}")
        st.dataframe(events_df(evs), hide_index=True)
        for line in rule_explain(evs) or ["no rule fired"]: st.write("•", line)
