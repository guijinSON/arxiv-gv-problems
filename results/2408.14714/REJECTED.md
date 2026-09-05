# Rejection: arXiv 2408.14714

Decision: **H fails on both tracks**. Generation (G) and exact verification (V) are available, but the paper does not support an acceptable hard family under the required distribution-aware test.

## Paper result used

Section 2 defines the projective line, the `PGL(2,q)` action, block orbits, and the orbit--stabilizer formula. Lemma 12 proves that for `B = <theta^r>` the maps `x -> theta^r x` and `x -> 1/x` already give the dihedral stabilizer in the non-subfield case; Theorem 13 then gives `lambda` by a displayed two-case formula. Lemma 14 and Theorem 15 do the analogous job for `<theta^r> union {0}`.

Consequently, asking for the design parameter is a constant-size divisibility test followed by the displayed formula, and asking for a stabilizer of either canonical block is answered by the explicit maps in the proofs. In each case the mechanical and compact routes have the same constant-order cost.

## Audit of the retained generator

The built candidate inverse-generates an affine disguise

`S = {s*h + t : h in H}`

of the order-`k` multiplicative subgroup `H` and asks for an involutory `PGL(2,p)` stabilizer. Its G and V claims are sound: the conjugated inversion is known before the instance is emitted, and the checker verifies the matrix action by exact finite-field arithmetic without reading the planted answer.

Its hardness claim is not sound. The statement itself promises the affine-subgroup form. Since the roots of `x^k-1` sum to zero,

`t = k^(-1) * sum(S) mod p`.

For any displayed `x0`, put `alpha = (x0-t)^2`. Then

`[[t, alpha-t^2], [1, -t]]`

represents `x -> t + alpha/(x-t)`, a conjugate of inversion that maps `S` onto itself. This is not merely a proof of existence; it is the exact algorithm that produces the requested certificate.

At the shipping preset (`k=127`), the algorithm costs 135 high-level field operations under the generator's own accounting. On seeds 1000 through 1007 it produced a verified witness on **8/8** instances, with mean wall-clock time **0.0000205 seconds** (maximum 0.0001304 seconds in the audit run).

| quantity | measured value at shipping |
|---|---:|
| strongest mechanical method | modular barycenter plus conjugated inversion |
| mechanical cost | 135 high-level field operations |
| mechanical wall clock | 0.0000205 s mean over 8 seeds |
| compact route | the same modular-barycenter construction |
| compact-route length | 135 high-level field operations |
| cost gap | 1:1 |
| attack success | 8/8 |

The earlier G6 panel used `sum(S)//k`, an ordinary integer average, and reported that failed probe as `greedy_integer_barycenter`. That is not arithmetic in `F_p` and does not test the construction's actual signature. The corrected `modular_barycenter_conjugated_inversion` attack is now retained in `rejected_gen_2408_14714.py`; it makes G6 fail explicitly.

## Track decision

- **Track A fails:** there is an exact `O(k)` algorithm for every instance in the generated distribution, so the distribution is not structurally hard.
- **Track B fails:** the certificate-producing mechanical algorithm and the claimed compact route are identical (135 versus 135 operations). The much slower generic three-point stabilizer enumeration is not the strongest algorithm once the stated affine-image promise is used.

Hiding a general `PGL` conjugator would remove the barycenter shortcut, but then the paper supplies no shorter reconstruction route than generic set-stabilizer search. Revealing that conjugator would make conjugation itself the direct mechanical algorithm. Neither variant creates the required Track B gap. Problems about `lambda` or the canonical stabilizers are even more direct because the paper writes their answers explicitly.

The previous generator, reports, and oracle-error transcripts are retained for auditability. The oracle calls were all HTTP 403 errors and play no role in this rejection.
