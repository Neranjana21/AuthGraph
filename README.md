# AuthGraph

**Heterogeneous graph neural networks for detecting unauthorized authentication-credential data flows in browser extensions — a controlled-lab prototype.**

Everything runs on `localhost` with **synthetic** credentials. No real site, user, cookie or token is ever touched, and the
lab's "attack" extensions are proof-of-concept behaviours that exist only to produce labelled telemetry.

## What was actually built (all implemented and executed)

```
 Flask auth app :5000 ──► real Chromium + generated MV3 extensions ──► telemetry JSONL (hashed credential ids only)
 (synthetic cookie/JWT)    chrome.cookies · localStorage · storage         │
 collector + sinks :5001   · DOM · fetch · WebAssembly                     ▼
 (*.lab.localhost, IP)                                          heterogeneous graph per session
                                                                           │
          rules · RF · MLP · GCN · GraphSAGE · R-GCN  ◄────────────────────┘
                              │
                 occlusion explainer → highlighted credential→sink path → Streamlit dashboard
```

* **Lab** (`lab/servers.py`): auth app with fresh synthetic cookies/JWT per login; collector + approved API / analytics / controlled sink hosts. The collector stores only body length and a 10-char hash, never bodies. A server-side request log is used to cross-check the self-reported telemetry.
* **Extensions** (`extgen/`): 12 scenario families → real MV3 extensions (content script + service worker + JS modules + a hand-assembled WebAssembly module). Benign: DOM only, storage, approved API, *authenticated* approved API (hard negative), credential read + unrelated analytics (hard negative), benign Wasm. Controlled suspicious: direct credential→sink, via JS hops, via Wasm, cross-component (content↔service worker), staged through storage, chunked to a raw-IP sink.
* **Ground truth** = credential-derived data is sent to an *unapproved* destination. The label comes from the scenario design, not from any detector.
* **Graph** (`authgraph/graph.py`): 11 node types, 17 relation types, including separate taint-flow relations (`flows_cred`, `carries`) so their contribution can be ablated.
* **Models**: rules R1/R2, Random Forest (NumPy implementation), MLP, GCN, GraphSAGE, R-GCN (plain PyTorch, no PyG).
* **Splits**: extension-level (all sessions of an extension stay in one split) and scenario-level (unseen suspicious families).

## Run it

```bash
./setup.sh            # venv + torch(CPU) + Playwright Chromium
./run_dataset.sh      # generate extensions, run 576 real browser sessions, validate, build graphs   (~4 min)
python tune.py        # validation-only hyper-parameter search for the GNNs
python train.py --exp all && python evaluate.py     # all experiments, tables.md, figures/
python ensemble.py    # trains the 10-model ensembles used by the dashboard + out-of-fold confidence bands (~10 min)
./run_demo.sh         # dashboard   (streamlit run dashboard.py)
```
Windows without bash: use the `.venv\Scripts\python` equivalents of each line.

## Where results live (nothing is hard-coded in this README)

* `results/tables.md` — every table, auto-generated from executed runs (mean ± std over 5 splits)
* `experiments.csv` — one row per executed run; `results/v1_untuned/` — the first, untuned run, kept on purpose
* `results/dataset_report.json`, `results/tuning_log.json`, `results/tuned_config.json`
* `figures/` — comparison, ROC/PR, confusion matrices, training curves, latency, ablation, unseen-flow, graph sizes
* `progress.md` — day log, decisions, failures · `REPORT.md` — research report · `VIVA.md` — demo script + Q&A

## Honest limitations (read before presenting)

1. **Telemetry is self-reported by instrumented lab extensions**, not captured by a generic browser-level taint tracker such as Arcanum. The extensions are generated from a small step vocabulary, so the data is far less diverse than real-world extensions.
2. **Taint visibility is a dataset parameter.** `wasm_taint_drop=0.5` models a JS-level tracker that loses taint inside WebAssembly. This is a design choice that shapes the Wasm results; it is not a measured property of real trackers.
3. When taint is visible, the task is nearly trivial for count-based models; the interesting cases are taint-lost and unseen-family flows. See `results/tables.md`.
4. Results are on one synthetic distribution (576 sessions, 144 extensions). They say nothing about real-world malware prevalence or detection rates.
5. Latency is offline per-session inference on CPU, not a deployed monitor.
6. Random Forest is a small NumPy implementation because this machine's Windows Application Control policy blocks scikit-learn's compiled tree module.
