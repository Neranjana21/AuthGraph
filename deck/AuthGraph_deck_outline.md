# AuthGraph — slide-by-slide content and speaker notes

Generated from AuthGraph_deck.pptx. Every number comes from the measured result files (see make_data.py).


## Slide 1: AuthGraph

- Authentication-aware graph learning to detect unauthorized credential flows in browser extensions
- Controlled-lab prototype  ·  real Chromium  ·  576 sessions  ·  144 extensions
- Presented by Neranjana

**Speaker notes:** OPENING (20 s). Browser extensions can legitimately read cookies and page data, so the security question is not 'is a credential read?' but 'where does it go?'. This project builds a controlled lab that produces real browser telemetry, turns it into an authentication-aware graph, and tests whether graph neural networks detect unauthorized credential flows — including flows that pass through WebAssembly. The picture is the actual output of the system: a session graph with the suspicious credential-to-sink path highlighted in red. Everything runs on localhost with synthetic credentials.


## Slide 2: A session cookie is one API call away

- Extensions legitimately read cookies, storage and pages. The question is where the credential goes, not whether it is read.
- AUTHORIZED  ·  BENIGN
- Extension
- chrome.cookies.get
- Session credential
- POST request
- api.lab.localhost / (approved)
- UNAUTHORIZED  ·  SUSPICIOUS
- Extension
- chrome.cookies.get
- Session credential
- JS / WebAssembly
- sink-a.lab.localhost / (unapproved)
- Same API calls, same credential. Only the destination and the data flow differ, so API-level rules are not enough.
- 2

**Speaker notes:** PROBLEM (60 s). Top row is a perfectly legitimate extension: it reads the session cookie and sends it to the approved API. Bottom row reads the same cookie through the same API, but routes it through JavaScript or a WebAssembly module and sends it to a destination that is not approved. A detector that only looks at 'cookie API was called' cannot tell these apart. That is why the project models the whole flow as a graph and also builds hard negatives into the dataset — benign sessions that read credentials and use approved APIs.


## Slide 3: What we found, in four numbers

- 576
- real browser sessions from 144 generated MV3 extensions in 12 scenarios; 0 credential leaks
- 0.929
- GraphSAGE recall on Wasm flows never seen in training. Taint rule 0.646, flat models 0.62–0.69
- 0.450
- R-GCN, our proposed heterogeneous model, on the same test. It lost, and we report it
- ≥99.3%
- top-band confidence: the 95% lower bound of accuracy observed on held-out data. Never 100%
- THE MESSAGE
- Graph structure helps exactly where instrumentation is incomplete: when taint is lost inside WebAssembly, the graph still exposes the flow. / But the relation-typed R-GCN did not beat plain GraphSAGE on this small synthetic dataset. The honest result is the useful one.
- 3

**Speaker notes:** EXECUTIVE SUMMARY (60 s). Four numbers carry the story. First, the evidence base: 576 real browser sessions, no credential value ever stored. Second, the research moment: with Wasm-involving flows removed from training, GraphSAGE still catches 93% of them, while a taint rule catches 65% and flat count-based models catch 62 to 69%. Third, the honest negative result: our proposed R-GCN reached only 0.45. Fourth, the confidence score: we never print 100%; we quote the lower bound of what was actually observed. Caveat to state out loud: this is synthetic data from a controlled lab, so it demonstrates the method, not real-world prevalence.


## Slide 4: Positioning: a narrow claim on top of strong prior work

- PRIOR WORK (CHECKED BY SEARCH)
- DoubleX (ACM CCS 2021): static Extension Dependence Graph for vulnerable data flows; 154,484 Chrome extensions. / Arcanum (USENIX Security 2024): dynamic taint tracking of page content to network sinks in modern extensions. / Heterogeneous-graph GNNs for malware behaviour graphs already exist (e.g. MalSage; title seen in search only). / Wasm–JS collaborative attacks on Chrome extensions (Electronics; title seen, not yet read in full).
- OUR CLAIM
- An authentication-aware heterogeneous graph of runtime behaviour, with GNN detection of credential flows, compared with rules, flat ML and homogeneous GNNs under extension-level and unseen-flow splits.
- WE DO NOT CLAIM
- the first extension graph or detector / the first GNN in browser security / any result on real-world extensions (NOT YET MEASURED)
- 4

