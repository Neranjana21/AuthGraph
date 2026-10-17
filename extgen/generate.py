"""Generate controlled lab extensions: one directory per extension variant.

Every extension is a real MV3 extension; its behaviour is a small step program
(see templates/ops.js) belonging to one scenario family. Family -> label is fixed by design:
  benign (0):     B1..B6      suspicious (1): S1..S6
Ground truth for "suspicious" = credential-derived data is sent to an UNAPPROVED destination.
"""
import json, random, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"

APPROVED = ["api.lab.localhost:5001", "cdn.lab.localhost:5001"]
UNAPPROVED = ["metrics.lab.localhost:5001", "stats.lab.localhost:5001",
              "sink-a.lab.localhost:5001", "sink-b.lab.localhost:5001", "127.0.0.1:5001"]
APPROVED_PATHS = ["/v1/sync", "/v1/profile", "/v1/settings"]
UNAPPROVED_PATHS = ["/collect", "/b", "/u", "/ping"]
MODULE_NAMES = ["helpers.js", "utils.js", "crypto-lite.js", "format.js", "sync-core.js", "tracker.js", "codec.js"]
FNS = ["b64", "rot", "hex", "rev", "fmt"]
EXT_NAMES = ["Tab Organizer", "Dark Reader Lite", "Price Tracker", "Notes Sidebar", "Page Summarizer",
             "Coupon Finder", "Reading Mode", "Grammar Helper", "Bookmark Sync", "Screenshot Tool"]

BENIGN = ["B1_dom_only", "B2_storage_settings", "B3_approved_api", "B4_authed_approved_api",
          "B5_cred_read_unrelated_analytics", "B6_wasm_benign"]
SUSP = ["S1_direct_cred_sink", "S2_cred_js_sink", "S3_cred_wasm_sink", "S4_cross_component_sink",
        "S5_staged_multi_component", "S6_chunked_ip_sink"]
FAMILIES = BENIGN + SUSP


class Builder:
    def __init__(self, rng, n_mod):
        self.r = rng
        self.steps = []
        self.n = 0
        self.modules = rng.sample(MODULE_NAMES, n_mod)

    def v(self):
        self.n += 1
        return f"v{self.n}"

    def add(self, **s):
        self.steps.append(s)
        return s.get("out")

    # primitives
    def dom(self):
        return self.add(op="dom_read", where="content", out=self.v())

    def cred(self, kind=None):
        kind = kind or self.r.choice(["cookie", "jwt"])
        if kind == "cookie":
            return self.add(op="cookie_read", where="bg", cookie=self.r.choice(["lab_session", "lab_jwt"]), out=self.v())
        return self.add(op="jwt_read", where="content", out=self.v())

    def js(self, src, where):
        return self.add(op="js_transform", where=where, module=self.r.choice(self.modules),
                        fn=self.r.choice(FNS), **{"in": [src]}, out=self.v())

    def wasm(self, src):
        return self.add(op="wasm_encode", where="bg", **{"in": [src]}, out=self.v())

    def send(self, srcs, dest, where):
        pool = APPROVED_PATHS if dest in APPROVED else UNAPPROVED_PATHS
        return self.add(op="send", where=where, dest=dest, path=self.r.choice(pool), **{"in": srcs})

    def stash(self, src, where, key):
        self.add(op="storage_write", where=where, key=key, **{"in": [src]})

    def unstash(self, where, key):
        return self.add(op="storage_read", where=where, key=key, out=self.v())

    def distract(self, k):
        """Benign noise that does NOT touch credentials (optional steps, executed with p)."""
        for _ in range(k):
            kind = self.r.choice(["dom", "dom_store", "approved", "wasm_dom"])
            d = self.add(op="dom_read", where="content", out=self.v(), p=0.7)
            if kind == "dom_store":
                self.add(op="storage_write", where=self.r.choice(["content", "bg"]), key="ui_" + d, **{"in": [d]}, p=0.7)
            elif kind == "approved":
                self.send([d], self.r.choice(APPROVED), self.r.choice(["content", "bg"]))
                self.steps[-1]["p"] = 0.7
            elif kind == "wasm_dom":
                self.add(op="wasm_encode", where="bg", **{"in": [d]}, out=self.v(), p=0.7)


