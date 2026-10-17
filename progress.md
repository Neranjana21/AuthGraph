# AuthGraph — progress log

Honesty rule: every metric comes from an executed run. Anything not run is marked **NOT YET MEASURED**.

## Starting state
Directory was empty (nothing to reuse). Python 3.13, Node 24, Docker, Chrome/Edge present. Branded Chrome ≥137 ignores `--load-extension`, so Playwright's bundled Chromium is used.

## What was done (work compressed into one session; the 5-day plan was executed back-to-back)
| Phase | Status |
|---|---|
| Lab: Flask auth app + collector/sinks (`lab/servers.py`) | done |
| Real MV3 extension runtime + 12-family generator (`extgen/`) | done |
| Browser→extension→telemetry→JSONL smoke test (24 sessions) | done, 24/24 complete |
| Full dataset: 576 sessions / 144 extensions (`lab/collect.py`, ~3 min) | done; QA in `results/dataset_report.json` |
| Graph builder (`authgraph/graph.py`), 11 node / 17 relation types | done |
| Models: rules, RF (NumPy), MLP, GCN, GraphSAGE, R-GCN (plain PyTorch) | done |
| Experiments: extension split ×5, unseen-flow (Wasm + LOSO ×6), 4 ablations | done (v1 untuned, v2 tuned) |
| Explainer (occlusion, model-agnostic), dashboard (8 pages), live run | done; pages 1–7 smoke-tested headlessly; live scenario run tested via script |
| Report, viva, README, architecture figure | done |

## Events worth knowing (including failures)
1. **sklearn blocked**: Windows Application Control blocked `sklearn.tree._criterion`. Did not bypass; wrote a NumPy Random Forest. sklearn.metrics works.
2. **v1 results (untuned GNNs, kept in `results/v1_untuned/`)**: R-GCN (349k params) was worst GNN: extension-split F1 0.904; unseen-Wasm recall 0.263. GraphSAGE best.
3. **Tuning (`tune.py`)**: validation-only, same grid for all GNNs. v2 selected R-GCN h=16, 4 bases (5.5k params). Result: R-GCN still worse than GraphSAGE (F1 0.904 vs 0.988; unseen-Wasm recall 0.450 vs 0.929). Hypothesis for the gap (untested): under-converged early stopping on 2/5 splits.
4. Explainer first returned no path for saturated scores; switched to log-odds importance and an explicitly-labelled structural fallback; fallback is shown only for flagged sessions.
5. Standard extension split is easy (RF/MLP/GraphSAGE F1 > 0.95) when taint is visible — reported, not hidden.

6. **Confidence display (three attempts)**: (a) validation-fitted temperature scaling rejected (worse test log-loss). (b) `calibrate_oof.py`: cross-fitted temperature/Platt/binning on 576 out-of-fold predictions — none beat raw softmax ECE. (c) `ensemble.py`: 10-model deep ensembles per architecture (`models/ENS_*.pt`): log-loss and Brier better for both, ECE better for GraphSAGE (0.015->0.011), slightly worse for R-GCN (0.041->0.047); scores no longer saturate. Dashboard shows the 95% Wilson lower bound of the pooled, monotone score band (never 100%, higher score never shows lower confidence); provisional "risk so far" for incomplete sessions. R-GCN on never-seen flows: ECE 0.287, accuracy 61% (caveat shown).

7. **Session Replay Play bugs (found by the user)**: (a) `StreamlitDuplicateElementId` when two consecutive frames produced identical charts -> unique `key` per frame; (b) slider state written after widget creation -> removed; slider now lives in a placeholder (progress bar while playing, created at final position afterwards), no `st.rerun(scope="fragment")`. My first browser check only looked for JS page errors and missed Streamlit error boxes; now verified with 48 Play runs (all 12 families x 4 sessions, AppTest, 0 exceptions, slider ends at last event) and a real-browser run over 6 families checking for `stException` boxes (0).

8. **UI fixes (user report)**: sidebar could not be re-opened once collapsed because CSS hid Streamlit's header -> header now transparent (only the Deploy button hidden), expand button styled; Session Replay events table was newest-first -> chronological with the latest row highlighted, fixed height, risk chart moved under the graph; added narrow-window (<=1150px) column wrapping, hover/transition polish. Verified: 16/16 page tests, 48/48 Play runs, real-browser collapse/re-expand and Play at 950px and 1600px (0 error boxes).

9. **Session Replay (user report)**: replay now starts at 0 events (READY) and resets on page entry/session change; events table full width and chronological; badge removed. First real-browser check was flawed (waited on an element present from the start); redone with timed waits. Sweep `data/sweep.py` (113 checks: all pages x detectors, all 12 families on session pages, replay start/play/re-entry, live run) 0 failures; real-browser pass 0 error boxes. AppTest cannot judge visuals; the zip has NOT been rebuilt since these changes.

## Frozen artifacts
- Dataset `data/graphs.pkl` sha256 prefix `aba4c1c4174241d0` (576 graphs). **Re-running `run_dataset.sh` produces a NEW random sample** (random credentials/timing/distractors), so re-run results will differ slightly from the reported ones.
- Tuned config `results/tuned_config.json`; all runs in `experiments.csv` (v2) and `results/v1_untuned/`.

## NOT YET DONE / NOT MEASURED
- Clean-environment end-to-end re-run of `./run_demo.sh` on a second machine (only the individual steps were run here).
- Dashboard browser-level visual check of the live-run page inside Streamlit (live pipeline tested outside it).
- Explanation faithfulness; real-extension corpus; adversarial evaluation; Docker compose (not needed; omitted).
