# Rank-one isomorphisms of constructed Yang--Baxter solutions

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | matrix certificate (normalized rank-one factors) |
| Intended intuition | invariant — recognize two rank-one perturbations |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Jedlička and Pilitowska, [*Indecomposable involutive solutions of the Yang--Baxter equation of multipermutation level 2 with non-abelian permutation group*](https://arxiv.org/abs/2207.02944). Theorem 4.1 constructs a solution \(\mathcal S(G\times\mathbb Z_m,\mathbf c)\) from a spanning sequence in an abelian group. Here \(G=\operatorname{GF}(p)^d\). An instance supplies two sequences \(c,c'\), hence two native Yang--Baxter solutions, and asks for normalized vectors `u,v` describing

`g(x) = x + u (v dot x)`.

Theorem 4.7 says that this `g` induces a solution isomorphism exactly when `g(c[i])=c'[i]` for every index. The generator samples the invertible map first and applies it, so it never solves an instance it generated. `verify` checks the two factors, invertibility, both spanning conditions, the non-abelian condition from Proposition 4.4, every sequence equation, and every symbolic left-action intertwining equation. It never reads `inst["answer"]`.

## Trust and Track B hardness

This is not a Track A claim. Theorem 4.7 makes the vector-space case efficiently solvable: normalize a nonzero column of `c'-c` to obtain `u`, then solve a dense modular linear system for `v`. Exact Gauss--Jordan elimination is \(O(d^3)\); at the declared `easy` shipping preset it solved 8/8, averaging 4,984 field operations, 17 inversions, and 0.010244 seconds in the final, heavily contended host run (an earlier run measured 0.000374 seconds).

The compact route observes more. The unknown map is `I+u v^T`, and the first `d` source vectors are the columns of `B=I+a b^T`. The displacement columns reveal `u` and the scalar vector `s`; Sherman--Morrison gives `v = s - b (a dot s)/(1+a dot b)`. The audited upper bound is 195 exact field operations at `easy`, versus 4,984 for elimination. Proposition 4.4 is the other easy regime: the permutation group is abelian exactly when `c[i]=i*c[1]`; a spanning sequence in dimension at least two cannot have that form.

All local gates pass, and the repository's current script-owned two-vendor oracle pool hardened `easy`: three completed calls from OpenAI and Google all returned parseable but invalid witnesses. This is valid evidence for the current harness, whose checked-in pool has two vendors despite the older task text describing four. The structural-hint and placebo diagnostics could not run afterward because the OpenRouter key hit its total limit; their 403 errors are not counted as model failures.

## Worked demo

`make_instance(seed=0, n=2, p=7, extra=1)` renders:

```text
Recover an isomorphism between two constructed Yang--Baxter solutions.

All vector coordinates and all additions, subtractions, products, and dot
products below are in the prime field GF(p), where p=7.  V=GF(p)^2 uses
the displayed coordinate order.  Sequence indices are residues modulo m=4;
for example c[-1] means c[m-1].

For any sequence c[0],...,c[m-1] in V with c[0]=0 that spans V, define maps
on X=V x Z_m by

  sigma_(a,i)(b,j) = (b + c[i-j-1] - c[-j-1], j+1),
  tau_(a,i)(b,j)   = (b - c[i-j+1] + c[-j], j-1),

where the second coordinate and every sequence subscript are modulo m.  With
the convention r(x,y)=(sigma_x(y),tau_y(x)), these maps define an involutive,
nondegenerate,
indecomposable set-theoretic solution of the Yang--Baxter equation of
multipermutation level 2; that equation is the braid identity
(id x r)(r x id)(id x r)=(r x id)(id x r)(r x id).  The two displayed
sequences c and c' each span V and therefore define two such solutions.

A linear map g:V->V that sends every c[i] to c'[i] gives the solution
isomorphism Phi(a,i)=(g(a),i), meaning
Phi(sigma_x(y))=sigma'_Phi(x)(Phi(y)) for every x,y.  It is promised that the
required map has the rank-one form

  g(x) = x + u * (v dot x).

Find u and v.  They are made unique by requiring u to be nonzero and its first
nonzero coordinate (scanning from coordinate 1 to coordinate 2) to equal 1.
Also v must be nonzero and 1+v dot u must be nonzero, which makes g invertible.
All answer entries are ordinary decimal integers in the inclusive range
0,...,p-1.  Coordinates and sequence indices in this statement are 1-indexed
and 0-indexed respectively.  Coordinate order matters, repeated field values
are allowed, and each vector must contain exactly 2 entries.

Source sequence c (indices 0 through 3):
  0: 0 0
  1: 2 0
  2: 3 1
  3: 3 3

Target sequence c' (indices 0 through 3):
  0: 0 0
  1: 1 1
  2: 3 1
  3: 6 0

Return exactly one JSON object with keys "u" and "v"; each value must be a
JSON list of exactly 2 decimal integers in coordinate order.

Give your final answer inside <answer></answer> tags, as the JSON object just specified.
Example: <answer>{"u":[1,0],"v":[2,3]}</answer>
Output nothing else inside the tags.
```

The answer is `{"u":[1,6],"v":[3,5]}`. A person can solve this demo: `c'[1]-c[1]=(6,1)` normalizes to `u=(1,6)`; the first two dot-product equations then give `v=(3,5)`.

```python
>>> verify(inst, {"u": [1, 6], "v": [3, 5]})
(True, "ok")
>>> verify(inst, {"u": [1], "v": [3, 5]})
(False, "u must have exactly 2 entries")
```

## Difficulty presets

| Preset | `d` | `p` | Extra checks | Sequence length | Search bits | Compact ops | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 2 | 7 | 1 | 4 | 2 | 27 | hand-solvable illustration |
| easy | 16 | 65,537 | 12 | 29 | 240 | 195 | **ships; hardened 0/3** |
| medium | 20 | 1,000,003 | 24 | 45 | 378 | 243 | available; not reached |
| hard | 24 | 2,147,483,647 | 40 | 65 | 712 | 291 | available; not reached |

No preset was rejected. After `hard`, `escalate` raises only coefficient entropy, first to a 61-bit prime and then to a 127-bit prime while keeping 48 answer atoms and 291 operations. At the latter level the worst-case answer is 1,933 characters; the next standard Mersenne-prime step would exceed the output cap, so `escalate` returns `cap_bound`.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; 76,832 complete demo involutivity pairs and 20,000 braid triples checked |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON round-trips through prose/fences; garbage returns `None` |
| G4 | pass | 0/200,000 informed guesses; exact probability \(1/(1.767\times10^{72})\approx5.66\times10^{-73}\) |
| G5 | pass | unique shipping witness; demo brute force count 1; 2,048 restarts cost 0.532184 s on the contended host |
| G6 | pass | five attacks each 0/8; reference elimination and compact route each 8/8 |
| G7 | pass | doubled dimension 32 built in 0.001362 s and verified; search prior grew 240 to 496 bits |
| G8 | pass | 160/160 key invariances, 160/160 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 205 worst-case answer chars, about 52 tokens, 32 atoms, 195 intended operations |

## Oracle loop

The bare transcript contains three completed HTTP 200 calls. Every reply was parsed; exact verification rejected each witness, so these are genuine solver failures rather than contract failures. The harness recorded `verdict: hardened` with `shipping_params={"n":16,"p":65537,"extra":12}`.

| Preset | Seed | Model | Result |
|---|---:|---|---|
| easy | 517,343,957 | Google Gemini 3.8 Flash | failed: parsed factors violate `g(c[1])=c'[1]` |
| easy | 1,468,062,675 | OpenAI GPT-5.6 Terra | failed: parsed `v` is zero |
| easy | 265,210,175 | Google Gemini 3.8 Flash | failed: parsed `v` is zero |

## G9 arms

| Arm | Solved / valid attempts | Error calls | Verdict |
|---|---:|---:|---|
| bare | 0 / 3 | 0 | hardened |
| structural hint | 0 / 0 | 4 | blocked |
| placebo hint | 0 / 0 | 4 | blocked |

`hinted - placebo` is undefined because neither arm obtained a valid attempt; the report stores `0.0` only as the zero-denominator fallback. No conclusion about structural help is justified. At `easy`, the measured answer is 197 characters (about 50 tokens); the format worst case is 205 characters (about 52 tokens), with 32 atomic entries and at most 195 exact operations.

## Use

```python
from gen_2207_02944 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer('<answer>{"u":[1],"v":[1]}</answer>')
ok, reason = verify(inst, candidate)
```

To reproduce the hardening evidence, rerun the bare loop here. After refreshing the OpenRouter quota, rerun both isolated G9 copies as specified in the task. Emit from the repository root with:

```bash
python3 ../../scripts/harden.py gen_2207_02944.py
bash scripts/emit.sh 2207.02944 20 easy
```

## Caveats

- A computer solves these instances almost instantly by modular elimination. This family measures no-tool recognition and execution, not complexity-theoretic Yang--Baxter hardness.
- The checked-in harness used only its current OpenAI/Google two-vendor pool, not the four-vendor pool described in the older task text. The bare level hardened, but the required hinted/placebo comparison remains missing because the key exhausted its total limit.
- The rank-one source frame is benchmark-side structure, not a statement about every sequence in Theorem 4.1.
- `random_candidate` already fixes the normalized `u` visible in `c'[1]-c[1]` and enforces the first dot-product equation and invertibility. The resulting probability addresses uninformed guesses inside that stronger prior; it says nothing about a solver that notices the second rank-one invariant.
- Extra sequence vectors are consistency checks and may expose bad guesses, but they do not materially raise elimination cost after a basis has been selected. Escalation therefore does not claim they are a hardness axis.
- The outlier, diagonal, identity-frame, one-equation sparse, and 256-restart attacks were tried. General CAS elimination and optimized low-rank factorization were not treated as failing attacks because Track B expects them to succeed; Gauss--Jordan is reported separately as the reference algorithm.
- `canonical_key` is exact under simultaneous finite-field basis changes and swapping source with target. It does not attempt canonicalization under arbitrary presentations outside this generated sequence format.
- The module is standard-library-only; `gvlib` is unnecessary because all arithmetic is over a prime field.
