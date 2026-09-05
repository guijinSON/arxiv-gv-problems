# Rejected at Step 0: arXiv:1911.12960

Paper: Vladimir N. Potapov, [*Constructions of Pairs of Orthogonal Latin
Cubes*](https://arxiv.org/pdf/1911.12960) (v2, 2020).

## Decision

No generator is shipped.  The natural theorem-backed family passes **G** and
**V**, but it cannot pass **H** on either track while respecting the answer and
intended-route caps.  This is a Step-0 rejection, not an oracle or hinted-arm
rejection, so no module, self-test report, README, or oracle transcripts were
fabricated after the failure was established.

The paper's main result is an **explicit construction**, not a hardness result.
At the first new order, 84, the native witness is necessarily enormous: a pair
of Latin 3-cubes contains

```text
2 * 84^3 = 1,185,408 symbol entries,
```

and the equivalent length-5 MDS code / orthogonal array contains

```text
84^3 rows * 5 coordinates = 2,963,520 symbol entries.
```

Thus the paper's main object exceeds the 256-atom answer cap by factors of
4,630 and 11,576 respectively.  Knowing Theorem 2 does not compress the task:
the theorem tells how to construct the entries, but a witness that a checker can
inspect must still emit them.  Replacing the witness by the words "apply
Theorem 2" would ask the checker to trust an unexpanded theorem invocation, not
inspect a pair of cubes.

At the other end, a full cube-pair answer fits the 256-atom cap only when
`2*q^3 <= 256`, hence `q <= 5`.  In precisely that range Proposition 3 gives
the standard finite-field/Reed--Solomon construction directly.  At the largest
writable order, `q=5`, the answer has 250 symbols; the mechanical constructor
and the best compact route are the same output-linear computation, with a lower
bound of 250 mandatory symbol emissions.  There is no million-operation
mechanical route hiding behind a dozen-operation structural shortcut.

## What the paper actually defines

Section 1 defines a Latin 3-cube of order `q` as a `q x q x q` array in which
every axis-parallel line contains every symbol exactly once.  Two cubes are
orthogonal when every pair of corresponding two-dimensional faces is a pair of
orthogonal Latin squares.

Section 2, Proposition 1 gives the exact equivalence used throughout the paper:

- two strong-orthogonal functions on `Q_q^3` (a pair of orthogonal Latin
  3-cubes);
- an `MDS(2,5,q)` code; and
- an `OA_1(3,5,q)` orthogonal array.

An `MDS(2,5,q)` code has `q^3` length-5 words.  In the orthogonal-array form,
each choice of three of the five columns must contain every element of
`Q_q^3` exactly once.

Section 3 contains the certificate-producing algorithms:

- Proposition 3 constructs linear MDS codes over every prime-power alphabet
  using a parity-check matrix.
- Proposition 6 is the McNeish Cartesian-product construction.
- Theorem 1 explicitly assembles a new code as the union of four displayed
  product pieces built from nested MDS codes and codes with holes.
- Lemma 1 supplies the exceptional order-6 code with a two-symbol hole by a
  fixed table and direct verification.
- Theorem 2 combines those ingredients and proves existence when
  `q = 16*(6*s +/- 1) + 4`.  Its smallest previously unknown result is `q=84`.

Section 4, Theorem 3 gives another explicit union construction from nested
Steiner systems.  It does not produce a smaller witness: its output is again a
`q^3`-row MDS code.

The paper also identifies easy and impossible regimes.  Proposition 3 covers
prime-power alphabets constructively; Proposition 6 covers products of known
orders; and the Hamming bound rules out a pair at order 3 (orders 2 and 6 are
also excluded in the introduction).  No section states computational hardness
for finding, completing, or recognizing a cube pair, and no distributional
hardness theorem is available for Track A.

## The certificate-production question

| proposed family | certificate producer | outcome |
|---|---|---|
| Given an admissible `q`, output two full Latin cubes | Theorem 1/2's explicit union and product construction | **G and V pass; Track A H fails, and the first new witness violates the output cap by over four thousand-fold.** |
| Output the equivalent OA/MDS code | The same explicit construction, with five coordinates per one of `q^3` rows | **Even larger; no compact-route advantage.** |
| Output a symbolic recipe such as `(THEOREM2,s,sign)` | Read `p=(q-4)/16` and the sign from the displayed formula | **Track B fails:** this is a constant-length substitution/lookup with at most two sign choices, not a large answer space. |
| Given a product order, return factors so Proposition 6 can be invoked | Integer factorization of the displayed order | **Not paper-native and no Track A basis:** Proposition 6 is a forward Cartesian-product construction, not a hardness theorem for its inverse.  Balanced-semiprime planting would change the computational core to generic integer factorization; this paper supplies neither a distributional theorem nor an instance-visible sub-300-operation Track B route. |
| Give a partly erased planted cube and return the missing entries | The generator retains entries of a known explicit cube | **Track A unsupported:** the paper proves no hardness for this planted completion distribution.  Exposed construction data makes direct evaluation the compact and mechanical route; hidden data leaves ordinary completion search with no paper-supplied shortcut. |
| Randomly relabel a known pair and ask for the relabelling | The private transformation used by the generator | **Not rescued:** exposed maps make the answer immediate, while hidden arbitrary maps create an isotopy/reconstruction puzzle not analyzed in the paper.  Relabellings of one fixed pair also collapse under a correct canonical key. |
| Ask for a few queried cube cells rather than the cubes | Direct evaluation of the displayed construction | **V passes but H fails:** the direct formula/table access and the purported compact route are the same constant-cost procedure. |

The symbolic-recipe option was considered before rejecting on Track A.  It is
not a valid Track B benchmark: a self-contained statement would have to define
the recipe constructors, at which point the answer for Theorem 2 is obtained by
the two divisions already displayed in the statement.  If the constructors are
not defined, verification appeals to semantics the checker cannot execute.

Nor does reversing McNeish's product construction rescue the paper.  Asking a
solver to factor a large integer `q` and returning its factors can be inverse
generated, but the object being searched is then an integer factorization, not
a Latin cube, MDS code, orthogonal array, or forward product map.  Proposition
6 proves only that held component codes compose; it does not establish hardness
for recovering component orders from their product.  A cryptographic-size
semiprime would therefore have no paper-backed Track A distribution claim and
no short Track B route, while visibly structured factors make the factorization
itself immediate.  This would be a benchmark-convenience number-theory problem,
not coverage of this paper's design construction.

## Mechanical cost versus compact route

For a native `OA_1(3,5,q)` witness, an exact checker can scan the ten choices of
three columns and insert each projected triple into a set.  This costs
`binom(5,3)*q^3 = 10*q^3` triple projections, plus linear parsing and range
checks.  At the first new order:

| quantity at `q=84` | exact count |
|---|---:|
| cube cells | 592,704 |
| symbols in a pair of cubes | 1,185,408 |
| coordinates in the equivalent MDS/OA witness | 2,963,520 |
| OA triple projections in the standard exact verifier | 5,927,040 |
| compact-route output lower bound, cube form | 1,185,408 emissions |
| permitted answer atoms | 256 |
| permitted intended-route operations | 300 |

Even flattened as decimal integers with only commas and one pair of brackets,
the order-84 cube pair needs at least 3,415,105 characters: each cube contains
each symbol `q^2` times, the decimal labels `0,...,83` contain 158 digits in
total, and therefore the pair contains `2*84^2*158 = 2,229,696` digit
characters plus 1,185,407 commas.  This is a lower bound; a properly nested or
tagged serialization is longer.  The character cap is 2,000.

The relevant comparison is not "5.9 million verification operations versus a
short theorem citation."  A theorem citation is not the requested witness.
After noticing the construction, a solver must still compute and emit at least
1,185,408 symbols, so the native mechanical and compact routes are both
`Theta(q^3)` and both exceed the no-tool effort cap by nearly four orders of
magnitude at `q=84`.

At the maximum writable full-pair setting, `q=5`:

| quantity at `q=5` | exact count |
|---|---:|
| symbols in a pair of cubes | 250 |
| mandatory compact-route emissions | 250 |
| standard explicit route | evaluate Proposition 3's linear code and emit the same 250 symbols |
| mechanical/compact asymptotic ratio | 1:1 (both output-linear) |

So Track B has no useful window.  Small witnesses fit but are produced by the
same short explicit algorithm; the first mathematically new witnesses are
millions of atoms long, and insight does not remove that output work.

## Gate outcome

| requirement | result |
|---|---|
| G | **Passable.**  Theorem 2 is a theorem-backed construction; Proposition 6 also carries certificates through products. |
| H -- Track A | **Fails.**  The paper gives an explicit polynomial/output-linear construction in its theorem regime and no hardness theorem for any generated distribution. |
| H -- Track B | **Fails.**  For full native witnesses the mechanical and compact routes are the same `Theta(q^3)` output computation: 250 versus at least 250 emissions at the largest writable order, and at least 1,185,408 versus 1,185,408 emissions at the first new order.  Symbolic theorem invocations instead reduce to a constant-size lookup/substitution. |
| V | **Passable.**  Scan all ten 3-column projections of the submitted OA using exact integer tuples and check that each is a bijection onto `Q_q^3`. |
| Answer/effort suitability | **Fails for the paper's new regime.**  The order-84 pair needs 1,185,408 atoms and at least 3,415,105 flattened decimal characters; its intended output route is over 300 operations. |
| G7/G8 for relabelled fixed examples | **Fails as a substitute for scale.**  Correct canonicalization identifies symbol/coordinate relabellings as the same underlying problem, so they do not manufacture unrelated instances. |
| Overall | **Rejected at Step 0.**  No paper-native family found clears G, H, and V while remaining writable and structurally meaningful. |

The rejection is not based merely on the existence of an efficient algorithm.
It is based on the required comparison: wherever the answer is writable, the
explicit constructor is already the compact route; wherever the paper's new
construction is relevant, the witness and every honest route to it are far
beyond the output and operation caps.
