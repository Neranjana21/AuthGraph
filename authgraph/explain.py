"""Model-agnostic occlusion explanation (works for GCN / GraphSAGE / R-GCN).
importance(node/edge) = logodds(suspicious | full graph) - logodds(suspicious | graph with that node/edge removed).
All values are measured model outputs, not attention weights."""
import networkx as nx
import torch, torch.nn.functional as F
from .data import batch_graphs


def _prob(model, g):
    with torch.no_grad():
        return F.softmax(model(batch_graphs([g])), 1)[0, 1].item()


def _margin(model, g):
    """log-odds of 'suspicious' (logit1 - logit0); does not saturate like the probability."""
    with torch.no_grad():
        lo = model(batch_graphs([g]))[0]
    return (lo[1] - lo[0]).item()


def _drop_node(g, i):
    keep = [k for k in range(len(g["ntype"])) if k != i]
    remap = {o: n for n, o in enumerate(keep)}
    g2 = dict(g)
    g2["ntype"] = [g["ntype"][k] for k in keep]; g2["x"] = g["x"][keep]
    g2["edges"] = {r: [(remap[s], remap[d]) for s, d in es if s in remap and d in remap] for r, es in g["edges"].items()}
    g2["edges"] = {r: e for r, e in g2["edges"].items() if e}
    return g2


def _drop_edge(g, rel, k):
    g2 = dict(g); g2["edges"] = {r: list(es) for r, es in g["edges"].items()}
    del g2["edges"][rel][k]
    if not g2["edges"][rel]: del g2["edges"][rel]
    return g2


def explain(model, g):
    model.eval()
    p0, m0 = _prob(model, g), _margin(model, g)
    node_imp = [0.0 if g["ntype"][i] == "extension" else m0 - _margin(model, _drop_node(g, i)) for i in range(len(g["ntype"]))]
    edge_imp = [{"rel": r, "src": s, "dst": d, "importance": m0 - _margin(model, _drop_edge(g, r, k))}
                for r, es in g["edges"].items() for k, (s, d) in enumerate(es)]
    path = suspicious_path(g, edge_imp)
    if path["nodes"] is None and p0 >= 0.5:      # only for sessions the model actually flags
        path = structural_path(g)
    return {"prob": p0, "margin": m0, "node_importance": node_imp, "edge_importance": edge_imp, "path": path}


def structural_path(g):
    """Fallback when no edge has positive measured importance: shortest undirected credential ->
    unapproved-domain path (NOT model-derived; flagged via method='structural')."""
    G = nx.Graph([(s, d) for r, es in g["edges"].items() if r != "follows" for s, d in es])
    creds = [i for i, t in enumerate(g["ntype"]) if t == "credential" and i in G]
    doms = [i for i, t in enumerate(g["ntype"]) if t == "domain" and i in G]
    best = None
    for c in creds:
        for d in doms:
            if nx.has_path(G, c, d):
                p = nx.shortest_path(G, c, d)
                if best is None or len(p) < len(best): best = p
    return {"nodes": best, "score": 0.0, "method": "structural"}


def suspicious_path(g, edge_imp, cutoff=9):
    """Highest total-importance simple path from a credential node to a domain node, over edges with
    positive measured importance (undirected view; edge directions are kept for display)."""
    G = nx.Graph()
    for e in edge_imp:
        w = max(e["importance"], 0.0)
        if e["rel"] == "follows" or w <= 1e-4: continue
        if G.has_edge(e["src"], e["dst"]): G[e["src"]][e["dst"]]["w"] += w
        else: G.add_edge(e["src"], e["dst"], w=w)
    creds = [i for i, t in enumerate(g["ntype"]) if t == "credential" and i in G]
    doms = [i for i, t in enumerate(g["ntype"]) if t == "domain" and i in G]
    best, best_s = None, 0.0
    for c in creds:
        for d in doms:
            for p in nx.all_simple_paths(G, c, d, cutoff=cutoff):
                sc = sum(G[a][b]["w"] for a, b in zip(p, p[1:]))
                if sc > best_s: best, best_s = p, sc
    return {"nodes": best, "score": best_s, "method": "importance"} if best else {"nodes": None, "score": 0.0}
