# Roman domination in strong product graphs — verified generator

> **Disposition: rejected for H on Track B.** Generation and exact verification
> pass, but 11 of 12 scored bare oracle attempts recovered a valid certificate,
> including all attempts at the escalated \(p=97\) setting. The implementation
> is retained as `rejected_gen_1111_3517.py` for audit and possible redesign.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | exact symbolic (two finite-field hyperplane equations) |
| Intended intuition | invariant: the nonlinear coefficient columns share a codimension-one span |
| Domain essentiality | native |
| Reduction | none |

The construction and checker are verified locally. The hardness claim failed:
the bare harness solved `easy` 3/3, `medium` 2/3, `hard` 3/3, and an escalated
setting 3/3. A later attempt to continue to \(p=191\) stopped on the OpenRouter
quota; those infrastructure errors are retained but are not counted as model
failures.

## What the family is

The source is Yero and Rodríguez-Velázquez, [*Roman domination in Cartesian product graphs and strong product graphs*](https://arxiv.org/abs/1111.3517). Section 1 defines a Roman dominating function. Section 2 defines the class \(\mathfrak F\) through efficient dominating sets—equivalently, perfect codes whose closed neighborhoods partition the graph. Section 3 defines the strong product, and the proof of Theorem 26 uses exactly that closed-neighborhood partition in a strong product.

An instance gives two Cayley factor graphs on \(\mathrm{GF}(p)^d\), each by a polynomial connection map \(F_i(t)\). The solver returns two normalized normal vectors \(a_i\). They symbolically define hyperplanes \(C_i=\{x:a_i\cdot x=0\}\), and hence the product set \(C=C_0\times C_1\). The represented Roman function is 2 on \(C\) and 0 elsewhere.

The generator samples each normal first, builds \(F_i(t)=tw+\sum_j h_j(t)u_j\) with \(a_i\cdot w=1\) and \(a_i\cdot u_j=0\), and carries the sampled normal as its certificate. Thus \(a_i\cdot F_i(t)=t\) by construction; no emitted instance is solved during generation. The checker independently evaluates all \(a_i\cdot F_i(t)\) and requires a permutation of the field. This proves every factor closed neighborhood meets \(C_i\) once, so the product neighborhood meets \(C\) once. Verification is exact and never reads `inst["answer"]`.

## Why this is Track B

This cannot honestly be Track A. The paper’s Theorems 10, 17, and 23 give direct Roman-function constructions once suitable factor witnesses are known. For this bounded hyperplane language, an exhaustive normalized-projective direction scan is also an exact algorithm: it costs \(O(d p^d)\) finite-field operations and succeeds on every generated instance.

At the tested setting \(p=29,d=5\), that scan averaged 25,019,321 counted operations and 0.832 seconds over eight seeds. A full exact count used 108,961,350 operations and 3.533 seconds. The compact route observes that all nonlinear coefficient columns span a common four-dimensional subspace, finds its one-dimensional annihilator in each factor, and uses 192 counted field operations total. Although this is a large mechanical-versus-compact gap, the oracle results show that the compact route is both visible and executable in context, so it does not support Track B hardness.

The easy regimes were deliberately separated. The `demo` field is small enough for hand calculation. Giving the normals or the nonlinear span would reveal the answer. Sparse or coordinate-aligned polynomials would make a coordinate-axis ansatz work, so shipping instances use dense random odd coefficients and randomized kernel bases.

## Worked demo

`make_instance(seed=0, n=5, dimension=2)` is genuinely hand-solvable. Its complete rendered statement is:

```text
Find a compact Roman dominating function on a strong product graph.

All arithmetic below is in the prime field GF(5); write every field element as
its canonical integer representative in the inclusive range 0,...,4.
Vectors have dimension d=2, coordinates are indexed 0,...,1,
and a dot product is reduced modulo 5.

For i=0,1, a displayed polynomial map F_i:GF(5)->GF(5)^2
defines a connection set

  S_i = {F_i(t) : t in GF(5)}.

The maps are injective, F_i(0)=0, and F_i(-t)=-F_i(t).  Define the finite
simple undirected Cayley graph G_i as follows.  Its vertices are all vectors in
GF(5)^2.  Distinct x and y are adjacent exactly when y-x belongs to
S_i without {0}.  Thus the closed neighborhood of x is x+S_i.

The strong product G_0 strong G_1 has vertex pairs (x,y).  Two distinct pairs
(x,y) and (x',y') are adjacent exactly when, in each coordinate, the entries
are equal or adjacent in the corresponding factor, and at least one coordinate
is adjacent.  Equivalently,

  N[(x,y)] = N_G0[x] x N_G1[y].

An efficient dominating set (also called a perfect code) is a vertex set C
such that every closed neighborhood contains exactly one member of C.  A Roman
dominating function assigns 0, 1, or 2 to each vertex and requires every vertex
assigned 0 to have a neighbor assigned 2.

You must give two nonzero normal vectors a_0,a_1.  They define factor
hyperplanes C_i={x : a_i dot x = 0} and the product set C=C_0 x C_1.
Your answer is valid when C is an efficient dominating set of the strong
product.  It then compactly represents the Roman function f that is 2 on C
and 0 off C, of exact weight 2*5^(2*2-2).

For an exact finite check, C_i is an efficient dominating set precisely when
the 5 values a_i dot F_i(t), as t ranges over GF(5), are all distinct
(equivalently, they are all field residues).  The checker performs this test
for both factors; it never expands the 625-vertex product.

Each normal must contain exactly 2 integers in 0,...,4.  Scalar
multiples name the same hyperplane, so use the unique projective normalization:
the first nonzero entry of each normal must be 1.  The order is factor 0 then
factor 1; vector-coordinate order matters, and no entry may be omitted.

Factor 0: F_0(t) has coordinates
  F_0,0(t) = 3*t + 1*t^3
  F_0,1(t) = 3*t + 4*t^3

Factor 1: F_1(t) has coordinates
  F_1,0(t) = 4*t + 1*t^3
  F_1,1(t) = 2*t + 4*t^3

Give your final answer inside <answer></answer> tags, as exactly one JSON object
with the single key "normals", whose value is the two arrays just described.
Example for d=2: <answer>{"normals":[[1, 0],[0, 1]]}</answer>
Output nothing else inside the tags.
```

The answer is `{"normals":[[1,1],[1,1]]}`. Direct checks give:

```python
>>> verify(inst, {"normals": [[1, 1], [1, 1]]})
(True, "ok")
>>> verify(inst, {"normals": [[1, 0], [1, 1]]})
(False, "factor 0 hyperplane is not an efficient dominating set")
```

For example, in factor 0 the nonlinear coefficient vector is `(1,4)`, whose annihilator is `(1,1)` modulo 5. A person can find both two-dimensional annihilators and check five projections on paper.

## Difficulty presets

| Preset | `n` | `p` | `d` | Symbolic candidates | Implicit product vertices | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 5 | 2 | 36 | 625 | hand-solvable illustration |
| easy | 29 | 29 | 5 | 536,616,316,681 | 420,707,233,300,201 | rejected: oracle 3/3 |
| medium | 37 | 37 | 5 | 3,710,327,340,841 | 4,808,584,372,417,849 | rejected: oracle 2/3 |
| hard | 47 | 47 | 5 | 24,857,812,749,121 | 52,599,132,235,830,049 | rejected: oracle 3/3 |

No preset held. An additional `escalate()` result with `n=94` (hence \(p=97\))
was also solved 3/3.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted answers, 24/24 transversal identities, JSON round-trip |
| G2 | pass | drop, swap, duplicate, empty, and range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose/fence; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `10/536616316681 = 1.864e-11` |
| G5 | pass | exactly 10 tested certificates; full count 108,961,350 operations / 3.533 s; 256-restart baseline 0.001 s |
| G6 | pass | five attacks each 0/8; reference scan and compact route each 8/8 |
| G7 | pass | doubled `n=58` uses `p=59`; candidate space grows to 151,937,203,290,961 while answer stays ten atoms |
| G8 | pass | 120/120 keys invariant, 120/120 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 41 answer characters, 11 estimated tokens, 10 atoms, 192 intended operations |

## Oracle loop

| Prompt | Parameters | Scored solves/attempts | Outcome |
|---|---|---:|---|
| bare | `easy`, \(p=29,d=5\) | 3/3 | defeated |
| bare | `medium`, \(p=37,d=5\) | 2/3 | defeated |
| bare | `hard`, \(p=47,d=5\) | 3/3 | defeated |
| bare | escalated, \(p=97,d=5\) | 3/3 | defeated |
| bare | escalated, \(p=191,d=5\) | 0/0 | four HTTP 403 quota errors; unscored |

## G9 arms

| Arm | Solved / scored attempts | Diagnostic conclusion |
|---|---:|---|
| bare | 3 / 3 | the unhinted tested preset was easy |
| structural hint | 0 / 0 | unavailable |
| placebo hint | 0 / 0 | unavailable |

Hinted minus placebo is undefined because neither diagnostic arm produced a
scored attempt. The bare evidence is nevertheless sufficient to reject H. The
size/effort portion passes: the tested answer is 41 characters (11 estimated
tokens), has ten atomic elements, and its intended route uses 192 exact
operations.

## Use

```python
from rejected_gen_1111_3517 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer('<answer>{"normals":[[1,1,1,1],[1,1,1,1]]}</answer>')
ok, reason = verify(inst, candidate)
```

This rejected family must not be emitted into the corpus. The snippet above is
for audit-only local experiments.

## Caveats

- This is Track B, not evidence that Roman domination or efficient domination is easy or hard on the generated distribution. The disclosed Python scan solves the declared symbolic language in seconds (0.832 seconds on average in the saved run).
- The instance is an exact implicit graph, not an expanded adjacency list. The product at shipping size has about \(5\times10^{11}\) vertices; the polynomial Cayley presentation and hyperplane witness are essential to keeping posing and checking finite.
- `P(random guess)` is uniform over pairs of normalized projective directions. It removes zero vectors and scalar duplicates, but it is not a prior over arbitrary Roman functions. The exact density applies only to the certificate language explicitly requested by the statement.
- The adversary panel tried coefficient-energy outliers, coordinate projection, linear-term and leading-term ansatzes, and 256 random restarts. It did not run SAT/ILP or exact cover on the expanded graph, which is infeasible to materialize. The strongest applicable symbolic scan is disclosed as the successful Track B reference algorithm.
- The canonical key uses projective subset-rank profiles. It is invariant under ambient invertible linear-coordinate changes, arbitrary parameter ordering (including tested scalar and nonlinear power maps), factor exchange, and compositions, but it is not a complete Cayley-graph isomorphism test and may collide on non-isomorphic configurations.
- There may be multiple valid hyperplane normals on some seeds. `verify` accepts all of them, and G5 counts them exactly at the shipping measurement seed. The recorded shipping instance had five valid directions in factor 0 and two in factor 1, hence ten valid pairs; the demo has four valid pairs.
- Most importantly, the required oracle hardness evidence failed: 11/12 bare attempts solved. The later quota exhaustion does not erase those scored results.
