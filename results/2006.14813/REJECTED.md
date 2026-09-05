# Rejected at STEP 0: the native certificates have no defensible hardness track

Paper: YG Liang, Sergio Da Silva, and Yang Zhang,
[*The Tensor Rank Problem over the Quaternions*](https://arxiv.org/abs/2006.14813)
(arXiv:2006.14813v2).

## Decision

No generator is shipped. I read the complete 24-page paper and its LaTeX
source. The natural quaternion decomposition family clears **G** and **V**, but
it fails **H under both Track A and Track B**. This is a STEP-0 rejection, so
there is intentionally no `gen_2006_14813.py`, self-test report, README, or
oracle transcript.

| requirement | result | reason |
|---|---:|---|
| G -- generatable | pass | Sample simple quaternion tensors first and sum them, retaining their factors. In the paper's square full-slice regime, Lemmas 1.6--1.7 can also certify minimal rank by construction. |
| V -- verifiable | pass | Multiply the proposed quaternion factors in the stated left-to-right order, sum them, and compare all four rational components of every tensor entry exactly. |
| H -- Track A | **fail** | The paper gives no worst-case, average-case, or planted-distribution hardness theorem. Its complete results concern only dimensions 2 and 3, and its most direct native family is solved by Proposition 2.2's explicit constant-size formula. |
| H -- Track B | **fail** | At the largest plausible under-cap coefficient setting, the mechanical formula and the compact route are the same 8 quaternion operations (142 counted scalar exact operations): there is no compression gap. |

The witness is not the problem. A three-term decomposition is a finite native
algebraic object and is cheap to check. The disqualifying fact is that the
paper's certificate-producing procedure is already the shortest evident route
to that witness.

## Exact paper-native problem

Section 1 works with arrays in
`H^(n1) tensor_H H^(n2) tensor_H H^(n3)`, where `H` is the real quaternion
algebra. A simple 3-tensor has entries

`T[a,b,c] = u[a] * v[b] * w[c]`,

with quaternion multiplication performed in that order. Tensor rank is the
minimum number of nonzero simple tensors whose sum is `T` (Definitions 1.1 and
1.3). The noncommutativity is load-bearing: Section 1 permits quaternionic row
operations only by left multiplication, column operations only by right
multiplication, and unrestricted frontal-slice operations only over the real
center.

The paper's actual results are upper bounds in a finite list of tiny shapes:

- Proposition 2.2 gives an explicit three-simple-tensor decomposition for an
  eligible `2 x 2 x 2` tensor; Theorem 2.3 extends the rank-at-most-three result
  to every tensor of that shape by rank-preserving operations.
- Theorems 3.3 and 3.4 prove rank at most three in the `2 x 2 x 3`,
  `3 x 2 x 2`, and `2 x 3 x 2` quaternion cases.
- Theorems 4.2 and 4.3 give rank at most four in the remaining shapes with one
  dimension 2 and two dimensions 3.
- Theorem 5.2 gives rank at most six for `3 x 3 x 3` tensors.
- Lemma 1.6 identifies a length-`r` decomposition with simultaneous
  factorizations `A_k = P D_k Q`; Lemma 1.7 specializes the square,
  nonsingular-first-slice case to simultaneous diagonalization.

These are decomposition and classification results, not computational
hardness results. The introduction in fact says that the goal is to provide
explicit criteria that can easily be checked by a computer program.

## Certificate-production test and measured costs

The strongest honest native candidate is: give a `2 x 2 x 2` tensor with
`A11 != 0` and `B11 != 0`, and ask for three simple quaternion tensors summing
to it. Proposition 2.2 computes the only nontrivial values as

```text
u  = inverse(A11) * A12
v  = inverse(B11) * B12
da = A22 - A21 * u
db = B22 - B21 * v
```

The three factors are then copied directly from `A11`, `A21`, `B11`, `B21`,
`u`, `v`, `da`, and `db`, together with zero and one coordinates.

I measured this exact formula on 10,000 random instances whose input quaternion
components are signed 48-bit integers. This coefficient height is a plausible
maximum preset: over 100 fixed seeds, compact JSON encodings of the three
factor triples ranged from 1,672 to 1,727 characters, already close to the
2,000-character answer cap. The run took **0.872459 seconds total**, or
**87.246 microseconds per instance**, using exact `fractions.Fraction`
arithmetic in CPython.

The operation accounting is:

| operation | count | scalar exact operations per quaternion operation | subtotal |
|---|---:|---:|---:|
| quaternion inverse | 2 | 11 (4 squares, 3 additions, 4 divisions; sign copies excluded) | 22 |
| quaternion multiply | 4 | 28 (16 multiplications, 12 additions/subtractions) | 112 |
| quaternion subtract | 2 | 4 | 8 |
| **total** | **8 quaternion operations** |  | **142 scalar exact operations** |

The **mechanical cost** is therefore 8 quaternion operations / 142 scalar
exact operations. The **compact route** is to notice Proposition 2.2's two
Schur-complement-like residuals and perform the same 8 quaternion operations /
142 scalar exact operations. The comparison is **142 versus 142**, ratio 1.
Both are by-hand scale under the task's 300-operation cap; there is nothing to
discover that compresses a large computation.

Exact verification is also fixed-size. Expanding the three factor triples and
comparing the eight quaternion entries requires only a constant number of
quaternion multiplications and additions. Thus V passes, but checker cost does
not manufacture solver hardness.

## Why the prior-triage inverse construction does not rescue Track A

The proposed construction -- sample random simple tensors and sum them -- is a
valid inverse generator. It knows a decomposition without solving its output,
and exact expansion verifies any candidate decomposition. It does **not** know
that its planted distribution is hard.

No theorem in this paper supplies distributional hardness for recovering those
random factors, or even a complexity classification for growing dimensions.
The paper's stated parameter regime is `2 <= n_i <= 3`. Worst-case folklore
about tensor rank would not establish hardness for a planted random
distribution in any event.

There is also a direct easy regime that a random-factor generator would have to
avoid. When the tensor is `n x p x n`, its first slice is nonsingular, and the
rank is `n`, Lemma 1.7 reduces decomposition to simultaneous diagonalization
of the matrices `A_j * inverse(A_1)`. In the factorization used by inverse
generation, these matrices expose the planted common diagonalizer. Declaring
Track A without a distribution-specific analysis against that standard attack
would therefore be unsupported.

Moving to overcomplete or rectangular tensors avoids that particular lemma,
but it does not create a Track A theorem. It merely leaves an unanalysed planted
distribution, which is precisely what Track A forbids.

## Why Track B cannot be manufactured by scaling

All fixed-shape routes were checked before rejection:

| attempted scaling | mechanical cost | compact route | outcome |
|---|---:|---:|---|
| Increase coefficient height in Proposition 2.2 | the same 142 arithmetic operations, with larger integer operands | the same 142 operations | no operation-count gap; 64-bit inputs already produced 2,107--2,152 answer characters over 100 seeds |
| Compose independent `2 x 2 x 2` blocks | `142k` operations and `k` written decompositions | the same `142k` operations and output | scales transcription, not insight, and soon exceeds the answer cap |
| Use Lemma 1.7 on growing square tensors | simultaneous diagonalization/factor recovery | no shorter route for randomly sampled dense factors | an algorithmic task with no compact planted shortcut supplied by the paper |
| Inverse-generate a singular pencil for Lemma 4.1 | recover a left eigenvalue of a fixed `3 x 3` quaternion pencil | no shorter route unless the planted value is visibly leaked | fixed dimension, and adding a leak makes the answer a read-off |

The first row is not a `cap_bound` situation. The family is easy well before
the answer limit; the cap merely prevents using operand length to turn constant
arithmetic into a transcription exercise. The second row grows the needle with
the haystack. The last two rows may create expensive generic algebra, but they
do not provide the short structural route Track B requires.

It would be possible to invent a Walsh, Kronecker, graph, SAT, or hidden-basis
puzzle around a planted tensor decomposition. None of those structures or
reductions is central to this paper. Any hardness or compression would come
from the added puzzle rather than the quaternion rank results, so it would not
be honest native coverage of this source.

## Easy regimes and witness caveat

The main easy regime is the paper's main theorem: every `2 x 2 x 2` quaternion
tensor has rank at most three, with Proposition 2.2 giving the decomposition
formula after elementary normalization. Several later proofs similarly reduce
their fixed shapes by row/column operations and then write down a bounded
number of simple tensors. Section 3's hardest-looking subcase invokes a single
quaternion quadratic equation, while Lemma 4.1 invokes a left eigenvalue; both
remain constant-dimensional and neither comes with a growing no-tool
compression gap.

If the requested answer were the *minimal rank* rather than merely a
decomposition, a planted sum alone would not certify minimality. A lower bound
must also be checked, for example through a full-rank matrix slice in the
Lemma-1.7 regime. That repair clears the witness rule but makes the
simultaneous-diagonalization route still more explicit; it does not repair H.

## Reconsideration criterion

This paper could be reopened if a source establishes either:

1. hardness for a precisely specified, efficiently samplable distribution of
   quaternion tensor decompositions in a growing parameter regime (Track A),
   together with evidence against the applicable diagonalization/algebraic
   attacks; or
2. an efficient reference algorithm with a measured large shipping-size cost,
   while a structure native to this paper yields a genuinely shorter
   under-300-operation certificate route (Track B).

Neither ingredient is present in arXiv:2006.14813. The correct result is
therefore a documented H rejection, not an easy generator with a large formal
answer space.
