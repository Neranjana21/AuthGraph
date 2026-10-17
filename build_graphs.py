"""Validate raw telemetry, build graphs, write data/graphs.pkl and results/dataset_report.json."""
import collections, json, sys
from pathlib import Path
import numpy as np
from authgraph.graph import build_dataset, load_events

ROOT = Path(__file__).resolve().parent
REQUIRED = {"session_id", "extension_id", "ts", "cseq", "event_type"}
EVENT_TYPES = {"session_start", "session_end", "api_call", "dom_access", "credential_access", "storage_write",
               "storage_read", "script_exec", "wasm_load", "wasm_call", "message", "http_request"}


def main(raw=ROOT / "data" / "raw", out=ROOT / "data" / "graphs.pkl"):
    raw = Path(raw)
    n_lines = sum(1 for _ in open(raw / "telemetry.jsonl", encoding="utf-8"))
    by = load_events(raw)
    n_unique = sum(len(v) for v in by.values())
    sessions = json.load(open(raw / "sessions.json"))
    bad_schema = sum(1 for v in by.values() for e in v if not REQUIRED <= e.keys() or e["event_type"] not in EVENT_TYPES)
    cred_leak = sum(1 for v in by.values() for e in v if "TESTSESS" in json.dumps(e) or "TESTJWT" in json.dumps(e))
    srv = collections.Counter(json.loads(l)["sid"] for l in open(raw / "server_requests.jsonl"))
    mism = 0
    for s in sessions:
        n_tel = sum(1 for e in by.get(s["session_id"], []) if e["event_type"] == "http_request")
        mism += n_tel != srv.get(s["session_id"], 0)
    graphs = build_dataset(raw, out)
    nn_ = np.array([len(g["ntype"]) for g in graphs]); ne = np.array([sum(len(v) for v in g["edges"].values()) for g in graphs])
    fam = collections.Counter(g["family"] for g in graphs); lab = collections.Counter(g["label"] for g in graphs)
    sus = [g for g in graphs if g["label"] == 1]
    rep = {
        "sessions_attempted": len(sessions), "sessions_completed": sum(s["completed"] for s in sessions),
        "graphs": len(graphs), "extensions": len({g["extension_id"] for g in graphs}),
        "telemetry_lines": n_lines, "unique_events": n_unique, "duplicates_removed": n_lines - n_unique,
        "events_failing_schema": bad_schema, "credential_value_leaks": cred_leak,
        "sessions_where_telemetry_requests_differ_from_server_log": int(mism),
        "label_counts": {"benign": lab[0], "suspicious": lab[1]}, "family_counts": dict(fam),
        "nodes_mean": float(nn_.mean()), "nodes_min": int(nn_.min()), "nodes_max": int(nn_.max()),
        "edges_mean": float(ne.mean()), "edges_min": int(ne.min()), "edges_max": int(ne.max()),
        "suspicious_taint_visible_at_sink": int(sum(g["taint_visible"] for g in sus)),
        "suspicious_taint_lost": int(sum(not g["taint_visible"] for g in sus)),
        "graph_sizes": [[int(a), int(b)] for a, b in zip(nn_, ne)],
        "graph_size_labels": [g["label"] for g in graphs],
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "dataset_report.json").write_text(json.dumps(rep, indent=1))
    print({k: v for k, v in rep.items() if k not in ("graph_sizes", "graph_size_labels")})


if __name__ == "__main__":
    main()
