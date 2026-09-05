# Anchored finite-field GBTD starters (arXiv:1304.0278)

| profile field | value |
|---|---|
| Track | **B** — an efficient reference scan is disclosed below |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | other (finite-field construction-parameter recovery) |
| Certificate | exact symbolic tuple `(omega, gamma, layer_perm)` |
| Intuition | symmetry: recognize affine images of three multiplicative cosets |
| Domain essentiality | native; no reduction |
| Shipping status | **hardened** at `easy` by the repository-owned bare oracle loop |

## What the problem is and what is verified

The source is Chee, Kiah, Ling, and Wang, [*Generalized Balanced Tournament Packings and Optimal Equitable Symbol Weight Codes for Power Line Communications*](https://arxiv.org/abs/1304.0278). Definition 6.1 describes a starter over `F_q × [3]`; Proposition 6.1 develops one into a `GBTD_1(3,q)`, Theorem 3.1 gives the reversible GBTP/ESWC correspondence, and Theorem 3.2 identifies the GBTD parameters with an optimal equitable-symbol-weight code meeting the generalized Plotkin bound. Proposition 6.2 gives the finite-field formula used here.

An instance supplies an affine frame and a few exact `A` and `B` blocks. The solver returns the primitive element `omega`, admissible `gamma`, and layer permutation that generate them. `verify` expands every `A_alpha` and `B_(t,j)` block, then checks the point partition, all pure and mixed difference multisets, and every row multiplicity using integer arithmetic modulo the prime `q`. It never reads `inst["answer"]`.

## Why this is Track B

Track A would be false: Proposition 6.2 is itself an explicit construction, Section 7 composes explicit recursive constructions, and Theorem 3.1 makes the design/code conversion reversible. Table 1 also labels several ESWC regimes “easy,” while Proposition 3.1 obtains the exceptional small values by exhaustive search; this family avoids both lookup-sized base cases and any structural-hardness claim. The reference algorithm scans every admissible `(omega,gamma)` pair and six layer permutations. After finite-field precomputation, at shipping `q=3001`, seed `271828`, it used 480,410 hypotheses, 1,441,572 point transformations, and 23.83 seconds. Across eight adversary seeds it solved 8/8, as expected, using 37,668,948 point transformations in 117.50 seconds on the final local run.

The compact route uses the supplied affine frame to recognize transformed `A_1`, reads `gamma` and the layer permutation from its three cross-layer slopes, and identifies `omega` from four consecutive same-layer cosets. The implemented route solved 8/8 seeds in 138–262 counted exact operations. That mechanical-versus-compact gap is the Track B claim.

## Difficulty presets

| preset | requested `n` | effective prime `q` | A/B anchors | admissible witness space | status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 7 | 5 / 1 | 36 | hand-scale |
| easy | 3000 | 3001 | 6 / 12 | 1,799,154 | **ships; bare oracle held 0/3** |
| medium | 3600 | 3607 | 6 / 12 | 3,251,286 | locally verified |
| hard | 4000 | 4003 | 6 / 12 | 3,698,568 | locally verified |

The preset name `easy` is only the first non-demo rung; it held all three bare oracle attempts, so no escalation was needed. Larger `n` increases the next admissible prime and the parameter haystack while the five-atom answer stays fixed. Beyond the named ladder, `escalate` also halves the redundant B-anchor count down to one, so it grows the haystack while removing clues rather than lengthening the witness.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON round-trip with prose/fences; garbage returned `None` |
| G4 | pass | 0/200,000 random hits; exact count 1/1,799,154 = 5.558×10⁻⁷ |
| G5 | pass | exact shipping density above; single-coset baseline failed; full reference cost recorded |
| G6 | pass | four attacks 0/8 each, including a by-hand identity-layer ansatz; reference scan 8/8; compact route 8/8 |
| G7 | pass | doubling `n` gave `q=6007`, a larger language, and a valid plant |
| G8 | pass | 60 invariance checks, 40 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 47 characters, about 12 tokens, 5 atoms; compact route at most 262 operations |
| G9(a,b) | partially measured | bare 0/3 and structural hint 0/3; placebo unavailable after four HTTP 403 redraws; these arms do not gate |

## Oracle loop

The repository-owned bare run held the first non-demo rung, so `easy` is the shipping preset. Every reply either contained a tagged but inadmissible parameter tuple or, in Gemini's longer response, ended with one; there is no parser false negative.

| preset | model | seed | solved | checker result |
|---|---|---:|---:|---|
| easy | Gemini 3.8 Flash | 208639218 | no | parsed; `omega,gamma` failed the primitive/exclusion/normalization checks |
| easy | GPT-5.6 Terra | 1862061530 | no | parsed; `omega,gamma` failed the primitive/exclusion/normalization checks |
| easy | GPT-5.6 Terra | 1232775496 | no | parsed; `omega,gamma` failed the primitive/exclusion/normalization checks |

## G9 arms

The structural-hint arm also held. The OpenRouter total limit was reached immediately afterward, so the placebo arm contains four honest, unscored HTTP 403 redraws. Those errors are retained and are not counted as model failures. G9(c) passes on the answer/effort caps.

| arm | scored solved/attempts | API errors | verdict |
|---|---:|---:|---|
| bare | 0/3 | 0 | hardened |
| structural hint | 0/3 | 0 | hardened |
| placebo hint | unavailable (0/0) | 4 | unavailable |

`hinted - placebo` is therefore undefined. The hint did not make any of its three instances solvable, but without a scored placebo arm that cannot be isolated from ordinary prompt variation. The answer is 47 characters (about 12 tokens), has five atomic elements, and the measured compact route used at most 262 exact operations.

## Worked demo

A person can solve this smallest case by enumerating its 36 admissible tuples. For seed 0 the answer is:

```json
{"omega":5,"gamma":1,"layer_perm":[1,2,0]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the permutation by `[1,1,0]` returns `(False, "layer_perm must be a permutation of 0,1,2")`.

<details>
<summary>Full rendered demo instance</summary>

```text
Anchored finite-field GBTD-starter reconstruction

All arithmetic below is in the prime field F_7; residues are represented by
the integers 0,...,6.  There are three layers 0,1,2.  The point with
residue x in layer i is encoded by the single integer i*7+x, hence points
are exactly 0,...,20.  A block is an unordered set of three distinct
encoded points; lists displaying blocks are written in increasing order.

Here q=7 and s=(q-1)/6=1.  The supplied affine frame is
  u=4, a=0,
  h=[2, 4, 3].
Find integers omega,gamma and a layer permutation pi that generate a GBTD
starter and all the anchored A-blocks below in this fixed affine frame.

The exact construction is as follows.  Return omega and gamma as canonical
residues in 0,...,6.  omega must be primitive modulo q, meaning its
powers omega^0,...,omega^(q-2) are all 6 nonzero residues.
gamma must avoid
  0, -1, -omega^(2s), -omega^(4s),
and, for every distinct i,j in {1,2,3} and t in {1,...,s-1}, it must avoid
  (omega^(2*i*s)-omega^(t+2*j*s)) / (omega^t-1).
Division means multiplication by the modular inverse.  Define
  Lambda = {-gamma*omega^(t-1+2*(i-1)*s): 1<=t<=s, 1<=i<=3}.
This problem additionally requires 1 not in Lambda.

For each alpha in F_q define a base block A_alpha.  If
alpha=-gamma*omega^(t-1+2*(i-1)*s), then A_alpha contains the three points
  (omega^(t-1+2*j*s), layer i-1), j=0,1,2.
Otherwise A_alpha contains
  (-alpha/gamma * omega^(2*i*s), layer i), i=0,1,2.
Also, for 1<=t<=s and 1<=j<=3, define B_(t,j) to contain
  (omega^(t-1+2*(j-1)*s) * (omega^(2*i*s)+gamma), layer i), i=0,1,2.

Transform every point of a base A block (x,i) to
  ((u*x + h[pi[i]]) mod q, layer pi[i]),
and move the A index alpha to (u*alpha+a) mod q.  In each B block use
  ((u*x + h[pi[i]] - a) mod q, layer pi[i]).
Here 1<=u<q,
0<=a,h[i]<q, and pi is a permutation of [0,1,2].

The expanded blocks must satisfy the starter axioms: the A blocks partition
F_q x [3]; every B block has one point in each layer; for each layer the
ordered nonzero within-layer differences occur exactly once; for each two
distinct layers every residue occurs exactly once as an ordered mixed
difference; and in the multiset formed from A_alpha-alpha together with all
B blocks, every point occurs once or twice.  The checker recomputes all of
these conditions exactly.

Required anchored blocks (their display order has no meaning):
  A[2] = [5, 9, 16]
  A[0] = [2, 11, 17]
  A[5] = [14, 18, 19]
  A[4] = [1, 7, 15]
  A[1] = [0, 10, 20]

The transformed B-family must also contain each of these unordered blocks:
  [1, 8, 20]

Give your final answer inside <answer></answer> tags as one JSON object with
exactly these keys: omega, gamma, layer_perm.  Use a three-integer JSON list
for pi.
Example format:
<answer>{"omega":2,"gamma":3,"layer_perm":[2,0,1]}</answer>
Output nothing else inside the tags.
```

</details>

## Use

From the repository root:

```python
import importlib.util
import json

spec = importlib.util.spec_from_file_location(
    "g", "results/1304.0278/gen_1304_0278.py"
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=123, **g.DIFFICULTY["easy"])
question = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(wire)
ok, reason = g.verify(inst, answer)
assert (ok, reason) == (True, "ok")
```

Because result-directory names are not normal Python package identifiers, direct file loading with `importlib.util.spec_from_file_location` is the portable route used by the repository scripts. The module is standard-library-only and does not need `gvlib`. Emit with:

```bash
bash scripts/emit.sh 1304.0278 20 easy
```

## Caveats

- This covers Proposition 6.2's prime-field starter objects, not the paper's prime-power extensions, recursive existence proof, or PLC performance model.
- The exact `1/1,799,154` density is relative to the declared uniform admissible-parameter prior. It does not model a solver that notices the affine/coset structure; that solver is represented by the compact attack.
- The reference scan is intentionally successful and must not be read as Track A hardness. No SAT/SMT system, computer algebra system, or optimized discrete-log/coset implementation was tried.
- Revealing the layer permutation or which same-layer anchors are the consecutive `t=1,2,3,4` cosets makes the compact recovery substantially easier; those roles are deliberately hidden while the affine frame remains public.
- The compact-operation count includes Euclidean-algorithm divisions, field multiplications, and subtractions, but excludes comparisons and table lookups.
- `canonical_key` exactly quotients the declared affine residue maps, independent layer translations, layer permutations, and input reorderings; it is not a complete isomorphism test for arbitrary set systems.
- The current repository harness recorded a two-model, two-vendor pool (GPT-5.6 Terra and Gemini 3.8 Flash), although the task text still describes the older four-vendor pool. The harness itself selected and recorded that pool; no builder-authored transcript or manual pool substitution was used.
- The placebo G9 diagnostic is missing because the OpenRouter key reached its total limit after the valid bare and hinted runs. This does not affect the bare `hardened` verdict or the gated G9(c) caps, but it prevents estimating `hinted - placebo`.
