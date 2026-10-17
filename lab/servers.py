"""Controlled local lab: auth app (:5000) + telemetry collector / sink hosts (:5001).

Everything binds to loopback only. Credentials are synthetic (random per login) and
the collector NEVER stores request bodies -- only length + a short hash.
"""
import hashlib, json, os, secrets, threading, time
from pathlib import Path
from flask import Flask, request, make_response, Response

RAW = Path(os.environ.get("AUTHGRAPH_RAW", Path(__file__).resolve().parent.parent / "data" / "raw"))
RAW.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()
ENDED = set()          # session ids whose content script reported session_end

def _append(name, obj):
    with _lock, open(RAW / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")

# ---------------------------------------------------------------- auth app (page origin)
app = Flask("lab_app")

PAGE = """<!doctype html><html><head><title>Lab Bank Dashboard</title></head><body>
<h1>Lab Dashboard</h1><p id="who">Signed in as test_user (synthetic)</p>
<ul><li>Balance: 0.00 (fake)</li><li>Messages: 3</li></ul>
<form><input name="q"><button>Search</button></form>
<script>localStorage.setItem('test_jwt', '%(jwt)s');</script></body></html>"""

def fake_jwt():
    h = secrets.token_urlsafe(8); p = secrets.token_urlsafe(16); s = secrets.token_urlsafe(12)
    return f"TESTJWT.{h}.{p}.{s}"

@app.route("/dashboard")
def dashboard():
    r = make_response(PAGE % {"jwt": fake_jwt()})
    r.set_cookie("lab_session", "TESTSESS-" + secrets.token_hex(12), httponly=True, samesite="Lax")
    r.set_cookie("lab_jwt", fake_jwt(), samesite="Lax")
    return r

@app.route("/healthz")
def health_app():
    return "ok"

# ---------------------------------------------------------------- collector / sinks
col = Flask("lab_collector")

def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "*"
    return resp

@col.route("/telemetry", methods=["POST", "OPTIONS"])
def telemetry():
    if request.method == "OPTIONS":
        return cors(Response(status=204))
    try:
        events = json.loads(request.get_data(as_text=True))
    except Exception:
        return cors(Response("bad json", status=400))
    now = time.time() * 1000
    for e in events:
        e["recv_ts"] = now
        _append("telemetry.jsonl", e)
        if e.get("event_type") == "session_end":
            ENDED.add(e.get("session_id"))
    return cors(Response("ok"))

@col.route("/healthz")
def health_col():
    return cors(Response("ok"))

@col.route("/", defaults={"p": ""}, methods=["GET", "POST", "PUT", "OPTIONS"])
@col.route("/<path:p>", methods=["GET", "POST", "PUT", "OPTIONS"])
def any_endpoint(p):
    """Approved API, analytics host, and controlled sinks all land here; the Host header
    distinguishes them. Server-side log is the ground truth used to cross-check telemetry."""
    if request.method == "OPTIONS":
        return cors(Response(status=204))
    body = request.get_data()
    _append("server_requests.jsonl", {
        "ts": time.time() * 1000, "host": request.host, "path": "/" + p,
        "sid": request.args.get("sid"), "method": request.method,
        "body_len": len(body), "body_sha": hashlib.sha256(body).hexdigest()[:10]})
    return cors(Response("ok"))

def run(port_app=5000, port_col=5001):
    from werkzeug.serving import make_server
    import logging; logging.getLogger("werkzeug").setLevel(logging.ERROR)
    srvs = [make_server("127.0.0.1", port_app, app, threaded=True),
            make_server("127.0.0.1", port_col, col, threaded=True)]
    for s in srvs:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    return srvs

if __name__ == "__main__":
    run()
    print(f"lab up: app http://localhost:5000  collector http://localhost:5001  raw={RAW}", flush=True)
    while True:
        time.sleep(3600)
