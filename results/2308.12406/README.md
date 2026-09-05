# arXiv 2308.12406 — affine equivalence of Bose `B_3`-sets

**Status: locally verified, awaiting oracle evidence.** Every executable gate passes,
but the mandatory OpenRouter run produced only HTTP 403 “Key limit exceeded” service
errors. The family is therefore neither hardened nor rejected and must not be emitted
until the three oracle arms are rerun with a funded key.

| profile field | value |
|---|---|
| Track | B — an efficient exact algorithm is acknowledged |
| native domain | number theory |
| object regime | finite discrete |
| computational core | other (modular affine equivalence) |
| certificate | integer tuple `[d,s]` |
| intuition | invariant: centered power sums scale homogeneously |
| domain essentiality | native; no reduction |

## Problem and provenance

The source is Kevin O’Bryant, [*Constructing Thick `B_h`-sets*](https://arxiv.org/abs/2308.12406).
Definition 1 and Section 3 construct a generalized Bose set in
`Z/(q^h-1)Z`. Theorem 3 proves it is a `B_h`-set: an `h`-sum collision becomes
equality of two split degree-`h` polynomials over `F_q`. The definition immediately
after that theorem makes affine equivalence of these modular sets explicit, and
Theorem 4 studies parameter choices that produce equivalent sets.

Here `h=3`. The generator builds a Bose set using a primitive cubic, samples a
subset (which remains `B_3`), samples `[d,s]` first, and forms an independently
shuffled image `B=dA+s`. A solver receives both native modular `B_3`-sets and must
give any promised affine equivalence. `verify` independently enumerates all
three-term multisets to confirm both inputs are `B_3`, checks that `d` is a unit,
and compares the exact modular image with `B`.

## Why Track B

The paper supplies constructions and sufficient affine-equivalence conditions; it
does not prove hardness for this inverse-planted distribution. Section 2 describes
finite-field computation and “computerized labor,” Section 6 exhaustively examines
small affine images/subsets, and Section 7 asks for faster interpretations of some
Theorem 4 conditions. Those facts cannot support Track A.

The acknowledged reference algorithm chooses one invertible ordered pair in `A`,
tries every ordered pair in `B`, derives `[d,s]`, and compares images. It is
`O(k^3)`. At shipping `q=47,k=15`, the latest audit solved 8/8 instances in 48,034
counted exact operations and 0.043 seconds total (about 6,004 operations each).
The compact route computes centers and second/third centered moments modulo the odd
factor `L`; their scale ratio gives `d mod L`, the promised parity lifts `d mod M`,
and the centers give `s`. It took at most 256 counted exact operations. Thus the
mechanical method is trivial for software but not executable by hand in context,
while noticing the invariant gives the intended compression.

## Worked demo (`seed=0`)

```text
Recover an affine equivalence between two modular B_3-sets.

Definitions.
All arithmetic below is in the cyclic group Z/MZ, represented by the canonical
residues 0,1,...,M-1. A finite subset S is a B_3-set if equality modulo M of
a1+a2+a3 and b1+b2+b3 for elements of S implies that the two triples are equal
as multisets (repetition inside a triple is allowed).

An affine map is x -> d*x+s modulo M. It is invertible exactly when gcd(d,M)=1.
It maps a set A to a set B when B equals {(d*a+s) mod M : a in A}; printed
list order is irrelevant and no entries repeat.

Instance.
M = 124 = L*R, with L = 31 and R = 4.
Both displayed lists have exactly k = 3 residues and are
promised to be B_3-sets. At least one valid affine map exists whose canonical
multiplier additionally satisfies d congruent to 1 modulo R.
For arithmetic convenience, k^(-1) mod M = 83 and
R^(-1) mod L = 8.

A (unordered): 1 106 99
B (unordered): 21 108 43

Find any valid promised map. Give d and s as canonical residues, so
0 <= d,s < M, gcd(d,M)=1, d mod R = 1 mod R, and d*A+s equals B modulo M.

Give your final answer inside <answer></answer> tags as the JSON list [d,s].
Example syntax: <answer>[1,0]</answer>
Output nothing else inside the tags.
```

The planted answer is `[101,66]`; `verify(inst,[101,66])` returns `(True,"ok")`.
Dropping the shift gives `verify(inst,[101]) == (False,"wrong length: expected
exactly two entries [d,s]")`. The three-point demo is genuinely hand-solvable by
trying the six ordered correspondences.

## Difficulty presets

| preset | q | M | k | promised candidate space | status |
|---|---:|---:|---:|---:|---|
| demo | 5 | 124 | 3 | 3,720 | hand example |
| easy | 11 | 1,330 | 9 | 574,560 | oracle unavailable |
| medium | 23 | 12,166 | 17 | 56,936,880 | not reached |
| hard | 47 | 103,822 | 15 | 4,933,621,440 | intended shipping preset; oracle unavailable |

`hard` is the candidate `SHIPPING_DIFFICULTY`, but there is no valid shipping
verdict yet.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified and JSON-round-tripped |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 uniform structure-aware guesses; space 4,933,621,440 |
| G5 | pass | exactly 1 valid map; fraction `2.0269e-10`; reference cost 6,026 operations on the measured seed |
| G6 | pass | four attacks each 0/8; reference algorithm 8/8 as expected |
| G7 | pass | `q=47` to `q=107`; candidate space grew to 577,906,213,248; answer stayed two atoms |
| G8 | pass | 80/80 invariant-key and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 13 characters, about 4 tokens, 2 atoms; compact route at most 256 operations |

The four failed attacks were minimum-value alignment, printed-order greedy
alignment, two random pair restarts, and the obvious translation (`d=1`) ansatz.

## Oracle loop and G9 arms

| arm | requested preset | usable solved/attempts | service errors | result |
|---|---|---:|---:|---|
| bare | easy (ladder start) | unavailable | 4 | OpenRouter total-limit 403 |
| structural hint | hard | unavailable | 4 | OpenRouter total-limit 403 |
| placebo hint | hard | unavailable | 4 | OpenRouter total-limit 403 |

No model response was obtained, so `hinted - placebo` is undefined and no
conclusion about hint efficacy or model hardness is justified. The three transcript
files are script-owned error evidence, not successful hardening evidence. The
structural hint only names the homogeneous centered-moment invariant; it does not
state the recovery formula.

## Use

```python
import gen_2308_12406 as g

inst = g.make_instance(seed=0, **g.DIFFICULTY["demo"])
answer = g.parse_answer("work... <answer>[101,66]</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

After a funded four-vendor run returns `hardened`, emission from the repository root
is:

```bash
bash scripts/emit.sh 2308.12406 20 hard
```

Do not emit the current result: `.meta.json` has no `harden_verdict`, and the bare
transcript contains service errors only.

## Caveats

This is deliberately not a claim of computational hardness: the exact reference
algorithm runs in milliseconds. The 0/200,000 guess result concerns a uniform prior
over the stated bounded language; it says nothing about a solver using moments,
correspondence guesses, or learned construction priors. The compact route still
requires many five-digit modular multiplications and lies close enough to the
300-operation cap that some failures may reflect arithmetic reliability as well as
failure to notice the invariant. No SAT/SMT or lattice attack is relevant to this
native affine-equivalence task, and no external CAS attack was run beyond the exact
pair algorithm. Finally, `canonical_key` uses the complete multiset of unit-denominator
affine ratios; it is invariant under every tested affine relabelling but is not proved
to be a complete affine-isomorphism canonization.
