# Exact signless-Laplacian radii of hidden multipartite graphs

Status: **parked (`cap_bound`), not shippable**. Every local gate passes, but the
bare oracle loop solved every admissible rung through `n=110`. The next fixed-degree
rung would require 308 exact operations, over the 300-operation no-tool cap. Per the
task contract this is not a rejection of the paper, but it is not a hardness claim.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | real algebraic |
| Computational core | linear algebra |
| Certificate form | algebraic number |
| Intended intuition | decomposition: equal adjacency rows expose equitable cells |
| Domain essentiality | native |
| Reduction | none |

## What the problem is and why it is trustworthy

The source is Zheng, Li, and Fan, [*Some Turán-type results for the signless
Laplacian spectral radius*](https://arxiv.org/abs/2507.02263). Section 1.3 defines
the paper’s central object: $Q(G)=D(G)+A(G)$ and its largest eigenvalue $q(G)$.
Section 1.1 defines complete multipartite Turán graphs and clique blowups; these
objects drive the results in Section 2. An instance gives a randomly relabelled
complete multipartite graph by exact hexadecimal adjacency rows. The solver must
return $q(G)$ as its monic integer minimal polynomial and an open isolating
interval with integer endpoints.

If the distinct part sizes are $s_1,\ldots,s_k$, $N=\sum_i s_i$, and the
Perron vector has value $x_i$ on part $i$, then its eigen-equations give

\[
  (q-N+2s_i)x_i=S,\qquad
  \sum_i \frac{s_i}{q-N+2s_i}=1.
\]

Clearing denominators gives, by composition, the certificate polynomial

\[
 P(X)=\prod_i(X-N+2s_i)-\sum_i s_i\prod_{j\ne i}(X-N+2s_j).
\]

The generator samples the part sizes first and keeps only vectors for which a
small-prime Rabin test proves $P$ irreducible modulo that prime. Gauss’s lemma
then proves that $P$ is the minimal polynomial over ℚ. Its Perron root is the
unique root above the largest pole $N-2\min s_i$, and $q(G)<2(N-1)$. Thus the
answer is known without solving the emitted matrix. `verify` reconstructs the
parts from adjacency rows, recomputes $P$, reruns the finite-field
irreducibility proof, and uses exact Sturm counting both inside and above the
submitted interval to certify that it isolates the largest real root. It never
reads the planted answer and accepts every valid isolating interval in the
declared language.

## Why this is Track B

This cannot honestly be Track A: exact eigenvalue algorithms exist. The measured
reference route builds the full integer matrix, computes its characteristic
polynomial by exact Faddeev–LeVerrier, removes rational eigenvalue factors, and
isolates the largest remaining root by Sturm’s theorem. It is polynomial time,
$O(N^4)$ exact scalar operations, and solved 8/8 base-preset instances. At
$N=56,k=7$, it averaged 16,141,202 counted operations and 0.859335 seconds
(maximum 16,765,266 and 0.937650 seconds) on the final audit run.

The compact route notices that identical adjacency rows are the multipartite
cells, counts their seven sizes, and accumulates the denominator and weighted
numerator of the displayed rank-one Perron identity together. Including all 56
row-count increments, it uses 226 exact arithmetic operations. That is within
the no-tool cap once the decomposition is seen; the 16-million-operation matrix
route is not executable by hand in the evaluation context.

The paper’s Theorem 2.4 does not itself make a finite benchmark: it guarantees a
$K_{k+1}[t]$ only for sufficiently large $n$, with hidden constants, and
Example 4.1 proves the logarithmic $t$-scale sharp. The theorem also fails for
$k=1$, as the discussion after Theorem 2.4 explains. Rather than claim a modest
planted blowup is theorem-backed, this family stays with the native spectral
quantity and uses an exact composition certificate.

## Worked demo

`make_instance(n=9, k=3, seed=0)` is hand-solvable: the three repeated row
patterns occur 2, 3, and 4 times, after which the cubic above takes a few lines of
arithmetic. Its complete rendered statement is:

```text
Find the signless Laplacian spectral radius of a graph exactly.

The graph is finite, simple, and undirected, with vertices 0,...,8.
Its adjacency matrix is A.  The degree d_i is the number of 1s in row i,
D is the diagonal matrix diag(d_0,...,d_8), and the signless Laplacian
is Q=D+A.  Its spectral radius q(G) is the largest real eigenvalue of Q.

The adjacency rows are hexadecimal bit masks of exactly 3 digits.
In row i, bit j is 1 exactly when vertices i and j are adjacent; bit 0
is the least-significant (rightmost) bit.  Leading zero hex digits are kept.
Rows:
  0: 06e
  1: 1b5
  2: 1db
  3: 1b5
  4: 06e
  5: 1db
  6: 1b5
  7: 06e
  8: 06e

It is guaranteed that exactly k=3 distinct adjacency-row patterns occur,
and that the requested number has a monic irreducible minimal polynomial
of degree k over the rationals.

Return q(G) as an exact real algebraic number.  The key minpoly must be
the dense coefficient list [c0,c1,...,c3] for
  c0 + c1*x + ... + c3*x^3,
in constant-to-leading order.  All coefficients are integers, c3=1,
and every nonleading coefficient must lie in the inclusive range [-H,H],
where H=4000.

The key interval must be [[L,1],[U,1]], representing the OPEN rational
interval L < q(G) < U.  Here L and U are integers satisfying
0 <= L < U <= 16, neither endpoint is a root, and the interval contains
exactly one root of minpoly.  Coefficient order matters; interval endpoint
order matters; no coefficient or endpoint may be omitted.

Give your final answer inside <answer></answer> tags, as exactly one JSON
object with keys minpoly and interval.
Example format for k=3: <answer>{"minpoly":[0,0,0,1],"interval":[[0,1],[1,1]]}</answer>
Output nothing else inside the tags.
```

The answer is
`{"minpoly":[-96,81,-18,1],"interval":[[5,1],[16,1]]}`.

```python
>>> verify(inst, inst["answer"])
(True, "ok")
>>> bad = {"minpoly": [-95, 81, -18, 1], "interval": [[5, 1], [16, 1]]}
>>> verify(inst, bad)
(False, "minpoly does not match the graph-derived Perron polynomial")
```

## Difficulty presets

| Preset | Vertices `n` | Cells `k` | Answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 9 | 3 | 8 | hand-solvable illustration |
| easy | 56 | 7 | 12 | oracle solved 2/3 |
| medium | 72 | 7 | 12 | oracle solved 2/3 |
| hard | 88 | 7 | 12 | oracle solved 3/3 |
| escalated | 110 | 7 | 12 | oracle solved 3/3; terminal admissible rung |

No preset held, so none ships. Escalation did increase the matrix and coefficient
haystack while keeping the polynomial degree and 12-atom answer fixed, but the
oracles continued to recover the row-class decomposition and exact polynomial.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted answers, all JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose/fence; garbage rejected |
| G4 | pass | 0/200,000 guesses; exact density (748/S=4.1832\times10^{-96}) |
| G5 | pass | exact 748 valid encodings; reference mean 16,141,202 ops / 0.859335 s |
| G6 | pass | five attacks each 0/8; exact reference algorithm 8/8 |
| G7 | pass | doubled `n=112` builds and verifies; answer remains 12 atoms |
| G8 | pass | 60/60 invariant keys, 60/60 carried certificates, 20/20 distinct seeds |
| G9(c) | pass | 111 chars, 28 estimated tokens, 12 atoms, 226 operations |

The five failed attacks are maximum-row-sum outlier guessing, average-row-sum
greedy guessing, a product of visible row-sum factors, a Perron-bound midpoint
ansatz, and 256 structure-aware random restarts. The successful general exact
algorithm is correctly reported outside `attacks` as Track B’s reference.

## Oracle loop

These are scored bare-prompt calls from the script-owned transcript.

| Preset | Seed | Model | Outcome | Verification |
|---|---:|---|---|---|
| easy | 1966427000 | GPT-5.6 Terra | failed | wrong minimal polynomial |
| easy | 1347004129 | Gemini 3.8 Flash | solved | `ok` |
| easy | 26175460 | Gemini 3.8 Flash | solved | `ok` |
| medium | 969627269 | GPT-5.6 Terra | failed | wrong minimal polynomial |
| medium | 1230503863 | Gemini 3.8 Flash | solved | `ok` |
| medium | 1107852127 | Gemini 3.8 Flash | solved | `ok` |
| hard | 646043693 | Gemini 3.8 Flash | solved | `ok` |
| hard | 1581192146 | GPT-5.6 Terra | solved | `ok` |
| hard | 1310674302 | GPT-5.6 Terra | solved | `ok` |
| escalated (`n=110`) | 1503703800 | Gemini 3.8 Flash | solved | `ok` |
| escalated (`n=110`) | 435964614 | GPT-5.6 Terra | solved | `ok` |
| escalated (`n=110`) | 666534821 | GPT-5.6 Terra | solved | `ok` |

The script verdict is `cap_bound` after three escalations. This is decisive
against shipping the current family: increasing only the number of displayed
rows did not defeat the compact pattern-recognition route.

## G9 arms

| Arm | Solved / scored attempts | Diagnostic conclusion |
|---|---:|---|
| bare (`easy`) | 2 / 3 | the unhinted family is already too easy |
| structural hint (`easy`) | 0 / 0 | prior run had four HTTP 403 errors |
| placebo hint (`easy`) | 0 / 0 | prior run had four HTTP 403 errors |

`hinted - placebo` is undefined because neither auxiliary arm produced a scored
attempt. The contract says to stop at `cap_bound`, so they were not rerun after
the successful bare call. At the base preset, G9(c) passes: 111 answer characters,
28 estimated tokens, 12 atoms, and 226 exact operations. The terminal `n=110`
rung costs 280 operations; the next `n=138` rung would cost 308.

## Use

```python
import json
import gen_2507_02263 as g

inst = g.make_instance(seed=12345, **g.DIFFICULTY["easy"])
question = g.render(inst)
candidate = g.parse_answer(
    "<answer>" + json.dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

The mechanics can be exercised from the repository root with the command below,
but do **not** publish its output unless a redesigned family first receives a
`hardened` verdict:

```bash
bash scripts/emit.sh 2507.02263 20 easy
```

## Caveats

- This is Track B. With tools, the disclosed exact matrix algorithm solves every
  generated instance in polynomial time; the benchmark is the compression gap,
  not a complexity-theoretic hardness claim.
- The exact density uses the declared prior over monic bounded coefficient lists
  and ordered integer endpoint pairs. It does not describe a solver’s posterior
  after recognizing the equal-row decomposition.
- Repeated rows deliberately expose the intended structure. Explicitly giving
  the seven cell sizes would remove the recognition step; reducing `k` makes the
  remaining polynomial arithmetic easy.
- Fixed-degree escalation reaches `n=110`; the next step is reported as
  `cap_bound` because tallying every displayed row would exceed the 300-operation
  no-tool cap, even though the 12-atom answer would still fit comfortably. The
  harness’s generic `cap_bound` reason mentions answer length; for this module the
  actual binding limit is intended-route effort.
- The panel did not test floating-point QR plus integer-relation reconstruction,
  arbitrary graph neural embeddings, or an oracle with external code execution.
  The stronger exact full-matrix algorithm was tested and is disclosed.
- `canonical_key` is complete for this generated class: two complete multipartite
  graphs are isomorphic exactly when their multisets of part sizes agree. The
  tests cover random relabelling, reversal, and their composition.
- `gvlib.roots` is used when available. A standard-library-only exact Sturm
  fallback is included and does not use floating point.
- The task text describes a four-vendor pool, while the repository’s current
  `scripts/harden.py` (dated 2026-09-05) uses the two vendors recorded in
  `.meta.json`: OpenAI and Google. The transcript reports the pool actually run;
  no four-vendor result is claimed.
- Most importantly, the cross-vendor result is negative: every rung was solved.
  `SHIPPING_DIFFICULTY="easy"` remains only the base preset used by local gates;
  it is not release-ready and must not be emitted as corpus data.