def build(family, rng):
    b = Builder(rng, rng.randint(1, 3))
    k = rng.randint(0, 3)
    w = lambda: rng.choice(["content", "bg"])
    unapp = lambda: rng.choice(UNAPPROVED)
    app = lambda: rng.choice(APPROVED)

    if family == "B1_dom_only":
        d = b.dom()
        if rng.random() < .6: d = b.js(d, w())
        b.stash(d, w(), "ui_state")
    elif family == "B2_storage_settings":
        d = b.dom()
        b.stash(d, "bg", "settings")
        b.unstash("bg", "settings")
    elif family == "B3_approved_api":
        d = b.dom()
        if rng.random() < .6: d = b.js(d, w())
        b.send([d], app(), w())
    elif family == "B4_authed_approved_api":
        c = b.cred()
        r = rng.random()
        if r < .35: c = b.js(c, w())
        elif r < .55: c = b.wasm(c)
        b.send([c], app(), w())
    elif family == "B5_cred_read_unrelated_analytics":
        c = b.cred()
        if rng.random() < .5: b.stash(c, "bg" if b.steps[-1]["where"] == "bg" else "content", "login_state")
        d = b.dom()
        if rng.random() < .5: d = b.js(d, w())
        b.send([d], unapp(), w())
    elif family == "B6_wasm_benign":
        d = b.dom()
        d = b.wasm(d)
        b.send([d], rng.choice(APPROVED + UNAPPROVED), w())
    elif family == "S1_direct_cred_sink":
        c = b.cred()
        b.send([c], unapp(), b.steps[-1]["where"])
    elif family == "S2_cred_js_sink":
        c = b.cred(); loc = b.steps[-1]["where"]
        for _ in range(rng.randint(1, 3)):
            loc = w() if rng.random() < .4 else loc
            c = b.js(c, loc)
        b.send([c], unapp(), loc)
    elif family == "S3_cred_wasm_sink":
        c = b.cred()
        if rng.random() < .5: c = b.js(c, w())
        c = b.wasm(c)
        b.send([c], unapp(), w())
    elif family == "S4_cross_component_sink":
        if rng.random() < .5:
            c = b.cred("jwt"); b.send([c], unapp(), "bg")       # content -> service worker -> network
        else:
            c = b.cred("cookie")
            if rng.random() < .5: c = b.js(c, "bg")
            b.send([c], unapp(), "content")                     # service worker -> content -> network
    elif family == "S5_staged_multi_component":
        c = b.cred(); loc = b.steps[-1]["where"]
        b.stash(c, loc, "cache_blob")
        b.add(op="wait", where="content", ms=rng.randint(100, 400))
        other = "bg" if loc == "content" else "content"
        c = b.unstash(other, "cache_blob")
        c = b.js(c, other)
        if rng.random() < .4: c = b.wasm(c)
        b.send([c], unapp(), w())
    elif family == "S6_chunked_ip_sink":
        c = b.cred(); loc = b.steps[-1]["where"]
        c = b.js(c, loc)
        b.add(op="wait", where="content", ms=rng.randint(200, 600))
        for _ in range(rng.randint(2, 4)):
            b.send([c], "127.0.0.1:5001", loc)
    core = b.steps
    b.steps = []
    b.distract(k)
    noise = b.steps
    b.steps = core
    for grp in noise:                      # splice distractors at random positions of the program
        b.steps.insert(rng.randint(0, len(b.steps)), grp)
    return b


def write_extension(out: Path, ext_id, family, steps, modules, wasm_taint_drop, rng):
    out.mkdir(parents=True, exist_ok=True)
    for f in ("lib.js", "ops.js", "content.js"):
        shutil.copy(TPL / f, out / f)
    shutil.copy(ROOT / "codec.wasm", out / "codec.wasm")
    cfg = {"ext_id": ext_id, "steps": steps, "wasm_taint_drop": wasm_taint_drop}
    (out / "config.js").write_text("self.AG_CFG = " + json.dumps(cfg) + ";\n", encoding="utf-8")
    tpl = (TPL / "utils.js").read_text()
    for m in modules:
        (out / m).write_text(tpl.replace("__NAME__", m), encoding="utf-8")
    imports = ["config.js", "lib.js", *modules, "ops.js"]
    bg = (TPL / "background.js").read_text().replace("__IMPORTS__", ", ".join(f"'{i}'" for i in imports))
    (out / "background.js").write_text(bg, encoding="utf-8")
    manifest = {
        "manifest_version": 3, "name": rng.choice(EXT_NAMES), "version": "1.0",
        "permissions": ["cookies", "storage"],
        "host_permissions": ["http://localhost/*", "http://*.localhost/*", "http://127.0.0.1/*"],
        "background": {"service_worker": "background.js"},
        "content_scripts": [{"matches": ["http://localhost:5000/*"], "run_at": "document_idle",
                             "js": ["config.js", "lib.js", *modules, "ops.js", "content.js"]}],
        "web_accessible_resources": [],
        "content_security_policy": {"extension_pages": "script-src 'self' 'wasm-unsafe-eval'; object-src 'self'"},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


def generate(out_dir, per_family=12, seed=7, wasm_taint_drop=0.5):
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    rng = random.Random(seed)
    meta = {}
    i = 0
    for fam in FAMILIES:
        for _ in range(per_family):
            i += 1
            ext_id = f"EXT{i:03d}"
            b = build(fam, random.Random(rng.random()))
            write_extension(out_dir / ext_id, ext_id, fam, b.steps, b.modules, wasm_taint_drop, rng)
            meta[ext_id] = {"family": fam, "label": int(fam.startswith("S")), "n_steps": len(b.steps)}
    (out_dir / "extensions.json").write_text(json.dumps(meta, indent=1))
    return meta


if __name__ == "__main__":
    import sys
    m = generate(sys.argv[1] if len(sys.argv) > 1 else "extensions", per_family=int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    print(len(m), "extensions generated")