**Speaker notes:** POSITIONING (60 s). Be explicit about what is not new. DoubleX and Arcanum are the closest prior art: one static, one dynamic. Graph-based malware detection with heterogeneous GNNs is established. What this project adds is narrower and testable: an authentication-aware graph representation and a controlled comparison against baselines, specifically under unseen flow patterns and with taint lost across the Wasm boundary. Two references (MalSage, the Electronics Wasm paper) were found through search snippets; they should be read in full before a formal citation. Say that if asked.


## Slide 5: A safe lab: nothing leaves localhost

- Localhost only
- App on :5000, collector and sink hosts on *.lab.localhost:5001 and 127.0.0.1. No external network.
- Synthetic credentials
- Fresh random cookie and JWT per login. Telemetry stores only a hashed ID, never a value.
- Controlled behaviours
- Proof-of-concept extensions exist only to produce labelled telemetry. No persistence, no real malware.
- Label by design
- Suspicious = credential-derived data sent to an unapproved destination. Fixed by scenario, not by a detector.
- 5

**Speaker notes:** THREAT MODEL AND SAFETY (45 s). All 'attacks' are controlled proof-of-concept behaviours inside an isolated browser profile against a local Flask app. No real user, site, cookie or token is ever involved, and the collector stores only body length and a short hash. We verified this: a search for the token strings in all 7,258 telemetry events found zero. The ground-truth label is a property of the scenario design, which matters for how we interpret the rule baselines later.


## Slide 6: System: from a real browser event to an explained verdict

- Controlled lab
- Flask auth app with synthetic cookie/JWT; collector and sink hosts
- Real Chromium
- Generated MV3 extensions use chrome.cookies, storage, DOM, fetch and WebAssembly
- Telemetry JSONL
- Hashed credential IDs; server-log cross-check of every request
- Heterogeneous graph
- 11 node types, 17 relations; taint edges kept separable
- Detectors
- Rules, RF, MLP, GCN, GraphSAGE, R-GCN; 10-model ensembles
- Explanation
- Occlusion importance and the highlighted credential-to-sink path
- Everything on localhost  ·  synthetic credentials only  ·  graph + verdict + path shown live in the dashboard
- 6

**Speaker notes:** ARCHITECTURE (60 s). Walk left to right. The lab generates extensions; each one is a real Manifest V3 extension loaded into Chromium via Playwright, performing real chrome.cookies, storage, DOM, fetch and WebAssembly calls. Telemetry is written as JSONL with hashed credential IDs, and every request is cross-checked against a server-side log. A graph builder converts each session into a typed graph; detectors score it; an occlusion explainer returns the path. Honest limitation to mention: the telemetry is self-reported by instrumented lab extensions, not captured at browser level the way Arcanum does.


## Slide 7: Dataset: 576 real sessions, hard negatives included

- 576
- sessions
- 144
- extensions
- 288 / 288
- benign / suspicious
- 7,258
- events captured
- INTEGRITY CHECKS (EVERY RUN)
- 0
- credential-value leaks in any event
- 0
- events failing the schema
- 0
- duplicate events
- 576 / 576
- sessions where telemetry matches the server log
- B1 | DOM only
- B2 | storage settings
- B3 | approved API
- B4 | authenticated call to approved API (hard negative)
- B5 | credential read + unrelated analytics (hard negative)
- B6 | benign WebAssembly
- S1 | direct credential to sink
- S2 | via 1–3 JS hops
- S3 | via WebAssembly
- S4 | content script ↔ service worker
- S5 | staged through storage
- S6 | chunked to a raw-IP sink
- Wasm output loses its taint tag with probability 0.5 (a design choice modelling a JS-level tracker). Result: 254 suspicious sessions have taint visible at the sink, 34 have it lost.
- 7

