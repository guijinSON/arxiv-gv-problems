# One-epoch hinge-SGD data debugging (arXiv:2408.01365)

Status: **locally verified; oracle hardening blocked by OpenRouter quota**.  The
three script-owned runs were attempted, but every request returned HTTP 403
`Key limit exceeded`; consequently no model failure is counted and this result
does not yet carry a `hardened` verdict.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | optimization |
| Object regime | rational exact |
| Computational core | subset sum |
| Certificate | integer tuple (native retained-row IDs) |
| Intuition | decomposition |
| Domain essentiality | native |
| Reduction kind | none |

## Problem and trust basis

The family instantiates Guo, Chen, Fu, and Miao, [“Data Debugging is NP-hard
for Classifiers Trained with SGD”](https://arxiv.org/abs/2408.01365).  A solver
receives an ordered set of exact rational, one-dimensional training samples, a
hinge-like loss with `beta=-1`, an initial classifier weight, a mandatory final
sentinel, and a labeled test point.  It must name a fixed-size subset of
ordinary rows whose one-epoch retraining changes the test prediction from -1
to +1.  `verify` checks shape and then replays every hinge-margin comparison
and SGD update with exact rational arithmetic; it never reads `inst["answer"]`.

Section 2 fixes the classifier, strict activation, and SGD conventions.
Theorems 4.1 and 4.2 are the easy cases that this family avoids: linear loss is
handled by the linear-time GTA algorithm, as is one-dimensional hinge-like loss
when `beta >= 0`.  Theorem 4.4 and its Appendix B.1 proof cover the chosen
regime: dimension 1, `beta=-1`, constant learning rate, a fixed adversarial
order, and one epoch.  Appendix B.1 maps fixed-cardinality Subset Sum into the
paper's rational samples and proves that a successful trajectory has exactly
the required cardinality and sum.

Generation is by composition, not search.  Each four-number block is sampled
with an identity `a+b=c+d`; one side from every block is chosen before the SGD
instance is assembled.  Distinct block residues and a global permutation hide
the composition, while all four members are produced by the same exchangeable
identity sampler.  The selected pairs total exactly half of all offsets, so
Appendix B.1 supplies the SGD witness.

This is explicitly Track B.  The complete, domain-standard reference algorithm
is fixed-cardinality Horowitz--Sahni meet-in-the-middle, with
`O(2^(n/2))` time and storage.  At shipping `n=40`, it completed in 20.0876 s,
enumerated 1,572,864 half-subset states, performed 3,145,725 counted operations,
and found all 600 valid canonical answers.  Once the hidden invariant is seen,
normalizing the rational coordinates and decomposing four-member residue
classes modulo 997 takes at most 180 exact arithmetic operations.  That large
mechanical-to-compact gap—not an average-case NP-hardness claim—is the stated
difficulty.

## Worked demo

For `make_instance(n=8, payload_bits=5, seed=0)`, the statement supplies
`w0=-23/6`, normalizer `A=216396`, sentinel `x=1298377/1298376`, and these
ordinary rows:

```text
0: 464563/649188   1: 458581/649188   2: 51175/72132
3: 464093/649188   4: 452129/649188   5: 460105/649188
6: 462569/649188   7: 152039/216396
```

The planted output is `<answer>[0, 1, 3, 4]</answer>` and
`verify(inst, [0, 1, 3, 4]) == (True, "ok")`.  Dropping the last ID gives
`(False, "too few IDs: exactly 4 ordinary samples are required")`.  A person
can solve this smallest case on paper: there are only 35 symmetry-broken
four-subsets, or two small residue blocks to recognize.

## Difficulty presets

| Preset | n | Payload bits | Answer IDs | Status |
|---|---:|---:|---:|---|
| demo | 8 | 5 | 4 | hand-scale illustration |
| easy | 40 | 20 | 20 | shipping candidate; local gates pass |
| medium | 52 | 28 | 26 | reserve escalation |
| hard | 64 | 36 | 32 | reserve escalation |

`SHIPPING_DIFFICULTY` is `easy`.  The bare oracle run could not accept or
reject this rung because all provider calls failed before producing replies.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 plants verify; 16/16 full models mispredict |
| G2 | pass | six corruptions rejected with six distinct reasons |
| G3 | pass | realistic fenced prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; 68,923,264,410 candidates |
| G5 | pass | exact 600 solutions; density 8.7053e-9; MITM 20.0876 s |
| G6 | pass | five attacks, 0/8 successes each; compact decoder 8/8 as expected |
| G7 | pass | `n=80` double-size build verifies; space 5.375e22 |
| G8 | pass | 60 invariant transforms, 60 witness transports, 20/20 distinct seeds |
| G9(c) | pass | 72 chars (18 estimated tokens; worst case 20), 20 atoms, 180 operations |

## Oracle loop

These rows are the actual harness output, not evidence that a model failed the
problem.  An error does not consume an attempt.

| Preset | Seed | Model | Scored result | Why |
|---|---:|---|---|---|
| easy | 42133524 | OpenAI GPT-5.6 Terra | error | HTTP 403 key limit |
| easy | 1965187272 | Anthropic Claude Sonnet 5 | error | HTTP 403 key limit |
| easy | 2130063737 | Anthropic Claude Sonnet 5 | error | HTTP 403 key limit |
| easy | 1873658756 | Anthropic Claude Sonnet 5 | error | HTTP 403 key limit |

The harness then stopped with “oracle pool is unreachable”; `.meta.json`
therefore has no `harden_verdict`.  Re-run the command below after restoring
OpenRouter quota.

## G9 arms

| Arm | Solved / scored attempts | Provider errors | Conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | unavailable |
| structural hint | 0/0 | 4 | unavailable |
| placebo hint | 0/0 | 4 | unavailable |

Thus `hinted - placebo` is not estimable; the zero stored in the report is only
the neutral value used when both denominators are zero.  The answer measures 72
serialized characters (18 estimated tokens, with a 20-token worst case), 20
atomic IDs, and at most 180 intended-route exact operations.

## Use

```python
from gen_2408_01365 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
prompt = render(inst)
candidate = parse_answer("<answer>[0, 1, 2]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit records after a successful hardening rerun with:

```bash
cd results/2408.01365
python3 ../../scripts/harden.py gen_2408_01365.py
cd ../..
bash scripts/emit.sh 2408.01365 20
```

## Caveats

The family deliberately has an `O(n)` generator-aware decoder, so it must never
be represented as Track A.  Revealing the modulus or residue blocks makes it
easy.  G4 samples uniform fixed-size subsets containing ID 0; it measures that
declared language, not a human prior or the probability of a heuristic search.
The exact solution count includes accidental cross-block solutions (600 rather
than the 512 guaranteed ones), which the density reports honestly.

The full meet-in-the-middle reference was run, but the LLL panel entry is only
an explicitly named 80-loop floating Gram--Schmidt prefix because no lattice
library is permitted; a complete, optimized LLL implementation was not tried.
Neither a general-purpose CSP solver nor modern representation-based subset-sum
algorithms were tested.  Canonicalization is complete for ordinary-row
permutations and simultaneous `(x,y)` sign flips, not for every possible affine
equivalence of rational SGD instances.  Most importantly, no claim of oracle
hardness is warranted until the quota-blocked bare run completes and returns
`hardened`.
