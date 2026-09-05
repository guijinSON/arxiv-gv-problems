# Rejected: arXiv 2505.08551

Paper: Jeremy M. Dover, [“Untouchable sets of size $2q\pm1$ in
$PG(2,q)$”](https://arxiv.org/abs/2505.08551) ([full HTML
text](https://arxiv.org/html/2505.08551v1)).

## Decision

This paper does not yield a paper-native family satisfying G, H, and V
simultaneously. The proposed geometric witness is generatable and exactly
verifiable, but it fails **H on Track A** and also fails the distinct **Track B**
test. No generator was written because STEP 0 already decides the issue.

The exact definition is in Section 1: an untouchable set is a set of projective
points for which no projective line has intersection size exactly one. This makes
V straightforward: normalize homogeneous coordinates over the finite field,
enumerate lines (or the directions through each selected point), and compare exact
intersection counts. G is also straightforward because Proposition 1.1 says that
the union of two untouchable sets is untouchable and Sections 2–3 explicitly supply
the required conics and completing points.

H is the failed gate. The certificate-producing algorithm is the paper's explicit
construction itself:

- **Theorem 2.1** gives size $2q-1$ for every even $q\geq8$ by taking
  $C_a\cup C_{a^2}$ and the displayed nucleus (with the cube-root exception stated
  in the theorem).
- **Theorem 2.2** gives size $2q+1$ for every even $q\geq8$ from any two distinct
  nonzero parameters $a,b$: output $D_a$, $D_b$, and their two displayed nuclei.
- **Proposition 3.2 and Theorem 3.3** give size $2q+1$ for odd
  $q\equiv3\pmod4$, $q\geq7$: choose $b$ with $b$ and $b-1$ nonsquares, then output
  $C_1\cup C_b\cup\{(0,0,1)\}$. Proposition 3.2 counts $(q-3)/4$ suitable values,
  so even the parameter is not sparse.

These are direct formulas in the paper's native objects, not certificates whose
discovery survives as a search problem on the generated distribution.

## Mechanical cost versus compact route

The prior-triage proposal was to output the point set and check all line
intersections. Theorem 2.2 exposes why that cannot become a Track B task. For even
$q$, its conic

\[
D_k=\mathcal V(kxy+z^2+xz)
\]

has the explicit parameterization

\[
D_k=\{(1,(z^2+z)/k,z):z\in GF(q)\}\cup\{(0,1,0)\}.
\]

For a pair $a,b$, compute $z^2+z$ once and multiply it by $a^{-1}$ and $b^{-1}$.
Thus the **mechanical cost** of emitting both conics is $4q+2$ field operations
($q$ squarings, $q$ additions, $2q$ multiplications, and two inversions), plus
linear-time serialization. At the largest even order compatible with the stated
256-atom output cap, $q=32$, the 65 projective points contain 195 scalar atoms and
cost **130 field operations** to produce. The next order, $q=64$, already needs 387
scalar atoms and is outside the cap.

The **compact route** is not shorter: it is exactly the same parameterization and
the same 130 operations, because the solver must still write the 65 points. There
is no million-operation mechanical route hiding behind a dozen-step invariant.
Both routes are $\Theta(q)$ and coincide operation-for-operation. This is small
enough to lie under the prompt's 300-operation no-tool cap at every admissible even
shipping size.

Making the answer symbolic does not rescue Track B. If the answer is the two conic
coefficient vectors and nuclei, Theorem 2.2 writes it down in constant time, so
both the mechanical method and the shortcut become the same constant-length
formula. If the answer is only $(a,b)$, almost every pair of distinct nonzero field
elements is valid. In the odd construction, roughly one parameter in four is valid
by Proposition 3.2. Those certificate languages fail structure-aware G4 rather
than creating hardness.

Accordingly:

- **Track A fails:** an $O(q)$ distribution-specific construction is stated and
  proved in Theorems 2.1–2.2 and 3.3; the paper gives no worst-case or
  distributional hardness claim for finding these sets.
- **Track B fails:** the standard certificate-producing method and the by-hand
  structural route are the same formula, with 130 operations at the largest
  cap-compliant even instance. Their costs are comparable because they are
  identical; there is no no-tool compression gap to measure.

## Other candidate tasks considered

| Candidate task | Failed gate | Reason |
|---|---:|---|
| Output a size-$2q-1$ set for even $q$ | H (A and B) | Theorem 2.1 directly supplies the two conics and the one additional nucleus. |
| Output a size-$2q+1$ set for even $q$ | H (A and B) | Theorem 2.2 works for every distinct nonzero $a,b$; the full point list costs only 130 field operations at maximal cap-compliant $q$. |
| Output a size-$2q+1$ set for $q\equiv3\pmod4$ | H / G4 | Theorem 3.3 is explicit and Proposition 3.2 gives a density near $1/4$ for its only parameter condition. |
| Find size $2q+1$ for $q\equiv1\pmod4$ | G | Section 4 says this remains conjectural and explains why the conic technique fails. |
| Find size $2q-1$ for odd $q$ | G | Section 4 states that nonexistence remains open; there is no scalable construction or certified negative. |
| Recover hidden conics from a scrambled or partially erased set | H unsupported / not paper-native | The paper studies existence constructions, not recovery from noisy observations. Adding erasures, anchors, hashes, or decoys would manufacture a new inverse problem with no hardness basis in the source. |

## Easy regimes checked

Section 1 notes that a hyperoval is already an untouchable set of minimum size
$q+2$ for even $q$, and Proposition 1.1 makes arbitrary unions of known
untouchable sets immediate. The same section reports previously known constructions
for every size in $\{2q\}\cup[2q+2,q^2+q+1]$ for $q\geq4$. Section 2's entire
purpose is to fill the two remaining even-order sizes by explicit pencils of
conics. The paper contains no NP-hardness, average-case hardness, or parameterized
hardness theorem to support a different native search distribution.

## Gate outcome

| Gate | Outcome |
|---|---|
| G — construction knows a witness | Passes for Theorems 2.1, 2.2, and 3.3; fails for the two open regimes in Section 4. |
| H — claimed hardness | **Fails on Track A and Track B** for every constructible paper-native candidate. |
| V — cheap exact witness checking | Passes by exact finite-field incidence counting. |

The correct outcome is therefore a STEP-0 rejection, before implementation or an
oracle hardening run. An oracle's unfamiliarity with the paper's displayed formula
would not turn that formula into a hard generated family.
