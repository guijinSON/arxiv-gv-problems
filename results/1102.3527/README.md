# Binary innovative vectors from arXiv:1102.3527

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | integer tuple (a binary encoding vector) |
| Intended intuition | invariant: recover each bit from a 3-to-1 receiver-index parity majority |
| Domain essentiality | native |
| Reduction | none |

## What the problem is, and whether to trust this result

This is the paper's native innovative-encoding-vector problem from Ho Yuet
Kwan, Kenneth W. Shum, and Chi Wan Sung, [“Generation of Innovative and Sparse
Encoding Vectors for Broadcast Systems with Feedback”](https://arxiv.org/abs/1102.3527).
A solver receives exact parity-check descriptions of receiver subspaces of
`GF(2)^n` and must return one binary vector outside every subspace.  Every
receiver span is a hyperplane, so checking a witness is only an exact XOR of
four submitted bits per receiver.

The generator is certified answer-first.  It chooses cyclic four-coordinate
checks for which an alternating vector in a hidden coordinate order has odd
parity, then randomly relabels the coordinates.  It never runs elimination to
obtain `inst["answer"]`.  The first cyclic layer has rank `n-1` by construction;
all checks have even weight, so the global complement is also valid and these
are exactly the two answers.

All local correctness and attack gates pass.  The required external oracle
loop could **not** complete: every OpenRouter request returned HTTP 403 “Key
limit exceeded.”  The three transcript files are the untouched files written
by `harden.py` and contain those errors, not model failures.  Consequently this
directory is locally verified but is **not yet oracle-hardened or ready to
submit**; no claim about four-vendor model resistance is inferred from 0 valid
attempts.

## Why this is Track B

Section II fixes “innovative” to mean outside the row span already known by a
receiver.  Section III defines `q-IEV`, proves binary `2-IEV` NP-complete, and
uses orthogonal `B` matrices as exact parity-check descriptions in Theorem 1's
proof.  It also identifies the easy large-field regime `q >= K`.  Theorem 2 and Section IV give
the cofactor method in that regime, with cost
`O(K N^3 + K^2 N)`.  Those results rule out pretending this construction is a
Track-A family.

This generated special case is also polynomial: because each subspace is the
kernel of one parity check, the task is `A x = 1` over `GF(2)`.  Reduced-row-
echelon Gaussian elimination solves all 8/8 audit instances in
`O(K n^2)` scalar work.  At the shipping preset it used at most **1,614,850**
counted pivot tests/scalar XORs and **0.0234 s** locally.  That is easy for a
machine and not executable by hand in the evaluation context.

The compact route is different.  In any block of `n` consecutive receivers,
each coordinate occurs four times; the parities of those four local receiver
indices have a 3-to-1 majority.  Taking that majority for every coordinate
produces the hidden alternating vector or its global complement.  It costs at
most `4n = 288` parity/majority operations at shipping size.  The test is
whether a solver sees this invariant amid 1,008 shuffled-looking checks.

## Worked demo (`n=8`, `layers=1`, `seed=0`)

The complete rendered mathematical data are:

```text
Binary innovative encoding vector

All arithmetic is in GF(2): addition is XOR, so a sum is 1 exactly when it
contains an odd number of ones.  Vector coordinates are indexed 0 through
7.  Receiver R_i already knows the hyperplane

    H_i = {y in GF(2)^8 : XOR of y[j] over the listed indices j is 0}.

Find one encoding vector x in GF(2)^8 that is innovative for every receiver,
meaning x is outside every H_i.  Equivalently, for every line below, the XOR of
the four listed coordinates of x must equal 1.  Receiver order has no effect on
validity.  Repeated coordinates are not allowed in a support (none occur here).

The 8 receiver parity-check supports are:
R0: 1 2 4 6
R1: 4 5 6 7
R2: 1 3 6 7
R3: 0 3 4 7
R4: 0 2 3 6
R5: 0 2 5 7
R6: 1 2 3 5
R7: 0 1 4 5

Give your final answer inside <answer></answer> tags as one JSON list of exactly
8 integers, each 0 or 1, in coordinate-index order.  Example syntax:
<answer>[0, 1, 0, 1]</answer>
The example is format-only and has the wrong length for this instance.  Output
nothing else inside the tags.
```

One answer is `<answer>[1, 0, 0, 0, 1, 1, 0, 1]</answer>`.
`verify(inst, answer)` returns `(True, "ok")`.  Swapping entries 0 and 1 gives
`[0, 1, 0, 0, 1, 1, 0, 1]`, which returns
`(False, "noninnovative_receiver:0")`.  A person can solve this demo on paper
by XOR elimination or by spotting the occurrence-parity majority.

## Difficulty presets

| preset | n | cyclic layers | receivers K | answer atoms | compact operations | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 1 | 8 | 8 | 32 | hand example |
| easy | 48 | 6 | 288 | 48 | 192 | local gates pass; oracle unavailable |
| medium | 60 | 10 | 600 | 60 | 240 | local gates pass |
| hard | 72 | 14 | 1,008 | 72 | 288 | **shipping preset**; local gates pass |

Escalation first adds cyclic layers at fixed answer length.  It only raises `n`
after exhausting that haystack axis and reports `cap_bound` before the compact
route would exceed 300 operations.

## Gate results at `hard`

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; all answers JSON-round-trip |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | tagged answer recovered from prose/fence; garbage returns `None` |
| G4 | 0/200,000 uniform structure-aware guesses; exact density `2 / 2^72 = 4.235e-22` |
| G5 | exactly 2 answers; rank 71; reference maximum 1,614,850 operations and 0.0234 s |
| G6 | degree outlier, greedy, 1,024 restarts, and obvious ansatzes each 0/8; Gaussian 8/8 |
| G7 | `n=144`, 14 layers builds in 0.0164 s and the certificate verifies |
| G8 | 20/20 relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 216 chars, about 54 tokens, 72 atoms, 288 intended operations; compact route verifies |

## Oracle and G9 diagnostics

| run | preset | valid solved/attempts | result |
|---|---|---:|---|
| bare hardening ladder | easy | 0/0 | four redraws returned HTTP 403; no verdict |
| structural hint | hard | 0/0 | four redraws returned HTTP 403; not run |
| placebo hint | hard | 0/0 | four redraws returned HTTP 403; not run |

`hinted - placebo` is therefore not measurable, and the recorded `0.0` in the
selftest report is only the zero-attempt placeholder.  It says nothing about
the quality of the invariant hint.  The structural hint names the 3-to-1
parity invariant and does not state what operation to perform with it.

## Use

```python
import gen_1102_3527 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=7)
prompt = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 1102.3527
```

Run `python3 results/1102.3527/gen_1102_3527.py` to reproduce the local gate
report.  Re-run `python3 ../../scripts/harden.py gen_1102_3527.py` from this
directory after restoring OpenRouter quota; then update the three G9 arm counts
and `SHIPPING_DIFFICULTY` from the actual verdict.

## Caveats

- This is a deliberately structured hyperplane subclass, not evidence that
  worst-case binary `2-IEV` became easy.  Gaussian elimination is the explicit
  reference algorithm and the reason for Track B.
- Receiver ordering carries the compact cyclic clue.  Arbitrarily permuting
  receivers preserves the mathematical instance and Gaussian solution but can
  destroy the no-tool shortcut.  The canonical key is invariant to that
  relabelling anyway.
- `canonical_key` uses sorted support-intersection and coordinate-cooccurrence
  profiles.  It passed the required relabellings but is not a complete
  hypergraph-isomorphism or arbitrary-`GF(2)` change-of-basis canonical form.
- The `P(guess)` prior is uniform over all correctly shaped binary vectors.  It
  exactly matches the declared certificate language but does not model a
  solver that has already inferred some parity equations.
- More layers do not reduce the two-solution set after rank `n-1`; they enlarge
  the visible haystack and the mechanical elimination workload.  They may also
  give a sophisticated structure learner more evidence.
- I did not test industrial SAT/SMT encodings, code-equivalence algorithms, or
  learned cyclic-structure recovery.  Exact Gaussian elimination is stronger
  than the four reported no-tool heuristics but is intentionally separated as
  the successful Track-B reference.
- Most importantly, the four-vendor oracle and both hint controls remain
  unmeasured because of account quota.  This must be resolved before shipping.
