# Inclusion-matrix polynomial certificate (arXiv:1511.03623)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | polynomial over `GF(p)` |
| Intended intuition | symmetry — inclusion columns fall into intersection-size orbits |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Ameera Chowdhury, [*Inclusion Matrices and the MDS Conjecture*](https://arxiv.org/abs/1511.03623). Definition 1.3 introduces the paper's matrix `M_G^{up n}`; at `n=0` it is exactly the inclusion matrix whose rows are `(p-1)`-subsets and columns are `(p-2)`-subsets. The proof of Theorem 1.13 constructs a column-space vector by assigning a coefficient to a column according to the size of its intersection with a distinguished `p`-set.

An instance gives `GF(p)`, a ground set `X` of size `2p-2`, a distinguished `p`-subset `B`, an invertible affine label for each intersection-size orbit, and a target scalar. The solver returns a degree-at-most-`p-2` polynomial `Q`. Giving column `A` the coefficient `Q(z(A))` must make the exact inclusion-matrix product equal the target on rows `C subset B` and zero on every other row.

Generation is theorem-backed and transformed, not solve-then-plant. At the boundary `k=p`, the proof's coefficient

`(-1)^ell * ell! * (p-2-ell)!`

is `1/(ell+1)` in `GF(p)`. Under the emitted label `z=a*ell+(a-1)`, the carried witness is

`Q(z) = target*a*(z+1)^(p-2)`.

The verifier does not use `inst["answer"]`. It validates the dense polynomial syntax, evaluates it exactly in `GF(p)`, and recomputes the inclusion-row sum for every feasible orbit `|C intersect B|=1,...,p-1`. This is executable substitution and comparison, not an appeal to the theorem.

## Why this is Track B

This is not a claim of complexity-theoretic hardness. The paper itself supplies the orbit construction in the proof of Theorem 1.13, and Theorem 1.6 gives the relevant inclusion-matrix rank formula. Those results rule out an honest Track A claim in the regime used here.

The disclosed mechanical algorithm writes the coefficient equations in the monomial basis and performs exact dense Gauss–Jordan elimination. Its complexity is `O(p^3)`. At shipping `p=101`, it solved 8/8 audits in an average 0.049464 seconds using 1,071,216 counted field operations and 100 inversions. A tool-equipped solver is therefore expected to succeed.

The compressed route is the symmetry. A row depends only on `r=|C intersect B|`, so its sum is

`(p-1-r) q_r + r q_(r-1)`, where `q_l=Q(a*l+a-1)`.

The recurrence and the last-row normalization give `q_l=target/(l+1)`. Fermat then packages all evaluations as the shifted power above, whose dense coefficients are `target*a*(-1)^j*(j+1)`. At shipping this takes at most 151 exact field operations, including coefficient multiplications and signs. That is the measured Track B gap: roughly 1.07 million generic operations versus 151 after recognizing the orbit invariant.

The easy regimes had to be stated honestly rather than avoided: generic finite-field elimination solves the task quickly; direct use of the paper's formula is shorter still. Difficulty comes only from finding and executing the compressed route without a sandbox or CAS.

## Worked demo

`make_instance(n=5, seed=0)` renders in full as:

```text
Find a polynomial certificate for a finite-field inclusion matrix.

All arithmetic is in GF(5); write every field element as its least
nonnegative decimal residue in 0,...,4.

The ground set is X={0,1,...,7}.  Its distinguished
p-element subset B is: [0, 2, 3, 6, 7]

For every (3)-element subset A of X, define

    ell(A) = |A intersect B|,
    z(A) = 4*ell(A) + 3 (mod 5).

The inclusion matrix has one row for every (4)-element subset C
and one column for every (3)-element subset A.  Its (C,A) entry
is 1 when A is a subset of C and 0 otherwise.

Find a polynomial Q(x) over GF(5) of degree at most 3 such that,
for every (4)-element subset C of X, the exact identity

    sum over A subset C with |A|=p-2 of Q(z(A))

equals 2 when C is a subset of B, and equals 0 otherwise.
The sum is in GF(p).  The polynomial is unique under the degree bound.

Return Q as dense JSON polynomial data.  Include exactly one term
[coefficient,[exponent]] for every exponent 0,...,3, including zero
coefficients.  Term order is irrelevant; exponents may not repeat.
For example, 4+3x^2 is [[4,[0]],[0,[1]],[3,[2]]].

Give your final answer inside <answer></answer> tags, as that JSON list.
Example: <answer>[[4,[0]],[0,[1]],[3,[2]]]</answer>
Output nothing else inside the tags.
```

The answer is `[[3,[0]],[4,[1]],[4,[2]],[3,[3]]]`. The demo has only `5^4=625` candidates, so a person can solve it on paper from the four orbit equations or verify it by evaluating four field values.

```python
>>> verify(inst, [[3,[0]],[4,[1]],[4,[2]],[3,[3]]])
(True, 'ok')
>>> verify(inst, [[4,[0]],[4,[1]],[4,[2]],[3,[3]]])
(False, 'inclusion-row sum mismatch at intersection size 1: got 4, expected 0')
```

## Difficulty presets

| Preset | `p` | Polynomial terms | Answer atoms | Answer-space bits | Intended ops | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 4 | 8 | 10 | 7 | hand-solvable illustration |
| easy | 101 | 100 | 200 | 666 | 151 | **shipping; bare oracle held** |
| medium | 109 | 108 | 216 | 731 | 163 | available; not reached |
| hard | 127 | 126 | 252 | 881 | 190 | available; not reached |

No named preset was rejected. Past `p=127`, the next prime would require more than 256 answer atoms, so `escalate()` correctly reports `cap_bound` rather than claiming the mathematics has run out of harder settings.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses across four presets; 12/12 JSON round-trips |
| G2 | pass | drop, coefficient swap, duplicate exponent, empty, and range corruptions all rejected with five distinct reasons |
| G3 | pass | tagged dense polynomial recovered from surrounding prose and a Markdown fence |
| G4 | pass | 0/200,000 uniform structure-aware guesses; exact density `101^-100`; 666-bit language |
| G5 | pass | shipping density and reference cost recorded; demo brute force found exactly one answer |
| G6 | pass | five attacks each 0/8; dense reference 8/8; compact construction 8/8 |
| G7 | pass | doubled input built at `p=211`, verified, and grew the language from 666 to 1,622 bits |
| G8 | pass | 140/140 keys invariant, 140/140 original witnesses carried, 20/20 unrelated keys distinct |
| G9 | pass | 981 actual / 1,091 worst-case answer characters, 200 atoms, 151 intended operations |

The five failing G6 attacks were a single outlier monomial, treating orbit values as monomial coefficients, forgetting the public affine scale in the Fermat ansatz, a by-hand linear ansatz, and 256 sparse random restarts. The construction-aware unscaled Fermat attack was the strongest failing baseline; it took 0.000551 seconds per audited seed. The standard algorithm is deliberately not in `attacks`, because Track B expects it to solve.

## Bare oracle loop

| Model | Preset | Seed | Solved | Exact outcome |
|---|---|---:|---:|---|
| Google Gemini 3.8 Flash | easy | 881679521 | no | parsed; row `r=1` gave 67 instead of 0 |
| OpenAI GPT-5.6 Terra | easy | 268761402 | no | malformed JSON: the outer list was not closed |
| OpenAI GPT-5.6 Terra | easy | 809912281 | no | parsed; row `r=1` gave 2 instead of 0 |

The script-owned `.meta.json` records `verdict: hardened`, zero escalations, and `easy` as the shipping preset. The parser failure above is not a contract bug: the reply visibly lacked the final outer-list bracket.

## G9 arms

| Arm | Solved / attempts | Observation |
|---|---:|---|
| bare | 0 / 3 | shipping evidence; hardened |
| structural hint | 1 / 3 | diagnostic `too_easy` under the old convention; does not gate |
| placebo hint | 3 / 3 | control sentence outperformed the real hint |

Hinted minus placebo is `1/3 - 3/3 = -0.6667`. With only three independently seeded attempts per arm, the placebo result prevents a causal claim that the structural hint helped. It may reflect seed/model variance or generic prompt sensitivity. The structural sentence names only the intersection-orbit invariant and does not reveal the recurrence or final polynomial. The measured answer is 981 characters (about 246 tokens); the exact worst-case formatting bound is 1,091 characters (273 tokens), with 200 atomic integers and 151 intended operations.

## Use

```python
from gen_1511_03623 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer("<answer>[[0,[0]]]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 1511.03623 20 easy
```

## Caveats

- This is emphatically Track B. Python, a CAS, or modular Gaussian elimination solves every instance quickly; it is not evidence for hard MDS-code search, arc extension, or the MDS conjecture.
- Coverage is native to the paper's `n=0` inclusion-matrix object and Theorem 1.13 certificate, but it does not exercise the determinant-weighted matrices `M_G^{up n}` for `n>0`, tangent functions, or classification of unknown arcs.
- A specialist can derive the bidiagonal orbit recurrence and bypass dense elimination. That is the intended insight, not an omitted attack; once the insight is known, the remaining 151 operations fit the no-tool cap.
- G4 is uniform over the exact dense coefficient language and proves resistance to uninformed guesses. It says nothing about guesses conditioned on recognizing a shifted Fermat polynomial; G6 and the oracle runs only sample a few such strategies.
- The external CAS, optimized finite-field linear algebra, and a symbolic recognizer for `(x+1)^(p-2)` were not counted as failing attacks because they are expected to succeed. The exact Gauss–Jordan implementation stands in for that tool-equipped regime.
- The three-arm oracle sample is tiny and highly variable: placebo solved 3/3 while the structural hint solved 1/3. No conclusion about the intuition label should be drawn from that difference alone.
- The canonical key is complete for this generated structure—one distinguished subset under arbitrary ground relabelling plus fixed field scalars—but it is not a canonical form for arbitrary weighted inclusion matrices.
- The module is standard-library-only. It does not need `gvlib`; all verification is modular integer arithmetic, with no floats or approximate algebra.
