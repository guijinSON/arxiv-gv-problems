# S-integral quadratic-form equivalence generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `number_theory` |
| Object regime | `rational_exact` |
| Computational core | `linear_algebra` |
| Certificate form | `exact_symbolic` |
| Intended intuition | `invariant`: decode the two-unit spectrum from a carry-free base-four trace |
| Domain essentiality | `native` |
| Reduction | none |

This module turns Irving Calderón's paper [*S-integral quadratic forms and homogeneous dynamics*](https://arxiv.org/abs/2202.10257) into exact equivalence problems. The solver receives two non-degenerate integral quadratic forms represented by their symmetric matrices and must give the positive (2)-unit spectral roots that define an explicit polynomial change of variables in (GL(d,\mathbb Z[1/2])). The checker expands that Lagrange polynomial exactly, checks its matrix square, checks its determinant is a (2)-unit, and therefore checks the original congruence. No graph, finite-field, or integer-coordinate surrogate replaces the paper's objects.

## Why this is Track B

Section 2.1 fixes the definition (Q_2=Q_1\circ g) for (g\in GL(d,R)). Section 5, Theorem 5.1 is the relevant real-isotropic (d\ge3) regime and gives a finite bounded search for an (S)-integral equivalence. This is not a Track-A claim: an exact algorithm exists here. The reference algorithm tests every allowed power-of-four eigenvalue with a Bareiss determinant and then expands the spectral square root; it is (O(E n^3)), solved 8/8 audit instances, and cost at most 479,724 counted exact operations and 0.259 seconds at the shipping preset.

The compact route uses only similarity invariance of trace. Every distinct eigenvalue is (4^e), all have the same public multiplicity (r), and therefore (\operatorname{tr}(C)/r) has base-four digit 1 precisely at the wanted exponents. Reading those digits and writing (2^e) costs at most 84 exact operations. A no-tool solver must discover that compression; a mechanical spectral scan is not executable in context. The generator avoids the easy regimes identified by the paper: dimension two, where the Introduction cites Gauss's efficient algorithm, and the everywhere-local-anisotropic case, which the opening of Section 5 calls easy because its local transporter sets are compact.

Generation is inverse. It samples the roots first, repeats their squares on a diagonal, and applies an integral unimodular similarity (C=R^TDR^{-T}). The Lagrange identity then supplies the retained witness. No eigenproblem or equivalence search occurs during generation.

## Worked demo

For `seed=7`, the full rendered `demo` instance is:

```text
S-integral equivalence of two quadratic forms

Let Z[1/2] be the rational numbers whose reduced denominator is a power of 2.
A square matrix G is in GL(d,Z[1/2]) when every entry of G and G^(-1) is in
Z[1/2]. For a symmetric integer matrix A, write Q_A(x)=x^T A x. An
S-integral equivalence from Q_A to Q_B is a matrix G in GL(d,Z[1/2]) satisfying
G^T A G = B exactly.

Here d=4 and n=2. Let I be the n by n identity matrix and set

    A = [[0,I],[I,0]].

The other symmetric matrix is

    B = [[0,C],[C^T,0]],

where the complete n by n integer matrix C is:

-368 -192
864 448

Find exactly k=2 distinct positive powers of 2, written in strictly
increasing order as u_0,...,u_(k-1), with u_i=2^e_i and
1 <= e_i <= E=5. From them define the rational Lagrange polynomial

  p(t) = sum_i u_i * product_(j!=i) (t-u_j^2)/(u_i^2-u_j^2).

Your roots are a valid certificate exactly when

  G = p(A^(-1)B)

belongs to GL(d,Z[1/2]) and satisfies G^T A G=B. Products over an empty set
are 1; indices are 0-based; roots may not repeat; and the displayed order is
part of the required output shape.

Encode every integer root u as the exact rational pair [u,1]. Give your final
answer inside <answer></answer> tags as exactly one JSON object of the form
{"roots":[[u_0,1],...,[u_(k-1),1]]}.
Example for k=2: <answer>{"roots":[[2,1],[8,1]]}</answer>
Output nothing else inside the tags.
```

