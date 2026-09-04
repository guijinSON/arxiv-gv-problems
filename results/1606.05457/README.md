# Verified generator for arXiv:1606.05457

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite discrete |
| Computational core | exact linear algebra |
| Certificate | matrix certificate over `Z/p^n Z` |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This module instantiates the two-sided decomposition used by Climent and
López-Ramos in [*Public Key Protocols over the Ring
E_p(m)*](https://arxiv.org/abs/1606.05457). The solver receives three elements
`M`, `X`, and `P` of the paper's noncommutative ring `E_p^(n)`. It must return an
`n x n` scalar matrix `Lambda` satisfying the exact ring identity

`P = sum_(i,j=0)^(n-1) Lambda[i,j] M^i X M^j`.

The checker expands this identity with the paper's row-dependent moduli. It uses
no floating point, search, stored answer, or external package, and accepts every
valid coefficient matrix rather than only the planted one.

## Why it can be trusted

Generation is inverse. It samples dense coefficient vectors `u,v`, forms
`A1=sum u_i M^i` and `A2=sum v_j M^j`, publishes `P=A1 X A2`, and retains
`Lambda[i,j]=u_i v_j`. Thus the certificate exists before the public target is
built. This is exactly the expansion behind Section 4, equation (6), Protocol 1,
and the DH decomposition problem; no graph or finite-field surrogate replaces
the native ring matrices.

Section 2 fixes `E_p^(n)`, its row-wise arithmetic, and its center. Section 3,
Theorem 3 and Corollary 1 identify an easy central-SAP ratio test, while Section
4 discusses attacks that use invertible elements. More decisively, Khathuria,
Micheli, and Weger later proved in [Theorem 15 and Algorithm
1](https://arxiv.org/abs/1810.02964) that the decomposition protocols are broken
by coefficient matching: solve an `n^2 x n^2` system over `Z/p^n Z` in
`O(n^6)` ring operations. The same paper reports 23.1 days for the originally
suggested `p=2,n=128` parameters. Consequently this family makes no Track A or
cryptographic-security claim.

The Track B gap is measured at the shipping preset. The construction-independent
Smith/linearization algorithm succeeds 8/8 and costs a median 823,826 counted
exact operations (0.05--0.09 s across local runs). The planted distribution makes `M mod p`
diagonal with a shuffled grid of all `n`-th roots of unity. Modulo `p`, entrywise
ratios expose a rank-one table of evaluations of `u` and `v`; two inverse NTTs
and one outer product recover a valid `Lambda` in 244 operations. That change of
variables is the intended insight.

## Worked demo

The `demo` preset with seed 0 is hand-solvable. Its complete rendered instance is:

~~~text
Find an exact two-sided polynomial-decomposition certificate in E_p^(n).

Here n=2, p=3 is prime, and q=p^n=9. Indices i,j,k start at 0.

Definition of E_p^(n): an element is an n by n integer matrix A. Entry A[i][j]
is represented by its unique integer in 0 <= A[i][j] < p^(i+1). If i>j it
must additionally be divisible by p^(i-j). Addition reduces every entry in row
i modulo p^(i+1). Multiplication is

  (A B)[i][j] = sum(k=0..n-1, A[i][k]*B[k][j]) mod p^(i+1).

M^0 is the identity matrix and higher powers use this multiplication. An integer
lambda acts as the central scalar whose multiplication simply multiplies every
entry and applies that row's modulus.

The public primitive n-th root omega=2 is supplied as instance data;
it satisfies omega^n = 1 (mod p), with no smaller positive power equal to 1.

Public matrices:
M = [
  [1,0]
  [3,8]
]

X = [
  [1,2]
  [3,7]
]

P = [
  [0,1]
  [0,6]
]

Output one n by n coefficient matrix Lambda in row-major JSON syntax. Every
lambda[i][j] must be an integer in the inclusive/exclusive range 0 <= value < q.
It is accepted exactly when

  P = sum(i=0..n-1, j=0..n-1, lambda[i][j] * M^i * X * M^j)

in E_p^(n). Order matters, repetitions are not a separate notion, and any
Lambda satisfying the identity is valid; it need not equal a particular planted
certificate.

Give your final answer inside <answer></answer> tags, as a JSON matrix with
exactly n rows and n base-10 integer entries per row.
Format example for n=2: <answer>[[1,2],[3,4]]</answer>
Output nothing else inside the tags.
~~~

The answer is `<answer>[[2,1],[2,1]]</answer>`.

~~~python
>>> verify(demo, [[2, 1], [2, 1]])
(True, 'ok')
>>> verify(demo, [[3, 1], [2, 1]])
(False, 'coefficient identity does not equal the public target P')
~~~

A person can enumerate the 6,561 demo matrices or expand the four basis terms on
paper. The compact roots-of-unity route is also only a two-point transform.

## Difficulty presets

| Preset | `n` | Prime size | Certificate entries | Generic system | Status |
|---|---:|---:|---:|---:|---|
| demo | 2 | 2 bits | 4 | 4 unknowns | hand-scale illustration |
| easy | 8 | 17 bits | 64 | 64 unknowns | **ships; bare and hinted hardened** |
| medium | 8 | 23 bits | 64 | 64 unknowns | available; larger coefficient entropy |
| hard | 8 | 29 bits | 64 | 64 unknowns | available; larger coefficient entropy |

`escalate()` continues increasing coefficient entropy at fixed certificate
length and returns `cap_bound` before the 2,000-character answer limit.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted and 12/12 independently reconstructed certificates verify |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structured-language guesses; one exact anchor gives probability at most `2.938e-39` |
| G5 | pass | shipping exact log-density `-982.563`; demo has 27 valid certificates; reference median 823,826 operations |
| G6 | pass | four non-reference attacks each 0/8; disclosed reference algorithm 8/8 |
| G7 | pass | doubled `n=16` instance builds and verifies; generic elimination grows by 64x |
| G8 | pass | 100/100 symmetry and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | hinted 0/3; 629 chars, 158 estimated tokens, 64 atoms; compact route 244 operations |

The four failing attacks were best single-orbit-term selection, greedy diagonal
coefficient matching, 256 structure-aware random restarts, and an in-context
affine-factor ansatz. Plants and random candidates use the same coefficient
bounds; higher `p`-adic digits in the public matrices prevent raw-entry outliers.

## Oracle loop

| Model | Seed | Solved | Exact outcome |
|---|---:|---|---|
| Google Gemini 3.1 Pro Preview | 2032755927 | no | parsed matrix failed the coefficient identity |
| xAI Grok 4.6 | 1729013508 | no | parsed matrix failed the coefficient identity |
| Anthropic Claude Sonnet 5 | 1837740891 | no | empty length-limited reply after 32,000 completion tokens |

The script-owned bare verdict is **hardened** with zero escalations. Full replies,
timings, and HTTP metadata are in `llm_loop_transcript.jsonl`.

## G9 arms

| Arm | Solved / attempts | Outcome |
|---|---:|---|
| bare | 0/3 | two parsed wrong matrices; one length-limited empty reply |
| structural hint | 0/3 | three parsed wrong matrices; hardened |
| placebo hint | 0/3 | three parsed wrong matrices |

Hinted minus placebo is **0.0**. In this small diagnostic the correct structural
hint bought no solved instances, so it gives no evidence that naming the claimed
change of variables was sufficient; the remaining exact NTT arithmetic still
defeated the sampled models. The shipping answer is 629 characters (about 158
tokens) and 64 atomic entries; the measured worst case is 721 characters (181
tokens). The intended route uses 244 exact operations.

## Use

From this directory:

~~~python
from gen_1606_05457 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
candidate = parse_answer("<answer>[[0,0,0,0,0,0,0,0]]</answer>")
ok, reason = verify(inst, candidate)
~~~

From the repository root, emit verified samples with:

~~~bash
bash scripts/emit.sh 1606.05457 20 easy
~~~

The module is standard-library-only. It attempts the repository `gvlib` import
as required, but the mixed-modulus `E_p^(n)` arithmetic is small and implemented
locally, so absence of `gvlib` does not change behavior.

## Caveats

- The reference algorithm is public, successful, and fast in wall-clock time.
  This family is a no-tool compression benchmark, not a hard cryptographic
  distribution and not evidence that the 2016 protocols are secure.
- `P(random guess)` is uniform over exactly the stated `q^(n^2)` bounded matrix
  language. It quantifies blind guessing, not a solver using the mod-`p`
  rank-one/NTT prior; the latter succeeds deterministically.
- The construction deliberately specializes `M mod p` to a roots-of-unity grid
  and the secret coefficients to residues below `p`. Removing either promise
  destroys the 244-operation shortcut; exposing both in a machine-readable
  normal form would make the task easier.
- G6 uses the paper-specific Smith/linearization attack, but not Sage, Magma, an
  optimized NTT library, Gröbner methods, or lattice reduction. The successful
  reference algorithm already establishes tool-equipped tractability.
- The canonical key is complete only for the declared central-unit scaling and
  redundant primitive-root inversion symmetries. It does not attempt general
  isomorphism of mixed-modulus matrix-ring instances; rare invariant-equivalent
  instances outside those transformations may receive different keys.
- The oracle sample is only three models per arm. The identical 0/3 rates do not
  prove the hint is useless or isolate arithmetic from recognition failures.
