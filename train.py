"""Train + evaluate every model for every experiment.  Results -> results/<exp>.json, experiments.csv.

  python train.py --exp main        # extension-level split, 5 split seeds
  python train.py --exp unseen      # held-out Wasm flows + leave-one-suspicious-family-out
  python train.py --exp ablation    # graph-information ablations
"""
import argparse, csv, json, os, pickle, time
from datetime import datetime
from pathlib import Path
import numpy as np, torch, torch.nn.functional as F
import pickle
from authgraph.forest import RandomForest

from authgraph.data import (load_graphs, extension_split, unseen_split, ablate, flat_features,
                            batch_graphs, SUSP_FAMILIES, WASM_SUSP)
from authgraph.graph import RELS, N_FEAT, load_events
from authgraph.models import GCN, SAGE, RGCN, MLP, n_params
from authgraph.metrics import compute
from authgraph.rules import RULES

ROOT = Path(__file__).resolve().parent
RES, MODELS = ROOT / "results", ROOT / "models"
RES.mkdir(exist_ok=True); MODELS.mkdir(exist_ok=True)
CSV_COLS = ["timestamp", "exp", "setting", "model", "split_seed", "model_seed", "n_train", "n_val", "n_test",
            "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "fpr", "fnr",
            "train_s", "infer_ms_per_graph", "params", "epochs"]
EPOCHS, LR, PATIENCE = 200, 5e-3, 40


def log_csv(row):
    p = ROOT / "experiments.csv"
    new = not p.exists()
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, CSV_COLS);
        if new: w.writeheader()
        w.writerow({k: row.get(k, "") for k in CSV_COLS})


def _graph_infer(model, graphs):
    model.eval(); probs = []
    t = time.perf_counter()
    with torch.no_grad():
        for g in graphs:                                   # batch size 1 = per-session inference
            probs.append(F.softmax(model(batch_graphs([g])), 1)[0, 1].item())
    return np.array(probs), (time.perf_counter() - t) / max(len(graphs), 1) * 1000


DEFAULT_CFG = {"h": 64, "lr": LR, "wd": 1e-4, "bases": 0}
_tc = ROOT / "results" / "tuned_config.json"
TUNED = json.loads(_tc.read_text()) if _tc.exists() else {}


def make_model(kind, cfg):
    if kind == "RGCN": return RGCN(N_FEAT, RELS, cfg["h"], 3, cfg.get("bases", 0))
    return (GCN if kind == "GCN" else SAGE)(N_FEAT, cfg["h"])


def train_gnn(kind, tr, va, seed, cfg=None):
    cfg = cfg or TUNED.get(kind, DEFAULT_CFG)
    torch.manual_seed(seed); np.random.seed(seed)
    model = make_model(kind, cfg)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"], weight_decay=cfg["wd"])
    btr, bva = batch_graphs(tr), batch_graphs(va)
    w = torch.tensor([1.0, 1.0])
    best, best_state, bad, curve = 1e9, None, 0, []
    t0 = time.perf_counter()
    for ep in range(EPOCHS):
        model.train(); opt.zero_grad()
        loss = F.cross_entropy(model(btr), btr["y"], weight=w); loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            lo = model(bva); vl = F.cross_entropy(lo, bva["y"]).item()
            va_acc = (lo.argmax(1) == bva["y"]).float().mean().item()
        curve.append({"epoch": ep, "train_loss": loss.item(), "val_loss": vl, "val_acc": va_acc})
        if vl < best - 1e-4: best, best_state, bad = vl, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= PATIENCE: break
    train_s = time.perf_counter() - t0
    model.load_state_dict(best_state)
    model.best_val = best
    return model, train_s, curve


def prep_flat(tr, with_reach):
    X = np.stack([flat_features(g, with_reach) for g in tr]); X = np.log1p(X)
    return X, X.mean(0), X.std(0) + 1e-6


