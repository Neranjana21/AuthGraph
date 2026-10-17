"""Out-of-fold calibration experiment.
5 extension-disjoint folds -> train on 4 (early-stop on a validation slice of those) -> logits for the held-out fold.
Pooled out-of-fold (OOF) logits of all 576 sessions are the calibration set. Calibrators are evaluated by
CROSS-FITTING (fit on 4 folds' OOF logits, score the 5th), so the reported improvement is on unseen extensions.
Output: results/calibration_oof.json"""
import json, random
from collections import defaultdict
from pathlib import Path
import numpy as np, torch, torch.nn.functional as F

import train as T
from authgraph.data import load_graphs, batch_graphs
from calibrate import ece

ROOT = Path(__file__).resolve().parent


def folds_by_extension(graphs, k=5, seed=0):
    by_fam = defaultdict(set)
    for g in graphs: by_fam[g["family"]].add(g["extension_id"])
    rng, fold = random.Random(seed), {}
    for fam, exts in sorted(by_fam.items()):
        exts = sorted(exts); rng.shuffle(exts)
        for i, e in enumerate(exts): fold[e] = i % k
    return fold


def logits(model, gs):
    model.eval()
    with torch.no_grad():
        l = torch.cat([model(batch_graphs([g])) for g in gs])
    return (l[:, 1] - l[:, 0]).numpy()                      # log-odds of "suspicious"


def nll(m, y):
    p = 1 / (1 + np.exp(-m)); p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit_T(m, y):
    t = torch.zeros(1, requires_grad=True); mt, yt = torch.tensor(m, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)
    opt = torch.optim.LBFGS([t], lr=0.1, max_iter=300)
    def cl():
        opt.zero_grad(); loss = F.binary_cross_entropy_with_logits(mt / t.exp(), yt); loss.backward(); return loss
    opt.step(cl); return float(t.exp().detach())


def fit_platt(m, y):
    ab = torch.tensor([1.0, 0.0], requires_grad=True); mt, yt = torch.tensor(m, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)
    opt = torch.optim.LBFGS([ab], lr=0.1, max_iter=300)
    def cl():
        opt.zero_grad(); loss = F.binary_cross_entropy_with_logits(ab[0] * mt + ab[1], yt); loss.backward(); return loss
    opt.step(cl); return [float(v) for v in ab.detach()]


def stats(m, y):
    p = 1 / (1 + np.exp(-m))
    return {"ece": ece(p, y), "nll": nll(m, y), "brier": float(np.mean((p - y) ** 2)),
            "mean_conf": float(np.mean(np.maximum(p, 1 - p))), "accuracy": float(np.mean((p >= .5) == y)),
            "max_conf": float(np.max(np.maximum(p, 1 - p)))}


EDGES = [0.5, 0.9, 0.99, 0.999, 1.0000001]


def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def make_bins(m, y):
    p = 1 / (1 + np.exp(-m)); conf = np.maximum(p, 1 - p); ok = ((p >= .5) == y); rows = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        sel = (conf >= a) & (conf < b); n = int(sel.sum()); k = int(ok[sel].sum()); lo, hi = wilson(k, n)
        rows.append({"lo": a, "hi": min(b, 1.0), "n": n, "correct": k, "accuracy": (k / n if n else None), "ci_lo": lo, "ci_hi": hi})
    return rows


def apply_bins(bins, m):
    """binned empirical probability of the PREDICTED class -> P(suspicious)"""
    p = 1 / (1 + np.exp(-m)); conf = np.maximum(p, 1 - p); out = np.zeros(len(m))
    for i in range(len(m)):
        for r in bins:
            if r["lo"] <= conf[i] < r["hi"] + 1e-9 and r["n"]:
                a = r["accuracy"]; out[i] = a if p[i] >= .5 else 1 - a; break
        else:
            out[i] = p[i]
    return out


def main():
    graphs = load_graphs(ROOT / "data" / "graphs.pkl")
    fold = folds_by_extension(graphs)
    out = {}
    for kind, name in (("SAGE", "GraphSAGE"), ("RGCN", "R-GCN")):
        m_oof = np.zeros(len(graphs)); y = np.array([g["label"] for g in graphs]); f_of = np.array([fold[g["extension_id"]] for g in graphs])
        for k in range(5):
            te = [g for g in graphs if fold[g["extension_id"]] == k]
            rest = [g for g in graphs if fold[g["extension_id"]] != k]
            exts = sorted({g["extension_id"] for g in rest}); random.Random(k).shuffle(exts)
            va_e = set(exts[: len(exts) // 4])
            tr = [g for g in rest if g["extension_id"] not in va_e]; va = [g for g in rest if g["extension_id"] in va_e]
            model, _, _ = T.train_gnn(kind, tr, va, k)
            m_oof[[i for i, g in enumerate(graphs) if fold[g["extension_id"]] == k]] = logits(model, te)
            print(name, "fold", k, "done", flush=True)
        # cross-fitted calibrators
        cal = {"raw": m_oof.copy(), "temperature": np.zeros(len(y)), "platt": np.zeros(len(y))}
        Ts = []
        for k in range(5):
            tr_i, te_i = f_of != k, f_of == k
            T_k = fit_T(m_oof[tr_i], y[tr_i]); Ts.append(T_k); cal["temperature"][te_i] = m_oof[te_i] / T_k
            a, b = fit_platt(m_oof[tr_i], y[tr_i]); cal["platt"][te_i] = a * m_oof[te_i] + b
        binned = np.zeros(len(y))
        for k in range(5):                                   # cross-fitted histogram-binning calibrator
            pb = apply_bins(make_bins(m_oof[f_of != k], y[f_of != k]), m_oof[f_of == k])
            binned[f_of == k] = np.log(np.clip(pb, 1e-6, 1 - 1e-6) / (1 - np.clip(pb, 1e-6, 1 - 1e-6)))
        cal["binned"] = binned
        res = {k: stats(v, y) for k, v in cal.items()}
        res["bins"] = make_bins(m_oof, y)
        res["T_per_fold"] = Ts; res["T_final"] = fit_T(m_oof, y); res["platt_final"] = fit_platt(m_oof, y)
        print("   bins:", [(round(b["lo"],3), b["n"], b["correct"], None if b["accuracy"] is None else round(b["accuracy"],3), round(b["ci_lo"],3), round(b["ci_hi"],3)) for b in res["bins"]])
        res["oof_errors"] = int(np.sum((m_oof >= 0) != y))
        out[name] = res
        print(name, "OOF errors", res["oof_errors"], "of", len(y), " T_final=%.2f" % res["T_final"])
        for k in ("raw", "temperature", "platt", "binned"):
            r = res[k]; print(f"   {k:12s} ECE {r['ece']:.3f}  NLL {r['nll']:.3f}  Brier {r['brier']:.3f}  mean conf {r['mean_conf']:.3f}  acc {r['accuracy']:.3f}  max conf {r['max_conf']:.4f}")
    (ROOT / "results" / "calibration_oof.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
