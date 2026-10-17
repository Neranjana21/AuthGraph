"""AuthGraph dashboard.  Run:  streamlit run dashboard.py"""
import json, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch, torch.nn.functional as F
import plotly.graph_objects as go
import streamlit as st

from authgraph.data import load_graphs, extension_split, batch_graphs
from authgraph.graph import RELS, N_FEAT, build_graph, load_events
from authgraph.models import RGCN, SAGE, Ensemble
from authgraph.explain import explain
from authgraph.rules import explain as rule_explain
from extgen.generate import FAMILIES

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="AuthGraph | Credential Flow Detector", layout="wide", page_icon="🛡️", initial_sidebar_state="expanded")

# ------------------------------------------------------------------ style
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp {
    background-color: #060c17 !important;
    background-image: 
        radial-gradient(circle at 10% 0%, rgba(34, 184, 207, 0.09) 0%, transparent 45%),
        radial-gradient(circle at 90% 90%, rgba(139, 92, 246, 0.07) 0%, transparent 45%),
        radial-gradient(circle at 50% 50%, rgba(10, 18, 32, 0.5) 0%, transparent 100%) !important;
    background-attachment: fixed !important;
    color: #e2e8f0 !important;
}

.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1550px !important;
    animation: fadeInPage 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

@keyframes fadeInPage {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

footer, [data-testid="stAppDeployButton"], [data-testid="stDecoration"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
}

/* Page Header & Title */
.pg-header-wrapper {
    margin-bottom: 1.6rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.pg-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
}
.pg-badge-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #00e5ff;
    box-shadow: 0 0 14px #00e5ff;
    display: inline-block;
}
h1.pg-title {
    font-size: 2.15rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
    margin: 0 !important;
    padding: 0 !important;
    background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.pg-sub {
    color: #94a3b8;
    margin: 0.4rem 0 0 0;
    font-size: 0.96rem;
    font-weight: 400;
}

.sec-header {
    margin-bottom: 0.9rem;
}
.sec-title-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
}
.sec-accent-bar {
    width: 4px;
    height: 16px;
    border-radius: 2px;
    background: linear-gradient(180deg, #00e5ff, #8b5cf6);
    display: inline-block;
}
.sec {
    font-size: 0.88rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    color: #f1f5f9;
}
.sec-sub {
    color: #94a3b8;
    font-size: 0.84rem;
    margin-top: 0.2rem;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: rgba(8, 15, 27, 0.92) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem !important;
}

.brand-card {
    background: linear-gradient(135deg, rgba(34, 184, 207, 0.15) 0%, rgba(139, 92, 246, 0.1) 100%);
    border: 1px solid rgba(34, 184, 207, 0.3);
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}
.brand-t {
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    background: linear-gradient(135deg, #00e5ff, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: flex;
    align-items: center;
    gap: 8px;
}
.brand-s {
    font-size: 0.67rem;
    letter-spacing: 0.12em;
    color: #94a3b8;
    font-weight: 600;
    margin-top: 0.35rem;
    text-transform: uppercase;
}

section[data-testid="stSidebar"] [data-testid="stRadioGroup"] {
    gap: 0.35rem;
}
section[data-testid="stSidebar"] [data-testid="stRadioGroup"] > div {
    width: 100%;
}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] {
    padding: 0.65rem 0.95rem !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    background: rgba(255, 255, 255, 0.02) !important;
    width: 100% !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"]:hover {
    background: rgba(34, 184, 207, 0.08) !important;
    border-color: rgba(34, 184, 207, 0.25) !important;
    transform: translateX(2px) !important;
}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] {
    background: linear-gradient(90deg, rgba(34, 184, 207, 0.18) 0%, rgba(34, 184, 207, 0.04) 100%) !important;
    border-color: rgba(34, 184, 207, 0.5) !important;
    box-shadow: 0 4px 14px rgba(34, 184, 207, 0.15) !important;
}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] p {
    color: #38bdf8 !important;
    font-weight: 700 !important;
}

/* Container Wrappers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    background: rgba(12, 22, 38, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.22) !important;
    transition: all 0.25s ease !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(34, 184, 207, 0.35) !important;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.32), 0 0 20px rgba(34, 184, 207, 0.08) !important;
}

/* Custom Hero Metrics Grid */
.hero-metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 1.1rem;
    margin-bottom: 1.6rem;
}
.hero-metric-card {
    background: linear-gradient(145deg, rgba(16, 28, 48, 0.85), rgba(11, 20, 36, 0.95));
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.1rem 1.25rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
.hero-metric-card:hover {
    transform: translateY(-3px);
    border-color: rgba(34, 184, 207, 0.45);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35), 0 0 15px rgba(34, 184, 207, 0.12);
}
.hm-icon-val {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.45rem;
}
.hm-icon {
    font-size: 1.4rem;
}
.hm-val {
    font-size: 1.85rem;
    font-weight: 800;
    font-family: 'Plus Jakarta Sans', sans-serif;
    letter-spacing: -0.025em;
}
.hm-label {
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
}

/* Custom Dataset Integrity Panel */
.integ-box {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}
.integ-item {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: all 0.2s ease;
}
.integ-item:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(34, 184, 207, 0.3);
}
.integ-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: #e2e8f0;
}
.integ-sub {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 2px;
}
.integ-val {
    font-size: 1.4rem;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
}

