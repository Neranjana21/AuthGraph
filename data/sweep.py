"""Systematic UI bug sweep (Streamlit AppTest). Prints only failures + a summary."""
import sys
from streamlit.testing.v1 import AppTest
from authgraph.data import load_graphs

PAGES = {"dash": ":material/dashboard: Dashboard", "replay": ":material/replay: Session Replay",
         "graph": ":material/hub: Graph Visualization", "models": ":material/compare_arrows: Model Comparison",
         "cm": ":material/grid_on: Confusion Matrices", "explain": ":material/psychology: Explainability",
         "unseen": ":material/science: Unseen-Flow & Ablation", "live": ":material/play_circle: Live Lab Run"}
graphs = load_graphs("data/graphs.pkl"); fams = sorted({g["family"] for g in graphs})
fails, checks = [], 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond: fails.append(msg); print("FAIL:", msg, flush=True)


def new(page, det=0):
    at = AppTest.from_file(str(__import__("pathlib").Path(__file__).resolve().parent.parent / "dashboard.py"), default_timeout=300); at.run()
    at.sidebar.radio[0].set_value(PAGES[page]); at.sidebar.selectbox[0].set_value(list(at.sidebar.selectbox[0].options)[det]); at.run()
    return at


def text(at): return " ".join(m.value for m in at.markdown)


# 1. every page x detector
for p in PAGES:
    for det in (0, 1):
        at = new(p, det); check(not at.exception, f"page {p} det{det}: {at.exception[0].value if at.exception else ''}")
check("CONTROLLED LAB" not in text(new("dash")), "badge still visible")

# 2. session pages x every family x detector (x training choice on Explainability)
for p in ("graph", "explain"):
    for det in (0, 1):
        at = new(p, det)
        for fam in fams:
            at.selectbox(key=("famgr" if p == "graph" else "famex")).set_value(fam); at.run()
            check(not at.exception, f"{p} det{det} {fam}: {at.exception[0].value if at.exception else ''}")
            if p == "explain":
                at.radio(key="trex").set_value("Trained WITHOUT Wasm exfiltration flows"); at.run()
                check(not at.exception, f"{p} det{det} {fam} no-wasm detector: {at.exception[0].value if at.exception else ''}")
                at.radio(key="trex").set_value("All families (extension split)"); at.run()

# 3. replay behaviour the user reported
at = new("replay")
sid = at.selectbox(key="sidrp").value; sl = at.slider(key=f"rp_k_{sid}")
check(sl.value == 0, f"replay should start at 0 events, got {sl.value}")
check("READY" in text(at), "replay start state should show READY")
n = sl.max
sl.set_value(max(1, n // 2)); at.run()
check(not at.exception, "replay mid-slider exception")
check("OBSERVING" in text(at), "partial session must show OBSERVING (no verdict)")
check("confidence" not in text(at).split("OBSERVING")[1][:600].lower().replace("confidence is reported", "").replace("confidence appear", ""), "partial session must not claim a confidence")
at.slider(key=f"rp_k_{sid}").set_value(n); at.run()
check(("SUSPICIOUS" in text(at)) or ("BENIGN" in text(at)), "complete session must show a verdict")
at.select_slider(key="rp_speed").set_value("Fast"); at.run()
at.slider(key=f"rp_k_{sid}").set_value(0); at.run()
at.button(key="rp_play").click().run()
check(not at.exception, "play exception")
check(at.slider(key=f"rp_k_{sid}").value == n, "after Play the slider must sit on the last event")
# leave and re-enter -> back to 0
at.sidebar.radio[0].set_value(PAGES["dash"]); at.run(); at.sidebar.radio[0].set_value(PAGES["replay"]); at.run()
check(at.slider(key=f"rp_k_{at.selectbox(key='sidrp').value}").value == 0, "re-entering Session Replay must restart at 0")
# changing session -> 0
at.selectbox(key="famrp").set_value("S5_staged_multi_component"); at.run()
check(at.slider(key=f"rp_k_{at.selectbox(key='sidrp').value}").value == 0, "changing family must restart at 0")

# 4. every family can be replayed to the end without errors
at = new("replay"); at.select_slider(key="rp_speed").set_value("Fast"); at.run()
for fam in fams:
    at.selectbox(key="famrp").set_value(fam); at.run()
    at.button(key="rp_play").click().run()
    check(not at.exception, f"replay play {fam}: {at.exception[0].value if at.exception else ''}")

# 5. live run end-to-end (headless browser)
at = new("live"); at.checkbox[0].set_value(False); at.run()
at.button(key="run_B4_authed_approved_api").click().run()
check(not at.exception, f"live run: {at.exception[0].value if at.exception else ''}")
check("BENIGN" in text(at) or "SUSPICIOUS" in text(at), "live run must show a verdict")
print(f"\nchecks: {checks}, failures: {len(fails)}")
sys.exit(1 if fails else 0)
