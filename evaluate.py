"""Aggregate results/*.json -> tables (results/tables.md, results/summary.json) and figures/*.png.
Only reads measured results; anything missing is reported as NOT YET MEASURED."""
import json, time
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve

ROOT = Path(__file__).resolve().parent
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
ORDER = ["Rule R1 (co-occurrence)", "Rule R2 (taint)", "RF (counts)", "RF (counts+reachability)",
         "MLP (counts)", "GCN", "GraphSAGE", "R-GCN"]
PAL = {"Rule R1 (co-occurrence)": "#999999", "Rule R2 (taint)": "#666666", "RF (counts)": "#E69F00",
       "RF (counts+reachability)": "#D55E00", "MLP (counts)": "#CC79A7", "GCN": "#56B4E9",
       "GraphSAGE": "#0072B2", "R-GCN": "#009E73"}
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})


def load(name):
    p = RES / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def ms(vals):
    v = np.array([x for x in vals if x == x], dtype=float)
    return (v.mean(), v.std()) if len(v) else (float("nan"), float("nan"))


def fmt(vals, pct=False):
    m, s = ms(vals)
    return "NaN" if m != m else (f"{m:.3f} ± {s:.3f}")


def group(runs, key):
    g = defaultdict(list)
    for r in runs: g[r[key]].append(r)
    return g


def main_table(main):
    rows = ["| Model | Precision | Recall | F1 | ROC-AUC | PR-AUC | FPR | FNR | Infer ms/graph | Train s | Params |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    summ = {}
    for m in ORDER:
        rs = [r for r in main if r["model"] == m]
        if not rs: continue
        rows.append(f"| {m} | " + " | ".join(fmt([r[k] for r in rs]) for k in
                    ["precision", "recall", "f1", "roc_auc", "pr_auc", "fpr", "fnr"]) +
                    f" | {np.mean([r['infer_ms_per_graph'] for r in rs]):.3f} | {np.mean([r['train_s'] for r in rs]):.2f} | {int(np.mean([r['params'] for r in rs]))} |")
        summ[m] = {k: ms([r[k] for r in rs]) for k in ["precision", "recall", "f1", "roc_auc", "pr_auc", "fpr", "fnr", "accuracy"]}
    return "\n".join(rows), summ


def fig_comparison(summ):
    ms_ = [m for m in ORDER if m in summ]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    w = 0.26
    for i, (k, lab) in enumerate([("precision", "Precision"), ("recall", "Recall"), ("f1", "F1")]):
        ax.bar(np.arange(len(ms_)) + (i - 1) * w, [summ[m][k][0] for m in ms_], w,
               yerr=[summ[m][k][1] for m in ms_], label=lab, capsize=2, color=["#56B4E9", "#E69F00", "#009E73"][i])
    ax.set_xticks(range(len(ms_))); ax.set_xticklabels([m.replace(" (", "\n(") for m in ms_], fontsize=7)
    ax.set_ylim(0, 1.05); ax.set_title("Extension-level split: mean ± std over 5 splits (higher is better)")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.22), frameon=False); fig.tight_layout(); fig.savefig(FIG / "model_comparison.png", bbox_inches="tight"); plt.close(fig)


def fig_curves(main):
    r0 = [r for r in main if r["split_seed"] == 0]
    for kind in ("roc", "pr"):
        fig, ax = plt.subplots(figsize=(4.6, 4))
        for m in ORDER:
            for r in r0:
                if r["model"] != m or len(set(r["y_true"])) < 2: continue
                y, p = np.array(r["y_true"]), np.array(r["y_prob"])
                if kind == "roc":
                    x, yy, _ = roc_curve(y, p); ax.plot(x, yy, label=m, color=PAL[m])
                else:
                    pr, rc, _ = precision_recall_curve(y, p); ax.plot(rc, pr, label=m, color=PAL[m])
        ax.set_xlabel("FPR" if kind == "roc" else "Recall"); ax.set_ylabel("TPR" if kind == "roc" else "Precision")
        ax.set_title(("ROC" if kind == "roc" else "Precision-Recall") + " (split 0, test extensions)")
        ax.legend(fontsize=6, frameon=False); fig.tight_layout(); fig.savefig(FIG / f"{kind}_curves.png"); plt.close(fig)


