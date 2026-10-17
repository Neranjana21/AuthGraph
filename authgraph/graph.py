"""Telemetry events -> authentication-aware heterogeneous graph (one graph per session)."""
import json, math, pickle
from collections import defaultdict
from pathlib import Path
import numpy as np

APPROVED = {"api.lab.localhost:5001", "cdn.lab.localhost:5001"}   # policy: approved destinations
NTYPES = ["extension", "content_script", "service_worker", "js_module", "wasm_module",
          "browser_api", "credential", "storage_object", "http_request", "domain", "page"]
RELS = ["contains", "injects", "invokes", "accesses_page", "accesses_cred", "returns", "writes",
        "read_by", "executes", "loads", "calls", "message", "issues", "sends_to",
        "flows_cred", "carries", "follows"]
CRED_TYPES = ["session_cookie", "jwt_cookie", "jwt_localstorage"]
API_CLASSES = ["cookies", "localStorage", "storage", "dom", "messaging", "fetch"]
# feature layout: ntype one-hot | domain(approved,is_ip) | cred type one-hot | api class one-hot | log count | log payload
N_FEAT = len(NTYPES) + 2 + len(CRED_TYPES) + len(API_CLASSES) + 2
F_DOM = len(NTYPES)
F_CRED = F_DOM + 2
F_API = F_CRED + len(CRED_TYPES)
F_CNT = F_API + len(API_CLASSES)


def api_class(a):
    if "cookies" in a: return "cookies"
    if "localStorage" in a: return "localStorage"
    if "storage" in a: return "storage"
    if "document" in a: return "dom"
    if a in ("chrome.runtime.sendMessage", "sendResponse"): return "messaging"
    return "fetch"


def build_graph(events, meta):
    ev = sorted(events, key=lambda e: (e["ts"], e.get("cseq", 0)))
    nodes, feats, names, counts = {}, [], [], defaultdict(int)
    edges = defaultdict(set)
    ntype = []

    def node(key, t, name):
        if key not in nodes:
            nodes[key] = len(nodes)
            f = np.zeros(N_FEAT, dtype=np.float32)
            f[NTYPES.index(t)] = 1
            feats.append(f); ntype.append(t); names.append(name)
        counts[nodes[key]] += 1
        return nodes[key]

    ext = node(("ext",), "extension", "Extension")
    reqs, creds_order, last_req = [], [], None

    def comp(c):
        n = node(("comp", c), c, "Content Script" if c == "content_script" else "Service Worker")
        edges["contains"].add((ext, n))
        return n

    def taint_edges(tags, dst, rel="flows_cred"):
        for t in tags or []:
            cid = t.split(":", 1)[1]
            if ("cred", cid) in nodes:
                edges[rel].add((nodes[("cred", cid)], dst))

    for e in ev:
        t, c = e["event_type"], e.get("component")
        if t == "session_start":
            cs = comp("content_script")
            pg = node(("page", e.get("page_origin")), "page", "Web Page")
            edges["injects"].add((cs, pg))
            continue
        if t == "session_end":
            continue
        cn = comp(c)
        a = e.get("api")
        if a:
            an = node(("api", a), "browser_api", a)
            feats[an][F_API + API_CLASSES.index(api_class(a))] = 1
            edges["invokes"].add((cn, an))
        if t == "dom_access":
            edges["accesses_page"].add((cn, node(("page", "http://localhost:5000"), "page", "Web Page")))
        elif t == "credential_access":
            cid = e["cred_id"]
            first = ("cred", cid) not in nodes
            k = node(("cred", cid), "credential", f"{e['cred_type']}:{cid[:6]}")
            feats[k][F_CRED + CRED_TYPES.index(e["cred_type"])] = 1
            edges["accesses_cred"].add((cn, k))
            edges["returns"].add((nodes[("api", a)], k))
            if first: creds_order.append((e["ts"], k))
        elif t == "storage_write":
            s = node(("store", e["object"]), "storage_object", "Storage Object")
            edges["writes"].add((cn, s)); taint_edges(e.get("in_tags"), s)
        elif t == "storage_read":
            s = node(("store", e["object"]), "storage_object", "Storage Object")
            edges["read_by"].add((s, cn)); taint_edges(e.get("out_tags"), cn)
        elif t == "script_exec":
            j = node(("js", e["script"]), "js_module", e["script"])
            edges["executes"].add((cn, j)); taint_edges(e.get("in_tags"), j)
        elif t == "wasm_load":
            edges["loads"].add((cn, node(("wasm", "codec.wasm"), "wasm_module", "codec.wasm")))
        elif t == "wasm_call":
            w = node(("wasm", "codec.wasm"), "wasm_module", "codec.wasm")
            edges["calls"].add((cn, w)); taint_edges(e.get("in_tags"), w)
        elif t == "message":
            tgt = comp(e["to_component"])
            edges["message"].add((cn, tgt)); taint_edges(e.get("tags"), tgt)
        elif t == "http_request":
            r = node(("req", len(reqs)), "http_request", f"POST {e['dest_path']}")
            feats[r][F_CNT + 1] = math.log1p(e.get("payload_len", 0))
            d = node(("dom", e["destination"]), "domain", e["destination"])
            host = e["destination"].split(":")[0]
            feats[d][F_DOM] = float(e["destination"] in APPROVED)
            feats[d][F_DOM + 1] = float(host.replace(".", "").isdigit())
            edges["issues"].add((cn, r)); edges["sends_to"].add((r, d))
            taint_edges(e.get("payload_tags"), r, "carries")
            if last_req is not None: edges["follows"].add((r, last_req))
            last_req = r; reqs.append((e["ts"], r))
    for ts, k in creds_order:                       # credential -> first request that follows it
        nxt = [r for rts, r in reqs if rts >= ts]
        if nxt: edges["follows"].add((k, nxt[0]))
    for i in range(len(feats)):
        feats[i][F_CNT] = math.log1p(counts[i])
    return {
        "session_id": meta["session_id"], "extension_id": meta["extension_id"],
        "family": meta["family"], "label": meta["label"],
        "ntype": ntype, "x": np.stack(feats), "names": names,
        "edges": {r: sorted(edges[r]) for r in RELS if edges[r]},
        "n_events": len(ev),
        "taint_visible": any(e["event_type"] == "http_request" and e.get("payload_tags")
                             and e["destination"] not in APPROVED for e in ev),
    }


def load_events(raw_dir):
    by = defaultdict(list)
    seen = set()
    for line in open(Path(raw_dir) / "telemetry.jsonl", encoding="utf-8"):
        e = json.loads(line)
        k = (e["session_id"], e["extension_id"], e["cseq"], e["event_type"], round(e["ts"], 3))
        if k in seen: continue                       # de-duplicate
        seen.add(k); by[e["session_id"]].append(e)
    return by


def build_dataset(raw_dir, out_path):
    sessions = json.load(open(Path(raw_dir) / "sessions.json"))
    by = load_events(raw_dir)
    graphs = [build_graph(by[s["session_id"]], s) for s in sessions if s["completed"] and by.get(s["session_id"])]
    with open(out_path, "wb") as f:
        pickle.dump(graphs, f)
    return graphs


if __name__ == "__main__":
    import sys
    g = build_dataset(sys.argv[1], sys.argv[2])
    print(len(g), "graphs")
