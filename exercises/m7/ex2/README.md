# M7 · Exercise 2 — Turn a free-form agent into a graph, and measure the difference

`impl.py` contains `freeform_triage(model, lines)`: a free-form loop where the model decides
what to do next ("classify 3", "done") and then classifies one line per call. It is complete,
and it works most of the time, but it spends a planning call per line and the scripted model
in the tests sometimes declares itself done early.

1. Write `graph_triage(model, lines)` as a **LangGraph** `StateGraph`: a node that classifies
   *every* line (one model call per line, prompt `"classify: <line>"`, the model answers with a
   label), then a node that groups them. Return `{"labels": [...], "calls": n}` where `calls` is
   the number of model calls (`len(model.calls)` on a `ScriptedModel`).
2. Write `compare(make_model, lines, gold)`: run both approaches (each with a fresh model from
   `make_model()`) and return
   `{"freeform": {"accuracy": a, "calls": c}, "graph": {"accuracy": a, "calls": c}}` where
   accuracy is the fraction of lines whose label equals `gold` (a missing label counts as wrong).

The point: the graph makes the control flow code, so it can't skip work, and it is cheaper.