/* Standard Metric fallback styling */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(16, 28, 48, 0.8), rgba(11, 20, 36, 0.9)) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    padding: 1rem 1.25rem !important;
    position: relative !important;
    overflow: hidden !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
}
div[data-testid="stMetric"]::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #22b8cf, #8b5cf6);
    opacity: 0.7;
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(34, 184, 207, 0.45) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3), 0 0 15px rgba(34, 184, 207, 0.12) !important;
}
div[data-testid="stMetricLabel"] p {
    color: #94a3b8 !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
div[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    color: #f8fafc !important;
    letter-spacing: -0.02em !important;
}

/* VCard styling */
.vcard {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    background: rgba(12, 22, 38, 0.75);
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    transition: all 0.25s ease;
}
.vcard:hover {
    border-color: rgba(34, 184, 207, 0.3);
}

/* Legend & Chips */
.legend-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.25);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}
.chip-legend-item {
    display: inline-flex;
    align-items: center;
    font-size: 0.8rem;
    color: #cbd5e1;
    background: rgba(255, 255, 255, 0.03);
    padding: 4px 10px;
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    font-family: 'JetBrains Mono', monospace;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    padding: 0.65rem 1.25rem !important;
    border-radius: 8px 8px 0 0 !important;
    color: #94a3b8 !important;
    transition: all 0.2s ease !important;
}
button[data-baseweb="tab"]:hover {
    color: #38bdf8 !important;
    background: rgba(34, 184, 207, 0.06) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #38bdf8 !important;
}
div[data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, #22b8cf, #38bdf8) !important;
    height: 3px !important;
    border-radius: 3px !important;
}

/* Buttons */
button[kind="primary"] {
    background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%) !important;
    border: none !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 15px rgba(0, 180, 216, 0.3) !important;
    transition: all 0.2s ease !important;
}
button[kind="primary"]:hover {
    filter: brightness(1.15) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(0, 180, 216, 0.45) !important;
}
button[kind="secondary"] {
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    background: rgba(255, 255, 255, 0.03) !important;
    transition: all 0.2s ease !important;
}
button[kind="secondary"]:hover {
    border-color: #38bdf8 !important;
    color: #38bdf8 !important;
    background: rgba(56, 189, 248, 0.08) !important;
}

/* Dataframe styling */
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* Live Lab Scenario Card Layout */
.sc-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1rem;
}
.sc-card {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 1.1rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.2s ease;
}
.sc-card:hover {
    border-color: rgba(34, 184, 207, 0.4);
    background: rgba(255, 255, 255, 0.04);
}
.sc-k {
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.4rem;
}
.sc-t {
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.35;
    margin-bottom: 0.35rem;
    color: #f8fafc;
}
.sc-d {
    font-size: 0.83rem;
    color: #94a3b8;
    margin-bottom: 0.8rem;
    min-height: 2.6rem;
    line-height: 1.45;
}

