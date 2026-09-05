# VT power-syndrome deletion decoding (arXiv:2501.13534)

> Status: the generator and local gates G1--G8 are audited, but this result is not
> shippable yet. OpenRouter quota reached zero during the one permitted medium-level
> G9 rerun. `selftest_report.json` therefore records G9 as failing/pending rather
> than claiming a passing result; this directory is not shippable yet. A fresh
> medium-level retry on 2026-09-05 again received HTTP 403 `Key limit exceeded
> (total limit)` on every redraw before any attempt could be scored.

| profile field | value |
|---|---|
| Track | B -- no-tool compression |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | integer tuple (the paper's support set) |
| Intended intuition | change of variables: detect an affine image of a centered template |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

This family isolates the exact set-code decoder in Sections 2.1--2.3 of
[Schaller, Toesca, and Vu, *A New Construction of Non-Binary Deletion Correcting
Codes and their Decoding*](https://arxiv.org/abs/2501.13534). The solver receives
the surviving support of a binary constant-weight word and its first `t` VT power
sums in `F_p`, and must return the `t` deleted support positions. This is a native
component of the paper's Construction 14/16 pipeline, not a graph encoding of it.

`make_instance` samples the deleted support first as an affine image of a centered
odd-step template, adds independently sampled survivors, and only then computes
the syndrome. Thus generation is inverse generation, not decoding disguised as
generation. `verify` checks shape, range, disjointness, and all power sums by exact
modular arithmetic; it never reads `inst["answer"]`. Definition 4's asymmetric-error
correction property gives uniqueness.

## Why Track B

Track A would be false. The paragraph following Definition 4 in Section 2.3 says
the cited decoder is linear in the binary word length `q` and `t`, up to
polylogarithmic factors. The bundled generic decoder instead uses Newton identities
and Cantor--Zassenhaus factorization, with expected polynomial complexity in `t`
and `log(p)`. At the medium preset it solved 8/8 cases in a median about 0.04 seconds
and 437,032 counted exact operations.

The compact route recognizes the deleted set as `c + uD`, recovers its two affine
parameters from centered moments, and expands the fixed template. It takes 232
counted exact operations at medium. That gap is the Track B claim: the generic route
is easy with code but impossible to carry out in this no-tool context, while the
compact route fits the 300-operation cap if the structure is noticed. The regimes
deliberately avoided are `t=1` (one subtraction reveals the deletion), tiny fields
(enumeration), and any claim that the paper's efficient decoder is structurally hard.

## Worked demo

The demo (`seed=5`) is genuinely hand-scale:

```text
VT POWER-SYNDROME DELETION DECODING

Work in the prime field F_p with p = 47; every congruence below is modulo p.
The alphabet positions are the ordinary integers 1 through q = 46, inclusive.
A support is a set of distinct alphabet positions. It represents the 1-positions
of a binary constant-weight word; a deletion changes a 1 to 0.

The original support had exactly 6 positions. Exactly t = 4 positions were deleted.
SURVIVORS 34 2
SYNDROME 34 24 33 36

Recover exactly 4 distinct positions in 1,...,46, disjoint from the survivors,
in strictly increasing order, reproducing all four power sums modulo 47.
Give: <answer>x1, x2, x3, x4</answer>
```

The answer is `<answer>11, 19, 27, 35</answer>`. Calling `verify` returns
`(True, "ok")`; dropping 35 returns
`(False, "expected exactly 4 deleted positions")`.

## Difficulty presets

| preset | requested `n` | actual `q` at seed 0 | `t` | survivors | status |
|---|---:|---:|---:|---:|---|
| demo | 43 | 46 | 4 | 2 | hand-solvable illustration |
| easy | 5,000 | 5,002 | 48 | 2 | bare held, but structural hint solved 3/3 |
| medium | 50,000 | 50,022 | 48 | 2 | intended shipping rung; G9 rerun blocked by quota |
| hard | 200,000 | 200,002 | 48 | 2 | locally verified, not oracle-tested |

## Local gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset/seed instances verified |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged comma list and fenced JSON both round-trip |
| G4 | pass | 0/200,000 structured guesses; exact density `1.753793e-160` |
| G5 | pass | unique shipping answer; demo exact count 1; generic decoder 439,740 operations on the fixed G5 seed |
| G6 | pass | four attacks at 0/8; reference decoder 8/8 as Track B requires |
| G7 | pass | doubling ambient size preserves a 48-element verified answer |
| G8 | pass | 60 invariance and 60 witness-preservation checks; 20/20 unrelated keys distinct |
| G9(c) | pass | at medium: 289-character bound, 97 lexical tokens, 48 atoms, 232 operations |
| G9(b) | **blocked** | medium hinted run could not start after the API limit reached zero |

The four failing G6 attacks were alternating small/large magnitudes, nearest-to-a-
survivor greedy completion, 256 structure-aware random restarts, and the by-hand
unit-scale ansatz. Plants and survivors have essentially uniform individual field
marginals; only the planted points' joint affine relation carries signal.

## Oracle evidence and G9 arms

| run | preset | outcome | interpretation |
|---|---|---|---|
| bare | easy | 0 solved / 3 | prior bare run held |
| hinted | easy | 3 solved / 3 | easy fails G9(b), so one move to medium is allowed |
| bare | medium | 0 solved / 2 completed | incomplete: remaining calls returned quota errors |
| hinted | medium | pending | required before shipping |
| placebo | medium | pending | required diagnostic |

No hinted-minus-placebo number is reported because the two medium arms are not
complete. The easy result does show that the hint carries real structural
information; it is not a mere prompt-length effect. After quota is restored, run
all three arms in their existing separate scratch directories, copy the finished
transcripts under the required `g9_*_transcript.jsonl` names, inject the counts into
`G9_EVIDENCE`, and regenerate `selftest_report.json`.

## Use

```python
import random
import gen_2501_13534 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["medium"])
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.random_candidate(inst, random.Random(1)) != inst["answer"]  # overwhelmingly likely
```

Once G9 and the final bare run pass, emit from the repository root with
`scripts/emit.sh 2501.13534`.

## Caveats

This benchmark covers the paper's VT set-code building block, not the permutation
decoder or the complete multiplicity-free sequence decoder in Section 4. It becomes
easy with any finite-field factorization package, for small `t`, or when the affine
template is both disclosed and the modular arithmetic is executable. The G4 prior
is uniform over distinct, survivor-disjoint, sorted `t`-sets already satisfying the
first syndrome; its exact density says guessing from that declared language is
hopeless, not that every conceivable inference attack is hopeless. I did not test
Berlekamp factorization, higher-moment affine classifiers, or model access to a CAS;
the successful generic factorizer already establishes that such tool-enabled routes
are expected to work. The decisive unresolved caveat is medium G9(b), not hidden:
the current OpenRouter key reports a total limit of 500 and zero remaining allowance.