def fig_confusion(main):
    sel = [m for m in ["Rule R1 (co-occurrence)", "Rule R2 (taint)", "RF (counts)", "GCN", "GraphSAGE", "R-GCN"]]
    fig, axs = plt.subplots(1, len(sel), figsize=(2.3 * len(sel), 2.6))
    for ax, m in zip(axs, sel):
        rs = [r for r in main if r["model"] == m and r["split_seed"] == 0]
        if not rs: continue
        r = rs[0]; cm = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
        ax.imshow(cm, cmap="Blues")
        for i in range(2):
            for j in range(2): ax.text(j, i, cm[i, j], ha="center", va="center", color="white" if cm[i, j] > cm.max() / 2 else "black")
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1]); ax.set_xticklabels(["Benign", "Susp."]); ax.set_yticklabels(["Benign", "Susp."])
        ax.set_title(m.replace(" (", "\n("), fontsize=7); ax.set_xlabel("Predicted")
    axs[0].set_ylabel("True"); fig.tight_layout(); fig.savefig(FIG / "confusion_matrices.png"); plt.close(fig)


def fig_training(main):
    fig, axs = plt.subplots(1, 2, figsize=(8, 3.2))
    for m in ["GCN", "GraphSAGE", "R-GCN"]:
        rs = [r for r in main if r["model"] == m and r["split_seed"] == 0 and "curve" in r]
        if not rs: continue
        c = rs[0]["curve"]
        axs[0].plot([e["train_loss"] for e in c], color=PAL[m], label=m)
        axs[1].plot([e["val_loss"] for e in c], color=PAL[m], label=m)
    axs[0].set_title("Train loss"); axs[1].set_title("Validation loss")
    for a in axs: a.set_xlabel("epoch"); a.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "training_curves.png"); plt.close(fig)


def fig_graph_sizes():
    rep = json.loads((RES / "dataset_report.json").read_text())
    gs = np.array(rep["graph_sizes"]); lab = np.array(rep["graph_size_labels"])
    fig, axs = plt.subplots(1, 2, figsize=(8, 3))
    for ax, i, t in ((axs[0], 0, "Nodes per graph"), (axs[1], 1, "Edges per graph")):
        ax.hist([gs[lab == 0, i], gs[lab == 1, i]], bins=15, label=["Benign", "Suspicious"], color=["#56B4E9", "#D55E00"])
        ax.set_title(t); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "graph_size_distribution.png"); plt.close(fig)


def fig_latency(main):
    fig, ax = plt.subplots(figsize=(6, 3))
    ms_ = [m for m in ORDER if any(r["model"] == m for r in main)]
    ax.barh(ms_, [np.mean([r["infer_ms_per_graph"] for r in main if r["model"] == m]) for m in ms_],
            color=[PAL[m] for m in ms_])
    ax.set_xlabel("inference ms / session graph (batch size 1, CPU)"); ax.invert_yaxis()
    fig.tight_layout(); fig.savefig(FIG / "latency.png"); plt.close(fig)


def fig_ablation(abl):
    modes = ["full", "no_auth", "no_jswasm", "no_dest", "no_taint"]
    models = ["RF (counts)", "RF (counts+reachability)", "MLP (counts)", "GCN", "GraphSAGE", "R-GCN"]
    fig, ax = plt.subplots(figsize=(8, 3.4)); w = 0.13
    for i, m in enumerate(models):
        vals = [ms([r["f1"] for r in abl if r["setting"] == mo and r["model"] == m]) for mo in modes]
        ax.bar(np.arange(len(modes)) + (i - 2.5) * w, [v[0] for v in vals], w, yerr=[v[1] for v in vals],
               label=m, color=PAL[m], capsize=1.5)
    ax.set_xticks(range(len(modes))); ax.set_xticklabels(["full graph", "− auth nodes", "− JS/Wasm", "− destinations", "− taint edges"])
    ax.set_ylabel("F1"); ax.set_ylim(0, 1.05); ax.set_title("Ablation: F1 (mean ± std, 5 extension-level splits)")
    ax.legend(fontsize=7, ncol=6, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12)); fig.tight_layout(); fig.savefig(FIG / "ablation.png", bbox_inches="tight"); plt.close(fig)