Here `trace(C)=80=4^2+4^3`, so the answer is `<answer>{"roots":[[4,1],[8,1]]}</answer>`. The demo is hand-solvable from that observation. `verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the final root returns `(False, "root_count")`.

## Difficulty presets

| Preset | (n) | Form dimension | Roots (k) | Exponent bound (E) | Mix steps | Candidate space | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 2 | 4 | 2 | 5 | 8 | 10 | hand example |
| easy | 18 | 36 | 6 | 54 | 108 | 25,827,165 | **ships; hardened** |
| medium | 28 | 56 | 7 | 78 | 196 | 2,641,902,120 | reserve |
| hard | 32 | 64 | 8 | 104 | 256 | 257,575,523,205 | reserve |

An earlier two-eigenvalue design passed the local gates but every bare level through (n=84) had an oracle solve and the harness returned `budget_bound`. It was replaced because the degree-one output format leaked nearly the entire method; simply increasing its matrix size would not have repaired the family.

## Gate results

| Gate | Result |
|---|---|
| G1 planted verifies | 12/12 across every preset |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round trip | tagged fenced JSON and JSON-native answer both pass |
| G4 guess resistance | 0/200,000; shipping space 25,827,165 |
| G5 density and baseline | 0/200,000 at shipping; demo has exactly 1 answer; reference 479,652 ops / 0.205 s |
| G6 adversaries | five attacks at 0/8; reference solver 8/8, as Track B expects |
| G7 scaling | doubled dimension 36→72 verifies; operation scale 314,928→2,519,424; answer stays 12 atoms |
| G8 canonical key | 20/20 composed relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9 caps | 119 chars, 30 estimated tokens, 12 atoms, 84 intended operations |

## Bare oracle loop

| Model | Seed | Solved | Outcome |
|---|---:|---|---|
| Gemini 3.8 Flash | 239110641 | no | parsed roots failed `spectral_trace` |
| GPT-5.6 Terra | 965278947 | no | parsed roots failed `spectral_trace` |
| Gemini 3.8 Flash | 1443396314 | no | length-limited response emitted no answer |

The harness verdict is `hardened` at `easy`, with no escalation.

## G9 diagnostic arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural | 1/3 | one solver used the named invariant successfully |
| placebo | 0/3 | extra prompt text alone bought nothing |

Hinted minus placebo is (1/3). The structural hint therefore carried measurable information, but did not hand over a complete procedure: two of three hinted attempts still failed. This diagnostic does not gate shipping.

## Use

From the repository root:

```python
import importlib.util

path = "results/2202.10257/gen_2202_10257.py"
spec = importlib.util.spec_from_file_location("gen", path)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
answer = gen.parse_answer('<answer>{"roots":[[4,1],[8,1]]}</answer>')
assert gen.verify(inst, answer) == (True, "ok")
```

Emit 20 shipping instances with:

```bash
bash scripts/emit.sh 2202.10257 20 easy
```

## Caveats

This is a Track-B benchmark, not evidence that the generated distribution is complexity-theoretically hard. The 0/200,000 density estimate uses the exact stated prior—uniform sorted (k)-subsets of allowed exponents—and says nothing about a solver using the trace invariant. General lattice reduction, external CAS eigensolvers, and specialized (p)-adic equivalence packages were not tested; the exact determinant scan is the implemented domain reference. The canonical key uses trace plus the absolute-entry multiset and is invariant under the tested signed similarities and block transpose, but it is not a complete invariant for arbitrary integral similarity.

One of three bare failures and one hinted failure were response-length exhaustion at the harness's 32,000-token setting; those are valid no-tool outcomes under the recorded protocol but weaker evidence than an incorrect parsed certificate. The run was not repeated with a larger response budget. Conversely, the successful hinted attempt shows that exposing the invariant can make the family easy. Finally, the construction deliberately has equal spectral multiplicities and powers-of-two roots; changing either promise would invalidate the compact route and this verifier's certificate language.
