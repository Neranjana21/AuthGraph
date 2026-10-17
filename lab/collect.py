"""Run the lab: start servers, load batches of generated extensions into Chromium,
visit the controlled app once per (extension, session), and collect telemetry to JSONL."""
import argparse, json, os, random, shutil, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from extgen.generate import generate

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=12)
    ap.add_argument("--sessions", type=int, default=4, help="sessions per extension")
    ap.add_argument("--batch", type=int, default=12, help="extensions loaded per browser launch")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--wasm-taint-drop", type=float, default=0.5)
    ap.add_argument("--out", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()

    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    os.environ["AUTHGRAPH_RAW"] = str(out)
    from lab import servers
    from playwright.sync_api import sync_playwright

    ext_dir = ROOT / "extensions"
    meta = generate(ext_dir, per_family=a.per_family, seed=a.seed, wasm_taint_drop=a.wasm_taint_drop)
    servers.run()
    rng = random.Random(a.seed)
    ids = list(meta)
    rng.shuffle(ids)                        # families mixed across batches
    batches = [ids[i:i + a.batch] for i in range(0, len(ids), a.batch)]
    sid_n, sessions, t0 = 0, [], time.time()
    with sync_playwright() as pw:
        for bi, batch in enumerate(batches):
            paths = ",".join(str(ext_dir / e) for e in batch)
            prof = tempfile.mkdtemp(prefix="authgraph_profile_")
            ctx = pw.chromium.launch_persistent_context(
                prof, headless=False, args=["--headless=new", f"--disable-extensions-except={paths}",
                                            f"--load-extension={paths}", "--no-first-run"] if not a.headed else
                [f"--disable-extensions-except={paths}", f"--load-extension={paths}"])
            time.sleep(1.5)                 # let service workers register
            plan = [(e, s) for e in batch for s in range(a.sessions)]
            rng.shuffle(plan)
            for e, _ in plan:
                sid_n += 1
                sid = f"S{sid_n:04d}"
                page = ctx.new_page()
                page.goto(f"http://localhost:5000/dashboard?ext={e}&sid={sid}")
                t = time.time()
                while sid not in servers.ENDED and time.time() - t < 12:
                    time.sleep(0.05)
                ok = sid in servers.ENDED
                sessions.append({"session_id": sid, "extension_id": e, "family": meta[e]["family"],
                                 "label": meta[e]["label"], "completed": ok})
                if not ok:
                    print(f"  WARN {sid} {e} did not finish", flush=True)
                page.close()
            ctx.close()
            shutil.rmtree(prof, ignore_errors=True)
            print(f"batch {bi+1}/{len(batches)} done  sessions={sid_n}  elapsed={time.time()-t0:.0f}s", flush=True)
    (out / "sessions.json").write_text(json.dumps(sessions, indent=1))
    (out / "extensions.json").write_text(json.dumps(meta, indent=1))
    (out / "collection_config.json").write_text(json.dumps(vars(a), indent=1))
    print("sessions:", len(sessions), "completed:", sum(s["completed"] for s in sessions))

if __name__ == "__main__":
    main()
