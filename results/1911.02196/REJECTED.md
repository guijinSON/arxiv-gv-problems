# Rejected: arXiv 1911.02196

This paper does not yield an acceptable generator under the present witness and
output constraints.  The attempted family clears **G** and **V**, but fails
**H on Track A**.  Track B was considered separately and also does not provide
a meaningful compression gap.

## Step 0 findings

The exact native problem is fixed in Section 1: a PSTS `(U,A)` embeds in an
STS `(V,B)` when `U` is a subset of `V` and every triple of `A` occurs in `B`.
The easy regime is explicit there: every PSTS of order `u` embeds at every
admissible order `v >= 2u+1`.  Theorem 1 proves NP-completeness only for
admissible functions whose maximum requested order satisfies
`max(F(u)) < (2-epsilon)u` on polynomially frequent values of `u`.

The proof reduces cubic 3-edge-colouring to small embedding.  In particular,
Section 2, Lemma 4 says that a proper 3-edge-colouring of a cubic graph `G`
with colour set `Z` produces the triangles `{x,y,colour(xy)}` that decompose
`overline(K_Z) vee G`.  Lemma 3 then constructs a `(u,v,G)` background for
`n >= 74`, `u >= 4n+43`, and `u <= v <= 2u-2n-13` with admissible `v`.
This is a valid paper-licensed certificate route, but it is a worst-case
reduction; it says nothing about the planted positive distribution needed by a
generator.

Section 3 does not supply a better route.  Example 9 is one fixed PSTS(15), not
an unlimited family.  For even `w >= 6`, Theorem 2 and Lemma 11 only establish
existence after an unspecified large threshold, and the required triangle
decomposition of the complement is not produced as a finite construction in
this paper.  The displayed graph obstruction itself is given by direct modular
formulae, so asking for that formula or its two distinguished vertices would
be a lookup rather than a hard witness problem.

## Attempted family and failed gate

The retained `rejected_gen_1911_02196.py` inverse-generates a simple connected
cubic graph as the union of three independently sampled perfect matchings,
then independently scrambles vertex names, edge order, and colour names.  Its
known colouring is a valid Lemma 4 triangle-decomposition certificate, and the
shipping candidate has 160 vertices, 240 edges, and a 240-atom answer.
Verification expands the 240 proposed triangles and compares their edge
multiset exactly.  Thus G and V are sound.

H is not.  A domain-standard exact 3-edge-colouring DPLL with incidence unit
propagation, colour-symmetry breaking, and minimum-remaining-values branching
solved **7 of 8** independently generated shipping instances.  The measured
results were:

| seed | solved | DPLL nodes | wall seconds |
|---:|:---:|---:|---:|
| 800 | yes | 1,069 | 0.350 |
| 801 | yes | 170 | 0.058 |
| 802 | yes | 393 | 0.163 |
| 803 | yes | 1,689 | 0.660 |
| 804 | yes | 316 | 0.175 |
| 805 | yes | 83 | 0.097 |
| 806 | no (budget exhausted) | 250,000 | 84.898 |
| 807 | yes | 22,081 | 8.265 |

The node budget was 250,000 per instance.  Generic endpoint-bucket, greedy
input-order, and 256 random-order greedy probes all failed, but G6 requires the
standard algorithm to fail too.  The 7/8 DPLL success rate is decisive.  The
paper's NP-completeness theorem cannot turn this easy planted distribution into
a Track A claim.

Two construction-preserving hardening ideas were also checked without using
solver performance as a generation filter.  Repeated colour-preserving
`Y -> Delta` expansion of the uniquely colourable `P(9,2)` can make naive DPLL
work harder, but a specialist simply contracts the conspicuous triangles in
linear time and colours the fixed core.  Random graph covers preserve a known
colouring and remove those triangles, but sampled 162-vertex covers were again
solved in as few as 443 DPLL nodes.  Neither supports Track A.

## Why Track B does not rescue it

For the attempted shipping distribution, the mechanical method is the DPLL
above: on the seven solved audit instances it used 83 to 22,081 nodes (median
393 nodes) and 0.058 to 8.265 seconds (median 0.175 seconds).  There is no
shorter structural route hidden in the rendered instance: the construction's
three matchings are deliberately exchangeable and forgotten.  Even someone
handed the planted partition must still emit 240 colour entries, versus only a
few hundred DPLL nodes on typical instances.  The nominal compact route is
therefore about 240 assignments, essentially the same scale as the mechanical
route, not the million-operations-versus-dozens gap required by Track B.

The prior-triage alternative—delete blocks from a known Steiner triple
system—is easier still.  The missing pairs are obtained by one scan and the
deleted triangles are exposed in the leave; the mechanical `O(v^2)` scan and
the compact reconstruction do the same work.  Increasing `v` merely makes the
input and output longer.  A full embedding in the theorem's regime would also
contain `v(v-1)/6` triples, vastly exceeding the 256-atom output cap already at
the smallest `n >= 74` reduction parameters.

Accordingly the failed gate is **H**, first on Track A and, after explicitly
comparing costs, on Track B as well.  No LLM hardening run was performed,
because running STEP 4 after a 7/8 success by the mandatory standard attack
would manufacture misleading evidence.

Paper: [Bryant, De Vas Gunasekara, and Horsley, “On determining when small
embeddings of partial Steiner triple systems exist”](https://arxiv.org/abs/1911.02196).
