"""Rule-based baselines operating directly on telemetry events (not on the graph).

R1 (co-occurrence): a credential was accessed AND the session sent a request to an unapproved destination.
R2 (taint rule):    a request to an unapproved destination carried a credential taint tag.
R2 mirrors how the ground-truth is defined but only sees what the instrumentation reports, so it
misses flows whose taint is lost inside WebAssembly."""
from .graph import APPROVED


def r1(events):
    cred = any(e["event_type"] == "credential_access" for e in events)
    bad = any(e["event_type"] == "http_request" and e["destination"] not in APPROVED for e in events)
    return int(cred and bad)


def r2(events):
    return int(any(e["event_type"] == "http_request" and e["destination"] not in APPROVED
                   and e.get("payload_tags") for e in events))


RULES = {"Rule R1 (co-occurrence)": r1, "Rule R2 (taint)": r2}


def explain(events):
    """Human-readable rule explanation for the dashboard."""
    out = []
    for e in events:
        if e["event_type"] == "http_request" and e["destination"] not in APPROVED:
            if e.get("payload_tags"):
                out.append(f"R2: request to UNAPPROVED {e['destination']}{e['dest_path']} carried credential taint {e['payload_tags']}")
            else:
                out.append(f"request to unapproved {e['destination']} (no taint reported)")
    if any(e["event_type"] == "credential_access" for e in events):
        out.append("R1: credential accessed in this session")
    return out
