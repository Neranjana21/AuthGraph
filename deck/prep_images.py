"""Resize dashboard screenshots for the deck and cut content-only crops (sidebar removed)."""
from pathlib import Path
from PIL import Image
S = Path(__file__).resolve().parent.parent / "screenshots"; O = Path(__file__).resolve().parent / "img"; O.mkdir(exist_ok=True)
X0 = 600                                   # content starts right of the sidebar at 2880 px width
def save(im, name, w):
    im = im.convert("RGB"); h = round(im.height * w / im.width); im.resize((w, h), Image.LANCZOS).save(O / f"{name}.jpg", quality=90, optimize=True)
    print(f"{name:26s} {w}x{h}")
def crop(name, y0, y1, out, w=1800, x0=X0, x1=2880):
    im = Image.open(S / f"{name}.png"); y1 = min(y1, im.height); save(im.crop((x0, y0, x1, y1)), out, w)
for n in ["01_dashboard", "02c_session_replay_complete", "03_graph_visualization", "06a_explainability", "07a_unseen_flow", "08b_live_result_wasm_exfiltration"]:
    save(Image.open(S / f"{n}.png"), "full_" + n.split("_", 1)[0], 1920)
crop("03_graph_visualization", 380, 1480, "c_graph")
crop("06a_explainability", 450, 1290, "c_explain")
crop("02c_session_replay_complete", 170, 1395, "c_replay")
crop("08b_live_result_wasm_exfiltration", 1070, 2000, "c_live_wasm")
crop("04d_confidence_calibration", 880, 2690, "c_calibration")
crop("04a_model_comparison_scores", 170, 900, "c_results_table")
crop("05_confusion_matrices", 170, 900, "c_confusion")
crop("04b_roc_pr_curves", 880, 2033, "c_roc_pr")
crop("04c_training_latency", 880, 1680, "c_training")
crop("07b_ablation", 170, 1829, "c_ablation")
crop("07a_unseen_flow", 170, 1868, "c_unseen")

crop("03_graph_visualization", 395, 1440, "c_graph_only", w=1500, x1=2010)
crop("06a_explainability", 488, 1485, "c_explain_graph", w=1500, x1=1842)
import shutil
for f in ["roc_curves", "pr_curves", "confusion_matrices", "training_curves", "latency"]:
    shutil.copy(S.parent / "figures" / "dark" / f"{f}.png", O / f"{f}.png")
print("figures copied")
