# Rejected at Step 0: the certificate is the paper's linear-time construction

Paper: Lorenzo Mella and Tommaso Traetta, [*Constructing generalized Heffter
arrays via near alternating sign matrices*](https://arxiv.org/abs/2306.09948),
arXiv:2306.09948v2.

## Decision

No problem generator is shipped.  The prior-triage proposal--give the parameters
and group entries of a generalized Heffter array (GHA), and ask for the array--is
generatable and exactly verifiable, but it fails **H (hardness)** on both tracks.

- **Track A fails.**  The paper proves no computational-hardness or
  distributional-hardness result.  In its main regimes it gives the requested
  certificate by an explicit deterministic construction.
- **Track B also fails.**  The construction is already the compact route: it
  makes one pass over the output array.  There is no large mechanical
  computation that a structural observation compresses.  At any writable size,
  applying the formula and writing the witness have comparable cost.

This is not a witness-rule failure.  A completed array is an excellent finite
witness: its support, multiplicities, row and column sums, and all partial sums
can be checked exactly.  It is the *search for that witness* that is too easy.
Per the task's Step 0 instruction, I stopped before writing a module, self-test
report, README, or oracle transcripts.

## Exact native objects and definitions

Definition 1.1 defines a
`GHA^lambda_S(m,n; h-vector,k-vector)` over an additive group `G`.  Its nonzero
entries have the prescribed row and column weights, and their absolute values
cover each noninvolution of `S` exactly `lambda` times and each involution
exactly `lambda/2` times.  Definition 1.3 distinguishes zero-sum from nonzero-sum
arrays.  The prose following Theorem 1.5 then defines simplicity by requiring
every proper contiguous run in every ordered row and column to have nonzero sum.

Definition 3.1 introduces the paper's main construction object: a near
alternating sign matrix (NASM), a `{0,+1,-1}` matrix whose nonzero entries
alternate in every row and every column.

These are all finite, paper-native objects.  Verification over the cyclic groups
used in Sections 3--4 consists only of integer counting and modular addition:

1. count the nonzeros in each row and column;
2. compare the multiset of absolute values with `S` at the stated multiplicity;
3. recompute every row and column sum modulo `v`; and
4. scan prefix sums (or all proper runs) to check simplicity exactly.

Thus **G would pass** by theorem-backed construction and **V would pass** by an
`O(mn)` exact checker.  Neither fact establishes H.

## The certificate-producing algorithm

The decisive theorem chain is explicit.

- **Theorem 3.6** proves that a uniform `NASM(m,n;h,k)` exists exactly when
  `mh=nk`.  Its proof computes
  `f=gcd(m,k)`, `g=gcd(n,h)`, `ell=m/f=n/g`, and `d=h/g=k/f`; writes down an
  `ell` by `ell` base matrix by a displayed cell formula; and tiles signed copies
  of that block.  This is a direct `O(mn)` construction, not a search.
- **Theorem 3.8** handles its stated nonuniform even-weight regime by first using
  the Gale--Ryser construction for a binary matrix with the desired margins and
  then replacing every bit by a fixed `2 by 2` block.  This is again polynomial
  and output-linear after the margin matrix is built.
- **Theorem 4.4** turns any NASM into a nonzero-sum, naturally simple cyclic GHA:
  enumerate the nonzero positions, map ranks increasingly to `S`, and take the
  Hadamard product with the NASM.  Lemma 4.1 proves the alternating increasing
  sequences are simple.  The requested GHA is therefore written down cell by
  cell.
- **Theorem 4.5** gives the zero-sum construction.  Formula (4.1) explicitly
  reorders the paired consecutive integers in each row, and the proof stacks two
  signed copies.  Lemma 4.2 supplies simplicity.  Corollary 4.7 and Theorem 1.7
  identify the advertised cyclic-group parameter regime.
- **Theorem 5.3** is explicitly an algorithm for nonzero-sum GHAs over an
  arbitrary group.  It builds a forest from the last occupied cells and fills
  them while avoiding at most one or two forbidden group values.  Theorem 1.5
  obtains the simpler sufficient condition `|S minus I(S)| >= m+n-1`.

The conclusion (Section 8) accurately describes these results as constructions
and an algorithm.  The word "harder" in Section 4 refers to the mathematical
difficulty of proving the zero-sum existence result, not to computational
hardness of finding an array once the parameters are given.

## Mechanical cost versus compact route

The Track B discriminating test gives no usable gap.

Consider the nontrivial but hand-writable uniform parameters

```text
m=8, n=12, h=6, k=4, weight w=mh=nk=48.
```

Theorem 3.6 gives `f=4`, `g=6`, `ell=2`, and `d=1`.  A direct implementation
examines the 96 output cells once and performs 48 sign/value placements to apply
Theorem 4.4: about **144 primitive cell operations**, plus four small gcd/division
computations.  On larger instances its cost is `Theta(mn+w)` (or
`O(mn+w log w)` if an unordered `S` must first be sorted).

The **compact route is the same 144-operation pass**: compute the four parameters,
use the displayed base-block formula, tile it, and attach the increasing group
entries.  It cannot asymptotically or materially beat the mechanical route,
because the solver must still emit the 96-cell array containing all 48 nonzero
entries.  At the largest permitted answers the witness itself approaches the
256-atomic-element cap, so scaling only adds transcription and formula
evaluation; it does not enlarge a hidden haystack at fixed route length.

Using the Section 5 algorithm does not create a Track B gap either.  Its forest
and forbidden-value choices *are* the proof's compact construction.  A generic
backtracking solver may do more work, but the strongest known algorithm is the
paper's direct one, and Track B cannot pretend that algorithm is unavailable.

## Nearby witness tasks considered

| Candidate task | Outcome | Reason |
|---|---|---|
| Construct a uniform nonzero-sum simple GHA from `(m,n,h,k,S)` | **H fails on A and B** | Theorems 3.6 and 4.4 output it in one cellwise pass. |
| Construct the zero-sum family | **H fails on A and B** | Theorem 4.5 gives the entry permutation and signs explicitly; Corollary 4.7 and Theorem 1.7 supply the advertised parameters. |
| Fill an arbitrary-group support with a nonzero-sum GHA | **H fails on A and B** | Theorem 5.3 is already a constructive forest/greedy algorithm. |
| Reveal an unsigned NASM support and ask for signs | **H fails** | Alternation says adjacent nonzeros in each row and column have opposite signs; this is a parity-propagation/2-colouring pass with at most a global flip per component. |
| Reveal a constructed GHA with scrambled signs and ask to restore simplicity/sums | **H unsupported or easy** | The NASM alternation constraints remain linear-time; arbitrary extra scrambling creates a new planted constraint problem for which the paper gives no hard distribution. |
| Find compatible row/column orderings for a biembedding | **No qualifying hardness basis** | Section 7 assumes a compatible ordering and Theorem 7.4 converts it to an embedding; it proves neither a scalable inverse construction with distributional hardness nor a compact-vs-mechanical Track B gap for finding one. |
| Output the orthogonal decompositions or surface embedding | **H / output-size failure** | Theorems 6.5, 6.8, and 7.4 develop the already known rows and columns by direct translations/rotations.  Succinct base walks are immediate; fully developed objects grow far beyond the answer cap. |

Row/column permutations, transposition, cyclic shifts, group automorphisms, or
sign reversal do not rescue the construction task.  They are inexpensive
structure-preserving transformations and the certificate is carried through
them directly.  Hiding an arbitrary value permutation that does not preserve
the group law would instead discard the theorem that proves the GHA properties.

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G -- known certificate by construction | Pass in principle | Theorems 3.6/3.8 followed by 4.4 or 4.5, or the algorithm of Theorem 5.3. |
| H -- Track A structural hardness | **Fail** | No hardness theorem or hard generated regime; the paper gives a polynomial, mostly output-linear constructor. |
| H -- Track B no-tool compression | **Fail** | Mechanical and compact costs coincide: about 144 primitive steps on the representative 96-cell instance, both `Theta(mn+w)` generally. |
| V -- cheap exact checking | Pass in principle | Exact counts, multiset comparison, modular sums, and prefix-sum distinctness. |
| Answer-space guessing | Irrelevant | A huge nominal space cannot override a deterministic constructor that succeeds on every instance. |
| Oracle loop | Not run | Step 0 already establishes H failure; model failures would not rebut the explicit algorithm. |

The paper is a strong source of *constructions*, but precisely for that reason
its native construction tasks do not form a hard witness-search benchmark under
either declared track.
