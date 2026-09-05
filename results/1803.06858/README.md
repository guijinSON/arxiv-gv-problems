# Verified generator for arXiv:1803.06858

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate | normalized `2 x 2` projective matrix |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |
| Configured shipping preset | **medium candidate** (`n=8,388,607`, `p=8,388,617`), pending completion of STEP 4 |

## Problem and trust status

Grohe, Neuen, Schweitzer, and Wiebking's [*An improved isomorphism test for
bounded-tree-width graphs*](https://arxiv.org/abs/1803.06858) studies exact
isomorphisms of finite undirected simple graphs. This generator hands the solver
two connected treewidth-3 graphs. Each is a wheel over the projective line
`P^1(F_p)`, with a seed-dependent number of pendant leaves at its hub. The rim
edges are specified succinctly by a projective matrix. The answer is another
projective matrix whose induced vertex permutation is an isomorphism.

Generation is inverse: sample coordinate systems `C1,C2`, publish
`A=C1*U*C1^-1` and `B=C2*U*C2^-1`, and retain `T=C2*C1^-1`. Verification never
reads that retained answer. It checks shape, normalization, invertibility, and
whether `T*A*T^-1` is `B` or `B^-1`, using exact modular arithmetic. These two
cases are precisely the orientation-preserving and orientation-reversing rim
maps, and the hub and fixed-name leaves then map correctly as well.

All local gates pass at the medium candidate. The result is **not yet
shippable**. A fresh bare run showed that easy is too easy: one of its three
oracles returned a verified witness. At medium, two scored attempts failed, but
the key then hit OpenRouter HTTP 403 `Key limit exceeded` on every redraw before
the required third attempt. The harness therefore produced no verdict. The
three transcript files are harness-owned records, but the incomplete medium and
zero-attempt G9 panels are not hardness evidence.

As an independent checker audit, exhaustive enumeration on 18 instances over
`F_5`, `F_7`, and `F_11` found that `verify` agreed with literal edge-set
transport for every normalized projective matrix and accepted exactly `2p`
witnesses each time. A further 200 shipping-size seeds all passed the compact
construction in at most 65 counted field operations.

## Why Track B

Track A would be false. Section 2 gives the exact edge-biconditional definition
of graph isomorphism. Theorem 1 tests bounded-treewidth isomorphism in
`2^(k polylog k) poly(N)`, Theorem 15 in Section 6 computes the entire
isomorphism coset in `2^O(k log^c k) N^O(1)`, and Theorem 2 canonizes in
`2^O(k^2 log k) poly(N)`. Section 7 also defines graph isomorphism restricted
to a supplied permutation group, exactly the witness regime used here. Here
`k=3`, so all of these routes are polynomial in the expanded graph order `N`.

The measured reference algorithm materializes both successor tables, identifies
the hub, traverses the rim, and fits/checks the induced projectivity. Across
eight medium seeds it solved 8/8, used at most **209,693,940** counted exact
operations, and took at most **337.539 s** (mean 80.267 s). The compact route notices
that the two parabolic edge generators are conjugate, obtains their double fixed
points, and fits a projectivity through three corresponding points. It solved
8/8 in **65 exact field operations**. The benchmark claim is only that finding
this change of variables avoids millions of mechanical graph operations in a
no-tool context.

## Worked demo

The demo is hand-scale: all arithmetic is modulo 7, and a person can find a
valid change-of-coordinates matrix without expanding the 30-vertex graph. Seed
0 renders in full as follows.

```text
PROJECTIVE CYCLE GRAPH ISOMORPHISM

All arithmetic is in the prime field F_7. Field elements are the integers
0,...,6, with every operation reduced modulo 7.

The projective line P^1(F_7) has the labels 0,...,6,inf. A matrix
M=[[a,b],[c,d]] with nonzero determinant acts as follows:
  M(x) = (a*x+b)/(c*x+d) for x in F_7;
  M(x) = inf when c*x+d=0;
  M(inf) = a/c when c!=0, and M(inf)=inf when c=0.
Division means multiplication by the unique modular inverse.

For either displayed matrix M, define the finite undirected simple graph G(M). Its
vertices are the projective labels plus L_0,...,L_21. For each
projective label x with M(x)!=x, G(M) has the unordered edge {x,M(x)};
repeated descriptions count once. Each displayed M has a unique fixed projective point
f. Add every edge {f,x} for projective x!=f, and every pendant edge {f,L_j}.
Thus G(M) is a wheel with pendant leaves: it is connected and has tree width 3.

common pendant count q = 22
A = [[1,0],[2,1]]
B = [[1,2],[6,2]]

Find a projective matrix T over F_7 whose induced vertex bijection is an
isomorphism from G(A) to G(B). On projective vertices it sends x to T(x); it
fixes each L_j. Thus it must preserve both adjacencies and non-adjacencies.

Output T as JSON [[a,b],[c,d]], with exactly two rows and two entries per row.
Every entry must lie in 0,...,6; det(T) must be nonzero; and T must be
normalized so its first nonzero entry in row-major order is exactly 1. Matrices
that differ by a nonzero scalar represent the same projective map, which is why
this normalization is required.

Give your final answer inside <answer></answer> tags, as a JSON 2 by 2 matrix.
Example: <answer>[[1,2],[3,4]]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[[1,6],[4,5]]</answer>`.
`verify(inst, [[1,6],[4,5]])` returns `(True, "ok")`; dropping the second row
returns `(False, "answer matrix must have 2 rows, got 1")`.

## Difficulty presets

The smallest prime `p >= n` is used. The graph order lies between `2p+1` and
`5p+1`, while every answer remains four residues.

| preset | n | p | graph-order range | status |
|---|---:|---:|---:|---|
| demo | 7 | 7 | 15–36 | hand-solvable illustration |
| easy | 4,194,301 | 4,194,301 | 8,388,603–20,971,506 | rejected by oracle: 1/3 solved |
| medium | 8,388,607 | 8,388,617 | 16,777,235–41,943,086 | configured candidate; 0/2 failed, panel incomplete |
| hard | 2,147,483,647 | 2,147,483,647 | 4,294,967,295–10,737,418,236 | available escalation |

`escalate()` continues through known larger primes while the matrix remains
writable, then returns `cap_bound`. It deliberately does not inflate only the
succinct pendant count: that would enlarge the graph described by the prompt
without making the displayed algebraic task harder.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verified across all presets; JSON round-trip held |
| G2 | empty, dropped-row, out-of-range, transposed, and duplicate-row corruptions rejected with five distinct reasons |
| G3 | realistic prose/fenced output round-tripped; garbage returned `None` |
| G4 | 0/200,000 hub-respecting projective guesses; exact density `2/(p-1)`, log10 `-6.623` |
| G5 | 16,777,234 valid matrices among 70,368,886,784,072; reference max 209,693,940 operations / 337.539 s |
| G6 | coefficient ratio, greedy labels, 256 restarts, and affine-only ansatz each 0/8; reference 8/8 as expected |
| G7 | doubled `n=16,777,214` chose `p=16,777,259`, enlarged the language, and verified |
| G8 | 120/120 invariance and 120/120 carried-witness checks, including composed symmetries; 20/20 unrelated keys distinct |
| G9(c) | 31 worst-case chars across 40 seeds, 8 estimated tokens, 4 atoms, 65 intended operations |

## Oracle loop and G9 arms

The bare harness completed easy, then reached only two of the three required
medium attempts before the quota failed. Its harness-written transcript records:

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 1,601,365,114 | failed | no parseable final answer after length stop |
| easy | GPT-5.6 Terra | 1,735,218,850 | **solved** | returned a matrix that verified |
| easy | GPT-5.6 Terra | 269,353,413 | failed | returned a non-isomorphism |
| medium | GPT-5.6 Terra | 2,002,250,643 | failed | returned a singular matrix |
| medium | Gemini 3.8 Flash | 1,323,601,159 | failed | empty length-limited response |
| medium | redraws | various | error | four HTTP 403 total-limit errors; run aborted |

| G9 arm | solved / scored attempts | errors | conclusion |
|---|---:|---:|---|
| bare (medium only) | 0 / 2 | 4 | incomplete; no verdict |
| structural hint | 0 / 0 | 4 | unmeasured |
| placebo hint | 0 / 0 | 4 | unmeasured |

Hinted minus placebo is unavailable, so nothing can yet be concluded about
whether naming conjugacy supplies useful structural information. The size and
effort cap is independent of the failed calls and passes at 31 worst-case characters,
4 atoms, and 65 intended operations.

## Use

```python
from gen_1803_06858 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["medium"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

After a successful rerun of STEP 4, emit from the repository root with:

```bash
bash scripts/emit.sh 1803.06858 20
```

The module is standard-library-only and performs no I/O or network access.

## Caveats

- This is not a computational-hardness claim. The paper supplies efficient
  bounded-treewidth algorithms, and the 65-operation projective method is an
  even stronger solver for this deliberately structured distribution.
- The graph objects and exact isomorphism witness are native, but projective
  wheels are a narrow subclass not studied separately in the paper. The family
  tests recognition of a succinct conjugacy, not the paper's full decomposition
  machinery or hard instances for its FPT algorithm.
- The reference implementation is a specialized exact materialize-and-traverse
  baseline, not an implementation of the paper's group-theoretic algorithm.
  Nauty/Traces, Weisfeiler–Leman refinement, SAT, and external computer-algebra
  systems were not run. For these wheels their extra power is unlikely to beat
  using the displayed projective structure, but that has not been benchmarked.
- The `0/200,000` result samples uniformly from normalized invertible matrices
  that already map the unique hub of `A` to the unique hub of `B`, enforcing
  that freely deducible graph constraint as well as the syntax constraints. It
  establishes sparse density under that prior, not difficulty under an informed
  prior; an informed solver should target the `2p` dihedral conjugators directly.
- The seed-dependent pendant count supplies genuine canonical diversity and
  expanded-input cost but does not make the projective certificate harder.
- Most importantly, medium has only two scored bare attempts and neither G9 arm
  has a scored attempt because the supplied OpenRouter key exhausted its total
  limit. The configured candidate must not be treated as hardened until the bare
  medium panel and both diagnostic arms are rerun with working quota.
