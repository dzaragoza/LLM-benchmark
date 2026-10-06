# practitioner-goals.md — The Study's Goals, From the Author's Own Rulings

What this study is for, stated as the author ruled it across the
lab notebook. Every goal below is on record with its ruling; the
report is written against these goals, and any methods choice that
does not serve them is out of scope.

---

## The goals

1. **Answer the practitioner's actual question: "what's the best
   model for MY hardware?"** There is a widespread misunderstanding
   of hardware capabilities vs model expectations; the study
   exists to replace that with measurement. (Author's motivation,
   on record at the study-#3 reframe, Session 26.)

2. **The guarantee is the reader's experience, not throughput.**
   The verdict is the reader-wall test (protocol v3.0, addendum
   55): a simulated 300-wpm reader (5.0 w/s, Brysbaert 2019; 0.45 s
   reaction) must never hit the wall — no word arrives after the
   reader is ready for it, mid-stream included. "The reader is the
   final judge. If the reader hits the wall, they feel the model
   is slow, so it fails." (Author, addendum 55.)

3. **Within-model, across-quant-ladder comparisons — no
   inter-model confounds** for the speed-vs-quality relationship.
   The ladder is Q8_0 → Q6_K → Q5_K_M → Q4_K_M (addendum 49):
   below ~4.5 bpw the quality penalty is too steep — "a user is
   better served by a smaller model in the q4–q8 band."
   (Author, addendum 49.)

4. **Right-sizing over flagships.** On integrated GPUs the family
   size grids (1B/3B/8B/14B) quantize coarser than the machine's
   passable window — the right-size model is usually NOT the
   family's flagship. The predictor's job is to find the largest
   family member INSIDE the window (addendum 58). A model that
   passes only at Q8_0 is suspect of "leaving brains on the
   table" — the pick should be the largest member predicted to
   pass at Q5_K_M (author, addendum 48).

5. **Class-exclusive benchmarking (bandwidth classes).** Machines
   are benchmarked on the model sizes they unlock: only sizes
   that fail on every lower bandwidth class and pass on this one.
   A below-class model is pointless on this hardware — the
   practitioner would simply switch machines. The real benefit
   for practitioners is the class-exclusive set. (Author,
   addendum 65.)

6. **Prefer the word-efficient tokenizer class.** The 1–6B window
   is tokenizer-shaped: the passable ceiling scales linearly with
   w/t_min (60% more model for 50% more tokenizer efficiency).
   Selection should prefer the word-efficient class; the
   tokenizer probe runs pre-shortlist at zero model cost.
   (Author, addendum 59: "the key is the tokenizer, we definitely
   want to aim for more efficient tokenizers.")

7. **A general, cheap predictor.** The per-family w/t factor is
   ad hoc — the study needs a general rule from cheap
   pre-download measurements (file size, params, tokenizer
   probe), refined by the w/t calibration pass (n=50
   conversations; trust band ±0.9 w/s: ≥5.9 trusted PASS, ≤4.1
   trusted FAIL, between → bench). "The predictor proposes, the
   walk disposes." (Author, addendum 57; trust band addendum 62.)

8. **Pre-registered, auditable, simple.** Predictions are
   recorded before any bench; the constants registry
   (protocol.md) is the single source of truth for every number;
   unused constants are deleted; the predictor carries at most
   ONE new term. "Sometimes a simple predictor is better than a
   complex one." (Author, addenda 44, 51, 57.)

9. **Same rules for everyone.** No model-specific debugging: a
   model that fails the gate fails — "it failed the test, it is
   out of scope why. The rules are the same for everyone."
   (Author, addendum 47, on gemma.)