**Speaker notes:** DATASET (60 s). 12 scenario families, 12 generated extensions each, 4 sessions per extension, all run in real Chromium. Six benign families and six controlled-suspicious families. Two benign families are deliberate hard negatives: B4 reads a credential and sends it to the approved API, B5 reads a credential but sends only unrelated data to an analytics host. The integrity panel is measured: no credential value in any event, no schema failures, and the number of requests in telemetry equals the server log in every session. One design choice you must disclose: with probability 0.5 the Wasm output loses its taint tag, modelling a JS-level tracker that cannot see inside Wasm. That gives 34 taint-lost suspicious sessions.


## Slide 8: An authentication-aware graph of each session

- REPRESENTATION
- 11 node types: extension, content script, service worker, JS, Wasm, API, credential, storage, request, domain, page / 17 relations, including flows_cred and carries (taint) that can be ablated / Mean 13.2 nodes and 19.4 edges per session / No names or scenario labels used as features
- 8

**Speaker notes:** GRAPH (60 s). Each session becomes a heterogeneous graph: components such as the content script and service worker, JavaScript and Wasm modules, browser APIs, credentials, storage objects, requests and destination domains. Orange is the credential; the red path is what the explainer highlights: credential to request to an unapproved domain. Taint information is represented by two dedicated relations, flows_cred and carries, so we can remove them in an ablation and see how much the structure alone contributes. Domain nodes only carry 'approved' and 'is an IP'; no extension names, module names or scenario labels leak into the features.


## Slide 9: Experimental protocol: built to avoid fooling ourselves

