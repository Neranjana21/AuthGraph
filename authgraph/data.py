"""Splits, ablations, flat features and tensor batching."""
import copy, pickle, random
from collections import defaultdict
import numpy as np
import torch
from .graph import NTYPES, RELS, N_FEAT, F_DOM, F_CRED, F_API, API_CLASSES

SUSP_FAMILIES = ["S1_direct_cred_sink", "S2_cred_js_sink", "S3_cred_wasm_sink",
                 "S4_cross_component_sink", "S5_staged_multi_component", "S6_chunked_ip_sink"]
WASM_SUSP = ["S3_cred_wasm_sink", "S5_staged_multi_component"]


def load_graphs(path):
    return pickle.load(open(path, "rb"))


# ----------------------------------------------------------------------------- splits
def extension_split(graphs, seed, fr=(0.6, 0.2, 0.2)):
    """Extension-level split, stratified by scenario family: no extension (hence no session)
    appears in more than one of train/val/test."""
    by_fam = defaultdict(set)
    for g in graphs:
        by_fam[g["family"]].add(g["extension_id"])
    rng = random.Random(seed)
    which = {}
    for fam, exts in sorted(by_fam.items()):
        exts = sorted(exts); rng.shuffle(exts)
        n = len(exts); a = round(n * fr[0]); b = round(n * (fr[0] + fr[1]))
        for i, e in enumerate(exts):
            which[e] = "train" if i < a else "val" if i < b else "test"
    out = {"train": [], "val": [], "test": []}
    for g in graphs:
        out[which[g["extension_id"]]].append(g)
    return out


def unseen_split(graphs, seed, held_out_families):
    """Scenario-level split. Train/val: all families except `held_out_families`, split by extension.
    Test: benign test-split extensions (unseen extensions) + ALL sessions of the held-out suspicious families."""
    base = extension_split([g for g in graphs if g["family"] not in held_out_families], seed)
    full = extension_split(graphs, seed)
    test = [g for g in full["test"] if g["label"] == 0] + [g for g in graphs if g["family"] in held_out_families]
    return {"train": base["train"], "val": base["val"], "test": test}


# ----------------------------------------------------------------------------- ablations
def ablate(g, mode):
    if mode == "full":
        return g
    drop_nt, drop_rel, drop_api, zero_dom = set(), set(), set(), False
    if mode == "no_auth":
        drop_nt = {"credential"}; drop_rel = {"accesses_cred", "returns", "flows_cred", "carries"}
        drop_api = {"cookies", "localStorage"}
    elif mode == "no_jswasm":
        drop_nt = {"js_module", "wasm_module"}
    elif mode == "no_dest":
        drop_nt = {"domain"}
    elif mode == "no_taint":
        drop_rel = {"flows_cred", "carries"}
    else:
        raise ValueError(mode)
    keep = []
    for i, t in enumerate(g["ntype"]):
        if t in drop_nt: continue
        if t == "browser_api":
            cls = API_CLASSES[int(np.argmax(g["x"][i][F_API:F_API + len(API_CLASSES)]))]
            if cls in drop_api: continue
        keep.append(i)
    remap = {o: n for n, o in enumerate(keep)}
    g2 = dict(g)
    g2["ntype"] = [g["ntype"][i] for i in keep]
    g2["names"] = [g["names"][i] for i in keep]
    g2["x"] = g["x"][keep].copy()
    g2["edges"] = {}
    for r, es in g["edges"].items():
        if r in drop_rel: continue
        ne = [(remap[s], remap[d]) for s, d in es if s in remap and d in remap]
        if ne: g2["edges"][r] = ne
    g2["keep_index"] = keep
    return g2


# ----------------------------------------------------------------------------- flat features
def _reach(g):
    """Directed reachability credential -> request / unapproved domain, ignoring 'follows' edges."""
    n = len(g["ntype"]); adj = defaultdict(list)
    for r, es in g["edges"].items():
        if r == "follows": continue
        for s, d in es: adj[s].append(d)
    creds = [i for i, t in enumerate(g["ntype"]) if t == "credential"]
    seen, st = set(creds), list(creds)
    while st:
        u = st.pop()
        for v in adj[u]:
            if v not in seen: seen.add(v); st.append(v)
    reach_req = any(g["ntype"][i] == "http_request" for i in seen)
    reach_bad = any(g["ntype"][i] == "domain" and g["x"][i][F_DOM] == 0 for i in seen)
    return float(reach_req), float(reach_bad)


FLAT_COUNT_NAMES = [f"n_{t}" for t in NTYPES] + [f"e_{r}" for r in RELS] + \
    ["n_unapproved_dest", "n_approved_dest", "n_ip_dest", "n_events", "n_cred_types"]


def flat_features(g, with_reach=False):
    f = [sum(1 for t in g["ntype"] if t == nt) for nt in NTYPES]
    f += [len(g["edges"].get(r, [])) for r in RELS]
    dom = [i for i, t in enumerate(g["ntype"]) if t == "domain"]
    f += [sum(1 for i in dom if g["x"][i][F_DOM] == 0), sum(1 for i in dom if g["x"][i][F_DOM] == 1),
          sum(1 for i in dom if g["x"][i][F_DOM + 1] == 1), g["n_events"],
          int(sum(g["x"][i][F_CRED:F_CRED + 3].sum() for i, t in enumerate(g["ntype"]) if t == "credential"))]
    if with_reach:
        f += list(_reach(g))
    return np.array(f, dtype=np.float32)


# ----------------------------------------------------------------------------- tensor batching
def batch_graphs(gs):
    xs, ys, bidx, off = [], [], [], 0
    rel = {r: ([], []) for r in RELS}
    for k, g in enumerate(gs):
        n = len(g["ntype"]); xs.append(torch.from_numpy(g["x"])); ys.append(g["label"])
        bidx.append(torch.full((n,), k, dtype=torch.long))
        for r, es in g["edges"].items():
            rel[r][0].extend(s + off for s, _ in es); rel[r][1].extend(d + off for _, d in es)
        off += n
    rel_t = {r: (torch.tensor(s, dtype=torch.long), torch.tensor(d, dtype=torch.long))
             for r, (s, d) in rel.items() if s}
    return {"x": torch.cat(xs), "y": torch.tensor(ys), "batch": torch.cat(bidx), "rel": rel_t, "n_graphs": len(gs)}
