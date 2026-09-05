# arXiv:2207.13456 — Waring witness generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | algebra / finite field |
| Computational core | polynomial identity |
| Certificate | exact symbolic set of Veronese support points |
| Objects | binary symmetric tensor, normal rational curve, projective Veronese points |
| Intuition | invariant: recognize a translated multiplicative cycle |
| Domain essentiality | native; no reduction |

## What the problem is

The source is Lavrauw and Zullo, [*Waring identifiable subspaces over finite fields*](https://arxiv.org/abs/2207.13456). An instance gives all (2k) moment coordinates of a degree-(2k-1) binary symmetric tensor over a prime field. The solver must return the (k) affine points (a) whose Veronese vectors ((1,a,\ldots,a^{2k-1})) span it. This is exactly the paper's Waring witness, not a graph or integer surrogate.

Checking is exact and cheap. For a proposed support (S), `verify` expands (Q(x)=\prod_{a\in S}(x-a)) modulo (p), substitutes its coefficients into the (k) moment-recurrence windows, and compares each result with zero. It never reads `inst["answer"]` or the generator's private construction data.

## Why the witness is trustworthy—and why this is Track B

Section 2.2 defines a Waring witness as the rational points on the variety spanning the subspace, and Section 2.3 identifies the binary Veronese variety with pure symmetric tensors. Proposition 7.1 says that a degree-(2t+1) binary point of rank (t+1) is identifiable when (q\ge 2t+1). Here (k=t+1), (d=2k-1), and (p\ge d). The generator first chooses (k) distinct points and nonzero coefficients. Any competing representation with fewer than (k) points would give a linear dependence among at most (2k) points of the normal rational curve, contradicting its arc property. Thus the rank is exactly (k), and Proposition 7.1 makes the planted support unique.

This is not a Track A hardness claim. The paper's Introduction explicitly distinguishes geometric identifiability from the complexity problem of finding a decomposition. A standard Prony–Hankel solve followed by Cantor–Zassenhaus factorization recovers the witness in expected polynomial time. The bundled exact implementation solves all 8 shipping tests; it averaged **34,205 field operations and 0.0039 s** per instance. That is easy for software but not an in-context hand calculation. The planted distribution has a shorter route: its support is (c+\langle\zeta\rangle), and low-degree coefficient power sums give (c=m_1/m_0). Finding the small order-20 generator and enumerating the cycle costs at most **160 exact operations** at shipping.

The explicit frame constructions in Section 3 and fixed-dimensional constructions/classifications in Sections 4–5 would be lookups, so this module does not benchmark them. It uses the scalable binary family in Section 7. Generation is inverse: sample the support and coefficients, expand the moments, and retain the already-known support. No emitted instance is solved during generation.

## Worked demo

With `seed=2`, the full `demo` statement is:

```text
WARING WITNESS FOR A BINARY FORM OVER A FINITE FIELD

Work in the prime field F_7; every arithmetic operation is modulo 7.
For a residue a, define its degree-5 affine Veronese point by
    v(a) = (1, a, a^2, ..., a^5) in F_7^6.
A set S of residues is a Waring witness for a target vector m when m
lies in the F_p-linear span of {v(a): a in S}.  Equivalently, there
exist field coefficients w_a such that m_j = sum_{a in S} w_a*a^j
for every j from 0 through 5.  The coefficients need not be output.

The target m has the following 6 coordinates:
m[0..5]: 3 4 2 3 6 1

Find a Waring witness containing exactly 3 distinct affine residues.
Each residue must be an integer from 0 through 6, inclusive.
The order of the residues does not matter, repetitions are forbidden,
and the point at projective infinity is not part of the requested witness.
The instance is guaranteed to have Veronese rank exactly this size and
to have a unique witness of this size.

Give your final answer inside <answer></answer> tags as one JSON object
with a key named "support" whose value is a list of exactly 3 integers.
Example shape: <answer>{"support":[2,9,14]}</answer>
The example only shows the syntax; use the required number of residues.
Output nothing else inside the tags.
```

The answer is `<answer>{"support":[0,1,3]}</answer>`. `verify` returns `(True, "ok")`. Replacing 3 by 2 gives `{"support":[0,1,2]}` and returns `(False, "support polynomial fails the moment recurrence at shift 0")`. This smallest setting is genuinely hand-solvable: only (\binom73=35) supports exist, and direct modular substitution is short.

## Difficulty presets

| Preset | (k) | (p) | Degree | Candidate-space bits | Compact ops | Result |
|---|---:|---:|---:|---:|---:|---|
| demo | 3 | 7 | 5 | 6 | 13 | hand example; hardener skips it |
| easy | 20 | 61 | 39 | 53 | 160 | **ships; bare oracle 0/3** |
| medium | 60 | 181 | 119 | 162 | 281 | retained as a harder rung |
| hard | 80 | 25601 | 159 | 777 | 253 | retained as a harder rung |

An earlier easy candidate used (p=41), where 2 itself generated the planted order-20 subgroup. The construction-aware ratio-2 attack therefore solved it; that distribution was discarded before the final oracle run. The shipping (p=61) distribution defeats that attack 0/8.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted, theorem-condition, and compact-identity checks |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons; valid reordering accepted |
| G3 | pass | prose + fenced JSON round-trips; answer is JSON-native |
| G4 | pass | 0/200,000 uniform structure-aware guesses; exact probability (1/6,236,646,703,759,395) |
| G5 | pass | demo exact count 1/35; shipping density exact by uniqueness; reference 273,642 ops over 8 runs |
| G6 | pass | five attacks at 0/8; Prony/Cantor–Zassenhaus reference at 8/8 |
| G7 | pass | (k=40) doubled instance verifies; search-space bits grow 53 to 153 |
| G8 | pass | 80 affine/scalar/composed invariance checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 69 characters, about 18 tokens, 20 atoms, 160 intended operations |

## Bare oracle loop

| Preset | Model | Seed | Solved | Exact grading result |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 1545951956 | no | recurrence failed at shift 0 |
| easy | Gemini 3.8 Flash | 950113327 | no | recurrence failed at shift 0 |
| easy | Gemini 3.8 Flash | 2120572118 | no | recurrence failed at shift 0 |

All three replies contained parseable, correctly shaped supports; these are not parser or API false negatives. The script-owned verdict is `hardened`, with `easy` as the shipping preset.

## G9 diagnostic arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | the shipped prompt held |
| structural | 2/3 | naming the multiplicative-cycle invariant often unlocks the compact route |
| placebo | 0/3 | an equally styled extra sentence did not help |

Hinted minus placebo is (2/3\). The hinted verdict is `too_easy`, which is diagnostic, not a gate: it supports the claim that difficulty lies in finding the intended invariant rather than doing long arithmetic after it is known.

## Use

```python
import importlib.util

path = "results/2207.13456/gen_2207_13456.py"
spec = importlib.util.spec_from_file_location("waring_gen", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))
answer = g.parse_answer('<answer>{"support":[...]}</answer>')  # replace ...
print(g.verify(inst, answer))
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2207.13456 20 easy
```

The module uses only the Python standard library.

## Caveats

- The family is deliberately structured and is efficiently solvable. It should never be cited as average-case or complexity-theoretic hardness; optimized Prony, Berlekamp–Massey, finite-field factorization, or a direct subgroup recognizer can solve it.
- The 0/200,000 figure samples uniformly from all (k)-subsets, already enforcing size/range/distinctness. It measures blind structure-aware guessing, not a solver prior that notices algebraic recurrences.
- The adversary panel did not run Gröbner-basis software, FFT-accelerated Hankel methods, or every possible subgroup detector. The successful reference algorithm is stronger evidence of tractability than those omissions are evidence of hardness.
- `canonical_key` is invariant under affine coordinate changes, support reordering, and global tensor scaling. It is not a full canonical form under all of PGL(2,p), especially transformations sending a support point to infinity; it uses the unique planted coefficient multiset as the strongest cheap invariant.
- Only prime fields and affine support points are generated. Proposition 7.1 also covers prime-power fields and projective points at infinity, but extension-field arithmetic is outside this module.
- The G9 hint is intentionally informative: 2/3 hinted solves versus 0/3 placebo shows the benchmark is sensitive to the claimed invariant. At larger presets, answer length and hand arithmetic become increasingly important despite remaining under the formal caps.
