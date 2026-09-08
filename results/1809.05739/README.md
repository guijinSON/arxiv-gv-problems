# arXiv 1809.05739 problem generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | rational exact |
| Computational core | linear algebra |
| Certificate form | polynomial |
| Native objects | affine blocks over `F_q`; an exact equiangular-line Gram matrix |
| Intended intuition | decomposition — find the hidden parallel classes and their zero-sum subspaces |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is [Casazza, Tran, and Tremain, *Equiangular lines, Incoherent sets and Quasi-symmetric designs*](https://arxiv.org/abs/1809.05739). The generator selects affine lines in `F_q^2`. They are `q`-subsets with intersection sizes 0 and 1, so Construction 6.1 and Theorem 6.2 turn them into equiangular Euclidean lines. The solver receives the affine blocks and the exact integer matrix rule for a scaled Gram matrix `G`, then must return `det(xI-G)` as two exact polynomial factors. Verification reconstructs the parallel classes from the submitted instance, expands the submitted factorization over the integers, and compares every coefficient. It never reads `inst["answer"]`.

Generation is inverse/theorem-backed, not solution by search. If the selected parallel-class sizes are `t_i`, the generator composes the identity

```text
(x-2q)^(N-r) * [ product_i(x-2q+2t_i)
                  - sum_i t_i product_{j!=i}(x-2q+2t_j) ].
```

## Why this is Track B

Track A would be false: characteristic polynomials are computable in polynomial time. The measured reference is exact Faddeev–LeVerrier with schoolbook matrix multiplication, `O(N^4)` exact operations. On a shipping-preset matrix of order 103 it used **222,948,182** counted integer operations and **19.325021 s** in the final self-test. It solved 1/1, as expected.

The compact route recognizes that blocks with proportional normals form parallel classes. Each within-class zero-sum subspace contributes eigenvalue `2q`; a rank-one determinant identity gives the remaining degree-7 factor. The conservative bound was 824 exact operations on the measured reference instance and 884 on the G9 shipping instance. That is within the no-tool cap but is not mechanical unless the solver discovers the decomposition.

Section 2.1 fixes the exact block-set terminology. Section 6, especially Construction 6.1 and Theorem 6.2, licenses the geometric objects and their Gram matrix. Theorem 1.1 classifies only absolute-bound equality cases in dimensions 2, 3, 7, and 23; using those examples would make the answer a small lookup. This generator instead uses the general Section 6 theorem. Small fields and few blocks are easy by direct expansion, while every generated size is also easy once the parallel-class decomposition is seen; those are why the claim is Track B rather than structural hardness.

## Worked demo

This is `render(make_instance(seed=0, **DIFFICULTY["demo"]))` in full:

```text
Exact spectrum of a Gram matrix from affine blocks

All scalar arithmetic below is exact. Let F_q be the field of integers modulo
the prime q=3. The point set is F_q^2, of size d=q^2=9.
A row [a,b,c,s] defines the q-point affine block
  B={(x,y) in F_q^2 : a*x+b*y=c (mod q)}
and an orientation sign s in {-1,+1}. Multiplying a,b,c by the same nonzero
field element does not change the block. Distinct blocks are parallel and
disjoint exactly when their normal pairs (a,b) are proportional modulo q;
otherwise they intersect in exactly one point.

The 8 oriented blocks are:
  0: [0, 2, 1, -1]
  1: [1, 2, 2, 1]
  2: [1, 2, 0, -1]
  3: [0, 2, 0, -1]
  4: [2, 2, 2, -1]
  5: [2, 2, 1, 1]
  6: [2, 1, 2, -1]
  7: [0, 1, 1, 1]

These blocks have exactly r=3 parallel classes. Define the
N-by-N integer matrix G, where N=8, by
  G[i,i] = 2q-1;
  G[i,j] = s_i*s_j  if B_i and B_j intersect;
  G[i,j] = -s_i*s_j if B_i and B_j are disjoint (i != j).
This is a positive scalar multiple of the Gram matrix of the equiangular
Euclidean-line representatives supplied by Construction 6.1: here d=q^2,
k=q, the two block intersections are 1 and 0, and Delta_1=q^2/2 >= 0.

Find the exact characteristic polynomial chi_G(x)=det(xI-G). Output it in the
promised compressed factorization into exactly two monic factors: one monic
linear polynomial with multiplicity N-r=5, and one
monic degree-r polynomial with multiplicity 1. Factor order and polynomial-term
order do not matter.

Represent a polynomial as a JSON list of terms [[num,den],[e]], meaning the
rational coefficient num/den times x^e. Exponents are nonnegative integers,
denominators are positive, repeated exponents are combined, and zero terms may
be omitted. Represent the factorization as
  {"factors":[{"poly": POLY, "multiplicity": INTEGER}, ...]}.
All coefficients here are integers (denominator 1). The certificate language
bounds every freely chosen coefficient magnitude by
H=21952.

Give your final answer inside <answer></answer> tags as one JSON object.
Example format: <answer>{"factors":[{"poly":[[[-6,1],[0]],[[1,1],[1]]],"multiplicity":4},{"poly":[[[-8,1],[0]],[[2,1],[1]],[[1,1],[2]]],"multiplicity":1}]}</answer>
Output nothing else inside the tags.
```

The exact answer is:

```json
{"factors":[{"poly":[[[-6,1],[0]],[[1,1],[1]]],"multiplicity":5},{"poly":[[[0,1],[0]],[[12,1],[1]],[[-10,1],[2]],[[1,1],[3]]],"multiplicity":1}]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Changing the residual `x` coefficient from 12 to 13 returns `(False, "residual coefficient of x^1 is wrong")`. A person can solve this demo by hand: normalize the eight line equations, tally the three parallel classes, and apply the displayed factor identity.

## Difficulty presets

| Preset | `n` / resulting `q` | Classes | Lines per class | Gram order `N` | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 / 3 | 3 | 2–3 | 6–9 | hand example |
| easy | 17 / 17 | 7 | 8–17 | 56–119 | current ladder |
| medium | 23 / 23 | 7 | 11–23 | 77–161 | current ladder |
| hard | 1,000,000 / 1,000,003 | 7 | 11–23 | 77–161 | **ships** |

The original `q=7,11,13` rungs and the escalated `q=17,23` rungs were solved by at least one bare oracle. The ladder was therefore slid upward after `q=1,000,003` held. Increasing `q` grows coefficient entropy and the structure-aware answer space while the degree-7 witness stays fixed in length.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted certificates verified; JSON round-trip also checked |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence; garbage rejected |
| G4 | pass | 0/200,000 structure-aware guesses; exact language density `1 / 4.1232600629e283` |
| G5 | pass | unique characteristic polynomial; reference 222,948,182 ops / 19.325021 s; failing restart 2,048 candidates / 0.154484 s |
| G6 | pass | five attacks, each 0/8; reference exact algorithm solved 1/1 |
| G7 | pass | doubling `n` gave prime 2,000,003, a larger candidate space, and a valid 32-atom answer |
| G8 | pass | 20/20 invariant relabellings, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass | 382 chars, about 96 tokens, 32 atoms, 884 intended operations |

The five failing attacks were a line-coefficient outlier, a diagonal-only root guess, a trace-only equal-root ansatz, a signed-row-sum ansatz, and 256 structure-aware random candidates per seed. Random equation scaling, input order, directions, intercepts, and orientation signs prevent the planted blocks from occupying a special representation.

## Bare oracle loop

The names in this table are the ladder labels at the time of the run; `escalated` rows became the current `easy`, `medium`, and `hard` presets afterward.

| Preset / parameters | Seeds and outcomes | Why |
|---|---|---|
| easy, `q=7` | 1729792616 solved; 1460999892 solved; 839520353 solved | all exact answers verified |
| medium, `q=11` | 1483613291 failed; 178107828 solved; 1691071828 solved | failure had wrong constant coefficient |
| hard, `q=13` | 184901872 solved; 927551006 failed; 198169473 solved | failure had wrong constant coefficient |
| escalated, `q=17` | 1327520941 solved; 738107404 solved; 131389996 solved | all exact answers verified |
| escalated, `q=23` | 1320978827 solved; 261697974 failed; 1306738975 failed | failures had wrong constant coefficients |
| escalated, `q=1,000,003` | 1024385114 failed; 2134869423 failed; 592747618 failed | wrong constant; no parsed answer; wrong constant |

Verdict: `hardened`, with the last row as the shipping parameters.

## G9 arms

| Arm | Solved / attempts | Result |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted − placebo = 0.0`. The hint names the constant-on-parallel-classes invariant but bought the sampled oracle pool no measured improvement. This does not refute the decomposition intuition: the replies generally attempted the right high-level spectral route but made exact coefficient errors. One malformed hinted provider response is retained in the transcript as `error` and was redrawn; it is not one of the three attempts. The placebo transcript was rerun with a larger response ceiling so all three preserved rows contain substantive model outcomes.

## Use

From the repository root:

```python
import importlib.util
import json

path = "results/1809.05739/gen_1809_05739.py"
spec = importlib.util.spec_from_file_location("generator", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
candidate = g.parse_answer('<answer>' + json.dumps(inst['answer']) + '</answer>')
assert g.verify(inst, candidate) == (True, 'ok')
```

The directory name is not a valid ordinary Python package segment, so robust callers should load the file with `importlib.util.spec_from_file_location`, as the repository scripts do. Emit 20 shipping instances with:

```bash
bash scripts/emit.sh 1809.05739 20 hard
```

## Caveats

- This is deliberately not a complexity-theoretic hardness claim. A CAS or exact linear-algebra program solves every instance in polynomial time, and a solver that notices the class decomposition solves it quickly.
- The paper does not claim that this generated distribution is hard. Its theorem certifies the equiangular Gram objects; the no-tool compression benchmark is built around those objects.
- The `1/4.12e283` density is for the declared structure-aware prior, which already enforces shape, degree, monicity, PSD sign alternation, trace, and coefficient bounds. It is not a model of all informed solver priors and should not be read as a success probability for a solver using affine geometry.
- The reference implementation is a deliberately plain exact Faddeev–LeVerrier baseline. Faster characteristic-polynomial algorithms, optimized CAS implementations, numeric eigensolvers followed by reconstruction, and arbitrary-isometry canonicalization were not benchmarked.
- `canonical_key` is complete for the generated family under affine point relabelling, equation rescaling, orientation flips, and input permutation because `q` and the multiset of class sizes determine the Gram matrix up to signed permutation. It does not attempt general isometry testing outside this family.
