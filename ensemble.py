"""Deep-ensemble confidence (M independently seeded GNNs, mean of member probabilities).

1. Out-of-fold experiment (5 extension-disjoint folds): single model vs ensemble -> ECE / log-loss / Brier + score-band
   accuracy with 95% Wilson intervals.  -> results/calibration_ens.json["oof"]
2. Final ensembles for the dashboard (extension split 0, and Wasm-flows-held-out), their held-out TEST calibration,
   saved to models/ENS_<arch>_<setting>.pt.  -> results/calibration_ens.json["test"]
"""
import json, random, sys
from pathlib import Path
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F

import train as T
from authgraph.models import Ensemble
from authgraph.data import load_graphs, extension_split, unseen_split, batch_graphs, WASM_SUSP
from calibrate import ece
from calibrate_oof import folds_by_extension, wilson, nll

ROOT = Path(__file__).resolve().parent
M = 10
EDGES = [0.5, 0.7, 0.85, 0.95, 0.99, 0.999, 1.0000001]


def train_members(kind, tr, va, seed0=0):
    return [T.train_gnn(kind, tr, va, seed0 + s)[0] for s in range(M)]


def probs(model, gs):
    model.eval()
    with torch.no_grad():
        return np.array([F.softmax(model(batch_graphs([g])), 1)[0, 1].item() for g in gs])


def stats(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"ece": ece(p, y), "nll": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), "brier": float(np.mean((p - y) ** 2)),
            "mean_conf": float(np.mean(np.maximum(p, 1 - p))), "accuracy": float(np.mean((p >= .5) == y)),
            "frac_conf_ge_999": float(np.mean(np.maximum(p, 1 - p) >= 0.999))}


def bins(p, y):
    conf = np.maximum(p, 1 - p); ok = ((p >= .5) == y); rows = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        sel = (conf >= a) & (conf < b); n = int(sel.sum()); k = int(ok[sel].sum()); lo, hi = wilson(k, n)
        rows.append({"lo": a, "hi": min(b, 1.0), "n": n, "correct": k, "accuracy": (k / n if n else None), "ci_lo": lo, "ci_hi": hi})
    return rows


def monotone_bins(rows):
    """Pool adjacent score bands (isotonic-style) until BOTH the observed accuracy and its 95% Wilson lower bound
    never decrease as the raw score rises -> a higher score can never display a lower confidence."""
    pools = [{"lo": r["lo"], "hi": r["hi"], "n": r["n"], "correct": r["correct"]} for r in rows if r["n"]]
    def lb(p): return wilson(p["correct"], p["n"])[0]
    def acc(p): return p["correct"] / p["n"]
    changed = True
    while changed:
        changed = False
        for i in range(len(pools) - 1):
            a, b = pools[i], pools[i + 1]
            if acc(a) >= acc(b) or lb(a) > lb(b):
                pools[i:i + 2] = [{"lo": a["lo"], "hi": b["hi"], "n": a["n"] + b["n"], "correct": a["correct"] + b["correct"]}]
                changed = True; break
    out = []
    for p in pools:
        lo, hi = wilson(p["correct"], p["n"])
        out.append({**p, "accuracy": p["correct"] / p["n"], "ci_lo": lo, "ci_hi": hi})
    return out


def main():
    graphs = load_graphs(ROOT / "data" / "graphs.pkl")
    out = {"oof": {}, "test": {}, "M": M}
    fold = folds_by_extension(graphs)
    y = np.array([g["label"] for g in graphs]); f_of = np.array([fold[g["extension_id"]] for g in graphs])
    for kind, name in (("SAGE", "GraphSAGE"), ("RGCN", "R-GCN")):
        p_ens, p_one = np.zeros(len(graphs)), np.zeros(len(graphs))
        for k in range(5):
            te = [g for g in graphs if fold[g["extension_id"]] == k]; rest = [g for g in graphs if fold[g["extension_id"]] != k]
            exts = sorted({g["extension_id"] for g in rest}); random.Random(k).shuffle(exts); va_e = set(exts[: len(exts) // 4])
            tr = [g for g in rest if g["extension_id"] not in va_e]; va = [g for g in rest if g["extension_id"] in va_e]
            mem = train_members(kind, tr, va, seed0=1000 * k)
            idx = np.where(f_of == k)[0]
            p_ens[idx] = probs(Ensemble(mem), te); p_one[idx] = probs(mem[0], te)
            print(name, "fold", k, "done", flush=True)
        out["oof"][name] = {"single": stats(p_one, y), "ensemble": stats(p_ens, y), "bins": bins(p_ens, y), "bins_mono": monotone_bins(bins(p_ens, y)),
                            "oof_errors_single": int(np.sum((p_one >= .5) != y)), "oof_errors_ensemble": int(np.sum((p_ens >= .5) != y))}
        for k_ in ("single", "ensemble"):
            r = out["oof"][name][k_]
            print(f"  {name:9s} {k_:9s} ECE {r['ece']:.3f}  NLL {r['nll']:.3f}  Brier {r['brier']:.3f}  mean conf {r['mean_conf']:.3f}  acc {r['accuracy']:.3f}  frac(conf>=.999) {r['frac_conf_ge_999']:.2f}", flush=True)
        print("  bins:", [(round(b["lo"], 3), b["n"], b["correct"]) for b in out["oof"][name]["bins"]], flush=True)

    # final ensembles used by the dashboard
    setups = {"extension_split": extension_split(graphs, 0), "heldout_wasm_flows": unseen_split(graphs, 0, WASM_SUSP)}
    for kind, name in (("SAGE", "GraphSAGE"), ("RGCN", "R-GCN")):
        for setting, sp in setups.items():
            mem = train_members(kind, sp["train"], sp["val"], seed0=0)
            ens = Ensemble(mem)
            torch.save({"kind": kind, "states": [m.state_dict() for m in mem]}, ROOT / "models" / f"ENS_{name}_{setting}.pt")
            yt = np.array([g["label"] for g in sp["test"]]); pt = probs(ens, sp["test"])
            out["test"][f"{name}_{setting}"] = {"n_test": len(yt), **stats(pt, yt)}
            r = out["test"][f"{name}_{setting}"]
            print(f"  TEST {name:9s} {setting:20s} n={len(yt)} ECE {r['ece']:.3f}  acc {r['accuracy']:.3f}  mean conf {r['mean_conf']:.3f}", flush=True)
    (ROOT / "results" / "calibration_ens.json").write_text(json.dumps(out, indent=1))
    print("saved results/calibration_ens.json")


if __name__ == "__main__":
    main()
