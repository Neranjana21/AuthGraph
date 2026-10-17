# Demo script (3 minutes) and viva Q&A

All numbers are from `results/tables.md`. If you re-run anything, re-read the tables first.

## 3-minute demo (dashboard: `./run_demo.sh`)
1. **(20 s) Lab.** Sidebar → *8 · Live lab run*. "Everything is localhost, synthetic credentials, a real Chromium with a freshly generated extension."
2. **(30 s) Benign.** Pick `B4_authed_approved_api` (credential read, but sent to the *approved* API) → *Run scenario*. Show BENIGN, low risk, no highlighted path. Say: this is the hard negative — a credential access alone is not a verdict.
3. **(60 s) Suspicious.** Pick `S3_cred_wasm_sink`, model "trained WITHOUT Wasm exfiltration flows". Show the event table, the graph, SUSPICIOUS + risk score, and the highlighted credential → … → sink path. If the path is labelled "structural fallback", say so out loud.
4. **(30 s) Comparison.** *4 · Model comparison* → on the standard split even simple count features reach F1 > 0.95 (be upfront), so that split is not the story.
5. **(40 s) The research moment.** *7 · Unseen-flow* → Wasm-involving flows were **never seen in training**: GraphSAGE recall 0.929, taint rule 0.646, count-based RF/MLP 0.62–0.69. Then, unprompted: "our R-GCN did **not** win (0.450); the best model was the simpler GraphSAGE."

Live runs can miss (e.g. an S5 session was scored 0.27 by the no-Wasm model in a test) — that is real; say it rather than re-rolling until it looks good.

## Likely viva questions

**Q1. Is this the first graph-based browser-extension detector?** No. DoubleX (CCS 2021) uses extension dependence graphs; Arcanum (USENIX Sec 2024) does dynamic taint tracking; graph/GNN malware detection exists. Our scope is narrower: an authentication-aware heterogeneous graph + GNNs, compared with baselines under unseen-flow splits, in a controlled lab.

**Q2. Are the attacks real?** They are controlled proof-of-concept behaviours inside a localhost lab with synthetic credentials, built only to generate labelled telemetry. No real site/user/token is involved.

**Q3. How can the labels not be circular?** The label is the scenario design (credential-derived data → unapproved destination). The rule R2 almost restates it, so it is perfect when taint is visible; we therefore also report R1, flat models and the taint-lost subset. The comparison that matters is how methods behave when the telemetry is incomplete or the flow is unseen.

**Q4. The telemetry is self-reported by our own extensions. Why trust it?** It's a limitation. We cross-checked request counts against a server-side log (576/576 sessions match) and verified no credential values leak. A real system needs browser-level capture (e.g. Arcanum-style).

**Q5. Why does the Wasm taint drop at 0.5?** A design parameter modelling JS-level trackers that cannot see inside Wasm. It is not measured from real trackers; it determines the 34 "taint-lost" suspicious sessions and shapes the Wasm results.

**Q6. Your proposed R-GCN lost. Why present it?** Because it's the measured result. v1 (untuned, 349k params) and v2 (validation-tuned, basis decomposition, 5.5k params) both lost to GraphSAGE; v1 is kept in `results/v1_untuned/`. Hypothesis (untested): under-converged/noisy early stopping on 2/5 splits and poor transfer of relation-specific weights with ~350 graphs.

**Q7. Is GraphSAGE's near-perfect score trustworthy?** Treat it cautiously: the dataset is synthetic and small, and graphs may contain a simple shortcut (credential connected to an unapproved domain). The ablations show destination info and auth nodes matter most; taint edges help (−0.04 F1 without) but are not essential.

**Q8. Data leakage?** Splits are by extension (all sessions of an extension stay together); features exclude names/scenario IDs; unseen-flow tests withhold whole families. Test sets of the 5 split seeds overlap, so std understates uncertainty.

**Q9. Why not PyTorch Geometric / scikit-learn trees?** PyG is a frequent Py3.13/Windows install risk, and writing GCN/SAGE/R-GCN in plain PyTorch keeps them explainable. This machine's Application Control policy blocked scikit-learn's compiled tree module, so the Random Forest is a small NumPy implementation (not a workaround of the policy).

**Q10. What does "latency" mean here?** Offline per-session cost: graph build 0.053 ms + inference 0.003–4.97 ms depending on model, CPU, batch size 1. Not a deployed real-time monitor.

**Q11. What's the explanation, exactly?** Occlusion: Δ log-odds when a node/edge is removed; path = highest-importance credential→domain path. When the score is saturated and no edge matters individually, a structural shortest path is shown and labelled as such. Faithfulness vs. ground truth is not yet measured.

**Q12. What would make this a real contribution?** Real extensions with browser-level telemetry, adversarial adaptation tests, and explanation faithfulness checks — all NOT YET MEASURED.

**Q13. Is the 99% confidence believable?** The detector is a 10-model ensemble, so the score is an average and no longer saturates. We measured it on 576 out-of-fold predictions (extensions never seen by the scoring model): the ensemble improves log-loss and Brier for both detectors (ECE: GraphSAGE 0.015->0.011, R-GCN 0.041->0.047). The card shows the 95% lower bound of the accuracy observed in the score band (GraphSAGE top band 550/550 -> >=99.3%), never 100%. Caveats: synthetic data from the same 576 sessions; for never-seen flow families R-GCN is badly calibrated (ECE 0.287, accuracy 61%) and the dashboard warns about it; while a session is still replaying we show only a provisional risk.
