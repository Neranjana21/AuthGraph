# AuthGraph: presentation script

**Talk length:** about 20 minutes plus questions (19 main slides). For a 15-minute slot, cut slides 5, 9 and 13 down to one sentence each and shorten the demo to two steps.
**Slides:** `AuthGraph_deck.pptx` (appendix slides 20 to 25 are for questions only).
**Style:** say it in your own words; the lines below are a guide. Numbers are exact and come from executed runs.

---

## Before you start (2 minutes)

- Open the deck in presenter view and the dashboard in a second window: `.\.venv\Scripts\python -m streamlit run dashboard.py`, then open http://localhost:8501.
- In the dashboard open **Live Lab Run** and untick "Show browser window" if you do not want a Chromium window to pop up.
- Have **Session Replay** ready as the fallback if a live run fails.
- Keep `results/tables.md` open in case someone asks for a number that is not on a slide.

---

## Slide 1: Title (20 seconds)

**Say:** "Browser extensions can legitimately read your cookies and page data. So the security question is not whether a credential is read, but where it goes. This project builds a controlled lab that produces real browser telemetry, turns it into an authentication-aware graph, and tests whether graph neural networks can detect unauthorized credential flows, including flows that pass through WebAssembly."
**Point to:** the picture on the right. "That is real output of the system: a session graph with the suspicious path in red."
**Transition:** "Let me start with why this is hard."

## Slide 2: A session cookie is one API call away (1 minute)

**Say:** "The top row is a perfectly legitimate extension. It reads the session cookie and sends it to the approved API. The bottom row reads the same cookie through the same API, but sends it through JavaScript or a WebAssembly module to a destination that is not approved."
"A detector that only asks whether the cookie API was called cannot tell these two apart. Only the destination and the data flow differ. That is why I model the whole flow as a graph, and why the dataset contains hard negatives: benign sessions that read credentials and use approved APIs."
**Transition:** "Here is the whole result in four numbers."

## Slide 3: What we found, in four numbers (1 minute)

**Say:** "Four numbers carry the story."
- "576 real browser sessions from 144 generated extensions, and zero credential values anywhere in the telemetry."
- "0.929: with every Wasm-involving suspicious flow removed from training, GraphSAGE still detects 93% of them. A taint rule detects 65%, and flat count-based models 62 to 69%."
- "0.450: our proposed R-GCN, the heterogeneous model, did much worse. It lost, and I report it."
- "At least 99.3%: the confidence on the top band. That is the lower bound of what was actually observed on held-out data. The system never prints 100%."
"The message: graph structure helps exactly where instrumentation is incomplete. But the relation-typed R-GCN did not beat plain GraphSAGE on this small synthetic dataset. The honest result is the useful one."
**Say once, clearly:** "This is synthetic data from a controlled lab, so it demonstrates the method, not real-world detection rates."

## Slide 4: Positioning (1 minute)

**Say:** "I want to be explicit about what is not new. DoubleX, from CCS 2021, builds a static Extension Dependence Graph and analysed over 154 thousand extensions. Arcanum, from USENIX Security 2024, does dynamic taint tracking from page content to network sinks. Graph neural networks on malware behaviour graphs already exist. And there is published work on WebAssembly and JavaScript attacks on Chrome extensions."
"My claim is narrower: an authentication-aware heterogeneous graph with GNN detection of credential flows, compared against rules, flat machine learning and homogeneous GNNs, under extension-level and unseen-flow splits, including the case where taint is lost inside WebAssembly. I make no claim about real-world extensions. That is not yet measured."
**If asked about the last two references:** "I found them through search results; I have not read them in full yet, so I flag them."

## Slide 5: A safe lab (45 seconds)

**Say:** "Everything runs on localhost. Credentials are synthetic and random per login. The collector stores only a body length and a short hash, never a credential value. The extensions are proof-of-concept behaviours that exist only to generate labelled telemetry; there is no persistence and no real malware."
"The label is by design: suspicious means credential-derived data sent to an unapproved destination. I checked: a search for the token strings in all 7,258 events found none."

## Slide 6: System (1 minute)

**Say:** "Left to right. The lab app issues synthetic cookies. Generated Manifest V3 extensions run in real Chromium and make real cookies, storage, DOM, fetch and WebAssembly calls. Telemetry is written as JSONL with hashed credential IDs, and every request is cross-checked against a server-side log. A graph builder turns each session into a typed graph. Detectors score it. An explainer returns the path."
**Be honest here:** "The telemetry is self-reported by instrumented lab extensions. It is not browser-level capture the way Arcanum does it."

## Slide 7: Dataset (1 minute)

