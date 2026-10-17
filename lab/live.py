"""Live demo run: generate ONE fresh extension for a scenario family (not in the dataset), run a real
browser session against the controlled lab, and write its telemetry to data/live/<sid>/."""
import argparse, json, os, random, shutil, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--wasm-taint-drop", type=float, default=0.5)
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else int(time.time()) % 100000 + 10_000
    sid = f"LIVE{seed}"
    out = ROOT / "data" / "live" / sid
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    os.environ["AUTHGRAPH_RAW"] = str(out)
    from extgen.generate import build, write_extension
    from lab import servers
    from playwright.sync_api import sync_playwright

    rng = random.Random(seed)
    ext_id = f"EXT_LIVE_{seed}"
    b = build(a.family, random.Random(rng.random()))
    ext_dir = ROOT / "extensions_live" / ext_id
    write_extension(ext_dir, ext_id, a.family, b.steps, b.modules, a.wasm_taint_drop, rng)
    servers.run()
    with sync_playwright() as pw:
        prof = tempfile.mkdtemp(prefix="authgraph_live_")
        args = [f"--disable-extensions-except={ext_dir}", f"--load-extension={ext_dir}", "--no-first-run"]
        ctx = pw.chromium.launch_persistent_context(prof, headless=False, args=args if a.headed else ["--headless=new"] + args)
        time.sleep(1.5)
        page = ctx.new_page()
        page.goto(f"http://localhost:5000/dashboard?ext={ext_id}&sid={sid}")
        t = time.time()
        while sid not in servers.ENDED and time.time() - t < 15: time.sleep(0.05)
        time.sleep(0.5)
        ctx.close(); shutil.rmtree(prof, ignore_errors=True)
    meta = {"session_id": sid, "extension_id": ext_id, "family": a.family,
            "label": int(a.family.startswith("S")), "completed": sid in servers.ENDED}
    (out / "sessions.json").write_text(json.dumps([meta]))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
