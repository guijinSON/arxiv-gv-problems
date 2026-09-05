# Fourier-orbit chain points in LP projection vertices

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | one-row matrix of normalized homogeneous coordinates |
| Intended intuition | invariant — root-of-unity power sums in a Fourier eigenbasis |
| Domain essentiality | native; no reduction |

This is a generator for Zanella and Zullo, [*Vertex properties of maximum scattered linear sets of \(PG(1,q^n)\)*](https://arxiv.org/abs/1906.05611). The solver receives a codimension-two projection vertex \(\Gamma\subset PG(d-1,q^d)\), the diagonal form of its Frobenius collineation, and two homogeneous equations. It must return the unique projective point whose first \(d-3\) Frobenius conjugates are independent points of \(\Gamma\). Verification uses only substitution, coordinatewise Frobenius action, normalization, and exact row rank modulo the prime \(q\).

All local construction and verification gates pass. The script-owned bare hardening loop rejected `easy` after 2/3 solvers found a witness, then held `medium` at 0/3; `medium` is therefore the shipping preset. The separate G9 diagnostic is also complete.

## Why this is Track B

Section 1 fixes the canonical subgeometry and Frobenius cycle. Theorem 2.3 defines the intersection number and produces the orbit-chain point; Theorems 3.1–3.2 specialize it to LP-type vertices. The displayed construction before Theorem 3.2 gives the native vertex \(x_0=0,\ x_{d-1}+\delta x_1=0\). For odd \(d\), Lemma 4.1 identifies the necessary easy boundary: the associated LP linear set is scattered exactly when \(N(\delta)\ne1\), which generation enforces.

Generation applies the finite-field Fourier matrix to that displayed vertex and carries its known chain point \(e_2\) through the inverse coordinate change. It never solves the generated equations. In the new coordinates the Frobenius multipliers \(\lambda_j\) are all \(d\)-th roots of unity and the carried point is \(p_j=\lambda_j^2\). Their nonconstant power sums vanish, which proves the orbit conditions.

An efficient algorithm is explicit and is why this is not Track A: stack the \(2(d-3)\) orbit-shifted equations and compute their one-dimensional nullspace by modular RREF. At shipping \(q=3299,d=97\), that reference algorithm solved 8/8 instances, averaging **1,505,250 field operations and 0.099 s** in the final self-test; repeated final runs ranged from 0.05 to 0.11 s under varying machine load. Its general complexity is \(O(d^3)\). Recognizing the Fourier invariant reduces the intended route to 97 coordinate squarings plus at most 12 symbolic checks, **109 exact operations**. Small \(d\), or access to any linear-algebra tool, makes the problem easy.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders the following hand-scale instance (the standard output-contract paragraph is included):

```text
Orbit-chain point in a finite projective vertex

Let q=29, a prime, and d=7.  Let K=GF(q^d).  We use homogeneous
coordinates [v_0:...:v_{d-1}] for PG(d-1,K).  In this instance all displayed
coefficients lie in the distinguished subfield GF(q), represented by the
integers 0,...,q-1; all arithmetic below is therefore exact arithmetic modulo q,
and you do not need to construct K.

The coordinates below are a Fourier eigenbasis for the Frobenius cycle.  For a
coordinate row v over GF(q), the Frobenius collineation sigma acts by
  sigma(v_0,...,v_{d-1})=(lambda_0*v_0,...,lambda_{d-1}*v_{d-1}),
where multiplication is modulo q and the multipliers lambda_j are
  1 16 24 7 25 23 20
in coordinate order j=0,...,d-1.  Superscript sigma^j means j repeated
applications of this coordinatewise map.  On arbitrary K-coordinate rows the
same formula also raises every v_j to its q-th power; answers here are required
over GF(q), where that extra operation is the identity.

The projective subspace Gamma has codimension two and consists of all rows x
whose dot product modulo q with each of the following coefficient rows is zero:
  E1: 1 1 1 1 1 1 1
  E2: 15 6 27 9 7 11 12

The LP parameter is delta=14; its norm to GF(q) is
delta^d=12 (mod q), which is not 1.  You are promised that
Gamma is a projection vertex of intersection number two in the sense encoded by
the conditions below.

Find a projective point P represented by one row p=(p_0,...,p_{d-1}) over
GF(q) such that:
  1. P, P^sigma, ..., P^sigma^(d-4) all lie in Gamma;
  2. those d-3 coordinate rows are linearly independent over GF(q); and
  3. P^sigma^(d-1) does not lie in Gamma.

The answer row must have exactly d=7 integer entries in 0,...,28, must
be nonzero, and must use the unique homogeneous normalization in which its first
nonzero entry is 1.  Return a JSON object containing a one-row matrix.

Give your final answer inside <answer></answer> tags, as JSON of the exact form
{"point":[[p_0,p_1,...,p_{d-1}]]}.
Example of the required shape: <answer>{"point":[[1,0,0,0,0,0,0]]}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"point":[[1,24,25,20,16,7,23]]}</answer>`. `verify` returns `(True, "ok")`. Replacing the last coordinate by 24 returns `(False, "orbit point sigma^0 violates equation E1")`. A person can solve this demo on paper by squaring the seven displayed multipliers modulo 29.

## Difficulty presets

Here `n` sets the lower target \(q\ge2^n\); the generator chooses the first prime \(q\equiv1\pmod d\) above it. `degree` is the paper's extension parameter \(d\). The evaluated rungs keep the 97-coordinate witness fixed while increasing field size.

| preset | `n` | `d` | resulting `q` | status |
|---|---:|---:|---:|---|
| demo | 2 | 7 | 29 | hand-scale; skipped by hardener |
| easy | 7 | 97 | 389 | rejected: bare oracle solved 2/3 |
| medium | 11 | 97 | 3299 | **ships: bare oracle solved 0/3** |
| hard | 15 | 97 | 33563 | available but not needed |

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; 12/12 Fourier-construction identities and JSON round-trips pass |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged prose/fence round-trip succeeds; garbage returns `None` |
| G4 | 0/200,000 hits from uniform normalized projective points already satisfying both equations of \(\Gamma\) |
| G5 | shipping density 0/200,000; generic RREF 1,505,308 operations and 0.069 s on the recorded seed |
| G6 | four attacks each 0/8; reference RREF 8/8 as expected, mean 1,505,250 operations and 0.099 s |
| G7 | doubling `n` from 11 to 22 gives \(q=4,194,863\), keeps 97 answer atoms, and verifies |
| G8 | 140/140 coordinate, equation-basis, generator-reversal, and composed relabellings preserve the key and carried witness; 20/20 unrelated seeds have distinct keys |
| G9(c) | 460 characters / 115 estimated tokens / 97 atoms; 109 intended operations |

## Oracle loop and G9 diagnostic

The bare hardener used two vendors at medium reasoning effort. A returned malformed or absent witness counts as a failure only when the reply contains no parseable final answer; the transcript shows no visible unparsed witness.

| preset | seed | model | solved | reason |
|---|---:|---|---:|---|
| easy | 88121362 | GPT-5.6 Terra | no | parsed point violates E2 |
| easy | 1011181435 | Gemini 3.8 Flash | yes | verified |
| easy | 2145504350 | Gemini 3.8 Flash | yes | verified |
| medium | 612066416 | Gemini 3.8 Flash | no | parsed point violates E1 |
| medium | 688410706 | GPT-5.6 Terra | no | parsed point violates E1 |
| medium | 737291593 | Gemini 3.8 Flash | no | reasoning ended without an answer |

| G9 arm | solved/attempts | conclusion |
|---|---:|---|
| bare | 0/3 | shipping level held |
| structural hint | 1/3 | one solver used the named invariant |
| placebo hint | 2/3 | generic prompt perturbation did at least as well |

The observed `hinted - placebo` rate is **-1/3**. With only three attempts per arm, this does not establish that the hint helps; it suggests solver/seed variance dominates this diagnostic. The structural hint still names only the root-of-unity invariant, not the square-coordinate witness or a procedure. The shipping answer is 460 characters (115 estimated tokens), with 97 atomic elements and a 109-operation intended route.

## Use

```python
from gen_1906_05611 import (
    DIFFICULTY, SHIPPING_DIFFICULTY, make_instance, render, verify,
)

inst = make_instance(seed=42, **DIFFICULTY[SHIPPING_DIFFICULTY])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

Emit corpus instances from the repository root with:

```bash
bash scripts/emit.sh 1906.05611 20
```

## Caveats

- Modular elimination solves this family efficiently with tools; only the no-tool compression gap is claimed.
- The generator samples Fourier transforms of the paper's displayed LP vertices with \(\delta\in GF(q)\), not arbitrary vertices over \(GF(q^d)\). It also chooses \(q\equiv1\pmod d\) so the Fourier eigenbasis is defined over the base field.
- The 0/200,000 estimate uses the exact declared prior—uniform projective points already in \(\Gamma\). It establishes resistance to uninformed guessing under that prior, not against the root-of-unity insight.
- The failing panel tests coordinate-support outliers, a sparse three-coordinate nullspace, 256 structure-aware random restarts, and constant/axis ansatzes. The root-of-unity power-sum method is intentionally the successful reference insight; no claim is made against all structured symbolic attacks.
- `canonical_key` removes coordinate/eigenvalue permutations and equation-basis changes and identifies \(\delta\) with \(\delta^{-1}\). Full projective-semilinear equivalence classification is not attempted, so the key may over-distinguish further equivalent vertices.
- The G9 placebo arm solved 2/3 while the structural arm solved 1/3, so this small diagnostic does not isolate the claimed invariant as the causal source of improvement. The bare 0/3 hardening result establishes the required no-tool difficulty claim, not a general complexity claim.