**Say:** "Twelve scenario families, twelve generated extensions each, four sessions per extension: 576 sessions, balanced 288 and 288. Six benign families and six controlled-suspicious ones."
"Two of the benign families are deliberate hard negatives. B4 reads a credential and sends it to the approved API. B5 reads a credential but sends only unrelated data to an analytics host."
"The integrity panel is measured: no credential leaks, no schema failures, no duplicates, and the number of requests in the telemetry equals the server log in all 576 sessions."
**Disclose the design choice:** "With probability 0.5 the WebAssembly output loses its taint tag, to model a JavaScript-level tracker that cannot see inside Wasm. That gives 254 suspicious sessions with taint visible and 34 with taint lost. That rate is my choice, not a measured property of real trackers."

## Slide 8: The graph (1 minute)

**Say:** "Each session becomes a heterogeneous graph: components like the content script and service worker, JavaScript and Wasm modules, browser APIs, credentials, storage objects, requests, and destination domains. Eleven node types and seventeen relations. On average 13 nodes and 19 edges."
"Orange is the credential. The red path is what the explainer highlights. Taint is represented by two dedicated relations, so I can remove them in an ablation and see what the structure alone contributes."
"Features carry no extension names, module names or scenario labels."

## Slide 9: Protocol (1 minute)

**Say:** "Three rules to avoid fooling myself. First, no leakage: splits are by extension, so no extension is in both train and test, and unseen-flow tests withhold whole scenario families. Second, fair tuning: all three GNNs get the same validation-only grid, and the test sets are never touched. Third, nothing hidden: every run is logged, and I kept the first untuned run."
**Two disclosures:** "The Random Forest is a small NumPy implementation, because a local Windows policy blocked scikit-learn's tree module and I did not bypass it. And the standard deviation over five splits understates uncertainty, because the test sets overlap."

## Slide 10: Standard split (1 minute)

**Say:** "On the standard split almost everything works, because when taint is visible the task is nearly trivial. Even a Random Forest on simple counts reaches 0.98. GraphSAGE is the best learned model at 0.988. Rule R1 has perfect recall but flags 16.7% of benign sessions. R-GCN is lowest at 0.904."
"So this split does not separate the methods. The next two slides do." (Mention the axis starts at 0.80.)

## Slide 11: Never-seen Wasm flows, the research moment (90 seconds)

**Say:** "Here I removed every WebAssembly-involving suspicious family from training. The test is 96 never-seen suspicious sessions plus 48 benign ones from unseen extensions."
"GraphSAGE still detects 93%, with a 3.7% false-positive rate. The taint rule reaches only 65%, because the taint tag is lost inside Wasm. Flat count models reach 62 to 69%. Rule R1 shows perfect recall, but only because it flags everything that touches a credential and an unapproved host, which is why its false positives are 16.7%."
"And then, our proposed R-GCN: 0.450."
**Do not oversell:** "This is one synthetic distribution and five overlapping splits."

## Slide 12: Leave-one-family-out and taint-lost (1 minute)

**Say:** "Leaving out only the Wasm family, or only the staged multi-component family, tells the same story: GraphSAGE generalises, the taint rule and flat models are less reliable, and R-GCN struggles."
"The right panel is the sharpest evidence for the graph. In the 25 test sessions where taint was lost inside Wasm, the taint rule detects none, by construction. GraphSAGE detects all of them."
**Caveat:** "Part of that advantage may come from dataset regularities, such as a credential connected to an unapproved domain in a small graph. Real extensions would not respect that."

## Slide 13: Ablation (45 seconds)

**Say:** "I removed one kind of information at a time and retrained everything. Removing destination information hurts most: GraphSAGE falls from 0.988 to 0.899. Removing credential nodes comes next, to 0.917. Taint edges help by about four points, but without them it still reaches 0.948. Removing the JS and Wasm nodes barely changes it."
(Mention the axis starts at 0.75.)

## Slide 14: The honest negative (1 minute)

**Say:** "I expected the heterogeneous R-GCN to win. It did not, in either run. The untuned version had 349 thousand parameters. After a validation-only search with basis decomposition it has 5.5 thousand, and it is still worse than GraphSAGE."
"My diagnosis is a hypothesis, not a finding. On two of five splits it stopped early with training loss still near 0.2, and per-relation weights may not transfer to unseen relation combinations with only about 350 training graphs."
"I did not tune on the test data, I kept the untuned run, and I did not rewrite the story around the model I wished had won."

## Slide 15: Explainability (1 minute)

**Say:** "The system does not just say suspicious. It removes each node and edge in turn, re-scores the graph, and reports how much the log-odds fall. The red path is the highest-importance route from the credential, through the POST request, to the unapproved sink."
"Two honesty points. Importance is occlusion on the model output, not attention weights. And when a score is saturated and no single removal matters, the dashboard shows a structural shortest path and labels it as such. I have not yet measured how faithful these explanations are."

## Slide 16: A confidence score you can believe (75 seconds)

