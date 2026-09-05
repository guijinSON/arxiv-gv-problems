# Rejected at Step 0: Beauville witnesses are dense in a fixed two-dimensional quotient

Paper: Şükran Gül, [*Beauville structures in \(p\)-central
quotients*](https://arxiv.org/abs/1604.06031), arXiv:1604.06031v1.

## Decision

No generator is shipped. I read the complete paper, including the definition of a
Beauville structure in Section 1, the free-group construction in Section 2, the
free-product construction and the exceptional prime-three argument in Section 3,
and the non-coincidence theorem at the end of Section 3.

The prior-triage proposal has a concrete finite witness and the paper constructs
one, so **G passes in isolation**. Exact checking can also be implemented for an
explicit finite group, so **V can pass in isolation**. The natural search problem,
however, fails **H on both tracks**. This is not merely because an efficient
algorithm exists: the paper's sufficient witnesses occupy at least 5% of the
structure-aware candidate space for every `p >= 5`, and the prime-three
construction has density at least 4/9 in its natural parameters. Thus even random
guessing violates G4 by many orders of magnitude.

Steps 1--4 were intentionally not run after this Step-0 failure. There is no
`gen_1604_06031.py`, self-test report, README, or oracle transcript; creating those
would contradict the instruction to stop when G, H, and V cannot hold
simultaneously.

## Exact native problem and certificate

For elements `x,y` of a finite group `G`, Section 1 defines

\[
\Sigma(x,y)=\bigcup_{g\in G}
  \left(\langle x\rangle^g\cup\langle y\rangle^g
  \cup\langle xy\rangle^g\right).
\]

A Beauville structure is two generating pairs `{x1,y1}` and `{x2,y2}` for which
`Sigma(x1,y1) intersect Sigma(x2,y2) = {1}`. The answer suggested by the paper is
therefore four native group elements. Given an exact finite-group representation,
a checker can test generation and enumerate powers and conjugates, or use the
paper's executable power-subgroup criterion for these quotients. The witness is
not a proof string or a bare yes/no claim.

The positive parameter regimes are classified completely:

- Theorem A (proved as Theorem 2.5) says that the quotients of the free group on
  two generators are Beauville exactly when `p >= 5` and `n >= 2`.
- Theorem B combines Theorems 3.2 and 3.5: for the free product of two cyclic
  groups of order `p`, the quotient is Beauville exactly when `p >= 5, n >= 2`,
  or `p = 3, n >= 4`.

The negative cases are consequently constant-time classification questions, not
hard witness searches. The paper does not give a bounded, scalable executable
certificate of nonexistence that would turn them into a different hard family.

## Step-0 certificate-producing algorithm

For both positive `p >= 5` families, the proof does not search for a tuple. With
`u,v` the images of the two displayed free generators, Theorems 2.5 and 3.2 give

\[
  \{u,v\},\qquad \{uv^2,uv^4\}.
\]

Using repeated squaring, producing the second pair costs exactly four group
multiplications: form `v^2`, `u*v^2`, `v^4=(v^2)^2`, and `u*v^4`. This cost is
independent of `p`, `n`, and the order of the quotient. If elements are accepted as
words in `u,v`, even those four evaluations disappear and the answer is a literal
four-word transcription.

The proof's real invariant is also tiny. Lemmas 2.2--2.4 show that in the
free-group quotient the relevant highest powers depend only on an element's
maximal subgroup, equivalently on its one-dimensional subspace in
`G/Phi(G) ~= F_p^2`. Theorem 3.2 uses the same six projective lines, together with
the maximal-class quotient, for the free-product case. The first pair occupies
the three lines represented by `(1,0)`, `(0,1)`, and `(1,1)`; the displayed second
pair occupies slopes 2, 4, and 3. Verification of this sufficient condition is a
constant number of exact modular determinant and equality tests.

## Mechanical cost versus compact route

The general brute-force algorithm for an arbitrary finite group is irrelevant to
the distribution generated here. A domain-aware standard algorithm immediately
passes to the two-dimensional Frattini quotient, samples a second generating pair,
and checks whether its three projective lines avoid the first three. Its cost never
grows with `n`.

Fix a first generating pair. Conditional on the proposed second ordered pair also
generating, the exact fraction whose two lines and product line avoid the first
three is

\[
 q_p=\frac{(p-2)(p-3)(p-4)}{p(p+1)(p-1)}.
\]

This follows by choosing two distinct projective lines outside the first three and
then choosing their relative nonzero scaling so that their sum line is outside
those three. At the hardest prime, `p=5`, it is

`q_5 = 24/480 = 1/20 = 0.05`.

It is already about `0.1786` for `p=7` and tends to one as `p` grows. Lifts from
`G/Phi(G)` do not lower this sufficient-witness density: the cited lemmas make the
line condition sufficient throughout the quotient tower.

| route at the hardest parameter `p=5` | measured/countable cost | scaling in `n` |
|---|---:|---:|
| paper's displayed tuple | exactly 4 group multiplications | constant |
| compact projective-line route | choose slopes 2 and 4; about 6 line comparisons | constant |
| standard randomized search | expected 20 candidate tests | constant |
| exhaustive quotient search | exactly 480 ordered generating vector pairs, 24 accepted | constant |

Thus the most honest mechanical figure is **20 expected constant-size tests**, not
enumeration of all elements of the enormous group. The compact route is **4 group
multiplications** (or a handful of modular comparisons). Both are executable in
context and are comparable; there is no million-operation mechanical route hiding
behind a dozen-operation insight. A 256-restart attack succeeds with probability
`1 - (19/20)^256 > 0.999998`, so it cannot supply a failing G6 attack.

This also shows why increasing the nilpotency depth is not an escalation: the group
order grows, but the actual answer search remains in the same `F_p^2`. Increasing
`p` makes random search easier rather than harder.

## The prime-three construction is even denser

For `p=3` and `n>=5`, Theorem 3.5 chooses `z,t` in `Phi(L)` and outputs

\[
  \{u,v\},\qquad \{(uz)^{-1},vt\}.
\]

Lemma 3.3 proves that each forbidden commutator image has size at most
`|Phi(L)|/3`. Consequently a uniform `z` has probability at least `2/3` of meeting
the proof's condition, as does an independent `t`; the pair succeeds with
probability at least

`(2/3)^2 = 4/9`.

Equivalently, rejection sampling needs at most `9/4` pair trials in expectation
(or at most three individual draws in expectation if `z` and `t` are tested
separately). This is fatal to G4 even before asking how a concrete group encoding
would implement the commutator-image test. The `n=4` endpoint is the single group
of order `3^5` identified in the proof, so relabellings of it do not provide
unlimited canonical diversity.

## Track analysis

**Track A fails.** Neither main theorem gives a hard distribution; both give the
answer directly. More strongly, the generated positive instances have the exact
high solution densities above. The paper states no NP-hardness, average-case
hardness, or other parameter regime that could override this calculation.

**Track B also fails.** A deliberately generic search over all four-tuples or all
conjugates would manufacture a mechanical/compact gap by ignoring the quotient
structure exposed in the instance. The distribution-standard randomized algorithm
needs only 20 expected constant-size tests in its hardest `p>=5` case, versus four
operations for the displayed construction. At `p=3`, a guess in the theorem's own
`z,t` parameterization works with probability at least 4/9. The required fourth
in-context failing attack therefore cannot exist, and the structural hint would
essentially expose the whole constant-size line calculation.

Randomly renaming group elements does not repair this. In the relatively free
quotient, any generating pair is the automorphic image of the displayed pair, so
the same `a,b -> ab^2,ab^4` construction carries through the relabelling. A random
ordered pair generates a two-generator finite `p`-group with probability
`(1-1/p)(1-1/p^2)`, already `0.768` at `p=5`.

## Other paper-native formulations considered

| candidate task | G | H | V | outcome |
|---|---:|---:|---:|---|
| Find a Beauville structure in `F/lambda_n(F)`, `p>=5` | Pass: Theorem 2.5 | **Fail:** displayed four-operation answer; at least 5% witness density | Can pass with an exact quotient model | Reject |
| Find one in `(C_p*C_p)/lambda_n`, `p>=5` | Pass: Theorem 3.2 | **Fail:** same tuple and same projective-line search | Can pass with an exact quotient model | Reject |
| Find one in the `p=3` tower | Pass in the theorem's `z,t` form | **Fail:** sufficient choices have density at least 4/9 | Potentially exact, but does not rescue H | Reject |
| Decide which parameters give a Beauville quotient | Pass by Theorems A and B | **Fail:** constant-time inequalities and a classification lookup | A bare boolean is not the requested hard witness | Reject |
| Certify the Section 3 non-isomorphism | Pass by Theorem 3.6 | **Fail:** the proof reads off the exponent of a derived subgroup | Exact invariant comparison | Reject |
| Output a full quotient multiplication table | Not supplied in bounded form by the paper | Fails the writable-answer caps before hardness matters | Exact but not cheaply scalable from a succinct presentation | Reject |
| Add a unique lexicographic or masking constraint | Plantable only by adding new machinery | Unsupported by this paper; difficulty comes from the wrapper | Minimality would require search, or the mask leaks the answer | Reject |

## Gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G -- generatable | Passes in isolation | Theorems 2.5 and 3.2 display a tuple; Theorem 3.5 constructs one using `z,t`. |
| H -- Track A | **Fail** | The answer is explicit and sufficient witnesses have density at least 0.05 (`p>=5`) or 4/9 (`p=3`). |
| H -- Track B | **Fail** | 20 expected constant-size tests versus a four-operation compact route at the hardest prime; both are by-hand scale. |
| V -- exact checking | Can pass in isolation | Finite group operations and the executable Frattini-quotient line criterion are exact. |
| G4 -- structure-aware guessing | **Fail** | `24/480 = 0.05` at `p=5`, versus the required `< 1e-6`; larger primes are easier. |
| G6 -- adversary panel | **Fail analytically** | Random restart 256 succeeds with probability above 0.999998 at `p=5`; direct theorem ansatz always succeeds. |
| Overall | **Rejected at Step 0** | No paper-native family makes G, H, and V hold simultaneously under either track. |

No gate result or oracle evidence was fabricated after the analytical H failure.
