# Dashboard screenshots (1920 px wide viewport, 1.5x, full page height)

| File | What it shows |
|---|---|
| 01_dashboard | Overview: dataset size, held-out detection table, dataset integrity checks |
| 02a_session_replay_ready | Session Replay at 0 events (READY) |
| 02b_session_replay_playing | Mid-replay: OBSERVING with risk so far, graph growing |
| 02c_session_replay_complete | Completed replay: SUSPICIOUS verdict, confidence, graph, risk curve, events |
| 03_graph_visualization | Heterogeneous graph with the credential-to-sink path highlighted |
| 04a_model_comparison_scores | Results table and score chart |
| 04b_roc_pr_curves | ROC and precision-recall curves |
| 04c_training_latency | Training curves and inference latency |
| 04d_confidence_calibration | Single model vs ensemble, score bands, never-seen-flow calibration |
| 05_confusion_matrices | Confusion matrices (split 0) |
| 06a-06c_explainability | Node importance, edge importance, rule-based explanation |
| 06d_explainability_no_wasm_detector | Detector trained without Wasm flows, with its caveat |
| 07a_unseen_flow | Unseen-flow recall table and chart |
| 07b_ablation | Ablation table and chart |
| 08a_live_lab_cards | Live Lab Run scenario cards |
| 08b_live_result_wasm_exfiltration | Live run: Wasm exfiltration, SUSPICIOUS + path |
| 08c_live_result_benign_authenticated_call | Live run: authenticated call to approved API, BENIGN |

Print-ready (white background) charts are in ../figures/, dark versions in ../figures/dark/.
