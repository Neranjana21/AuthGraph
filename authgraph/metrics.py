import numpy as np
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score, confusion_matrix)


def compute(y, p, thr=0.5):
    y = np.asarray(y); p = np.asarray(p, dtype=float); yh = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yh, labels=[0, 1]).ravel()
    both = len(set(y.tolist())) == 2
    return {
        "accuracy": accuracy_score(y, yh),
        "precision": precision_score(y, yh, zero_division=0),
        "recall": recall_score(y, yh, zero_division=0),
        "f1": f1_score(y, yh, zero_division=0),
        "roc_auc": roc_auc_score(y, p) if both else float("nan"),
        "pr_auc": average_precision_score(y, p) if both else float("nan"),
        "fpr": fp / (fp + tn) if fp + tn else float("nan"),
        "fnr": fn / (fn + tp) if fn + tp else float("nan"),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "n": int(len(y)),
    }
