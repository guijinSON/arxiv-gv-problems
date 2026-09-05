# Polynomial-lattice fixed-weight decoding generator

| profile | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | algebra |
| Object regime | finite discrete (the ring `Z/(q-1)`) |
| Computational core | subset sum / fixed-weight syndrome decoding |
| Certificate | integer tuple: the binary error support |
| Intended intuition | duality: remove the systematic message with a parity check |
| Domain essentiality | licensed reduction, paper-central |

This module turns Li, Ling, Xing, and Yeo’s [*On the Closest Vector Problem for
Lattices Constructed from Polynomials and Their Cryptographic Applications*](https://arxiv.org/abs/1710.02265)
into an unlimited exact witness problem.  The solver receives columns of the
parity-check dual of the paper’s public polynomial-lattice map and a modular
syndrome.  It must give the support of a binary error of prescribed weight.
The checker adds those columns modulo `q-1` and compares with the syndrome.

The reduction is the paper’s own decoding step: Section 4 evaluates
`c = m[I|-G] + e`, and Section 5 eliminates the systematic message while
searching for `e`.  For `P=[G^T|I]`, this is exactly `Pc^T=Pe^T`.  Proposition 1
is used to construct `G` from distinct finite-field roots and evaluation
points; the coordinate permutation is explicitly permitted by the final
remark of Section 4.  The answer is sampled before the syndrome, so generation
never decodes its own instance.

## Why Track A

No efficient general recovery method is known for this generated distribution.
Section 5 gives systematic search cost
`O(C(n-d,l)(n-d)d)`, with `l=(n-d)(d-1)/n`, and Proposition 2 gives the BKZ
cost model.  At the shipping preset, `n=400`, `d=15`, and the main systematic
layer is `C(385,13)` (about 79.7 bits); the complete answer language
`C(400,14)` has about 84.3 bits.  The measured implementation exhausted 50,000
nodes and 10,500,000 modular operations on each of eight seeds, with median
wall time 0.466258 s, without solving any.

This is not a claim that the encryption proposal remains secure.  The later
[Athukorala–Galbraith cryptanalysis](https://doi.org/10.1109/TIT.2025.3573912)
breaks the claimed CCA protection and identifies May–Ozerov information-set
decoding as the strongest decoding attack.  That attack is still exponential,
so it does not turn certificate recovery into Track B, but it materially limits
the cryptographic interpretation of this benchmark.

The paper’s easy regimes were avoided.  Section 5 shows that `d>n/2` can be
replaced by a smaller negative error; all presets have `d<n/2`.  It also reports
that Babai becomes more effective as `d` grows and less effective as `n` grows.
The non-demo ladder fixes `d=15` and its 14-index answer while growing the code
and field.  This is below Section 6’s practical table (`d=29..33`), a deliberate
G9-size choice and an explicit caveat rather than a security parameter claim.

## Worked demo

For `make_instance(n=10, d=3, field_slack=0, seed=11)`, the complete rendered
data are:

```text
modulus: 16
syndrome: 4 1 15
columns (index: 3 coordinates):
0: 15 9 2
1: 8 8 5
2: 11 4 13
3: 1 7 4
4: 7 15 9
5: 0 1 0
6: 9 1 5
7: 1 0 0
8: 12 9 10
9: 0 0 1
```

The required support size is 2.  The answer is `<answer>[1, 8]</answer>`:
`(8,8,5)+(12,9,10) = (4,1,15) mod 16`, so `verify` returns `(True, "ok")`.
Deleting one index gives `[1]`, and `verify` returns
`(False, "support must contain exactly 2 indices")`.  A person can solve this
demo by checking its 45 pairs on paper; exhaustive enumeration confirms that
exactly one pair works.

## Difficulty presets

| preset | n | d | q | weight | legal supports | rendered chars | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 10 | 3 | 17 | 2 | 45 | 1,206 | hand-scale only |
| easy | 400 | 15 | 419 | 14 | 24,462,390,289,488,419,628,473,400 | 25,092 | **ships; hardened** |
| medium | 520 | 15 | 719 | 14 | 1,016,179,801,403,563,036,214,357,760 | 33,286 | reserve rung |
| hard | 700 | 15 | 1,151 | 14 | 68,255,781,490,722,290,709,554,824,200 | 46,511 | reserve rung |

`q` and rendered sizes above use seed 0; `q` depends only on preset parameters.
No preset was rejected.  The oracle pool already failed at `easy`, so the
script correctly stopped without spending the higher rungs.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified; all JSON-native |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | prose + fenced tagged JSON round-tripped exactly |
| G4 | pass | 0/200,000 structure-aware random supports; space `C(400,14)` |
| G5 | pass | shipping density 0/200,000; demo exactly 1/45; baseline 0/8 after 50,000 nodes each |
| G6 | pass | outlier, greedy, 256 restarts, and systematic decoder all 0/8 |
| G7 | pass | doubled `n=800` instance built and verified; answer stayed 14 indices |
| G8 | pass | 20 permutation/composition invariance checks, 20 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass | answer 55 chars, 14 atoms, 14 tokens on measured seed (15-token worst-case bound); route confirmation 225 operations |

The `P(guess)` experiment samples uniformly from sorted, distinct,
fixed-weight supports—the full space a reader gets after enforcing every
stated syntactic constraint.  It does not sample malformed lists.

## Oracle hardening loop

All bare replies parsed as 14 indices and failed because their selected columns
did not sum to the syndrome.

| preset | model | seed | solved | verifier outcome |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 471771501 | no | syndrome mismatch |
| easy | Google Gemini 3.1 Pro Preview | 733734724 | no | syndrome mismatch |
| easy | xAI Grok 4.6 | 2142750814 | no | syndrome mismatch |

The script-owned verdict is `hardened`, with zero escalations and shipping
parameters `n=400,d=15,field_slack=0`.

## G9 arms

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | shipping prompt held |
| structural hint | 0 / 3 | polarity-flipped gate held |
| placebo hint | 0 / 3 | control also held |

Hinted minus placebo is `0.0`.  Naming the parity-check dual bought the tested
oracles nothing, so this run does not show a measurable response to the claimed
duality intuition; it shows that even after the invariant is named, locating
the support remains the hard part.  The answer is 55 characters / 14 atomic
elements on the gate seed, and exact confirmation takes 225 arithmetic or
comparison operations, below all G9 caps.

## Use

From this directory:

```python
from gen_1710_02265 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
candidate = parse_answer("<answer>[0,1,2,3,4,5,6,7,8,9,10,11,12,13]</answer>")
ok, reason = verify(inst, candidate)
print(ok, reason)
```

From the repository root, emit deterministic shipping instances with:

```bash
bash scripts/emit.sh 1710.02265 20
```

## Caveats

- Track A is an average-distribution claim supported by the paper’s analysis,
  the later identification of exponential ISD, and bounded measurements—not a
  reduction proving this particular planted distribution hard.
- The 0/200,000 density observation proves neither uniqueness nor a density of
  zero.  It only gives the observed hit rate under uniform legal supports.  The
  demo, not shipping, is exhaustively counted.
- The adversary panel does not implement May–Ozerov ISD, production BKZ/fplll,
  or a full meet-in-the-middle decoder.  Those need substantial non-standard
  machinery.  The implemented domain attack is the paper’s exact systematic
  error search, capped at 50,000 nodes and reported honestly as incomplete.
- Key generation rejects discrete-log matrices unless the simple exact
  Gauss–Jordan order exposes unit pivots.  Accepted keys are checked to have a
  two-sided inverse, but this rejection biases the paper’s nominal key
  distribution.
- The canonical key handles every coordinate relabelling and composition, but
  not arbitrary invertible row-basis changes of the parity-check equations.
- The benchmark asks for one static decoding witness.  It does not model
  chosen-ciphertext access, semantic security, or security of the paper’s
  encryption wrapper.
