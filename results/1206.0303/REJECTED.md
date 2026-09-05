# Rejected: arXiv:1206.0303

Paper: Prosenjit Bose and Sander Verdonschot, *A History of Flips in
Combinatorial Triangulations*
([arXiv:1206.0303v2](https://arxiv.org/abs/1206.0303)).

## Decision

No generator is shipped. The prior proposal—apply random legal flips and hide
the sequence—clears **G** and **V**, but not **H on Track A**. The paper gives a
constructive route for the unrestricted witness problem, while it gives no
hardness theorem or hard distribution for recovering a planted bounded-length
sequence. The paper's exact lower-bound constructions do not rescue the family
on **Track B**: at the largest sizes allowed by the answer cap, their mechanical
and compact routes are both short linear procedures dominated by writing the
certificate.

## STEP 0: what produces the certificate?

The native object is a combinatorially embedded simple planar triangulation. A
flip deletes an edge shared by two triangular faces and inserts the opposite
diagonal, provided that diagonal is absent (Section 1). Replaying a proposed
list of deleted edges therefore verifies a transformation exactly and cheaply.

For the unrestricted task, however, the certificate is produced by the paper's
own constructive algorithms:

- Lemma 1 and Theorem 2 (Section 2) transform both inputs through the canonical
  triangulation in at most `2n^2-14n+24` flips.
- Lemma 4 and Theorem 5 (Section 3) improve this to at most `8n-54` flips for
  `n >= 13`.
- Lemmas 6, 8, and 9 and Theorem 10 (Section 4) explicitly remove separating
  triangles, use the resulting Hamiltonian cycle, and transform through the
  canonical triangulation in at most `6n-30` flips.
- Theorem 12 and Corollary 13 (Section 5) sharpen the first stage and the
  diameter bound further.

Thus “find any sequence” has a theorem-backed constructive algorithm on every
instance, including every planted distribution. Putting that algorithm in a
Track A adversary panel would record successes, as it must.

## Why bounding the sequence does not establish Track A

Changing the question to “give at most `k` flips” prevents the universal
canonical route when `k` is small, but the paper proves no computational
hardness theorem for this decision/search problem and no average-case statement
for endpoints of a random flip walk. Section 7 calls determining the minimum
number of flips the main open problem and says that the known canonical methods
are insensitive to the true distance. That is an open question, not the
distribution-specific hardness basis required for Track A.

Inverse generation supplies only an upper-bound witness: the hidden planted
walk. Asking instead for the *minimum* distance would need an executable lower-
bound certificate meeting that walk. The degree bounds in Theorems 14 and 15
(Section 6) are not generally tight, and the paper explicitly leaves a linear
gap between its `2n-15` lower bound and `5.2n-24.4` upper bound. Consequently a
shortest-distance family cannot be generated with certified optima merely by
sampling a walk.

Worst-case hardness for a related triangulation model would not repair this
specific proposal: randomly walked positive instances are not a reduction
distribution, and the paper focuses on combinatorial sphere triangulations,
not a geometric or polygonal surrogate.

## Track B audit: mechanical cost versus compact route

Two paper-native candidates were checked against the output and effort caps.

| candidate | largest cap-compatible scale | paper's mechanical route | compact route available to the solver |
|---|---:|---:|---:|
| any transformation sequence, each flip encoded by its two edge endpoints | at most 128 flips (`256` atomic integers); Theorem 10 always fits only through `n=26`, where `6n-30=126` | at most 126 constructive flip steps, plus the graph bookkeeping in Lemmas 6, 8, and 9 | the planted walk has up to 128 replay/write steps, but is random and hidden; recovering it has no shorter invariant in the construction |
| an optimal certificate for making the Theorem 16 triangulation 4-connected, consisting of `q` flipped edges and `q` edge-disjoint separating triangles | `5q <= 256`, hence `q <= 51`; the tight construction reaches this at `n=88` | Theorem 12 uses at most `floor((3n-6)/5)=51` flips after a linear separating-triangle scan of the `3n-6=258` edges | the recursive construction still requires choosing 51 flips and listing 51 three-vertex lower-bound triangles (`255` atomic integers) |

For the first candidate there is no solver-visible compact route at all. The
generator knows the random walk, but “the generator remembers it” is not an
insight a solver can recover. Revealing a seed or a deterministic flip pattern
would simply make an obvious in-context replay attack succeed.

The second candidate is the strongest certified-optimum alternative in the
paper. Theorem 16 supplies `q=ceil((3n-10)/5)` edge-disjoint separating
triangles, proving that at least `q` flips are required, and Theorem 12 supplies
the matching upper bound. But the mechanical and compact routes are both
`Theta(n)`: at the cap-compatible endpoint the reference performs 51 flips and
one 258-edge scan, while the answer itself contains 102 records/255 integers.
There is no million-operation mechanical calculation replaced by a short
symmetry or invariant; the exercise is mainly graph scanning and transcription.
This is too small a gap, and of the wrong kind, for Track B.

The other paper-native witness candidates have the same defect. Lemma 6 gives a
direct greedy flip at every step in a maximal outerplanar graph. Theorem 17's
black/white obstruction is recovered by a linear scan. Theorems 14 and 15 use
maximum degree or sorted degree sequences, also directly computable in
polynomial time with no compact-vs-mechanical separation at the writable sizes.

## Gate summary

| gate | result |
|---|---|
| G | **Passes** for a feasible sequence by inverse generation, and for the Theorem 16 4-connectivity optimum by theorem-backed construction. **Fails** for general shortest distance because the planted path has no matching lower-bound certificate. |
| H, Track A | **Fails** for unrestricted sequences by Theorems 5 and 10. The bounded random-walk distribution has no hardness theorem or distributional evidence in the paper. |
| H, Track B | **Fails:** at the answer cap, 126 constructive flips versus at most 128 hidden planted flips for reconfiguration; for the certified optimum alternative, 51 flips plus a 258-edge scan versus 51 flip choices and a 255-integer certificate. No compact solver-visible route replaces a large mechanical computation. |
| V | **Passes:** replay each flip, check legality in the two incident faces, and compare the final embedded triangulation; separating-triangle lower bounds are also exactly checkable. |

Because the disqualifying result occurs at STEP 0, no module, self-test report,
or oracle transcripts were fabricated.
