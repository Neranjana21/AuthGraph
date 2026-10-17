"""Extract every number used in the deck from the measured result files -> deck/data.json (no hand-typed metrics)."""
import json
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parent.parent / "results"
main = json.load(open(R / "main.json")); unseen = json.load(open(R / "unseen.json")); abl = json.load(open(R / "ablation.json"))
rep = json.load(open(R / "dataset_report.json")); ens = json.load(open(R / "calibration_ens.json"))
lat = json.load(open(R / "latency_build.json"))
ORDER = ["Rule R1 (co-occurrence)", "Rule R2 (taint)", "RF (counts)", "RF (counts+reachability)", "MLP (counts)", "GCN", "GraphSAGE", "R-GCN"]


def agg(runs, key):
    v = np.array([r[key] for r in runs], float); return float(np.nanmean(v)), float(np.nanstd(v))


out = {"order": ORDER}
out["main"] = {m: {k: agg([r for r in main if r["model"] == m], k)[0] for k in ("precision", "recall", "f1", "roc_auc", "pr_auc", "fpr", "fnr", "infer_ms_per_graph", "train_s", "params")}
               for m in ORDER}
for m in ORDER:
    out["main"][m]["f1_std"] = agg([r for r in main if r["model"] == m], "f1")[1]

settings = list(dict.fromkeys(r["setting"] for r in unseen))
out["unseen"] = {s: {m: {"recall": agg([r for r in unseen if r["setting"] == s and r["model"] == m], "recall")[0],
                         "recall_std": agg([r for r in unseen if r["setting"] == s and r["model"] == m], "recall")[1],
                         "fpr": agg([r for r in unseen if r["setting"] == s and r["model"] == m], "fpr")[0],
                         "f1": agg([r for r in unseen if r["setting"] == s and r["model"] == m], "f1")[0]} for m in ORDER} for s in settings}
out["unseen_n_test"] = {s: [r for r in unseen if r["setting"] == s][0]["n_test"] for s in settings}

modes = ["full", "no_auth", "no_jswasm", "no_dest", "no_taint"]
out["ablation"] = {mo: {m: agg([r for r in abl if r["setting"] == mo and r["model"] == m], "f1")[0]
                        for m in ("RF (counts)", "MLP (counts)", "GCN", "GraphSAGE", "R-GCN")} for mo in modes}

# recall on suspicious test sessions by taint visibility (pooled over the 5 splits)
vis = {}
for m in ORDER:
    v, l = [], []
    for r in [r for r in main if r["model"] == m]:
        for y, p, tv in zip(r["y_true"], r["y_prob"], r["taint_visible"]):
            if y == 1: (v if tv else l).append(p >= .5)
    vis[m] = {"visible": float(np.mean(v)), "n_visible": len(v), "lost": float(np.mean(l)) if l else None, "n_lost": len(l)}
out["taint_visibility"] = vis

out["dataset"] = {k: rep[k] for k in ("sessions_completed", "graphs", "extensions", "unique_events", "duplicates_removed", "events_failing_schema",
                                      "credential_value_leaks", "sessions_where_telemetry_requests_differ_from_server_log", "nodes_mean", "edges_mean",
                                      "nodes_min", "nodes_max", "edges_min", "edges_max", "suspicious_taint_visible_at_sink", "suspicious_taint_lost")}
out["dataset"]["label_counts"] = rep["label_counts"]
out["latency_build_ms"] = lat["graph_build_ms_mean"]
out["calibration"] = {arch: {"single": r["single"], "ensemble": r["ensemble"], "bins": r["bins_mono"]} for arch, r in ens["oof"].items()}
out["calibration_test"] = ens["test"]
(Path(__file__).resolve().parent / "data.json").write_text(json.dumps(out, indent=1))
print("ok")
u = out["unseen"]["heldout_wasm_flows"]
print("heldout wasm recall:", {m: round(u[m]["recall"], 3) for m in ORDER})
print("calibration GraphSAGE:", {k: round(out["calibration"]["GraphSAGE"]["ensemble"][k], 3) for k in ("ece", "nll", "brier")})
print("taint lost R2 / GraphSAGE:", vis["Rule R2 (taint)"], vis["GraphSAGE"])
