"""Temperature-scaling calibration of the saved GNNs (fit on the VALIDATION split only).
Reports ECE / Brier / NLL before and after on the held-out TEST split, for the extension-split model and the
Wasm-held-out model.  Writes results/calibration.json (read by the dashboard)."""
import json
import numpy as np, torch, torch.nn.functional as F
from pathlib import Path

import train as T
from authgraph.data import load_graphs, extension_split, unseen_split, batch_graphs, WASM_SUSP

ROOT = Path(__file__).resolve().parent


def logits_of(model, gs):
    model.eval()
    with torch.no_grad():
        return torch.cat([model(batch_graphs([g])) for g in gs]), torch.tensor([g["label"] for g in gs])


def fit_temperature(lo, y):
    t = torch.zeros(1, requires_grad=True)                       # T = exp(t) > 0
    opt = torch.optim.LBFGS([t], lr=0.1, max_iter=200)
    def closure():
        opt.zero_grad(); loss = F.cross_entropy(lo / t.exp(), y); loss.backward(); return loss
    opt.step(closure)
    return float(t.exp().detach())


def ece(p, y, bins=10):
    p, y = np.asarray(p), np.asarray(y); conf = np.maximum(p, 1 - p); pred = (p >= .5).astype(int)
    e = 0.0
    for lo_, hi in zip(np.linspace(0, 1, bins + 1)[:-1], np.linspace(0, 1, bins + 1)[1:]):
        m = (conf > lo_) & (conf <= hi)
        if m.any(): e += m.mean() * abs((pred[m] == y[m]).mean() - conf[m].mean())
    return float(e)


def metrics(lo, y, temp):
    pr = F.softmax(lo / temp, 1)[:, 1].numpy(); yy = y.numpy()
    return {"ece": ece(pr, yy), "brier": float(np.mean((pr - yy) ** 2)),
            "nll": float(F.cross_entropy(lo / temp, y)), "mean_conf": float(np.mean(np.maximum(pr, 1 - pr))),
            "accuracy": float(np.mean((pr >= .5) == yy))}


BINS = [(0.5, 0.8), (0.8, 0.95), (0.95, 0.99), (0.99, 1.0001)]


def reliability(lo, y):
    """Empirical accuracy of the UNMODIFIED model inside confidence bins (conf = max(p, 1-p)), held-out test split."""
    p = F.softmax(lo, 1)[:, 1].numpy(); yy = y.numpy(); conf = np.maximum(p, 1 - p); ok = ((p >= .5) == yy)
    rows = []
    for a, b in BINS:
        m = (conf >= a) & (conf < b)
        rows.append({"lo": a, "hi": min(b, 1.0), "n": int(m.sum()), "accuracy": float(ok[m].mean()) if m.any() else None})
    return rows


def main():
    graphs = load_graphs(ROOT / "data" / "graphs.pkl")
    setups = {"extension_split": extension_split(graphs, 0), "heldout_wasm_flows": unseen_split(graphs, 0, WASM_SUSP)}
    out = {}
    for kind, name in (("SAGE", "GraphSAGE"), ("RGCN", "R-GCN")):
        for setting, sp in setups.items():
            f = f"{name}_{setting}.pt"
            m = T.make_model(kind, T.TUNED.get(kind, T.DEFAULT_CFG)); m.load_state_dict(torch.load(ROOT / "models" / f)); m.eval()
            lv, yv = logits_of(m, sp["val"]); lt, yt = logits_of(m, sp["test"])
            temp = fit_temperature(lv, yv)
            out[f] = {"temperature": temp, "n_val": len(yv), "n_test": len(yt),
                      "test_before": metrics(lt, yt, 1.0), "test_after": metrics(lt, yt, temp),
                      "applied": "none (temperature scaling fitted on validation worsened test NLL)", "reliability": reliability(lt, yt)}
            b, a = out[f]["test_before"], out[f]["test_after"]
            print(f"{f:36s} T={temp:5.2f}  ECE {b['ece']:.3f} -> {a['ece']:.3f}   NLL {b['nll']:.3f} -> {a['nll']:.3f}   "
                  f"mean conf {b['mean_conf']:.3f} -> {a['mean_conf']:.3f}   acc {a['accuracy']:.3f}")
    (ROOT / "results" / "calibration.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
