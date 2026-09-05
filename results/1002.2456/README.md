# arXiv:1002.2456 — cyclic-code equivalence by multipliers

This is a **Track B** generator. Its native domain is **algebra**, its object
regime is **finite-field exact**, its computational core is **permutation**, and
its certificate is an **integer tuple containing a multiplier and its inverse**.
The solver is given cyclic codes through their native q-cyclotomic defining-set orbits, so
`domain_essentiality="native"` and `reduction_kind="none"`. The intended
intuition is an **invariant**: multiply the orbit representatives in the quotient
group instead of matching and expanding possible orbit images one at a time.

Status: all local gates pass and the script-owned OpenRouter hardening loop returned
`hardened` at the easy preset. Three bare attempts, three structural-hint attempts,
and three placebo attempts all produced parseable but invalid witnesses.

## The problem

The source is Kenza Guenda, [*The Permutation Groups and the Equivalence of
Cyclic and Quasi-Cyclic Codes*](https://arxiv.org/abs/1002.2456). Section II
defines permutation equivalence and its coordinate convention. Section III
defines the multiplier `M_a: i -> a*i (mod p)`, Brand's set `H(P)`, and the
q-cyclotomic structures used to restrict cyclic-code equivalences.

An instance gives two length-p cyclic codes over `F_q`. Each code is represented
exactly by one representative from each q-cyclotomic orbit in its defining zero
set. The solver must return `[a,a_inverse]` for any coordinate multiplier mapping
the first code to the second. Verification computes exact quotient-coset labels,
checks their finite-set equality, and checks the inverse. Generation first samples
`a`, then multiplies the first defining set by `a_inverse`; the answer is carried
through that transformation and is never recovered by search.

## Why Track B

This paper does not license a Track A distributional-hardness claim. Section III's
paragraph before Lemma 10 states that when `gcd(n,phi(n))=1`, equivalence of cyclic
objects reduces to a multiplier; this applies to the generated prime lengths.
Theorem 15 also explicitly identifies `H(P)` in small-Sylow regimes. Section II
notes the very easy case `ord_p(q)=p-1`, where only four elementary cyclic codes
exist. This generator avoids that lookup regime: `ord_p(q)=m` ranges from 4 to
256, still tiny relative to `p-1`, and the defining set is a proper nontrivial
union of full orbits.

The disclosed reference algorithm labels every `<q>`-coset by `x^m`, fixes one
orbit of CODE 2, and tries its `t` possible image orbits in CODE 1. It costs
`O(t*log(m) + t^2)`, solved 8/8 shipping instances, averaged 874.125
counted exact operations, and averaged 0.000297 seconds in the recorded run. Thus Track A
would be false. The compact route works in `F_p^*/<q>`: if `P1` and `P2` are products of the two
representative lists, then `P1/P2 = a^t` modulo `<q>`. Construction enforces
`gcd(t,(p-1)/m)=1`, so one exponentiation yields some valid member of `a<q>`.
The post-insight route used at most 144 exact operations over 512 shipping
seeds—short enough for the stated cap, but unlike the reference scan it first
requires seeing the quotient invariant.

## Worked demo

For `seed=0`, the complete rendered demo instance is:

```text
Cyclic-code equivalence by a coordinate multiplier

All arithmetic in exponents is modulo the prime code length p=41.
The code alphabet is the prime field F_q with q=173.  The residue of q modulo
p is 9 and has exact multiplicative order m=4.

For a nonzero residue r modulo p, define its q-cyclotomic orbit
    O(r) = {r*q^j mod p : j=0,1,...,3}.
Every orbit here has exactly 4 distinct elements.  A list R of representatives
defines the exponent set D(R)=the union of O(r) over r in R.  Relative to a
primitive p-th root alpha in F_(q^4), D(R) defines the length-p cyclic code
C(R) over F_q whose code polynomials vanish at alpha^d for every d in D(R).
The listed representatives have pairwise disjoint orbits; their printed order
has no meaning, and replacing a representative by another element of its orbit
does not change the code.

CODE 1 has these 3 q-orbit representatives:
[19, 33, 9]

CODE 2 has these 3 q-orbit representatives:
[36, 32, 13]

For 1 <= a < p, the coordinate multiplier M_a sends coordinate i to a*i mod p
(coordinates are 0-based, including coordinate 0).  With the convention above,
M_a maps CODE 1 to CODE 2 exactly when multiplying every defining exponent of
CODE 2 by a gives the defining exponent set of CODE 1.

Find any such a and also give b=a^(-1) mod p.  Output exactly two canonical
integers [a,b], each in the inclusive range 1,...,p-1.  The first entry is the
forward multiplier from CODE 1 to CODE 2 under the stated convention, and the
second is its inverse.
Repetitions are not allowed for this instance.

Give your final answer inside <answer></answer> tags as compact JSON [a,b].
Example of the required syntax: <answer>[2,21]</answer>
Output nothing else inside the tags.
```

The planted answer is `[10,37]`; `verify(inst,[10,37])` returns `(True,"ok")`.
The quotient-product route independently produces `[33,5]`, which also verifies:
there are exactly four valid multipliers, one coset of `<9>`. Swapping the planted
fields gives `verify(inst,[37,10]) == (False,"forward multiplier does not map CODE
2's defining set to CODE 1's")`. A person can solve this demo on paper: products
are taken modulo 41 and the relevant quotient has order 10.

## Difficulty presets

| preset | requested `n` | actual `p` (seed 0) | orbit order `m` | orbits `t` | valid / candidate multipliers |
|---|---:|---:|---:|---:|---:|
| demo | 41 | 41 | 4 | 3 | 4 / 38 |
| easy (**shipping**) | 20,000,000 | 20,000,033 | 16 | 31 | 16 / 20,000,030 |
| medium | 80,000,000 | 80,000,513 | 64 | 53 | 64 / 80,000,510 |
| hard | 300,000,000 | 300,003,841 | 256 | 89 | 256 / 300,003,838 |

The easy preset held on all three bare oracle attempts, so no harder preset was
needed. `escalate()` doubles both `n` and the orbit order, increasing the multiplier
space, integer bit cost, and quotient-labelling work while keeping the two-residue
answer and the displayed-orbit count fixed.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses and 16/16 JSON round trips |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range rejected with 5 reasons |
| G3 | pass | prose/fenced response round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structured guesses; exact density 16/20,000,030 |
| G5 | pass | reference scan 8/8; 6,993 total operations; demo brute-force count 4 |
| G6 | pass | seven attacks all 0/8; reference algorithm separately succeeds 8/8 |
| G7 | pass | shipping `n` doubles to 40,000,000 (p=40,000,033) with the same two-residue answer |
| G8 | pass | 80 invariant-key and 80 carried-witness checks; 20/20 distinct seeds |
| G9(c) | pass | 19 chars, about 5 tokens, 2 atoms; max 144 route operations over 512 seeds |

The failing Track B attacks are first/minimum/maximum representative ratios,
ordinary-sum ratio, raw-product ratio, sorted-position vote, and 256 uniform
random restarts. The successful quotient-label fixed-orbit scan is correctly
disclosed only as `reference_algorithm`.

## Oracle loop

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | openai/gpt-5.6-terra | 613834960 | failed | wrong forward multiplier |
| easy | google/gemini-3.8-flash | 12523117 | failed | entries were not modular inverses |
| easy | openai/gpt-5.6-terra | 1169496788 | failed | wrong forward multiplier |

All replies parsed; these are mathematical failures rather than output-contract bugs.
The harness returned `hardened` with zero escalations.

## G9 arms

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | hardened at shipping |
| structural hint | 0 / 3 | hardened at shipping |
| placebo hint | 0 / 3 | hardened at shipping |

`hinted - placebo = 0.0`. The hint names the quotient-product invariant without
giving an algorithmic chain, but in this three-attempt diagnostic it bought no
observable improvement. This weakens evidence that the measured failures isolate
invariant discovery rather than large-number arithmetic.

## Use

```python
import gen_1002_2456 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer(
    "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

To repeat the bare oracle run, use
`python3 ../../scripts/harden.py gen_1002_2456.py` here; run hint arms in separate
directories because the harness overwrites its transcript. From the repository root,
emission is `bash scripts/emit.sh 1002.2456`.

## Caveats

- This is deliberately not a complexity-theoretic hardness claim. Exact software
  solves the shipping preset in well under a second; the benchmark tests
  recognition and execution of a no-tool compression.
- The exact density uses the proof that a t-element subset of the quotient cannot
  have a nontrivial translation stabilizer when `gcd(t,(p-1)/m)=1`. The sampled
  0/200,000 figure measures a uniform nonzero, non-self-inverse multiplier with
  its inverse already filled in; it does not measure resistance to algebraic analysis.
- Generation conditions on the listed cheap signatures failing. This prevents a
  known planting leak but means the instance distribution is not an unconditional
  random distribution of orbit representatives.
- The quotient-product invariant itself solves every generated instance. That is
  the intended Track B route, not an omitted attack. No support-splitting package,
  general code-equivalence canonicalizer, or CAS was run; each would be expected
  to succeed and would not strengthen this no-tool claim.
- The quasi-cyclic conjectural results in Section IV are not used. This family uses
  only the exact cyclic-code definitions and multiplier action from Sections II–III.
- Prime testing is deterministic over the 64-bit range containing all presets and
  tested escalations. Extremely large user-supplied `n` outside that range is not
  supported by the stated primality guarantee.
- The current repository harness used its configured two-vendor pool (OpenAI and
  Google), with OpenAI drawn twice per three-attempt arm. This is weaker vendor
  diversity than the four-vendor design described by the task prompt and should be
  revisited if the harness pool expands again.
