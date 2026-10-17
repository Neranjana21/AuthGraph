"""Validation-only hyper-parameter search, identical grid/budget for every GNN. Test sets are never used.
Selection criterion: mean best validation loss over 3 extension-level splits (seeds 0-2).
Writes results/tuned_config.json and results/tuning_log.json."""
import itertools, json, time
import numpy as np
import train as T
from authgraph.data import load_graphs, extension_split

graphs = load_graphs(T.ROOT / "data" / "graphs.pkl")
splits = [extension_split(graphs, s) for s in range(3)]
grid = {"GCN": [{"h": h, "lr": lr, "wd": wd, "bases": 0} for h, lr, wd in itertools.product([16, 32, 64], [5e-3, 1e-2], [1e-4, 1e-3])]}
grid["SAGE"] = [dict(c) for c in grid["GCN"]]
grid["RGCN"] = [{"h": h, "lr": lr, "wd": wd, "bases": b} for h, lr, wd, b in itertools.product([16, 32, 64], [5e-3, 1e-2], [1e-4, 1e-3], [0, 4])]
log, best = [], {}
for kind, cfgs in grid.items():
    for cfg in cfgs:
        t = time.time()
        vl = [T.train_gnn(kind, sp["train"], sp["val"], i, cfg)[0].best_val for i, sp in enumerate(splits)]
        log.append({"model": kind, **cfg, "val_loss_mean": float(np.mean(vl)), "val_loss_std": float(np.std(vl))})
        print(kind, cfg, f"val_loss={np.mean(vl):.4f}  ({time.time()-t:.0f}s)", flush=True)
    best[kind] = min((r for r in log if r["model"] == kind), key=lambda r: r["val_loss_mean"])
    best[kind] = {k: best[kind][k] for k in ("h", "lr", "wd", "bases")}
json.dump(best, open(T.ROOT / "results" / "tuned_config.json", "w"), indent=1)
json.dump(log, open(T.ROOT / "results" / "tuning_log.json", "w"), indent=1)
print("selected:", best)