def run_models(splits, setting, split_seed, exp, events_by_sid, save_first=False, which=None, keep_curves=False):
    """Train/evaluate all models on one split. Returns list of result dicts."""
    tr, va, te = splits["train"], splits["val"], splits["test"]
    yte = np.array([g["label"] for g in te]); out = []
    meta = dict(exp=exp, setting=setting, split_seed=split_seed, model_seed=split_seed,
                n_train=len(tr), n_val=len(va), n_test=len(te))

    def record(name, probs, train_s, infer_ms, params, epochs, extra=None):
        m = compute(yte, probs)
        r = {**meta, "model": name, **m, "train_s": train_s, "infer_ms_per_graph": infer_ms,
             "params": params, "epochs": epochs, "y_true": yte.tolist(), "y_prob": [float(p) for p in probs],
             "test_sessions": [g["session_id"] for g in te], "test_family": [g["family"] for g in te],
             "taint_visible": [bool(g["taint_visible"]) for g in te], **(extra or {})}
        out.append(r)
        log_csv({**meta, **m, "model": name, "timestamp": datetime.now().isoformat(timespec="seconds"),
                 "train_s": round(train_s, 3), "infer_ms_per_graph": round(infer_ms, 4), "params": params, "epochs": epochs})

    want = lambda n: which is None or n in which
    # --- rules (no training)
    for name, fn in RULES.items():
        if not want(name): continue
        t = time.perf_counter()
        p = np.array([fn(events_by_sid[g["session_id"]]) for g in te], dtype=float)
        record(name, p, 0.0, (time.perf_counter() - t) / len(te) * 1000, 0, 0)
    # --- flat models
    for name, reach in (("RF (counts)", False), ("RF (counts+reachability)", True)):
        if not want(name): continue
        Xtr, _, _ = prep_flat(tr, reach)
        t = time.perf_counter()
        rf = RandomForest(200, seed=split_seed).fit(Xtr, [g["label"] for g in tr])
        ts = time.perf_counter() - t
        Xte = np.log1p(np.stack([flat_features(g, reach) for g in te]))
        t = time.perf_counter(); p = rf.predict_proba(Xte)[:, 1]
        record(name, p, ts, (time.perf_counter() - t) / len(te) * 1000, rf.node_count, 0)
        if save_first: pickle.dump(rf, open(MODELS / f"RF_{'reach' if reach else 'counts'}_{setting}.pkl", "wb"))
    if want("MLP (counts)"):
        Xtr, mu, sd = prep_flat(tr, False); Xva = (np.log1p(np.stack([flat_features(g) for g in va])) - mu) / sd
        torch.manual_seed(split_seed)
        mlp = MLP(Xtr.shape[1]); opt = torch.optim.Adam(mlp.parameters(), lr=5e-3, weight_decay=1e-4)
        xt = torch.tensor((Xtr - mu) / sd, dtype=torch.float32); yt = torch.tensor([g["label"] for g in tr])
        xv = torch.tensor(Xva, dtype=torch.float32); yv = torch.tensor([g["label"] for g in va])
        best, bs, bad, t0, ep = 1e9, None, 0, time.perf_counter(), 0
        for ep in range(EPOCHS):
            mlp.train(); opt.zero_grad(); F.cross_entropy(mlp(xt), yt).backward(); opt.step()
            mlp.eval()
            with torch.no_grad(): vl = F.cross_entropy(mlp(xv), yv).item()
            if vl < best - 1e-4: best, bs, bad = vl, {k: v.clone() for k, v in mlp.state_dict().items()}, 0
            else:
                bad += 1
                if bad >= PATIENCE: break
        ts = time.perf_counter() - t0; mlp.load_state_dict(bs); mlp.eval()
        Xte = torch.tensor((np.log1p(np.stack([flat_features(g) for g in te])) - mu) / sd, dtype=torch.float32)
        t = time.perf_counter()
        with torch.no_grad(): p = F.softmax(mlp(Xte), 1)[:, 1].numpy()
        record("MLP (counts)", p, ts, (time.perf_counter() - t) / len(te) * 1000, n_params(mlp), ep + 1)
    # --- GNNs
    for kind, name in (("GCN", "GCN"), ("SAGE", "GraphSAGE"), ("RGCN", "R-GCN")):
        if not want(name): continue
        model, ts, curve = train_gnn(kind, tr, va, split_seed)
        p, ims = _graph_infer(model, te)
        record(name, p, ts, ims, n_params(model), len(curve), {"curve": curve} if keep_curves else None)
        if save_first: torch.save(model.state_dict(), MODELS / f"{name}_{setting}.pt")
    return out


def save(exp, results):
    (RES / f"{exp}.json").write_text(json.dumps(results))
    print(f"saved results/{exp}.json  ({len(results)} runs)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="all", choices=["main", "unseen", "ablation", "all"])
    ap.add_argument("--graphs", default=str(ROOT / "data" / "graphs.pkl"))
    ap.add_argument("--raw", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--split-seeds", type=int, default=5)
    a = ap.parse_args()
    graphs = load_graphs(a.graphs); ev = load_events(a.raw)
    seeds = range(a.split_seeds)
    print(f"{len(graphs)} graphs, {len({g['extension_id'] for g in graphs})} extensions")

    if a.exp in ("main", "all"):
        res = []
        for s in seeds:
            print("main split", s, flush=True)
            res += run_models(extension_split(graphs, s), "extension_split", s, "main", ev,
                              save_first=(s == 0), keep_curves=True)
        save("main", res)
    if a.exp in ("unseen", "all"):
        res = []
        settings = [("heldout_wasm_flows", WASM_SUSP)] + [(f"loso_{f}", [f]) for f in SUSP_FAMILIES]
        for name, held in settings:
            for s in seeds:
                print("unseen", name, "seed", s, flush=True)
                res += run_models(unseen_split(graphs, s, held), name, s, "unseen", ev,
                                  save_first=(name == "heldout_wasm_flows" and s == 0))
        save("unseen", res)
    if a.exp in ("ablation", "all"):
        res = []
        for mode in ("full", "no_auth", "no_jswasm", "no_dest", "no_taint"):
            gs = [ablate(g, mode) for g in graphs]
            for s in seeds:
                print("ablation", mode, "seed", s, flush=True)
                res += run_models(extension_split(gs, s), mode, s, "ablation", ev,
                                  which={"MLP (counts)", "RF (counts)", "RF (counts+reachability)", "GCN", "GraphSAGE", "R-GCN"})
        save("ablation", res)


if __name__ == "__main__":
    main()