/* Scrollbar */
*::-webkit-scrollbar {
    width: 7px;
    height: 7px;
}
*::-webkit-scrollbar-track {
    background: rgba(6, 12, 23, 0.6);
}
*::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.25);
    border-radius: 8px;
}
*::-webkit-scrollbar-thumb:hover {
    background: rgba(34, 184, 207, 0.5);
}
</style>""", unsafe_allow_html=True)

COL = {"extension": "#8b9bb4", "content_script": "#3b82f6", "service_worker": "#38bdf8", "js_module": "#f59e0b",
       "wasm_module": "#e879f9", "browser_api": "#5eead4", "credential": "#fb923c", "storage_object": "#a3e635",
       "http_request": "#a78bfa", "domain": "#34d399", "page": "#94a3b8"}
LAYER = {"extension": 0, "content_script": 1, "service_worker": 1, "page": 2, "browser_api": 2, "credential": 3,
         "js_module": 4, "wasm_module": 4, "storage_object": 4, "http_request": 5, "domain": 6}
RED = "#ff5c5c"
ALL_MODELS = ["Rule R1 (co-occurrence)", "Rule R2 (taint)", "RF (counts)", "RF (counts+reachability)",
              "MLP (counts)", "GCN", "GraphSAGE", "R-GCN"]
TRAIN_CHOICES = ["All families (extension split)", "Trained WITHOUT Wasm exfiltration flows"]
MODEL_FILES = {"GraphSAGE (best measured)": ("ENS_GraphSAGE_extension_split.pt", "ENS_GraphSAGE_heldout_wasm_flows.pt"),
               "R-GCN (proposed)": ("ENS_R-GCN_extension_split.pt", "ENS_R-GCN_heldout_wasm_flows.pt")}
TUNED = json.loads((ROOT / "results" / "tuned_config.json").read_text()) if (ROOT / "results" / "tuned_config.json").exists() else {}


# ------------------------------------------------------------------ data / models
@st.cache_data
def read_json(p):
    p = ROOT / p
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_resource
def graphs_and_events():
    return load_graphs(ROOT / "data" / "graphs.pkl"), load_events(ROOT / "data" / "raw")


@st.cache_resource
def get_model(name):
    """Each detector is a deep ensemble of independently seeded GNNs (models/ENS_*.pt)."""
    p = ROOT / "models" / name
    if not p.exists(): return None
    d = torch.load(p); members = []
    for st_ in d["states"]:
        if d["kind"] == "RGCN":
            c = TUNED.get("RGCN", {"h": 64, "bases": 0}); m = RGCN(N_FEAT, RELS, c["h"], 3, c.get("bases", 0))
        else:
            m = SAGE(N_FEAT, TUNED.get("SAGE", {"h": 64})["h"])
        m.load_state_dict(st_); m.eval(); members.append(m)
    ens = Ensemble(members); ens.eval(); return ens


def prob(model, g):
    with torch.no_grad():
        return F.softmax(model(batch_graphs([g])), 1)[0, 1].item()


@st.cache_data(show_spinner=False)
def cached_explain(_model, model_file, sid):
    return explain(_model, by_sid[sid])


@st.cache_data(show_spinner=False)
def cached_curve(_model, model_file, sid):
    evs = sorted(events[sid], key=lambda e: (e["ts"], e.get("cseq", 0)))
    g = by_sid[sid]; meta = {k: g[k] for k in ("session_id", "extension_id", "family", "label")}
    return [prob(_model, build_graph(evs[:j], meta)) for j in range(1, len(evs) + 1)]      # curve[j-1] = risk after j events


# ------------------------------------------------------------------ ui helpers
def header(title, sub=""):
    st.markdown(
        f"<div class='pg-header-wrapper'>"
        f"<div class='pg-title-row'>"
        f"<span class='pg-badge-dot'></span>"
        f"<h1 class='pg-title'>{title}</h1>"
        f"</div>"
        + (f"<div class='pg-sub'>{sub}</div>" if sub else "") +
        f"</div>",
        unsafe_allow_html=True
    )


def section(title, sub=""):
    st.markdown(
        f"<div class='sec-header'>"
        f"<div class='sec-title-wrap'>"
        f"<span class='sec-accent-bar'></span>"
        f"<div class='sec'>{title}</div>"
        f"</div>"
        + (f"<div class='sec-sub'>{sub}</div>" if sub else "") +
        f"</div>",
        unsafe_allow_html=True
    )


def hero_metrics(items):
    cards_html = "".join([
        f"<div class='hero-metric-card' style='border-top: 3px solid {colr};'>"
        f"  <div class='hm-icon-val'>"
        f"    <span class='hm-icon'>{icon}</span>"
        f"    <span class='hm-val' style='color: {colr};'>{val}</span>"
        f"  </div>"
        f"  <div class='hm-label'>{label}</div>"
        f"</div>"
        for label, val, icon, colr in items
    ])
    st.markdown(f"<div class='hero-metrics-grid'>{cards_html}</div>", unsafe_allow_html=True)


def integrity_panel(rep):
    items = [
        ("Credential Leaks", rep["credential_value_leaks"], "0 leaks detected", "#34d399"),
        ("Schema Failures", rep["events_failing_schema"], "100% compliant", "#34d399"),
        ("Duplicates Removed", rep["duplicates_removed"], "0 duplicates", "#38bdf8"),
        ("Log Mismatches", rep["sessions_where_telemetry_requests_differ_from_server_log"], "100% matched", "#34d399")
    ]
    cards = "".join([
        f"<div class='integ-item'>"
        f"  <div class='integ-left'>"
        f"    <div class='integ-title'>{title}</div>"
        f"    <div class='integ-sub'>{sub}</div>"
        f"  </div>"
        f"  <div class='integ-val' style='color:{colr}'>{val}</div>"
        f"</div>"
        for title, val, sub, colr in items
    ])
    st.markdown(f"<div class='integ-box'>{cards}</div>", unsafe_allow_html=True)


def legend():
    chips = "".join(f"<span class='chip-legend-item'><span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{c};box-shadow:0 0 6px {c}aa;margin-right:6px'></span>{t.replace('_', ' ')}</span>"
                    for t, c in COL.items())
    st.markdown(f"<div class='legend-container'>{chips}</div>", unsafe_allow_html=True)


def verdict(p):
    return ("SUSPICIOUS", RED, p) if p >= 0.5 else ("BENIGN", "#34d399", 1 - p)


def fmt_pct(x):
    return ">99.9%" if x >= 0.9995 else f"{x*100:.1f}%"


def _arch(model_file):
    return "GraphSAGE" if model_file and "GraphSAGE" in model_file else "R-GCN"


def band(model_file, conf):
    """Empirical (out-of-fold, unseen-extension) accuracy of this ENSEMBLE inside the score band `conf` falls in."""
    oof = ((read_json("results/calibration_ens.json") or {}).get("oof") or {}).get(_arch(model_file))
    if not oof: return None
    for r in oof.get("bins_mono") or oof["bins"]:
        if r["lo"] <= conf < r["hi"] + 1e-9 and r["n"]: return r
    return None


def conf_display(model_file, conf):
    """Believable confidence = the 95% LOWER bound of the accuracy observed (out-of-fold) in this score band.
    Pooled bands guarantee that a higher score never shows a lower confidence."""
    r = band(model_file, conf)
    if r is None: return fmt_pct(conf), None, None
    head = f"≥{r['ci_lo']*100:.1f}%"
    detail = (f"Observed {r['accuracy']*100:.1f}% correct (95% interval {r['ci_lo']*100:.1f}–{r['ci_hi']*100:.1f}%): "
              f"{r['correct']} of {r['n']} held-out sessions in this score band" + (" · small sample" if r["n"] < 20 else ""))
    return head, detail, r


def banner(p, model_file=None):
    v, c, conf = verdict(p)
    head, detail, r = conf_display(model_file, conf)
    if r is not None:
        risk = f"≥{r['ci_lo']*100:.1f}%" if p >= .5 else f"≤{(1-r['ci_lo'])*100:.1f}%"
    else:
        risk = fmt_pct(p)
    shift = ""
    if model_file and "heldout_wasm" in model_file:
        t = ((read_json("results/calibration_ens.json") or {}).get("test") or {}).get(f"{_arch(model_file)}_heldout_wasm_flows")
        if t:
            shift = (f"This detector never saw Wasm exfiltration flows. Bands above were measured on unseen extensions of known flow types; "
                     f"on its never-seen-flow test the measured calibration error was ECE {t['ece']:.3f} (accuracy {t['accuracy']*100:.0f}%).")
    icon = "🚨" if p >= 0.5 else "🛡️"
    st.markdown(
        f"<div class='vcard' style='border-left:5px solid {c}; background: linear-gradient(135deg, rgba(12,22,38,0.95), rgba(18,32,54,0.9));'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
        f"<div style='display:flex;align-items:center;gap:10px'>"
        f"<span style='font-size:1.5rem'>{icon}</span>"
        f"<span style='font-size:1.65rem;font-weight:800;color:{c};letter-spacing:-0.02em'>{v}</span>"
        f"</div>"
        f"<div style='background:rgba(255,255,255,0.06);padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,0.1);font-size:0.83rem;color:#cbd5e1'>"
        f"Confidence: <b style='color:#f8fafc'>{head}</b>"
        f"</div></div>"
        f"<div style='margin-top:10px;display:flex;align-items:center;justify-content:space-between;font-size:0.88rem;color:#cbd5e1'>"
        f"<span>Risk Score P(suspicious):</span>"
        f"<b style='color:{c};font-family:\"JetBrains Mono\", monospace;font-size:1.05rem'>{risk}</b>"
        f"</div>"
        f"<div style='height:8px;border-radius:6px;background:rgba(255,255,255,0.08);margin-top:8px;overflow:hidden;border:1px solid rgba(255,255,255,0.05)'>"
        f"<div style='width:{min(p,1)*100:.1f}%;height:100%;border-radius:6px;background:linear-gradient(90deg, {c}, {c}dd);box-shadow:0 0 10px {c}88'></div></div>"
        + (f"<div style='margin-top:10px;font-size:0.8rem;color:#94a3b8;line-height:1.5;background:rgba(0,0,0,0.25);padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.05)'>{detail}</div>" if detail else "")
        + (f"<div style='margin-top:8px;font-size:0.75rem;color:#64748b;line-height:1.45;font-style:italic'>{shift}</div>" if shift else "")
        + "</div>",
        unsafe_allow_html=True)


def path_chips(g, exp):
    n = exp["path"]["nodes"]
    if not n:
        st.caption("No credential → destination path flagged."); return
    chips = " ".join(("<span style='color:rgba(255,255,255,0.35);font-weight:700;margin:0 2px'>→</span>" if k else "") +
                     f"<span style='display:inline-flex;align-items:center;background:linear-gradient(135deg, {COL[g['ntype'][i]]}dd, {COL[g['ntype'][i]]});color:#06101c;font-weight:700;padding:4px 11px;"
                     f"border-radius:14px;font-size:0.8rem;margin:2px;box-shadow:0 2px 8px rgba(0,0,0,0.25);font-family:\"JetBrains Mono\", monospace'>{g['names'][i]}</span>"
                     for k, i in enumerate(n))
    st.markdown(f"<div class='vcard' style='margin-top:10px'>"
                f"<div class='sec' style='margin-bottom:8px'>Highlighted Attack Path · {len(n)} Nodes</div>"
                f"<div style='line-height:2.4;margin-top:0.2rem'>{chips}</div></div>", unsafe_allow_html=True)
    if exp["path"].get("method") != "importance":
        st.caption("Structural fallback: no single removal changed the score, so the shortest credential → destination path is shown (not model-derived).")


def layout(g):
    layers, pos = {}, {}
    for i, t in enumerate(g["ntype"]): layers.setdefault(LAYER[t], []).append(i)
    for l, ids in layers.items():
        for k, i in enumerate(ids): pos[i] = (l, (k - (len(ids) - 1) / 2) * -1.0)
    return pos


def draw_graph(g, exp=None, height=480, pos=None, yr=None):
    pos = pos or layout(g)
    path = exp["path"]["nodes"] if exp and exp["path"]["nodes"] else []
    hot_e = {frozenset(e) for e in zip(path, path[1:])}
    fig = go.Figure()
    for r, es in g["edges"].items():
        for s, d in es:
            hot = frozenset((s, d)) in hot_e
            fig.add_annotation(x=pos[d][0], y=pos[d][1], ax=pos[s][0], ay=pos[s][1], xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=3, arrowsize=1.1, arrowwidth=3.2 if hot else 1,
                               arrowcolor=RED if hot else "rgba(150,165,190,.45)", standoff=9)
    nimp = exp["node_importance"] if exp else [0] * len(g["ntype"])
    on = set(path)
    nm = lambda i: g["names"][i] if len(g["names"][i]) < 19 else g["names"][i][:17] + "…"
    fig.add_trace(go.Scatter(
        x=[pos[i][0] for i in pos], y=[pos[i][1] for i in pos], mode="markers+text", text=[nm(i) for i in pos],
        textposition=["top center" if g["ntype"][i] == "browser_api" else "bottom center" for i in pos],
        textfont=dict(size=10, color="#c3cedb"),
        marker=dict(size=[30 if i in on else 22 for i in pos], color=[COL[g["ntype"][i]] for i in pos],
                    line=dict(width=[4 if i in on else 1 for i in pos], color=[RED if i in on else "#0a1220" for i in pos])),
        hovertext=[f"{g['ntype'][i]}: {g['names'][i]}<br>Δlog-odds={nimp[i]:+.2f}" for i in pos], hoverinfo="text"))
    fig.update_layout(height=height, margin=dict(l=6, r=6, t=6, b=6), showlegend=False,
                      xaxis=dict(visible=False, range=[-0.5, 6.7]), yaxis=dict(visible=False, range=yr),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def events_df(evs):
    ev = sorted(evs, key=lambda e: (e["ts"], e.get("cseq", 0))); t0 = ev[0]["ts"]; rows = []
    for e in ev:
        det = e.get("destination") or e.get("object") or e.get("script") or e.get("cred_type") or e.get("to_component") or ""
        tags = e.get("payload_tags") or e.get("in_tags") or e.get("tags") or e.get("out_tags") or []
        rows.append({"t (ms)": round(e["ts"] - t0, 1), "event": e["event_type"], "component": e.get("component", ""),
                     "api / module": e.get("api") or e.get("module") or "", "detail": det,
                     "credential taint": ",".join(t.split(":")[1][:6] for t in tags)})
    return pd.DataFrame(rows)


def pivot(runs, setting_key, value, models, settings=None):
    settings = settings or list(dict.fromkeys(r[setting_key] for r in runs)); rows = []
    for s_ in settings:
        row = {"setting": s_}
        for m in models:
            v = [r[value] for r in runs if r[setting_key] == s_ and r["model"] == m]
            row[m] = float(np.mean(v)) if v else np.nan
        rows.append(row)
    return pd.DataFrame(rows).set_index("setting")


def shade(df, vmin=0.0, vmax=1.0):
    return df.style.format("{:.3f}").background_gradient(cmap="GnBu", vmin=vmin, vmax=vmax, axis=None)


def show_fig(name, caption=None):
    for d in ("figures/dark", "figures"):
        f = ROOT / d / f"{name}.png"
        if f.exists():
            st.image(str(f), caption=caption, width="stretch"); return
    st.warning(f"{name}: NOT YET MEASURED")


# ------------------------------------------------------------------ sidebar
PAGES = {":material/dashboard: Dashboard": "dash", ":material/replay: Session Replay": "replay",
         ":material/hub: Graph Visualization": "graph", ":material/compare_arrows: Model Comparison": "models",
         ":material/grid_on: Confusion Matrices": "cm", ":material/psychology: Explainability": "explain",
         ":material/science: Unseen-Flow & Ablation": "unseen", ":material/play_circle: Live Lab Run": "live"}
with st.sidebar:
    st.markdown(
        "<div class='brand-card'>"
        "<div class='brand-t'>🛡️ AUTHGRAPH</div>"
        "<div class='brand-s'>CREDENTIAL FLOW DETECTION PLATFORM</div>"
        "</div>",
        unsafe_allow_html=True
    )
    st.write("")
    page = PAGES[st.radio("Navigation", list(PAGES), label_visibility="collapsed")]
    st.divider()
    MK = st.selectbox("Detector", list(MODEL_FILES), help="Each detector is an ensemble of 10 independently trained models; its score is their mean.")
    st.caption("Localhost only · synthetic credentials · every metric is read from an executed run in results/")

_entered = st.session_state.get("_page") != page
st.session_state["_page"] = page
if _entered:                                           # fresh visit -> replay always starts from 0 events
    for _k in [k for k in st.session_state if str(k).startswith("rp_k_")]:
        del st.session_state[_k]

if not (ROOT / "data" / "graphs.pkl").exists():
    st.error("No dataset yet. Run ./run_dataset.sh first."); st.stop()
graphs, events = graphs_and_events()
by_sid = {g["session_id"]: g for g in graphs}
FILE_ALL, FILE_UNSEEN = MODEL_FILES[MK]
model_all, model_unseen = get_model(FILE_ALL), get_model(FILE_UNSEEN)
test0 = {g["session_id"] for g in extension_split(graphs, 0)["test"]}


def pick_session(key, default_family="S3_cred_wasm_sink"):
    c1, c2 = st.columns(2)
    fam = c1.selectbox("Scenario family", FAMILIES, index=FAMILIES.index(default_family), key=f"fam{key}")
    sids = [g["session_id"] for g in graphs if g["family"] == fam]
    sids = [x for x in sids if x in test0] + [x for x in sids if x not in test0]
    return fam, c2.selectbox("Session (held-out test extensions first)", sids[:60], key=f"sid{key}")


def pick_model(key):
    c = st.radio("Detector trained on", TRAIN_CHOICES, horizontal=True, key=f"tr{key}")
    return (model_all, FILE_ALL) if c == TRAIN_CHOICES[0] else (model_unseen, FILE_UNSEEN)


def risk_fig(curve, k):
    n = len(curve); xs = list(range(1, n + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=curve, mode="lines", line=dict(color="rgba(34,184,207,.25)", width=2), hoverinfo="skip"))
    if k >= 1:
        fig.add_trace(go.Scatter(x=xs[:k], y=curve[:k], mode="lines+markers", line=dict(color="#22b8cf", width=3),
                                 marker=dict(size=5), hovertemplate="%{x} events: %{y:.3f}<extra></extra>"))
    fig.add_hline(y=0.5, line_dash="dot", line_color="rgba(255,255,255,.35)")
    grid = "rgba(120,140,170,.15)"
    fig.update_layout(height=190, margin=dict(l=8, r=8, t=6, b=28), showlegend=False,
                      yaxis=dict(range=[0, 1.02], title="risk so far", gridcolor=grid),
                      xaxis=dict(range=[0.7, n + 0.3], title="events observed", gridcolor=grid),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c3cedb", size=11))
    return fig


def provisional_card(p, j, n):
    """Shown while a session is still being observed: a risk-so-far number, NO verdict/confidence claim."""
    if j == 0:
        title, colr, line, bar = "READY", "#94a3b8", "No events observed yet. Press ▶ Play or drag the slider.", 0.0
    else:
        colr = "#f59e0b" if p >= 0.5 else "#22b8cf"
        title = "OBSERVING"
        line = f"Risk so far: <b style='color:{colr}; font-family:\"JetBrains Mono\", monospace'>{fmt_pct(p)}</b> after {j} of {n} events"
        bar = p
    st.markdown(
        f"<div class='vcard' style='border-left:5px solid {colr}; background: linear-gradient(135deg, rgba(12,22,38,0.95), rgba(18,32,54,0.9));'>"
        f"<div style='font-size:1.6rem;font-weight:800;color:{colr};letter-spacing:-0.02em'>{title}</div>"
        f"<div style='margin-top:8px;color:#cbd5e1;font-size:0.9rem'>{line}</div>"
        f"<div style='height:8px;border-radius:6px;background:rgba(255,255,255,0.08);margin-top:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.05)'>"
        f"<div style='width:{bar*100:.1f}%;height:100%;border-radius:6px;background:linear-gradient(90deg, {colr}, {colr}dd);box-shadow:0 0 10px {colr}88'></div></div>"
        f"<div style='margin-top:10px;font-size:0.78rem;color:#94a3b8;line-height:1.45;background:rgba(0,0,0,0.25);padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.05)'>The verdict and its confidence appear when the "
        f"session is complete — the detector was calibrated on complete sessions only.</div></div>", unsafe_allow_html=True)


@st.fragment
def replay_view(g0, fam):
    """Only this fragment reruns while dragging / playing, so the replay stays smooth."""
    evs = sorted(events[g0], key=lambda e: (e["ts"], e.get("cseq", 0))); n = len(evs)
    g = by_sid[g0]; meta = {x: g[x] for x in ("session_id", "extension_id", "family", "label")}
    pos_full = layout(build_graph(evs, meta))                    # fixed positions: nodes never jump as the graph grows
    ys = [p[1] for p in pos_full.values()]; yr = [min(ys) - 0.9, max(ys) + 0.9]
    curve = cached_curve(model_all, FILE_ALL, g0) if model_all else None
    key = f"rp_k_{g0}"
    if key not in st.session_state: st.session_state[key] = 0    # every replay starts from 0 events
    c1, c2, c3 = st.columns([1.2, 2, 7], vertical_alignment="bottom")
    play = c1.button("▶ Play", key="rp_play", type="primary", width="stretch")
    speed = c2.select_slider("Speed", ["Slow", "Normal", "Fast"], value="Normal", key="rp_speed", label_visibility="collapsed")
    slider_ph = c3.empty()                                       # progress bar while playing, slider otherwise
    make_slider = lambda: slider_ph.slider("Events observed so far", 0, n, key=key)
    left, right = st.columns([5, 7])
    with left:
        ph_banner = st.empty(); ph_last = st.empty(); st.write("")
        with st.container(border=True):
            section("Risk so far", "Offline replay of the recorded session · dotted line = decision threshold 0.5")
            ph_risk = st.empty()
    with right, st.container(border=True):
        section("Graph so far"); ph_graph = st.empty(); legend()
    section("Runtime events", "Chronological · latest event highlighted"); ph_events = st.empty()
    tbl_h = 38 + 35 * min(n, 18)                                  # fixed height -> layout never jumps while playing

    def render(j):
        if j == 0:
            empty = go.Figure(); empty.update_layout(height=400, margin=dict(l=6, r=6, t=6, b=6), paper_bgcolor="rgba(0,0,0,0)",
                                                      plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False, range=[-0.5, 6.7]),
                                                      yaxis=dict(visible=False, range=yr))
            with ph_banner.container(): provisional_card(0.0, 0, n)
            ph_last.caption(f"Event 0/{n} · waiting for the first event")
            ph_events.dataframe(pd.DataFrame(columns=["t (ms)", "event", "component", "api / module", "detail", "credential taint"]),
                                height=tbl_h, hide_index=True, width="stretch")
            ph_graph.plotly_chart(empty, width="stretch", key=f"rp_graph_{g0}_0")
            if curve: ph_risk.plotly_chart(risk_fig(curve, 0), width="stretch", key=f"rp_risk_{g0}_0")
            return
        gj = build_graph(evs[:j], meta)
        pos = {i: pos_full[i] for i in range(len(gj["ntype"]))}
        e = evs[j - 1]; det = e.get("destination") or e.get("object") or e.get("script") or e.get("cred_type") or e.get("api") or ""
        if curve:
            with ph_banner.container():
                if j < n: provisional_card(curve[j - 1], j, n)
                else: banner(curve[j - 1], FILE_ALL)             # verdict + calibrated confidence only for the COMPLETE session
        ph_last.caption(f"Event {j}/{n} · +{e['ts'] - evs[0]['ts']:.0f} ms · **{e['event_type']}** {('· ' + det) if det else ''}")
        df_j = events_df(evs[:j])
        hl = lambda row: ["background-color: rgba(34,184,207,.22); font-weight: 600" if row.name == len(df_j) - 1 else "" for _ in row]
        ph_events.dataframe(df_j.style.apply(hl, axis=1).format({"t (ms)": "{:g}"}), height=tbl_h, hide_index=True, width="stretch")
        ph_graph.plotly_chart(draw_graph(gj, height=400, pos=pos, yr=yr), width="stretch", key=f"rp_graph_{g0}_{j}")
        if curve: ph_risk.plotly_chart(risk_fig(curve, j), width="stretch", key=f"rp_risk_{g0}_{j}")

    if play:
        delay = {"Slow": 0.6, "Normal": 0.3, "Fast": 0.1}[speed]
        render(0); time.sleep(delay)
        for j in range(1, n + 1):
            slider_ph.progress(j / n, text=f"Playing… event {j}/{n}")
            render(j); time.sleep(delay)
        st.session_state[key] = n                                # slider not created yet in this run -> allowed
        make_slider()
    else:
        render(make_slider())


# ================================================================== Dashboard
if page == "dash":
    header("Dashboard", "Authentication-aware graph detection of credential data flows in browser extensions")
    rep, main = read_json("results/dataset_report.json"), read_json("results/main.json")
    
    hero_metrics([
        ("Sessions Completed", rep["sessions_completed"], "🛡️", "#00e5ff"),
        ("Extensions Monitored", rep["extensions"], "🧩", "#38bdf8"),
        ("Benign Sessions", rep["label_counts"]["benign"], "🟢", "#34d399"),
        ("Suspicious Sessions", rep["label_counts"]["suspicious"], "🚨", "#ff5c5c"),
        ("Avg Nodes / Graph", f"{rep['nodes_mean']:.1f}", "📊", "#a78bfa"),
        ("Avg Edges / Graph", f"{rep['edges_mean']:.1f}", "⚡", "#f59e0b")
    ])

    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        section("Detection on held-out extensions", "Mean over 5 extension-level splits")
        rows = []
        for m in ["Rule R1 (co-occurrence)", "Rule R2 (taint)", "RF (counts)", "GraphSAGE", "R-GCN"]:
            rs = [r for r in main if r["model"] == m]
            rows.append({"Model": m, "Detection rate": np.mean([r["recall"] for r in rs]),
                         "False-positive rate": np.mean([r["fpr"] for r in rs]), "F1": np.mean([r["f1"] for r in rs])})
        df = pd.DataFrame(rows).set_index("Model")
        st.dataframe(df.style.format("{:.3f}").background_gradient(cmap="GnBu", subset=["Detection rate", "F1"], vmin=0.5, vmax=1)
                     .background_gradient(cmap="OrRd", subset=["False-positive rate"], vmin=0, vmax=0.5), width="stretch")
        st.caption("Count-based models are already strong when taint is visible — see Unseen-Flow & Ablation for the informative test.")
    with right, st.container(border=True):
        section("Dataset integrity", "12 scenario families · 48 sessions each · checked on every run")
        integrity_panel(rep)

# ================================================================== Session replay
elif page == "replay":
    header("Session Replay", "Events arrive → graph grows → risk score updates")
    with st.container(border=True):
        fam, g0 = pick_session("rp")
    replay_view(g0, fam)

# ================================================================== Graph visualization
elif page == "graph":
    header("Graph Visualization", "Authentication-aware heterogeneous graph with the suspicious path highlighted")
    with st.container(border=True):
        fam, sid = pick_session("gr", "S5_staged_multi_component")
    exp = cached_explain(model_all, FILE_ALL, sid); g = by_sid[sid]
    l, r = st.columns([8, 4])
    with l, st.container(border=True):
        st.plotly_chart(draw_graph(g, exp, 520), width="stretch"); legend()
    with r:
        banner(exp["prob"], FILE_ALL); st.write(""); path_chips(g, exp)
        st.caption(f"{len(g['ntype'])} nodes · {sum(len(v) for v in g['edges'].values())} edges · "
                   + ("held-out test extension" if sid in test0 else "extension was in this model's training split"))

# ================================================================== Model comparison
elif page == "models":
    header("Model Comparison", "Extension-level split · mean over 5 splits · threshold 0.5 · all values measured")
    summ, main = read_json("results/summary.json"), read_json("results/main.json")
    s, rows = summ["main"], []
    for m in ALL_MODELS:
        if m in s:
            rs = [r for r in main if r["model"] == m]
            rows.append({"Model": m, "Precision": s[m]["precision"][0], "Recall": s[m]["recall"][0], "F1": s[m]["f1"][0],
                         "ROC-AUC": s[m]["roc_auc"][0], "FPR": s[m]["fpr"][0],
                         "Infer ms": np.mean([r["infer_ms_per_graph"] for r in rs]),
                         "Train s": np.mean([r["train_s"] for r in rs]), "Params": int(np.mean([r["params"] for r in rs]))})
    with st.container(border=True):
        section("Results table")
        st.dataframe(pd.DataFrame(rows).set_index("Model").style.format(
            {"Precision": "{:.3f}", "Recall": "{:.3f}", "F1": "{:.3f}", "ROC-AUC": "{:.3f}", "FPR": "{:.3f}",
             "Infer ms": "{:.3f}", "Train s": "{:.2f}", "Params": "{:,}"})
            .background_gradient(cmap="GnBu", subset=["Precision", "Recall", "F1", "ROC-AUC"], vmin=0.8, vmax=1), width="stretch")
        st.caption("Latency = offline per-session inference (batch size 1, CPU), not a deployed monitor. Params for RF = tree nodes.")
    t1, t2, t3, t4 = st.tabs(["Scores", "ROC / PR curves", "Training & latency", "Confidence calibration"])
    with t1: show_fig("model_comparison")
    with t2:
        a, b = st.columns(2)
        with a: show_fig("roc_curves")
        with b: show_fig("pr_curves")
    with t3:
        a, b = st.columns(2)
        with a: show_fig("training_curves")
        with b: show_fig("latency")
    with t4:
        ce = read_json("results/calibration_ens.json"); old = read_json("results/calibration_oof.json")
        if ce:
            with st.container(border=True):
                section("Is the confidence score trustworthy?",
                        "Out-of-fold predictions on 576 sessions from extensions the model never saw (5 disjoint extension folds)")
                rows = []
                for arch, r in ce["oof"].items():
                    for meth, label in (("single", "Single model"), ("ensemble", "10-model ensemble (shown in dashboard)")):
                        rows.append({"Detector": arch, "Method": label, "ECE": r[meth]["ece"], "Log-loss": r[meth]["nll"], "Brier": r[meth]["brier"],
                                     "Mean conf.": r[meth]["mean_conf"], "Accuracy": r[meth]["accuracy"], "Scores ≥ 99.9%": r[meth]["frac_conf_ge_999"]})
                st.dataframe(pd.DataFrame(rows).set_index(["Detector", "Method"]).style.format(
                    {"ECE": "{:.3f}", "Log-loss": "{:.3f}", "Brier": "{:.3f}", "Mean conf.": "{:.3f}", "Accuracy": "{:.3f}", "Scores ≥ 99.9%": "{:.0%}"}),
                    width="stretch")
                st.caption("Averaging 10 independently trained models lowers log-loss and Brier score for both detectors and spreads the scores out "
                           "instead of saturating them. ECE improves for GraphSAGE and is about equal for R-GCN." +
                           (" Temperature and Platt scaling were also tried on the single model and did not beat its raw scores." if old else ""))
            with st.container(border=True):
                section("Score bands (ensemble)", "Adjacent bands are pooled so a higher score never shows a lower confidence. The verdict card quotes the 95% lower bound")
                rows = [{"Detector": arch, "Confidence band": f"{b['lo']*100:.1f}–{b['hi']*100:.1f}%", "Sessions": b["n"], "Correct": b["correct"],
                         "Accuracy": b["accuracy"], "95% low": b["ci_lo"], "95% high": b["ci_hi"]} for arch, r in ce["oof"].items() for b in r.get("bins_mono") or r["bins"]]
                st.dataframe(pd.DataFrame(rows).set_index(["Detector", "Confidence band"]).style.format(
                    {"Accuracy": "{:.3f}", "95% low": "{:.3f}", "95% high": "{:.3f}"}), width="stretch")
            with st.container(border=True):
                section("Never-seen flows", "Saved ensembles on their held-out test sets (the Wasm-flows-held-out detectors never saw Wasm exfiltration)")
                rows = [{"Detector / training": k.replace("_", " "), "Test sessions": t["n_test"], "Mean conf.": t["mean_conf"],
                         "Accuracy": t["accuracy"], "ECE": t["ece"]} for k, t in ce["test"].items()]
                st.dataframe(pd.DataFrame(rows).set_index("Detector / training").style.format(
                    {"Mean conf.": "{:.3f}", "Accuracy": "{:.3f}", "ECE": "{:.3f}"}), width="stretch")
        else:
            st.warning("NOT YET MEASURED — run ensemble.py")

# ================================================================== Confusion matrices
elif page == "cm":
    header("Confusion Matrices", "Extension-level split 0 · held-out test extensions")
    with st.container(border=True):
        show_fig("confusion_matrices")

# ================================================================== Explainability
elif page == "explain":
    header("Explainability", "Why was this session flagged? Occlusion importance on the selected detector")
    with st.container(border=True):
        m, mf = pick_model("ex"); fam, sid = pick_session("ex")
    if m is None:
        st.warning("Model file not found — run train.py first."); st.stop()
    exp = cached_explain(m, mf, sid); g = by_sid[sid]
    l, r = st.columns([7, 5])
    with l, st.container(border=True):
        st.plotly_chart(draw_graph(g, exp, 430), width="stretch"); legend()
    with r:
        banner(exp["prob"], mf); st.write(""); path_chips(g, exp)
    t1, t2, t3 = st.tabs(["Node importance", "Edge importance", "Rule-based explanation"])
    with t1:
        nodes = sorted(((exp["node_importance"][i], g["ntype"][i], g["names"][i]) for i in range(len(g["ntype"]))), reverse=True)[:8]
        st.dataframe(pd.DataFrame(nodes, columns=["Δ log-odds if removed", "type", "node"]).round(3), hide_index=True, width="stretch")
    with t2:
        edges = sorted(exp["edge_importance"], key=lambda e: -e["importance"])[:8]
        st.dataframe(pd.DataFrame([{"Δ log-odds if removed": round(e["importance"], 3), "relation": e["rel"],
                                    "edge": f"{g['names'][e['src']]} → {g['names'][e['dst']]}"} for e in edges]),
                     hide_index=True, width="stretch")
    with t3:
        for line in rule_explain(events[sid]) or ["No rule fired."]: st.write("•", line)
    st.caption("Importance = log-odds(suspicious | full graph) − log-odds(suspicious | node/edge removed): measured model outputs, not attention weights.")

# ================================================================== Unseen-flow & ablation
elif page == "unseen":
    header("Unseen-Flow & Ablation", "Which flows are caught when the family was never seen in training — and which information matters?")
    un, ab = read_json("results/unseen.json"), read_json("results/ablation.json")
    t1, t2 = st.tabs(["Unseen-flow generalisation", "Ablation"])
    with t1:
        with st.container(border=True):
            section("Recall on the never-seen suspicious family", "Mean over 5 splits · first row removes both Wasm-involving families from training")
            df = pivot(un, "setting", "recall", [m for m in ALL_MODELS if m != "Rule R1 (co-occurrence)"])
            df.index = [i.replace("loso_", "leave out ").replace("heldout_wasm_flows", "HELD OUT: all Wasm flows (S3+S5)") for i in df.index]
            st.dataframe(shade(df), width="stretch")
        show_fig("unseen_flow")
    with t2:
        with st.container(border=True):
            section("F1 after removing information", "Extension-level split · mean over 5 splits")
            df = pivot(ab, "setting", "f1", ["RF (counts)", "MLP (counts)", "GCN", "GraphSAGE", "R-GCN"],
                       ["full", "no_auth", "no_jswasm", "no_dest", "no_taint"])
            df.index = ["Full graph", "− authentication nodes", "− JS/Wasm nodes", "− destination nodes", "− taint edges"]
            st.dataframe(shade(df), width="stretch")
        show_fig("ablation")

# ================================================================== Live lab run
else:
    header("Live Lab Run", "Generates a NEW extension (not in the dataset), runs it in real Chromium against the local lab, then classifies it")
    SCEN = [("B4_authed_approved_api", "Scenario 1", "Authenticated API Call", "Reads a credential and sends it to the approved API — the hard negative.", "#34d399"),
            ("S1_direct_cred_sink", "Scenario 2", "Direct Credential → Sink", "Cookie read, then sent straight to an unapproved host.", "#f2c14e"),
            ("S3_cred_wasm_sink", "Scenario 3", "Credential via WebAssembly", "Credential passes through a Wasm module before the sink.", "#e879f9"),
            ("S5_staged_multi_component", "Scenario 4", "Staged Multi-Component Flow", "Stashed in storage, read by another component, then sent.", "#22b8cf")]
    with st.container(border=True):
        section("Run settings")
        c1, c2 = st.columns([3, 1])
        m_choice = c1.radio("Detector trained on", TRAIN_CHOICES, horizontal=True)
        headed = c2.checkbox("Show browser window", True)
    clicked = None
    with st.container(border=True):
        section("Controlled scenarios", "Each run generates a fresh extension and loads it into an isolated browser profile")
        cols = st.columns(4)
        for col, (fam_id, k, t, d, colr) in zip(cols, SCEN):
            with col:
                st.markdown(
                    f"<div class='sc-card' style='border-top: 3px solid {colr};'>"
                    f"  <div class='sc-k' style='color:{colr}'>⚗ {k}</div>"
                    f"  <div class='sc-t'>{t}</div>"
                    f"  <div class='sc-d'>{d}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button("Run this scenario →", key=f"run_{fam_id}", width="stretch"): clicked = fam_id
    with st.container(border=True):
        section("Run any other scenario")
        c1, c2 = st.columns([4, 1])
        other = c1.selectbox("Scenario family", FAMILIES, index=FAMILIES.index("S6_chunked_ip_sink"), label_visibility="collapsed")
        if c2.button("Run →", key="run_other", width="stretch"): clicked = other
    if clicked:
        with st.spinner("Running browser session…"):
            cmd = [sys.executable, str(ROOT / "lab" / "live.py"), "--family", clicked] + (["--headed"] if headed else [])
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            st.error(r.stderr[-2000:]); st.stop()
        meta = json.loads(r.stdout.strip().splitlines()[-1])
        evs = load_events(ROOT / "data" / "live" / meta["session_id"])[meta["session_id"]]
        st.session_state["live"] = (meta, evs)
    if "live" in st.session_state:
        meta, evs = st.session_state["live"]; mc = m_choice
        g = build_graph(evs, meta)
        model = model_all if mc == TRAIN_CHOICES[0] else model_unseen
        exp = explain(model, g)
        st.write(""); section("Result", f"{meta['family']} · ground-truth label: {'suspicious' if meta['label'] else 'benign'} · {len(evs)} telemetry events")
        l, r = st.columns([5, 7])
        with l:
            banner(exp["prob"], FILE_ALL if mc == TRAIN_CHOICES[0] else FILE_UNSEEN); st.write(""); path_chips(g, exp)
        with r, st.container(border=True):
            st.plotly_chart(draw_graph(g, exp, 400), width="stretch"); legend()
        t1, t2 = st.tabs(["Runtime events", "Rule-based explanation"])
        with t1: st.dataframe(events_df(evs), hide_index=True, width="stretch")
        with t2:
            for line in rule_explain(evs) or ["No rule fired."]: st.write("•", line)