def fig_unseen(un):
    settings = [s for s in dict.fromkeys(r["setting"] for r in un)]
    models = ["Rule R2 (taint)", "RF (counts)", "RF (counts+reachability)", "MLP (counts)", "GCN", "GraphSAGE", "R-GCN"]
    fig, ax = plt.subplots(figsize=(9, 3.6)); w = 0.12
    for i, m in enumerate(models):
        vals = [ms([r["recall"] for r in un if r["setting"] == s and r["model"] == m]) for s in settings]
        ax.bar(np.arange(len(settings)) + (i - 3) * w, [v[0] for v in vals], w, yerr=[v[1] for v in vals], label=m,
               color=PAL[m], capsize=1.5)
    ax.set_xticks(range(len(settings))); ax.set_xticklabels([s.replace("loso_", "").replace("_", "\n", 1)[:26] for s in settings], fontsize=6)
    ax.set_ylabel("Recall on UNSEEN suspicious flow"); ax.set_ylim(0, 1.05)
    ax.set_title("Unseen-flow generalisation (family never seen in training)"); ax.legend(fontsize=6, ncol=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    fig.tight_layout(); fig.savefig(FIG / "unseen_flow.png", bbox_inches="tight"); plt.close(fig)


def md_setting_table(runs, settings, models, keys=("recall", "precision", "f1", "roc_auc", "fpr")):
    rows = ["| Setting | Model | " + " | ".join(k for k in keys) + " | n_test |", "|---|---|" + "---:|" * (len(keys) + 1)]
    for s in settings:
        for m in models:
            rs = [r for r in runs if r["setting"] == s and r["model"] == m]
            if rs: rows.append(f"| {s} | {m} | " + " | ".join(fmt([r[k] for r in rs]) for k in keys) + f" | {rs[0]['n_test']} |")
    return "\n".join(rows)


def main():
    out, summary = ["# Measured results (auto-generated by evaluate.py)\n"], {}
    rep = RES / "dataset_report.json"
    if rep.exists():
        fig_graph_sizes()
    main_r, un, abl = load("main"), load("unseen"), load("ablation")
    if main_r:
        t, summ = main_table(main_r); summary["main"] = summ
        out += ["## Main: extension-level split (mean ± std over 5 splits; threshold 0.5)\n", t, ""]
        fig_comparison(summ); fig_curves(main_r); fig_confusion(main_r); fig_training(main_r); fig_latency(main_r)
        # subgroup: wasm taint lost vs visible, among suspicious test graphs
        out += ["### Recall on suspicious sessions by taint visibility at the sink (pooled over splits)\n",
                "| Model | taint visible | taint lost (Wasm) |", "|---|---:|---:|"]
        for m in ORDER:
            vis, lost = [], []
            for r in [r for r in main_r if r["model"] == m]:
                for y, p, tv in zip(r["y_true"], r["y_prob"], r["taint_visible"]):
                    if y == 1: (vis if tv else lost).append(p >= .5)
            if vis: out.append(f"| {m} | {np.mean(vis):.3f} (n={len(vis)}) | " + (f"{np.mean(lost):.3f} (n={len(lost)})" if lost else "n/a") + " |")
        out.append("")
    else:
        out.append("Main experiment: NOT YET MEASURED\n")
    if un:
        ss = list(dict.fromkeys(r["setting"] for r in un))
        out += ["## Unseen-flow generalisation (recall = detection of the never-seen suspicious family)\n",
                md_setting_table(un, ss, ORDER), ""]
        fig_unseen(un)
    else:
        out.append("Unseen-flow experiment: NOT YET MEASURED\n")
    if abl:
        ss = ["full", "no_auth", "no_jswasm", "no_dest", "no_taint"]
        out += ["## Ablation (extension-level split)\n", md_setting_table(abl, ss, [m for m in ORDER if any(r["model"] == m for r in abl)],
                                                                            keys=("precision", "recall", "f1", "roc_auc")), ""]
        fig_ablation(abl)
    else:
        out.append("Ablation: NOT YET MEASURED\n")
    (RES / "tables.md").write_text("\n".join(out), encoding="utf-8")
    (RES / "summary.json").write_text(json.dumps(summary, indent=1))
    if not DARK:
        print("\n".join(out))


DARK = False

if __name__ == "__main__":
    main()                                   # print-ready (white) figures -> figures/
    DARK = True                              # dashboard (dark) figures -> figures/dark/
    FIG = FIG / "dark"; FIG.mkdir(exist_ok=True)
    PAL.update({"Rule R1 (co-occurrence)": "#b8c2cc", "Rule R2 (taint)": "#8895a3"})
    plt.rcParams.update({"figure.facecolor": "#0f1b2d", "axes.facecolor": "#0f1b2d", "savefig.facecolor": "#0f1b2d",
                         "text.color": "#e5ecf4", "axes.labelcolor": "#e5ecf4", "axes.edgecolor": "#5b6b7f",
                         "xtick.color": "#c3cedb", "ytick.color": "#c3cedb", "axes.titlecolor": "#e5ecf4"})
    main()
