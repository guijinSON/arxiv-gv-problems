# Rejection: arXiv:1406.5454, *Equitable block colourings*

Paper: [Paola Bonacini and Lucia Marino, *Equitable block colourings*](https://arxiv.org/abs/1406.5454)

## Decision

No generator is built. The natural family passes **G** (the colourings are known by
construction) and **V** (expand the colouring and count the incident colours and
their multiplicities at every vertex), but it fails **H on Track A** and does not
become a meaningful **Track B** family.

## Step-0 evidence from the full paper

Section 1 defines a `4CS(v)` as a partition of the edges of `K_v` into 4-cycles.
For `v = 1 + 8k`, every vertex is in exactly `4k` blocks.  When `4k = qs+r`, an
equitable colouring of type `s` must use exactly `s` colours at each vertex, with
`r` incident colour classes of size `q+1` and `s-r` of size `q`.

Theorem 2.1 is explicitly constructive for every value it proves belongs to the
spectrum, namely

`c = s, s+1, ..., floor((2s^2+s)/3)` when `k = hs`.

Its four cases directly produce the certificate:

- For `c=s`, it gives the cyclic starter blocks
  `(0,i,4k+1,k+i)`, `1 <= i <= k`, and assigns colour `j` to the
  consecutive starter indices `(j-1)h+1, ..., jh` and all their translates.
- For `c=s+1`, it assigns colour `i` to the internal subsystem on `A_i` and
  colour `p+q mod (s+1)` to every cross-family `[A_p,A_q]`.
- For `s+2 <= c <= (s^2+s)/2`, it merely recolours any selected distinct
  cross-families with fresh colours.
- For the remaining range it takes a stated triangle/4-cycle decomposition of
  `K_(2s)-I`; each part of that decomposition is itself the colour class.

Corollary 2.2 then reads off the lower chromatic index.  Theorem 2.3 is only a
counting upper bound; it supplies no hard parameter regime.  The paper contains
no NP-hardness, average-case hardness, FPT lower-bound discussion, or empirical
evidence that finding these colourings is hard.

## Why Track A fails

The paper's own distribution is solved by Theorem 2.1's displayed rules.  There
is no search whose difficulty can be inherited from a theorem in the paper.
Moreover, the first case is maximally guessable once the statement's obvious
orbit constraint is respected.  Each translated starter orbit meets every
vertex in exactly four blocks.  Therefore **any** partition of the `k=hs`
starter orbits into `s` labelled groups of size `h` is an equitable `s`-colouring:
each vertex sees exactly `4h` blocks of every colour.  A structure-aware
`random_candidate` that samples balanced orbit assignments consequently has

`P(valid) = 1`,

so G4 fails independently of the nominal number of assignments.

The later cases also expose their colouring at construction time: once the
`A_i` sets and, in the last case, the edge-cycle decomposition are supplied,
colour evaluation is a direct table/formula lookup.  Hiding those objects behind
an unrelated permutation or CSP encoding would create an obfuscation benchmark,
not a hard regime established or studied by this paper.

## Why Track B does not rescue it

The algorithm producing the certificate is the construction in Theorem 2.1.
In the cyclic case its compressed work is exactly `k` starter-orbit colour
assignments, or `s` consecutive-range descriptors; the supposed compact route is
the same `s` range descriptors.  Thus there is no algorithm-versus-insight gap.

For a concrete cap-scale measurement, take `v=41`, so `k=s=5`, `h=1`.  The
system has

`v(v-1)/8 = 205`

blocks.  The mechanical method performs 205 direct colour evaluations if the
full map is expanded; the compact form performs 5 starter-range assignments.
Both are below the 300-operation no-tool cap, and the factor of 41 is only the
cost of serialising the same displayed rule, not search.  At larger `v`, the
expanded cost grows as the output itself, while the compressed construction
remains the same direct formula.  That is precisely the transcription/expansion
gap G9 excludes.

For the other three cases the mechanical and compact descriptions are likewise
the same displayed operations: modular addition on a cross-family, selection of
cross-families, or traversal of a supplied triangle/4-cycle decomposition.  If
the decomposition is withheld, the generator no longer has a theorem-backed
hard distribution; if it is supplied, the colouring is immediate.

Accordingly the relevant numbers are **205 versus 5** at the largest simple
full-map example under the 256-atom cap, and **`k` versus `s`** in general.  The
only scalable gap is output expansion, not a hidden invariant or change of
variables.  This fails the Track B discriminating test.

## Failed gates and retained artifacts

| Gate | Result | Reason |
|---|---:|---|
| G | pass | Theorem 2.1 constructs both system and colouring. |
| H / Track A | fail | The source construction directly computes the certificate; no hard distribution is identified. |
| H / Track B | fail | Mechanical and compact routes are the same rule; any large cost is certificate expansion. |
| V | pass | Exact finite incidence counts decide validity. |
| G4 for the cyclic candidate | fail | Structure-aware balanced orbit assignments verify with probability 1. |

This rejection happened before implementation, so there is no `rejected_gen_1406_5454.py`
to retain and no oracle transcript to preserve.