- DETECTORS
- Rule R1: credential accessed AND unapproved request / Rule R2: unapproved request carrying a credential taint tag / Random Forest and MLP on count features / GCN, GraphSAGE, R-GCN in plain PyTorch / 10-model ensembles for the dashboard scores
- SPLITS
- Extension-level: all sessions of an extension stay in one split / 5 split seeds, mean ± std / Unseen flow: hold out Wasm families (S3 + S5) entirely / Leave-one-family-out for S1 to S6
- RIGOR
- Validation-only tuning, identical grid for all GNNs / Test sets never used for any choice / Threshold 0.5, not tuned / Every run logged; the untuned v1 run is kept / NumPy Random Forest (a local policy blocked sklearn's tree module)
- 9

**Speaker notes:** PROTOCOL (60 s). Three rules guard against self-deception. First, no leakage: the split is by extension, so no extension appears in both train and test, and unseen-flow tests withhold whole scenario families. Second, fair tuning: all three GNNs get the same validation-only grid; the test sets are never touched. Third, nothing hidden: every run is in experiments.csv and the first untuned run is kept alongside the tuned one. Disclose: scikit-learn's tree module was blocked by a local Windows policy, so the Random Forest is a small NumPy implementation; we did not bypass the policy. Std over five splits understates uncertainty because test sets overlap across seeds.


## Slide 10: Standard split: easy when taint is visible

- HOW TO READ THIS
- RF and MLP on simple counts already reach F1 0.98 and 0.96 / GraphSAGE is best: F1 0.988, ROC-AUC 1.000 / Rule R1 flags 16.7% of benign sessions / R-GCN is lowest of the learned models: 0.904 / This split does not separate the methods, so the unseen-flow test matters
- 10

**Speaker notes:** RESULT 1 (60 s). On the standard extension-level split, almost everything works, because when taint is visible the task is nearly trivial: even a Random Forest on counts gets 0.98. GraphSAGE is the best learned model at 0.988. Rule R1, the 'credential plus unapproved request' co-occurrence rule, gets perfect recall but flags 16.7% of benign sessions. R-GCN trails at 0.904. The honest reading: this split does not discriminate between methods. That is why the next two slides, unseen flows and taint-lost sessions, are the informative tests. Note the axis starts at 0.80 to make differences visible; say so.


## Slide 11: Never-seen Wasm flows: graph structure still detects them

- THE RESEARCH MOMENT
- 0.929
- GraphSAGE recall at 3.8% false positives
- Taint rule R2: 0.646, because taint is lost inside Wasm / Flat models: 0.62–0.69 / Rule R1 reaches 1.00 recall but with 16.7% false positives / R-GCN: 0.450
- 11

**Speaker notes:** RESULT 2 — THE RESEARCH MOMENT (90 s). We removed every Wasm-involving suspicious family, S3 and S5, from training. The test is 96 never-seen suspicious sessions plus 48 benign ones from unseen extensions. GraphSAGE still detects 93% at a 3.7% false-positive rate. The taint rule only reaches 65%, because the taint tag is lost inside Wasm. Flat count-based models reach 62 to 69%. Rule R1 has perfect recall but only because it flags every session that touches a credential and an unapproved host, which is why its false-positive rate is 16.7%. Then, unprompted: our proposed R-GCN reached only 0.45. Do not oversell the 0.93: this is one synthetic distribution and five overlapping splits.


## Slide 12: Leave-one-family-out, and the taint-lost sessions

- TAINT LOST INSIDE WASM
- n = 25 suspicious test sessions
- 0%
- Rule R2 (taint rule)
- 92%
- RF (counts)
- 100%
- GraphSAGE
- 64%
- R-GCN
- Detection rate on these sessions. A taint rule cannot see them at all.
- 12

**Speaker notes:** RESULT 3 (60 s). Leaving out only S3 (credential via Wasm) or only S5 (staged across components) tells the same story: GraphSAGE generalises, the taint rule and flat models are less reliable, and R-GCN struggles. The right panel is the sharpest evidence for why a graph helps: in the 25 test sessions where taint was lost inside Wasm, Rule R2 detects none by construction, while GraphSAGE detects all of them. Caveat: part of that advantage may be dataset regularities, such as a credential connected to an unapproved domain in a small graph, which real extensions would not respect.


## Slide 13: Ablation: which information actually matters

- WHAT THE DATA SAY
- Destinations matter most: GraphSAGE F1 0.988 → 0.899 / Auth nodes next: → 0.917 / Taint edges help: → 0.948, yet the structure alone keeps most of the signal / JS/Wasm nodes barely change GraphSAGE (0.988)
- 13

**Speaker notes:** ABLATION (45 s). We removed one kind of information at a time and retrained everything. Removing destination information hurts the most, and removing credential nodes hurts next: the model genuinely uses the destination and the authentication context. Taint edges help by about four F1 points for GraphSAGE, but without them it still reaches 0.948, so structure alone carries a lot. Removing the JS and Wasm nodes barely changes GraphSAGE. Be careful to state that the y-axis starts at 0.75; all models are high on this standard split.


## Slide 14: The honest negative: our proposed R-GCN lost

-  | Parameters | Standard split F1 | Unseen Wasm recall
- R-GCN, untuned (v1) | 349,058 | 0.904 | 0.263
- R-GCN, validation-tuned (v2) | 5,498 | 0.904 | 0.450
- GraphSAGE | 28,034 | 0.988 | 0.929
- HYPOTHESES (NOT YET TESTED)
- Under-converged: on 2 of 5 splits the best epoch was 10 and 21 with train loss near 0.2 / Per-relation weights may transfer poorly to unseen relation combinations with about 350 training graphs
- WHAT WE DID NOT DO
- Tune anything on the test sets / Hide the first run: results/v1_untuned/ is kept / Move the goalposts: the unseen-flow headline is GraphSAGE
- 14

**Speaker notes:** NEGATIVE RESULT (60 s). We expected the heterogeneous R-GCN to win. It did not, in either run. The untuned version had 349 thousand parameters; after a validation-only search with basis decomposition it has 5.5 thousand, and it is still worse than GraphSAGE. The diagnosis is a hypothesis, not a finding: on two of five splits it stopped at epoch 10 and 21 with training loss still near 0.2, and per-relation weights may not transfer to relation combinations never seen in training with only about 350 graphs. We did not tune on the test data, we kept the untuned run, and we did not rewrite the story around the model we wished had won. That is the point of reporting it.


## Slide 15: Explainability: the path that triggered the verdict

- SUSPICIOUS
- confidence ≥99.3%
- 550 of 550 held-out sessions in this score band were correct
- HIGHLIGHTED ATTACK PATH
- jwt_localstorage:6c988e
- POST /b
- stats.lab.localhost:5001
- credential → request → unapproved sink
- How it works. Remove one node or edge, re-score, and measure the drop in log-odds; the path is the highest-importance route from credential to domain. A saturated score falls back to a labelled structural path. Faithfulness vs ground-truth paths: NOT YET MEASURED.
- 15

**Speaker notes:** EXPLAINABILITY (60 s). The system does not just say 'suspicious'. It removes each node and edge in turn, re-scores the graph, and reports how much the log-odds fall. The red path in the screenshot is the highest-importance route from the credential, through the POST request, to the unapproved sink. Two honesty points: importance is occlusion on the model output, not attention weights; and when the score is saturated and no single removal matters, the dashboard shows a structural shortest path and says so. We have not measured how faithful these explanations are against known ground-truth paths. That is future work.


## Slide 16: A confidence score you can believe

- Detector | Model | ECE | Log-loss | Brier
- GraphSAGE | single | 0.015 | 0.039 | 0.012
- GraphSAGE | ensemble | 0.011 | 0.032 | 0.010
- R-GCN | single | 0.041 | 0.263 | 0.067
- R-GCN | ensemble | 0.047 | 0.161 | 0.048
- SUSPICIOUS
- confidence ≥99.3%
- Observed 100.0% correct (95% interval 99.3–100.0%): 550 of 550 held-out sessions in this score band.
- The card quotes the 95% lower bound of observed accuracy. It never prints 100%.
- HOW IT IS BUILT
- 10 independently seeded models, scores averaged / 576 out-of-fold predictions from unseen extensions / Bands pooled so a higher score never shows lower confidence
- CAVEAT
- On never-seen flows, R-GCN reports confidence of about 86% while being 61% accurate (ECE 0.287). Its confidence is not trustworthy there; the dashboard warns.
- 16

**Speaker notes:** CONFIDENCE (75 s). A raw softmax from one small network saturates near 100%, which is not believable. We tried temperature scaling, Platt scaling and binning on the single model, cross-fitted on 576 out-of-fold predictions, and none beat the raw scores. What does help is an ensemble: averaging ten independently trained models lowers log-loss and Brier for both architectures, and the share of sessions scoring 99.9% or more drops from 90% to 69% for GraphSAGE and from 45% to 8% for R-GCN. ECE improves for GraphSAGE and is about the same for R-GCN. The dashboard then quotes the 95% lower bound of the accuracy actually observed in the score band, so GraphSAGE's top band, 550 of 550 correct, reads 'at least 99.3%'. State the caveat: on never-seen flow families R-GCN's confidence is badly off, ECE 0.287 at 61% accuracy, and bands come from the same synthetic dataset.


## Slide 17: Live demo: event to graph to verdict, in a real browser

- Session Replay: events arrive, the graph grows, the verdict appears when the session completes
- Live Lab Run: a freshly generated extension in real Chromium, classified on the spot
- 3-minute path:  1 benign authenticated call → BENIGN   2 Wasm exfiltration → SUSPICIOUS + path   3 unseen-flow chart   4 comparison table
- 17

**Speaker notes:** DEMO (3 min). Open the dashboard. Step 1: Live Lab Run, scenario 1 'Authenticated API Call'. The system generates a brand-new extension, runs it in real Chromium, and shows BENIGN with no flagged path. Step 2: scenario 3, 'Credential via WebAssembly', which shows SUSPICIOUS with the red credential-to-sink path and the confidence card. Step 3: Unseen-Flow and Ablation page for the research chart. Step 4: Model Comparison. If a live run misses, say so; do not re-roll until it looks good. Session Replay is the fallback: press Play and watch the graph build and the verdict appear at the end. While a session is still in progress the card says 'OBSERVING' with a provisional risk number; verdict and confidence appear only for complete sessions.


## Slide 18: Limitations, and what comes next

- LIMITATIONS
- Telemetry is self-reported by instrumented lab extensions, not captured at browser level / A generator with a small step vocabulary, not real extensions / Label defined by construction; the Wasm taint-drop rate (0.5) is our choice / One dataset of 576 sessions; the 5 splits overlap / No adaptive adversary / Latency is offline CPU inference, not a deployed monitor
- NEXT STEPS (NOT IMPLEMENTED)
- Browser-level capture (CDP, Arcanum-style) instead of self-reporting / A corpus of real extensions / Adversarial and evasion evaluation / Understand and fix R-GCN: longer training, edge-type regularisation / Explanation faithfulness against known flows / Streaming, real-time deployment
- 18

**Speaker notes:** LIMITATIONS AND NEXT STEPS (60 s). The biggest limitation is realism: our extensions are generated from a small vocabulary and report their own telemetry, so results demonstrate the method on a controlled distribution, not detection rates on real malware. The Wasm taint-drop rate is a design parameter, not a measured property of real trackers. The next steps that would change the conclusions most are browser-level telemetry and real extensions, then an adversary who adapts to the detector.


## Slide 19: Conclusion

- It works end to end
- Real browser events become an authentication-aware graph, a verdict, a confidence and an explained path, live.
- Structure helps when instrumentation fails
- GraphSAGE caught 100% of the taint-lost Wasm sessions and 0.929 of never-seen Wasm flows. A taint rule caught none of the former.
- We report what lost
- R-GCN did not beat GraphSAGE (0.450 vs 0.929). The untuned run, the failed calibrators and the limits are all documented.
- Everything shown is reproducible from the repository; every number comes from an executed run.
- 19

**Speaker notes:** CONCLUSION (45 s). Three sentences. One: the system works end to end in a real browser. Two: graph structure helps precisely where instrumentation fails, which is the Wasm boundary. Three: we report what lost, and everything, including failures, is documented and reproducible. Then invite questions; the appendix has the full tables, ROC and PR curves, confusion matrices, training curves and calibration bands.


## Slide 20: Appendix A: full results, extension-level split

- Model | Precision | Recall | F1 | ROC-AUC | FPR | Infer ms | Train s | Params
- Rule R1 (co-occurrence) | 0.857 | 1.000 | 0.923 | 0.917 | 0.167 | 0.004 | 0.00 | 0
- Rule R2 (taint) | 1.000 | 0.896 | 0.945 | 0.948 | 0.000 | 0.005 | 0.00 | 0
- RF (counts) | 0.976 | 0.992 | 0.984 | 0.997 | 0.025 | 0.304 | 0.88 | 7,086
- RF (counts+reachability) | 0.955 | 0.996 | 0.974 | 0.996 | 0.050 | 0.225 | 0.69 | 5,880
- MLP (counts) | 0.944 | 0.971 | 0.957 | 0.993 | 0.058 | 0.003 | 0.12 | 6,466
- GCN | 0.935 | 0.933 | 0.934 | 0.983 | 0.067 | 0.635 | 2.67 | 18,306
- GraphSAGE | 0.984 | 0.992 | 0.988 | 1.000 | 0.017 | 0.659 | 1.35 | 28,034
- R-GCN | 0.909 | 0.904 | 0.904 | 0.966 | 0.100 | 4.974 | 4.27 | 5,498
- Mean over 5 extension-level splits, threshold 0.5. Inference is offline, per session graph, batch size 1, CPU; graph construction adds 0.053 ms. Params for RF are tree nodes.
- 20

**Speaker notes:** APPENDIX A. Full table behind slide 10. Latency is offline CPU inference, not a deployed real-time monitor.


## Slide 21: Appendix B: ROC and precision-recall curves

- 21

**Speaker notes:** APPENDIX B. ROC and PR curves for split 0 on held-out test extensions.


## Slide 22: Appendix C: confusion matrices, training curves and latency

- 22

**Speaker notes:** APPENDIX C. Confusion matrices (split 0), training and validation loss for the three GNNs, and inference latency per model.


## Slide 23: Appendix D: confidence calibration in detail

- SCORE BANDS (ENSEMBLE, OUT-OF-FOLD)
- Detector | Score band | Sessions | Correct | Accuracy | 95% lower
- GraphSAGE | 50–70% | 7 | 3 | 0.429 | 0.158
- GraphSAGE | 70–85% | 19 | 15 | 0.789 | 0.567
- GraphSAGE | 85–100% | 550 | 550 | 1.000 | 0.993
- R-GCN | 50–70% | 28 | 14 | 0.500 | 0.326
- R-GCN | 70–85% | 85 | 61 | 0.718 | 0.614
- R-GCN | 85–95% | 132 | 131 | 0.992 | 0.958
- R-GCN | 95–100% | 331 | 330 | 0.997 | 0.983
- SAVED ENSEMBLES ON THEIR TEST SETS
- Detector · training | n | Mean conf. | Accuracy | ECE
- GraphSAGE · standard split | 96 | 0.990 | 0.990 | 0.014
- GraphSAGE · Wasm held out | 144 | 0.945 | 0.972 | 0.028
- R-GCN · standard split | 96 | 0.927 | 0.917 | 0.076
- R-GCN · Wasm held out | 144 | 0.861 | 0.611 | 0.287
- The verdict card quotes the 95% lower bound of the band accuracy. Adjacent bands are pooled so a higher score never shows a lower confidence. ECE above 0.2 means the confidence is not trustworthy for that detector under that shift.
- 23

**Speaker notes:** APPENDIX D. Single model versus ensemble, the pooled score bands with Wilson intervals, and the never-seen-flow calibration of the saved ensembles.


## Slide 24: Appendix E: reproducibility and what is not yet measured

- RUN IT
- ./setup.sh / ./run_demo.sh /   / streamlit run dashboard.py /   / Dataset frozen (576 graphs); re-running the lab produces a new random sample. All runs are logged in experiments.csv; the untuned v1 run is kept.
- NOT YET MEASURED
- Clean-machine end-to-end re-run / Explanation faithfulness / Real-extension corpus / Adversarial evaluation / Browser-level (non-self-reported) telemetry
- 24

**Speaker notes:** APPENDIX E. Reproducibility and the explicit list of things that were not measured.


## Slide 25: Appendix F: references

- Fass, Somé, Backes, Stock. DoubleX: Statically Detecting Vulnerable Data Flows in Browser Extensions at Scale. ACM CCS 2021. / Xie, Kasi Murali, Pearce, Li. Arcanum: Detecting and Evaluating the Privacy Risks of Browser Extensions on Web Pages and Web Content. USENIX Security 2024. / I Spy with My Little Eye: Analysis and Detection of Spying Browser Extensions. arXiv:1612.00766. / The Blind Spot of Extension Security: WebAssembly–JavaScript Collaborative Attacks on Chrome. Electronics, doi:10.3390/electronics15143049 (title only; read before citing). / Kipf and Welling. Semi-Supervised Classification with Graph Convolutional Networks. ICLR 2017. / Hamilton, Ying, Leskovec. Inductive Representation Learning on Large Graphs. NeurIPS 2017. / Schlichtkrull et al. Modeling Relational Data with Graph Convolutional Networks. ESWC 2018.
- 25

**Speaker notes:** APPENDIX F. References. The Electronics paper and MalSage were located via search snippets and should be read in full before a formal citation.