**Say:** "A raw softmax from one small network saturates near 100%, which is not believable. I tried temperature scaling, Platt scaling and binning, cross-fitted on 576 out-of-fold predictions. None beat the raw scores."
"What did help is an ensemble. Averaging ten independently trained models lowers log-loss and Brier for both architectures. The share of sessions scoring 99.9% or more drops from 90% to 69% for GraphSAGE, and from 45% to 8% for R-GCN."
"The dashboard then quotes the lower bound of the accuracy actually observed in the score band. GraphSAGE's top band was 550 correct out of 550, so it reads at least 99.3%."
**Caveat:** "On never-seen flows R-GCN's confidence is badly off: ECE 0.287 at 61% accuracy. The dashboard warns about it. Bands come from the same synthetic dataset."

## Slide 17: Live demo (3 minutes)

1. **Live Lab Run, scenario 1 (Authenticated API Call).** "A brand-new extension is generated, loaded into real Chromium, and classified." Expect BENIGN, no highlighted path. "It reads the credential, but sends it to the approved API."
2. **Scenario 3 (Credential via WebAssembly).** Expect SUSPICIOUS, the red path, and the confidence card. "Notice the card quotes the lower bound, not 100%."
3. **Unseen-Flow and Ablation page.** Show the research chart.
4. **Model Comparison page.** Show the table.

**If a live run misses:** say so. Do not re-roll until it looks good. Use **Session Replay**: press Play and watch the graph build; the verdict appears only when the session completes, and while it runs the card says OBSERVING with a provisional risk.

## Slide 18: Limitations and next steps (1 minute)

**Say:** "The biggest limitation is realism: my extensions come from a small generator and report their own telemetry, so these results demonstrate the method on a controlled distribution, not detection rates on real malware. The Wasm taint-drop rate is my design choice."
"The next steps that would change the conclusions most are browser-level telemetry and real extensions, then an adversary who adapts to the detector."

## Slide 19: Conclusion (45 seconds)

**Say:** "Three sentences. It works end to end in a real browser. Graph structure helps precisely where instrumentation fails, at the Wasm boundary. And I report what lost; everything, including failures, is documented and reproducible."
**Close:** "Thank you. I am happy to take questions; the appendix has the full tables, ROC and precision-recall curves, confusion matrices, training curves and calibration bands."

---

## Backup questions and answers

**Is this the first graph-based browser-extension detector?** No. DoubleX (CCS 2021) uses extension dependence graphs, Arcanum (USENIX Security 2024) does dynamic taint tracking, and graph neural networks for malware behaviour exist. My scope is narrower and I list what I do not claim on slide 4.

**Are the attacks real?** They are controlled proof-of-concept behaviours in a localhost lab with synthetic credentials, built only to produce labelled telemetry. No real site, user or token is involved.

**Isn't the label circular?** The label comes from the scenario design (credential-derived data to an unapproved destination). The taint rule almost restates it, so it is perfect when taint is visible. That is why I also report the co-occurrence rule, flat models, and the taint-lost subset. The informative comparison is what happens when telemetry is incomplete or the flow is unseen.

**The telemetry is self-reported. Why trust it?** It is a limitation. I cross-checked request counts against a server log in all 576 sessions and verified no credential values leak. A real system needs browser-level capture.

**Why 0.5 for the Wasm taint-drop?** It models a JavaScript-level tracker that cannot see inside Wasm. It is my design choice, not a measurement; it produces the 34 taint-lost suspicious sessions.

**Your proposed model lost. Why present it?** Because it is the measured result. Both the untuned and the validation-tuned versions lost to GraphSAGE. The untuned run is kept in the repository.

**Can I trust GraphSAGE's near-perfect scores?** Be cautious: the data are synthetic and small, and graphs may contain a simple shortcut, a credential connected to an unapproved domain. The ablations show destinations and authentication nodes matter most.

**Is there data leakage?** Splits are by extension, features exclude names and scenario IDs, and unseen-flow tests withhold whole families. The test sets of the five seeds overlap, so the standard deviation understates uncertainty.

**Why not PyTorch Geometric or scikit-learn trees?** PyTorch Geometric is a common install risk on Python 3.13 and Windows, and plain PyTorch keeps the models explainable. A local policy blocked scikit-learn's compiled tree module, so the Random Forest is a small NumPy implementation; I did not bypass the policy.

**What does latency mean here?** Offline per-session cost: graph building is about 0.05 ms and inference 0.003 to 5 ms depending on the model, on a CPU, batch size 1. It is not a deployed real-time monitor.

**How is the explanation computed?** Occlusion: the drop in log-odds when a node or edge is removed. The path is the highest-importance credential-to-domain route. If the score is saturated, a labelled structural fallback is shown. Faithfulness against ground-truth paths is not yet measured.

**Is the 99% confidence believable?** The detector is a ten-model ensemble, so the score is an average. On 576 out-of-fold predictions the ensemble lowers log-loss and Brier for both models. The card shows the 95% lower bound of the accuracy observed in the score band, never 100%. Caveats: synthetic data from the same 576 sessions, and for never-seen flow families R-GCN is badly calibrated, which the dashboard warns about.

**What would make this a real contribution?** Real extensions with browser-level telemetry, adversarial adaptation tests, and explanation-faithfulness checks. All of them are not yet measured.
