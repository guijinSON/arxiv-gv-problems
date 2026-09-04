# Rejected at Step 0: the construction is the solution

Paper: Xiang-dong Hou, [*Proof of a Conjecture on Permutation Polynomials over Finite Fields*](https://arxiv.org/abs/1304.2254), arXiv:1304.2254v1.

## Decision

This paper does not provide a problem family that simultaneously satisfies G, H,
and V.  I read the complete four-page paper, including the proof of Theorem 1.1 and
the generalization in Theorem 3.1.  The prior-triage proposal—choose `k` and ask for
the constructed finite-field permutation polynomial—fails **H** at the
discriminating test: the certificate is produced by direct evaluation of the main
theorem's displayed formula.  No generator, self-test report, or oracle transcript
was produced, because the task requires rejection before implementation when a gate
already fails.

## What produces the proposed certificate, and what does it cost?

For `q = 4` and every `k >= 1`, Theorem 1.1 itself supplies

\[
g_k(x)=x+S_{2k}(x)^{q^{2k}}+S_{2k}(x)^{q^k+3},
\qquad
S_{2k}(x)=\sum_{i=0}^{2k-1}x^{q^i}.
\]

Writing this sparse symbolic expression requires `2k` Frobenius monomials and a
constant number of additions and exponent annotations: `O(k)` output work.  It is
not obtained by searching an instance.  Any instance containing only `k` has the
same publicly specified answer, so increasing `k` merely lengthens a formula whose
construction remains immediate.

Theorem 3.1 does not create a harder search problem.  It says that a 2-linearized
polynomial `L` satisfying two stated conditions makes
`L + S_(2k)^(q^k+3)` a permutation polynomial.  The note immediately following the
theorem gives the qualifying polynomial explicitly:

\[
L=(x+S_{2k}^{q^{2k}})^{4q^{3k-1}}.
\]

The note then verifies condition (ii) by a short Frobenius-power identity and calls
condition (i) obvious.  Thus this candidate too is produced by a closed formula,
not by a hard witness search.

## Track analysis

**Track A is unavailable.**  The paper proves a permutation property; it states no
worst-case, average-case, or distributional hardness theorem for finding a
permutation polynomial, an inverse, or any related witness.  More decisively, the
native witness proposed by triage is available in `O(k)` symbolic work throughout
the theorem's entire parameter regime.

**Track B is also unavailable for that proposal.**  Track B requires a large
mechanical route and a distinct compact route that is difficult to notice.  Here the
compact route is the problem's displayed answer: substitute `k` into Theorem 1.1.
It takes only a handful of symbolic steps, so it is executable without tools and
cannot support a no-tool-compression claim.

## Other paper-native formulations considered

| Candidate task | Gate failure | Reason |
|---|---|---|
| Given `k`, output `g_k` | **H** | Theorem 1.1 displays `g_k` explicitly; construction is `O(k)` in its written size. |
| Output an `L` meeting Theorem 3.1 | **H** | The note after Theorem 3.1 displays such an `L` and verifies its conditions directly. |
| Certify that a supplied `g_k` is a permutation by enumerating the field | **V / scaling** | The suggested checker evaluates all `4^(3k)` field elements, exponential in the succinct parameter `k`; it is not a cheap scalable verifier. |
| Supply the complete value table as a bijectivity witness | **V / witness size** | The answer and checker both have size at least `4^(3k)`, violating the bounded, writable witness requirement. |
| Supply an inverse polynomial and check both compositions modulo `x^(4^(3k))-x` | **G / H unsupported** | The paper neither constructs an inverse polynomial nor proves that finding one is hard. Computing it from the generated instance would be solving the instance, while an interpolation table is exponential in `k`. |
| Given `y`, find `x` with `g_k(x)=y` | **H unsupported** | A preimage can be planted and checked by evaluation, but the paper makes no one-wayness or inversion-hardness claim and gives no hard distribution. Track A would therefore lack its required theorem and parameter regime; Track B would lack the required efficient mechanical algorithm plus a sub-300-operation compact route. |
| Output the character-sum proof witnesses used in Section 2 | **H / witness shape** | Case 1 obtains a translation by elementary trace pairing, and Case 2 reduces the sum through explicit identities. Packaging the paper's proof is not a new hard search; asking for all field-indexed witnesses would instead be exponential-size. |

Random affine disguises, added interpolation constraints, or generic finite-field
linear systems could make some of these tasks look less transparent, but their
difficulty would come from a new masking construction rather than from this paper.
They would not repair the missing Track A hardness theorem, and an efficiently
decodable disguise would merely move the result to Track B without making the
paper's displayed formula hard to discover.

## Gate outcome

| Requirement | Outcome | Evidence |
|---|---|---|
| G — generatable by construction | Passes for the proposed output task | Theorem 1.1 directly constructs `g_k`; Theorem 3.1 and its note directly construct the generalization. |
| H — hard under a declared track | **Fails** | The proposed answer costs `O(k)` to write and no paper result supplies a hard search regime. |
| V — cheap exact witness checking | Fails for bijectivity enumeration; otherwise does not rescue H | Exhaustive evaluation costs `4^(3k)`; comparing with the displayed formula is cheap but makes the task transparently easy. |

The family is therefore rejected at Step 0.  Running adversarial probes or the LLM
hardening loop cannot turn a known explicit construction into a defensible hardness
claim.
