# Verified free-Lie polynomial witness generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | polynomial |
| Native objects | rank-three free Lie algebra, Hall monomials, coordinate polynomial |
| Intended intuition | decomposition: a Jacobi chain followed by a cyclic character transform |
| Domain essentiality | native; no reduction |

This directory turns Kharlampovich and Myasnikov's [*Undecidability of
Equations in Free Lie Algebras*](https://arxiv.org/abs/1708.07419) into an
unlimited exact witness family. A solver receives a rank-three free Lie algebra
over a prime field, Hall terms `T_i`, a displayed basis `P_j`, and a right-hand
side `R`. It must return the coordinate polynomial whose Lie element `S`
satisfies `[S,a]=R`. Verification substitutes the coefficients, applies the
Jacobi derivation in exact Hall coordinates, and compares with `R` modulo the
prime. It never reads the planted answer.

## Why this is Track B

Section 4 fixes the left-normed adjoint notation and Hall basis. Its Lemma 6
constructs bracket preimages through the recurrence behind
`[H(p,q),a]=H(p+1,q)+H(p,q+1)`; Lemma 4 supplies Hall-basis faithfulness.
Theorem 3 e-interprets `K[t]`, and Theorem 5 uses that interpretation to prove
the unrestricted Diophantine problem undecidable for rank greater than two.
That is worst-case undecidability, not a distributional theorem for these
inverse-generated positive instances, so this module does **not** claim Track A.

The bounded problem here is linear. The disclosed reference method recovers the
Hall coefficients and runs exact Gauss–Jordan elimination over `F_p`: `O(n^3)`,
measured at **36,527 field operations and 0.0014 seconds** (median of eight
shipping seeds). A solver that notices the displayed matrix is a cyclic
character table can instead use a radix-2 inverse number-theoretic transform.
The implemented compact route takes **273 exact operations** and verifies 8/8.
That operation gap is meaningful without tools, even though either algorithm is
easy for software.

The paper's easy structure was not hidden. Section 3 explicitly realizes field
addition and multiplication by equations, and the introduction notes known
descriptions for restricted linear equations. Our fixed-span subclass is one of
those tractable situations; the paper's undecidability theorem is not used to
mislabel it hard. The original `F_65537` hard candidate passed the bare oracle
but one hinted oracle solved it, so G9(b) rejected that rung. The specification's
single permitted promotion enlarged the field at fixed 32-term answer length to
`F_786433`; both bare and hinted reruns then held 0/3.

## Worked demo (`seed=5`)

```text
FREE-LIE POLYNOMIAL WITNESS OVER A PRIME FIELD

Work in the free Lie algebra over the prime field F_17 on the three
free generators a, b, c. Field elements are represented by their unique
integer residues 0,...,16; every addition and multiplication of
coefficients is modulo 17. The Lie bracket is bilinear,
[u,u]=0, [u,v]=-[v,u], and it satisfies the Jacobi identity. All repeated
brackets are left-normed. Define

  ad_a^0(u)=u,    ad_a^(r+1)(u)=[ad_a^r(u),a],
  H(p,q)=[ad_a^p(c), ad_a^q(b)].

The Hall order is degree-first with a<b<c. Every H(p,q) used below has
p>q, so the displayed H terms are distinct Hall-basis elements. There are
n=4 displayed terms:
  T_0 = H(12,3)
  T_1 = H(13,2)
  T_2 = H(14,1)
  T_3 = H(15,0)

Define Lie polynomials P_0,...,P_3 by

  P_j = sum from i=0 to 3 of M[i,j]*T_i.

The matrix M is listed by rows; each row has exactly 4 field residues:
  row 0: 1 1 1 1
  row 1: 1 4 16 13
  row 2: 1 16 1 16
  row 3: 1 13 16 4

Also put U_r=H(12+r,4-r) for 0<=r<=4. The right-hand side R is

  R = sum from r=0 to 4 of q_r*U_r,

where q_0,...,q_4 in that order are:
  1 3 15 12 16

Find the unique coordinate polynomial

  X(z)=x_0+x_1*z+...+x_3*z^3

whose coefficients define S=sum from j=0 to 3 of x_j*P_j and make the
free-Lie identity [S,a]=R true. Your answer must contain exactly 4 terms,
one for every exponent 0,...,3, in increasing exponent order. Write a
term as exponent:coefficient. Coefficients must be canonical integer residues
in the inclusive range 0..16; exponents and coefficients are
ordinary decimal integers, and repeated exponents are not allowed.

Give your final answer inside <answer></answer> tags, as exactly 4
comma-separated exponent:coefficient terms.
Example format for n=3 only: <answer>0:2, 1:0, 2:7</answer>
Output nothing else inside the tags.
```

The witness is `<answer>0:8, 1:11, 2:16, 3:0</answer>` and verifies as
`(True, "ok")`. Changing its first coefficient from 8 to 9 gives
`(False, "Lie identity mismatch at Hall coordinate H(12,4): got 2, expected 1")`.
A person can solve this four-term demo on paper by recovering four adjacent-sum
coefficients and inverting the displayed 4-point transform.

## Difficulty presets

| Preset | Terms `n` | Field | Hall padding | Compact operations | Status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 17 | 1 | 17 | hand-solvable illustration |
| easy | 8 | 257 | 8 | 45 | oracle solved 3/3 |
| medium | 16 | 257 | 32 | 113 | oracle solved 2/3 |
| **hard** | **32** | **786433** | **257** | **273** | **ships; oracle solved 0/3** |

The superseded 32-term `F_65537` rung was rejected by G9(b), not by a local
correctness gate: its bare arm held 0/3, but the structural hint was solved 1/3.

## Mandatory gates

| Gate | Measured result | Pass |
|---|---|:---:|
| G1 planted verifies | 16/16 preset/seed instances | yes |
| G2 corruptions | 5/5 rejected with 5 distinct reasons | yes |
| G3 round trip | fenced answer with surrounding prose parsed exactly | yes |
| G4 structured guess | 0/200,000 uniform bounded polynomials | yes |
| G5 density and cost | demo: 1/83,521 exact; shipping: 0/200,000; Gaussian 36,527 ops | yes |
| G6 attacks | outlier, diagonal greedy, 256 restarts, unmixed ansatz: each 0/8 | yes |
| G7 scales | 64-term build verifies; fixed-length field escalation verifies | yes |
| G8 canonical key | 80/80 invariant real transforms; 20/20 unrelated distinct | yes |
| G9 no-tool | 340 chars, 85 tokens, 64 atoms, 273 operations; hinted 0/3 | yes |

## Oracle hardening loop

All calls used medium reasoning effort. `Solved` means the returned polynomial
passed exact verification.

| Preset | Seed | Oracle | Solved | Result |
|---|---:|---|:---:|---|
| easy | 1116306214 | GPT-5.6 Terra | yes | `ok` |
| easy | 1352312834 | Claude Sonnet 5 | yes | `ok` |
| easy | 158742488 | Gemini 3.1 Pro Preview | yes | `ok` |
| medium | 656461779 | Grok 4.6 | yes | `ok` |
| medium | 1794437511 | Gemini 3.1 Pro Preview | no | parsed, wrong Hall coefficient |
| medium | 1460033195 | GPT-5.6 Terra | yes | `ok` |
| hard | 836932095 | Grok 4.6 | no | parsed, wrong Hall coefficient |
| hard | 1854956181 | GPT-5.6 Terra | no | parsed, wrong Hall coefficient |
| hard | 1573814403 | Claude Sonnet 5 | no | exhausted 32k reasoning budget, no answer |

The script verdict is `hardened` at the named `hard` preset after two ladder
escalations. Full replies and timings are in `llm_loop_transcript.jsonl`.

## G9 arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is **0.0**. At this sample size the structural sentence
bought the oracle pool no measured advantage, so the result does not show that
the claimed decomposition intuition helped. It does show that merely naming the
character-table invariant was insufficient to make the promoted instances
solvable. The answer is 340 characters (about 85 tokens), contains 64 atomic
integers in its polynomial representation, and the intended route uses 273 exact
operations.

## Use

```python
from gen_1708_07419 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=1234, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>0:1, 1:2</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 fresh verified instances with:

```bash
bash scripts/emit.sh 1708.07419 20 hard
```

The module is standard-library-only; `gvlib` is not needed for prime-field
arithmetic or the sparse Hall-coordinate check.

## Caveats

- This is intentionally not computational hardness: software solves every
  shipping instance in milliseconds. It measures no-tool recognition and exact
  execution of a compressed transform.
- The general undecidability theorem does not transfer distributional hardness
  to this linear positive subclass. Calling this Track A would be false.
- G4 samples uniformly from the full declared language `F_p^32`, incorporating
  all format and field constraints. The solution is unique, so the true uniform
  probability is `p^-32`; 0/200,000 is a density observation, not a runtime
  lower bound for informed algorithms.
- The compact inverse NTT is implemented and succeeds 8/8. It is reported as the
  intended route, not hidden among failing attacks. The failing panel did not
  try alternative FFT factorizations, computer algebra systems, or error-corrected
  partial transforms.
- In each final three-call arm, Claude used its entire 32k reasoning budget and
  emitted no answer. Those are weaker failures than the other two parsed,
  incorrect polynomials; the transcripts preserve that distinction.
- The character-table construction may be immediately obvious to a specialist,
  and the structural hint explicitly names it. Difficulty comes from accurately
  executing 273 modular operations without tools, not from obscurity alone.
- The canonical key exactly handles the declared row, column, and generator-name
  relabellings. It does not attempt to quotient by every automorphism of the free
  Lie algebra or by arbitrary invertible changes of the displayed span.
