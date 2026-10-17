"""Minimal NumPy Random Forest (CART, Gini, bootstrap, sqrt(d) features per split).
Used instead of sklearn.ensemble because this machine's Application Control policy blocks sklearn's
compiled tree module. Same fit / predict_proba interface."""
import numpy as np


def _gini(pos, n):
    p = pos / n
    return 2 * p * (1 - p)


class _Tree:
    def __init__(self, max_depth, min_leaf, rng):
        self.md, self.ml, self.rng = max_depth, min_leaf, rng
        self.nodes = []                       # (feat, thr, left, right, prob)

    def _split(self, X, y, feats):
        best, n = (None, None, 1e9), len(y)
        for f in feats:
            order = np.argsort(X[:, f], kind="stable")
            xs, ys = X[order, f], y[order]
            cl = np.cumsum(ys)[:-1]; nl = np.arange(1, n)
            valid = xs[1:] > xs[:-1]
            valid &= (nl >= self.ml) & (n - nl >= self.ml)
            if not valid.any(): continue
            tot = ys.sum()
            g = (nl * _gini(cl, nl) + (n - nl) * _gini(tot - cl, n - nl)) / n
            g = np.where(valid, g, 1e9)
            i = int(np.argmin(g))
            if g[i] < best[2]: best = (f, (xs[i] + xs[i + 1]) / 2, g[i])
        return best

    def _grow(self, X, y, depth):
        idx = len(self.nodes); self.nodes.append(None)
        prob = y.mean()
        if depth >= self.md or prob in (0.0, 1.0) or len(y) < 2 * self.ml:
            self.nodes[idx] = (-1, 0, -1, -1, prob); return idx
        d = X.shape[1]
        feats = self.rng.choice(d, max(1, int(np.sqrt(d))), replace=False)
        f, t, g = self._split(X, y, feats)
        if f is None:
            self.nodes[idx] = (-1, 0, -1, -1, prob); return idx
        m = X[:, f] <= t
        l = self._grow(X[m], y[m], depth + 1); r = self._grow(X[~m], y[~m], depth + 1)
        self.nodes[idx] = (f, t, l, r, prob)
        return idx

    def fit(self, X, y):
        self._grow(X, y.astype(float), 0); return self

    def predict(self, X):
        out = np.empty(len(X))
        for k, x in enumerate(X):
            i = 0
            while self.nodes[i][0] >= 0:
                f, t, l, r, _ = self.nodes[i]; i = l if x[f] <= t else r
            out[k] = self.nodes[i][4]
        return out


class RandomForest:
    def __init__(self, n_trees=200, max_depth=12, min_leaf=1, seed=0):
        self.n, self.md, self.ml, self.seed = n_trees, max_depth, min_leaf, seed

    def fit(self, X, y):
        rng = np.random.default_rng(self.seed); y = np.asarray(y)
        self.trees = []
        for _ in range(self.n):
            b = rng.integers(0, len(y), len(y))
            self.trees.append(_Tree(self.md, self.ml, rng).fit(X[b], y[b]))
        return self

    def predict_proba(self, X):
        p = np.mean([t.predict(X) for t in self.trees], axis=0)
        return np.stack([1 - p, p], 1)

    @property
    def node_count(self): return sum(len(t.nodes) for t in self.trees)
