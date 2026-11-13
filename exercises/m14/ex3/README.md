# Ex 14.3: WER vs latency: choosing an ASR model size

The syllabus exercise measures the WER/latency trade-off between whisper.cpp model sizes. Running
whisper.cpp needs its models and real speech recordings, which the course box doesn't have, so the
**measurement step is untested**. This exercise builds the scoring and choosing code; the test data
(`tests/asr_runs.json`) is **synthetic**: hypotheses written by hand to contain realistic error
types, with made-up timings. Replace it with your own whisper.cpp runs.

Write:

1. `wer(ref, hyp)`: word error rate = (substitutions + deletions + insertions) / reference words,
   after lower-casing and removing punctuation except apostrophes. Empty reference: 0.0 if the
   hypothesis is empty too, else 1.0.
2. `corpus_wer(pairs)`: total edits / total reference words (word-weighted, *not* the mean of
   per-utterance WERs).
3. `choose(runs, max_wer, max_rtf)`: the run with the lowest `rtf` (compute seconds per audio second)
   whose corpus WER is <= `max_wer` and `rtf <= max_rtf`; ties go to the lower WER; `None` if none fit.
