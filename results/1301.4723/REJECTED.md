# Rejected at Step 0: arXiv 1301.4723

Paper: Abdurashid Mamadolimov, Herman Isa, and Moesfa Soeheila Mohamad,
[*Practical Bijective S-box Design*](https://arxiv.org/abs/1301.4723)
(2013).

## Decision

This paper does not support a self-contained problem family satisfying **G, H,
and V** simultaneously. The prior-triage proposal---construct a bijective
finite-field S-box from selected power functions and verify its truth table---is
generatable and exactly checkable only in regimes where the paper also gives a
direct construction or a small exhaustive computation. The one stage that could
be turned into a search problem, replacing duplicate image values while retaining
good differential uniformity and nonlinearity, is neither specified exactly nor
proved to scale.

The family therefore fails **H**, and its most promising repair-search variant
also fails **G**. I stopped before writing a generator or running the oracle
hardening loop, as the task requires. No `TRACK` declaration would repair the
problem: Track A has no supported hard distribution, while Track B has no
paper-backed compact route distinct from the already-short mechanical
construction.

## The Step-0 question

The decisive question is: *what algorithm produces the certificate, and what
does it cost?* For each paper-native candidate, the answer is one of the
following.

| Candidate certificate | Producing algorithm | Cost in the explicit truth-table model |
|---|---|---:|
| A non-affine Boolean permutation from Section 3 | The two-step construction in the proof of Theorem 3.1 | Linear up to sorting/shuffling, `O(n 2^n)` bit work |
| Whether `x -> x^d` is bijective, or its fibre size | Compute `gcd(d, 2^n-1)` using Theorem 4.1 | Polynomial in `n` |
| DU/NL of `x^d + x^(2^i)` from those of `x^d` | Copy the values using Theorem 4.2 | Constant work after identifying the form |
| DU/NL of an explicit S-box table | Difference-table enumeration and an exact Walsh transform | Polynomial in the table length `N=2^n` (roughly `O(N^2)` to `O(N^2 log N)`) |
| A strong repaired `8 x 8` S-box from Section 5 | Search unspecified duplicate replacements and exhaustively score them | Fixed-size experiment; no scalable construction or complexity result is given |

Thus the exact certificates are either direct outputs of efficient algorithms,
or the paper does not give enough information to construct them by a permitted
answer-first route.

## What the paper actually proves

Section 2 defines an `n x n` S-box as a vectorial Boolean map from
`F_2^n` to itself. It is a Boolean permutation precisely when it is balanced,
meaning that every output occurs once. Differential uniformity is the maximum,
over nonzero input difference `a` and output difference `b`, of the number of
solutions to

```text
F(x + a) + F(x) = b.
```

Nonlinearity is the minimum Hamming distance between every nonzero linear
combination of the output components and the affine Boolean functions. These
definitions make verification of a supplied finite truth table exact and
polynomial in the table's displayed length. They do not make finding the table
hard.

Theorem 3.1 is itself a generator. Its proof says to choose a balanced non-affine
Boolean function as one component, choose two permutations of the
`(n-1)`-bit vectors, and use those two lists for the remaining components on the
two fibres of the chosen Boolean function. The result is automatically a
non-affine Boolean permutation. Asking a solver to output such a permutation is
therefore not a hard witness search. If `random_candidate` incorporates the
obvious balance and permutation constraints stated in the problem, essentially
every candidate made by the same recipe is valid, so this formulation would also
fail the structure-aware spirit of G4.

Section 4 makes the power-function candidates easier still. It states that
`x -> x^d` is bijective exactly when `gcd(d, 2^n-1)=1`. Theorem 4.1 gives the
fibre size as that gcd. Theorem 4.2 proves that adding the linearized Frobenius
term `x^(2^i)` leaves differential uniformity and nonlinearity unchanged. These
are direct gcd and theorem-substitution computations, not searches over a large
witness space.

Section 5 is only an `8 x 8` experiment. It first enumerates the power functions
over `F_(2^8)`, then considers all `256^2` coefficient pairs in
`alpha*x^3 + beta*x^4`. For three reported pairs, the image has 192 values. The
paper then says that remaining duplicate image elements are replaced by missing
field elements "in such a way" that DU and NL are not compromised significantly.
It reports the final pair `(DU, NL) = (8, 102)`, but it gives none of the following:

- the repaired 256-entry S-box truth tables;
- the positions replaced and the replacement values;
- the irreducible polynomial and basis needed to interpret field elements such
  as 50 and 89 exactly;
- an algorithm that chooses the replacements;
- a theorem guaranteeing suitable replacements for general `n`; or
- a hardness, average-case, or parameterized result for finding them.

Consequently, reproducing this construction would require solving the very
repair search used to obtain the certificate, which violates G. Hard-coding a
newly searched base table and applying affine relabellings would not fix the
provenance problem, and at `n=8` it would only recycle a finite equivalence orbit.

## Candidate formulations considered

| Candidate task | Gate failure | Reason |
|---|---|---|
| Output a non-affine Boolean permutation with one prescribed balanced component | **H / G4** | Theorem 3.1 gives the answer directly, and the statement leaves a huge number of equally immediate valid completions. |
| Decide or witness bijectivity of a power map | **H / G4** | One gcd decides it; a yes/no or small numeric answer also has an answer space far too small for the required guess-resistance claim. |
| Return DU and NL for a binomial power-plus-Frobenius map | **H / G4** | Theorem 4.2 returns the two numbers from the power map, and the two-integer answer is easily guessed relative to the required threshold. |
| Return the full truth table of the inverse/AES-style power permutation | **H / G9** | Section 1 gives the inverse exponent explicitly. Evaluating it is routine, while typing 256 entries approaches the answer cap and tests transcription rather than insight. |
| Repair `alpha*x^3 + beta*x^4` into a strong bijection | **G / scaling** | Section 5 omits the repairs and supplies no theorem-backed construction beyond the fixed `n=8` search. |
| Find affine maps showing equivalence to a power function | **paper relevance / H unsupported** | The paper mentions equivalence but gives no associated hard search regime; hiding random affine maps would add a new affine-equivalence puzzle rather than instantiate a result of the paper. |
| Invert a rendered S-box at one output | **H** | An explicit table is inverted by a linear scan; a power representation is inverted by standard finite-field arithmetic. The paper makes no one-wayness claim. |

## Why neither hardness track is honest

**Track A** is unavailable. The paper contains no worst-case hardness theorem,
no average-case theorem for a generated distribution, and no parameter regime in
which certificate recovery is claimed to resist an efficient general method.
Cryptographic DU/NL quality measures resistance of a cipher component to
differential and linear cryptanalysis; it is not evidence that constructing or
recognizing that component is a hard witness problem.

**Track B** is also unavailable for the natural constructions. The polynomial
algorithms above are already the compact route: a gcd, the two-list construction,
or Theorem 4.2. There is no million-operation mechanical method paired with a
distinct sub-300-operation structural insight. Conversely, exhaustive DU/NL
scoring may be mechanically large, but its result is only a tiny pair of
integers, and the paper's theorem makes the intended binomial cases immediate.
The unspecified duplicate-repair stage has no compact route that the generator
can carry by construction.

## Gate outcome

| Requirement | Outcome | Evidence |
|---|---:|---|
| G --- answer known by permitted construction | Possible for Theorems 3.1, 4.1, and 4.2; **fails** for the potentially difficult Section 5 repair search | The easy cases are explicit; the repair choices and a general existence theorem are absent |
| H --- claimed hardness for the generated distribution | **Fails** | Direct constructions, gcd, theorem substitution, and polynomial truth-table algorithms solve all exact paper-backed candidates |
| V --- cheap exact witness checking | Possible | Bijectivity, difference counts, Walsh sums, and finite-field evaluations can all be recomputed exactly |
| Unlimited scalable diversity | **Not supplied for the strong repaired family** | The reported strong construction is fixed at `n=8`; only the easy structural theorems are general in `n` |
| Overall | **Rejected** | No one family clears all gates simultaneously |

No `gen_1301_4723.py`, `selftest_report.json`, `README.md`, or hardening
transcripts were created. Oracle failures could not cure this analytical Step-0
failure and would provide misleading evidence for a family whose standard
algorithm is already known.
