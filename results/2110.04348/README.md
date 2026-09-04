# Verified generator for arXiv:2110.04348

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `number_theory` |
| Object regime | `integer_lattice` |
| Computational core | `subset_sum` |
| Certificate form | `integer_tuple` |
| Intended intuition | `invariant`: least-first 2-adic peeling |
| Domain essentiality | `native` |
| Reduction | none |

This directory turns Brüdern and Wooley’s [*On smooth Weyl sums over biquadrates and Waring’s problem*](https://arxiv.org/abs/2110.04348) into an exact witness task. The solver receives a target `N`, a smoothness bound `R`, and twelve disjoint bands for the 2-adic valuations of the bases. It must return twelve distinct, increasing, positive `R`-smooth integers—one from each band—whose fourth powers sum to `N`. Verification uses only exact integer arithmetic, valuation checks, smooth-number membership, and equality of the fourth-power sum. It never reads the planted answer.

## Why this is faithful, and why Track B

Section 1 defines `A(P,R)` as the positive integers at most `P` whose prime factors are at most `R`. Corollary 1.3 states the native twelve-biquadrate representation result, and the paragraph immediately after it records the local fact that every integer fourth power is `0` or `1` modulo 16. The generator stays with those native integer objects and strengthens the task with an explicit separated-valuation promise; it does not compile the problem into a graph, finite field, or SAT instance.

Theorem 1.2 and Corollary 1.3 are analytic existence results, not representation-search algorithms—the paper explicitly omits the corollary’s proof. This module therefore inverse-generates the twelve bases before forming `N`; no instance is solved during generation. It makes no Track A or average-case hardness claim.

The honest Track B reference algorithm is the exact band-by-band modular sieve. At the shipping preset it solves 8/8 instances in `O(12*a_width*M_R(odd_bits))`, averaging 90,465 candidate probes, 624,726 counted exact operations, and 0.026438 seconds in the final selftest. That is easy for software and infeasible to perform manually in context.

The compact route is the 2-adic invariant. In the residual sum, the least valuation band contributes the only term visible modulo the next band. Divide out `2^(4a)`, remove the known odd multiplier modulo a sufficiently large power of two, and the residue is the exact fourth power of the bounded odd part. Its integer fourth root recovers one base; subtract and repeat. The operation budget is at most 120 high-level exact operations for all twelve bands.

## Worked demo

The `demo` preset with seed 3 renders in full as follows:

```text
Twelve smooth biquadrates in separated 2-adic bands

A positive integer is R-smooth when every prime divisor is at most R;
the integer 1 is R-smooth.  The 2-adic valuation v2(x) is the unique
nonnegative integer a for which x=2^a*y with y odd.

Here R = 3, P = 11118121133111046, and the odd-part cap is
2^1 = 2 (the upper endpoint is excluded).
The target integer N is:
17429434276949627035017610164402118628837538426093269033615467792

Find exactly 12 distinct R-smooth positive integers
x_0 < x_1 < ... < x_11, each at most P, such that

    x_0^4 + x_1^4 + ... + x_11^4 = N.

There must be exactly one answer integer for each band line below.  A line
'lo hi s' requires v2(x)=a in the inclusive range lo..hi and requires
x=2^a*s*y, where y is odd, R-smooth, and satisfies
1 <= y < 2^1.  The band lines are deliberately unordered;
their printed order carries no meaning.  The increasing order of the answer
is mandatory, and repeats are forbidden.

V2 BANDS AND ODD MULTIPLIERS (lo hi s):
21 21 387420489
33 33 19683
13 13 282429536481
17 17 10460353203
1 1 5559060566555523
9 9 7625597484987
5 5 205891132094649
29 29 531441
45 45 1
41 41 27
25 25 14348907
37 37 729

Return one JSON array of exactly 12 decimal integers in
strictly increasing order.  Do not return fourth powers, exponents,
factorizations, labels, ellipses, or more than one array.
Give your final answer inside <answer></answer> tags, as that JSON array.
Example syntax only: <answer>[1,2,3,4,5,6,7,8,9,10,11,12]</answer>
Output nothing else inside the tags.
```

The answer is:

```json
[35184372088832, 59373627899904, 100192997081088, 169075682574336, 285315214344192, 481469424205824, 812479653347328, 1371059415023616, 2313662762852352, 3904305912313344, 6588516227028768, 11118121133111046]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Increasing the last entry by one returns `(False, "out of range: every integer must lie in 1..11118121133111046")`. The demo is hand-solvable: every band has width one, `R=3`, and the odd-part cap forces `y=1`, so each base follows directly from its band and multiplier. The printed arithmetic is long, but no search is needed.

## Difficulty presets

| Preset | `R` (`n`) | `odd_bits` | `a_width` | Status |
|---|---:|---:|---:|---|
| demo | 3 | 1 | 1 | hand illustration; not shipped |
| easy | 29 | 16 | 12 | **shipping preset; bare and hinted hardened** |
| medium | 59 | 16 | 16 | available, not needed by the oracle loop |
| hard | 97 | 18 | 16 | available, not needed by the oracle loop |

Escalation first raises `R`, enlarging the smooth decoy pool at the same twelve-element answer length. At higher levels it also raises the odd-part and valuation ranges. It returns `cap_bound` only when a conservative projected JSON answer nears 1,900 characters.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified; JSON round-trip checked |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range rejected with 5 distinct reasons |
| G3 | pass | realistic tagged response round-tripped and verified |
| G4 | pass | 0/200,000 structured guesses; exact language size `111162132341761046299603376405428945314722334375936` (167 bits) |
| G5 | pass | exact promised-language solution count 1; density `8.995869177154342e-51`; reference cost 90,465 probes / 624,726 operations / 0.026438 s |
| G6 | pass | five attacks at 0/8 each; reference sieve and compact peel both 8/8 |
| G7 | pass | doubling `R` from 29 to 58 raises candidate-space bits 167→181; witness remains 12 elements |
| G8 | pass | 60/60 relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9 | pass | hinted oracle verdict `hardened`; 1,332 worst-case characters, 333 estimated tokens, 12 atoms, 120 intended operations |

The five failing G6 attacks are band midpoints, largest-first greedy, nearest-fourth-root greedy, independent band minima, and 256 structure-aware random restarts. Plants and candidates use the same uniform choice of valuation and bounded odd smooth part within each band.

## Bare oracle loop

The script-owned main transcript used the easy preset. A Grok call timed out at the hard deadline and was excluded rather than scored.

| Model | Seed | Solved? | Recorded outcome |
|---|---:|---:|---|
| Claude Sonnet 5 | 305017465 | no | exhausted the response budget without an answer |
| Gemini 3.1 Pro | 1461619776 | no | parsed list failed ordering; sorting it still failed a band multiplier |
| GPT-5.6 Terra | 772709468 | no | incorrectly claimed local insolubility and returned no witness |

Verdict: `hardened`, with zero escalations; `SHIPPING_DIFFICULTY = "easy"`.

## G9 three-arm diagnostic

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

The hinted-minus-placebo solved-rate difference is `0.0`. Thus the one-sentence hint did not measurably improve success in this small three-model diagnostic. This does not show that the 2-adic invariant is irrelevant—the two parsed hinted answers still violated the first band’s huge required multiplier—but it does show that naming the direction was insufficient to make exact execution succeed. The shipping answer measured 1,295 characters (324 estimated tokens); the worst-case bound is 1,332 characters (333 tokens), with 12 atomic elements and a 120-operation compact-route budget.

## Use

From this directory:

```python
from gen_2110_04348 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["easy"])
prompt = render(inst)
candidate = parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit deterministic sample records with:

```bash
bash scripts/emit.sh 2110.04348 20
```

## Caveats

- This is a promised, separated-valuation subfamily constructed for Track B. It is not evidence that arbitrary integers covered by Corollary 1.3 are easy or hard to represent, and the paper proves no distributional computational-hardness theorem.
- The exact density is for `random_candidate`’s stated prior: one uniformly sampled legal base from every band. It is not the success probability of a solver using the 2-adic invariant.
- Uniqueness is claimed only inside the bounded certificate language with one base per band; the target could conceivably have unrelated unrestricted Waring representations.
- The reference algorithm is openly fast in software. This benchmark measures no-tool compression, not complexity-theoretic hardness.
- The 120-operation figure counts modular inverses, integer square roots, and modular powers as high-level exact operations; their bit complexity and the effort of transcribing a 1,300-character answer are real additional costs.
- No general-purpose SMT, ILP, lattice-reduction, or CAS attack was run. The more relevant complete band-by-band modular sieve was run and succeeds, as Track B expects.
- The module stays standard-library-only because its certificate and verifier use integers exclusively; no `gvlib` helper is needed.
