# M4 · Exercise 3 (TypeScript) — Grep vs embedding retrieval, measured

Don't argue about RAG, measure it. Implement in `retrieval.ts`:

- `recallAtK(ranked, relevant, k)`: the fraction of `relevant` ids found in the first `k`
  of `ranked` (0 when `relevant` is empty).
- `compare(questions, retrievers, k)`: `questions` is a list of `{ q, relevant }`;
  `retrievers` maps a name to `(q) => string[]` (ranked ids). Return, per retriever name,
  `{ meanRecall, wins }` where *wins* counts the questions on which that retriever's recall
  is strictly higher than every other retriever's.

The tests compare an exact-match "grep" retriever with a fuzzy one on identifier and
paraphrase questions. Neither wins everywhere, which is the point of the lesson.
