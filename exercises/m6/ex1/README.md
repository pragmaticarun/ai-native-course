# M6 · Exercise 1 — Write a judge rubric and calibrate it against 10 human labels

An LLM judge is a measuring instrument: check it against humans before trusting it.

1. Write `RUBRIC`: a rubric for grading a release-notes entry with **anchors for every score
   1–5** (each of the strings `"1"`, `"2"`, `"3"`, `"4"`, `"5"` must appear followed by a
   colon, e.g. `"5: ..."`).
2. `cohen_kappa(a, b)`: Cohen's kappa for two equal-length lists of booleans
   (κ = (p_o − p_e) / (1 − p_e); return 1.0 when p_e == 1).
3. `calibrate(judge_scores, human_pass)`: for each threshold t in 1..5, the judge "passes" an
   item when `score >= t`. Return `(best_t, kappa)` for the threshold with the highest kappa
   against the human labels (ties → the lower threshold).
