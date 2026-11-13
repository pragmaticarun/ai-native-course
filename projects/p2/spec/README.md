# P2 — Graph research agent with supervisor, critic, HITL and evals

**After:** M5–M7 · **Language:** Python, LangGraph (mock model; no API key)

A LangGraph supervisor decomposes a question into sub-questions and routes them to parallel
researcher workers (fan-out with `Send`). Their findings fan in to a writer; a critic checks
every citation and sends bad drafts back (reflection, capped); a human approves, rejects or
edits the report at an `interrupt`. Checkpoints make the pause survive a restart, every node
is traced with OpenTelemetry, and an eval suite scores trajectory, factuality, cost and
latency.

The corpus (`common/corpus.json`) is about **an invented city, Riverton**: every number in it
is fictional. The mock LLM (`common/p2_kit.py`) can be *sloppy* (changes a number, cites the
wrong document) so the critic has real mistakes to catch.

## Milestones

| # | File | You build | Evals |
|---|---|---|---|
| M1 | `p2_graph.py` | supervisor + router: one `Send` per sub-question, `no_evidence` when nothing matches | `test_supervisor_*`, `test_out_of_scope_*` |
| M2 | `p2_graph.py` | workers: `RetryPolicy` for transient search errors, drop other-year sources, merge duplicates at fan-in | `test_transient_*`, `test_retries_*`, `test_outdated_*` |
| M3 | `p2_critic.py` + graph | support rules (numbers + content words + right document) and a capped reflection loop | `test_critic_rules`, `test_reflection_*`, `test_revision_cap_*` |
| M4 | `p2_graph.py` | the human gate (`interrupt` / `Command(resume=...)`), checkpoint resume in a new graph | `test_human_gate`, `test_pause_survives_a_restart` |
| M5 | `p2_tracing.py` | an OTel span per node with node, topic, tokens and simulated seconds | `test_every_node_is_traced` |
| M6 | `p2_evals.py` | trajectory checks, gold recall, strict citation precision, cost and critical-path latency | `test_trajectory_*`, `test_factuality_metrics`, `test_suite_*` |

## Done when

All evals pass; the suite scores 1.0 trajectory, gold recall and citation precision on the
five questions with a sloppy first draft; out-of-scope questions are refused, not answered.

## Stretch (not built here)

A TypeScript port with LangGraph.js; a real LLM behind `MockLLM`'s three methods; an LLM
judge for paraphrased claims, calibrated against the rule-based critic; OTLP export to a real
tracing backend.
