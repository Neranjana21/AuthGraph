"""GCN, GraphSAGE and R-GCN graph classifiers in plain PyTorch (no PyG dependency)."""
import torch, torch.nn as nn, torch.nn.functional as F


def readout(h, batch, n_graphs):
    d = h.shape[1]
    s = torch.zeros(n_graphs, d).index_add_(0, batch, h)
    cnt = torch.zeros(n_graphs).index_add_(0, batch, torch.ones(h.shape[0])).clamp(min=1).unsqueeze(1)
    mx = torch.full((n_graphs, d), -1e9).scatter_reduce_(0, batch.unsqueeze(1).expand(-1, d), h, "amax", include_self=True)
    return torch.cat([s / cnt, mx], 1)


def _undirected(rel, n):
    src = torch.cat([s for s, _ in rel.values()] + [d for _, d in rel.values()]) if rel else torch.zeros(0, dtype=torch.long)
    dst = torch.cat([d for _, d in rel.values()] + [s for s, _ in rel.values()]) if rel else torch.zeros(0, dtype=torch.long)
    return src, dst


class Head(nn.Module):
    def __init__(self, h):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(2 * h, h), nn.ReLU(), nn.Dropout(0.2), nn.Linear(h, 2))
    def forward(self, z): return self.net(z)


class GCN(nn.Module):
    """Homogeneous GCN: edge types ignored; symmetric normalisation with self loops."""
    def __init__(self, in_dim, h=64, layers=3):
        super().__init__()
        self.lin = nn.ModuleList([nn.Linear(in_dim if i == 0 else h, h) for i in range(layers)])
        self.head = Head(h)
    def forward(self, b):
        x, n = b["x"], b["x"].shape[0]
        s, d = _undirected(b["rel"], n)
        loop = torch.arange(n); s, d = torch.cat([s, loop]), torch.cat([d, loop])
        deg = torch.zeros(n).index_add_(0, d, torch.ones(d.shape[0]))
        w = (deg[s] * deg[d]).rsqrt().unsqueeze(1)
        h = x
        for l in self.lin:
            m = torch.zeros(n, l.out_features).index_add_(0, d, l(h)[s] * w)
            h = F.relu(m)
        return self.head(readout(h, b["batch"], b["n_graphs"]))


class SAGE(nn.Module):
    """Homogeneous GraphSAGE (mean aggregator, separate self/neighbour weights)."""
    def __init__(self, in_dim, h=64, layers=3):
        super().__init__()
        self.ws = nn.ModuleList([nn.Linear(in_dim if i == 0 else h, h) for i in range(layers)])
        self.wn = nn.ModuleList([nn.Linear(in_dim if i == 0 else h, h, bias=False) for i in range(layers)])
        self.head = Head(h)
    def forward(self, b):
        x, n = b["x"], b["x"].shape[0]
        s, d = _undirected(b["rel"], n)
        deg = torch.zeros(n).index_add_(0, d, torch.ones(d.shape[0])).clamp(min=1).unsqueeze(1)
        h = x
        for ws, wn in zip(self.ws, self.wn):
            agg = torch.zeros(n, h.shape[1]).index_add_(0, d, h[s]) / deg
            h = F.relu(ws(h) + wn(agg))
        return self.head(readout(h, b["batch"], b["n_graphs"]))


class RGCN(nn.Module):
    """Relational GCN (Schlichtkrull et al.): one weight matrix per relation AND direction,
    per-relation mean normalisation, plus a self-loop weight. `bases` > 0 enables the paper's basis
    decomposition (W_r = sum_b a_rb V_b). Optional edge_weight dict {rel: tensor} is used by the explainer."""
    def __init__(self, in_dim, rels, h=64, layers=3, bases=0):
        super().__init__()
        self.rels = list(rels); self.layers = layers
        self.keys = [f"{r}_{d}" for r in self.rels for d in ("f", "b")]
        dims = [in_dim] + [h] * layers
        R = len(self.keys)
        self.self_w = nn.ModuleList([nn.Linear(dims[i], h) for i in range(layers)])
        if bases:
            self.basis = nn.ParameterList([nn.Parameter(torch.randn(bases, dims[i], h) * dims[i] ** -0.5) for i in range(layers)])
            self.coef = nn.ParameterList([nn.Parameter(torch.randn(R, bases) / bases ** 0.5) for _ in range(layers)])
        else:
            self.full = nn.ParameterList([nn.Parameter(torch.randn(R, dims[i], h) * dims[i] ** -0.5) for i in range(layers)])
        self.bases = bases
        self.head = Head(h)

    def _W(self, i):
        return torch.einsum("rb,bio->rio", self.coef[i], self.basis[i]) if self.bases else self.full[i]

    def embed(self, b, edge_weight=None):
        x, n = b["x"], b["x"].shape[0]
        norm = {}
        for r, (s, d) in b["rel"].items():
            ew = edge_weight[r] if edge_weight and r in edge_weight else torch.ones(s.shape[0])
            norm[r] = (ew, torch.zeros(n).index_add_(0, d, ew).clamp(min=1e-6), torch.zeros(n).index_add_(0, s, ew).clamp(min=1e-6))
        h = x
        for i in range(self.layers):
            W = self._W(i); out = self.self_w[i](h)
            for r, (s, d) in b["rel"].items():
                ew, df, db = norm[r]; k = self.keys.index(f"{r}_f")
                out = out + torch.zeros(n, out.shape[1]).index_add_(0, d, (h @ W[k])[s] * (ew / df[d]).unsqueeze(1))
                out = out + torch.zeros(n, out.shape[1]).index_add_(0, s, (h @ W[k + 1])[d] * (ew / db[s]).unsqueeze(1))
            h = F.relu(out)
        return h

    def forward(self, b, edge_weight=None):
        return self.head(readout(self.embed(b, edge_weight), b["batch"], b["n_graphs"]))


class MLP(nn.Module):
    def __init__(self, in_dim, h=64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(0.2),
                                 nn.Linear(h, h), nn.ReLU(), nn.Linear(h, 2))
    def forward(self, x): return self.net(x)


class Ensemble(nn.Module):
    """Deep ensemble: forward returns log of the MEAN member probability, so softmax(forward(b)) is the ensemble probability
    and (logit1 - logit0) is its log-odds. Works with the occlusion explainer unchanged."""
    def __init__(self, members):
        super().__init__(); self.members = nn.ModuleList(members)

    def forward(self, b, edge_weight=None):
        p = torch.stack([F.softmax(m(b), 1) for m in self.members]).mean(0).clamp(1e-6, 1 - 1e-6)
        return torch.log(p)


def n_params(m): return sum(p.numel() for p in m.parameters() if p.requires_grad)
