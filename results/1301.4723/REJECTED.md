# Rejected at Step 0: the strong S-box repair is an unspecified search

Paper: Abdurashid Mamadolimov, Herman Isa, and Moesfa Soeheila Mohamad,
[*Practical Bijective S-box Design*](https://arxiv.org/abs/1301.4723),
arXiv:1301.4723.

## Decision

No generator is shipped. I read the complete five-page paper, including the exact
definitions in Sections 2.1--2.3, the construction in Theorem 3.1, the finite-field
results in Theorems 4.1--4.2, and the proposed strong-S-box construction in Section
5. The prior-triage proposal fails **G** for the paper's native strong-S-box task:
the last and decisive operation is not a construction at all. Section 5 says that
the duplicate image values are replaced by missing values "in such a way" that
differential uniformity (DU) and nonlinearity (NL) are not compromised, but it
does not specify the replacements, an algorithm for finding them, or a theorem
that makes an arbitrary replacement work.

Exact checking would be straightforward, so V is not the problem. A proposed
truth table can be checked for bijectivity and its DU and NL can be recomputed.
What is missing is a certificate-producing construction that does not solve the
same repair problem posed to the benchmark solver.

Track A is also unsupported: the paper proves no worst-case or distributional
hardness result for finding the replacements, coefficients, or a strong S-box.
Track B was considered before rejecting, but the paper supplies no compact route
for the repair search. Its proved side problems instead have mechanical and
compact routes of essentially the same length. Thus the paper fails to yield a
family satisfying G, H, and V under either track.

## What the paper actually constructs

For an 8-bit field, Section 5 starts with the cubic Gold map `x -> x^3`. Its image
has 86 elements and Theorem 4.1 explains the three-to-one multiplicity on the
nonzero field elements. The paper then considers

`F_(alpha,beta)(x) = alpha*x^3 + beta*x^4`.

Theorem 4.2 explains why adding the linear Frobenius term preserves the DU and NL
of the power map (up to the harmless nonzero output scaling used in Section 5).
The selected binomial image is reported to contain 192 of the 256 field elements.
It is still not a permutation. The paper's final instruction is to replace the
remaining duplicate outputs by elements outside that image while retaining good
DU and NL. No repaired truth table is printed.

The paper reports an exhaustive coefficient domain of `256^2 = 65,536` pairs and
lists three best pairs,

`(50, 89), (167, 16), (218, 71)`.

Those constants are results of the search, not a scalable parameterized theorem.
The paper reports the final quality `(DU, NL) = (8, 102)` only for the 8x8 case.
Its statement that preceding results hold for general `n` does not supply a
general repair theorem or general strong-S-box parameter regime.

## Certificate-production cost and the missing compact route

The image size 192 leaves exactly 64 excess table occurrences after retaining one
occurrence for every image value, and exactly 64 missing output values. Even after
the 64 positions to change have been fixed, assigning the missing values has

`64! = 126886932185884164103433389335161480802865516174545192198801894375214704230400000000000000`

possibilities. This is only a lower bound on the repair choices because choosing
which occurrence of a repeated value to retain adds further choices. Arbitrary
assignments are not certified to preserve the required DU and NL.

The paper's stated coefficient scan already visits 65,536 binomials. With `x^3`
and `x^4` precomputed, merely materializing every 256-entry table takes about
`65,536 * 256 * 3 = 50,331,648` elementary field multiply/XOR operations under a
simple accounting. Checking one repaired candidate needs 65,280 derivative-table
entries for DU. NL can be checked with 255 length-256 Walsh transforms, costing
261,120 butterfly pairs, or 522,240 integer additions/subtractions, after the
component signs are formed. These are perfectly acceptable verifier costs for a
single 8x8 table; they do not produce the table.

The **compact route length is undefined**: Section 5 gives no invariant, symmetry,
change of variables, or formula that selects the 64 replacements. The only route
available from the text is search followed by recomputation of DU and NL. Track B
requires an efficient mechanical algorithm *and a distinct sub-300-operation
route after recognizing structure*. This candidate has neither such a compact
route nor a specified certificate-producing algorithm. Calling the omitted search
"practical" does not fill that gap.

Hard-coding a repair found independently would not repair the family. It would
give at most a fixed 8x8 base example and its affine relabellings; a correct
`canonical_key` would collapse those relabellings rather than count them as an
unlimited supply of unrelated instances. Varying `(alpha,beta)` would again require
solving the undocumented repair problem for each new instance.

## Track-B audit of the proved side results

| Paper-native candidate | Mechanical route | Compact route | Outcome |
|---|---:|---:|---|
| Find the multiplicity of `x -> x^d` (Theorem 4.1) | Euclidean algorithm for `gcd(d, 2^n-1)` | The same gcd; for the paper's `n=8,d=3`, `255 mod 3 = 0` is one division | H fails on Track A; there is no Track-B gap |
| Give DU/NL after adding `x^(2^i)` (Theorem 4.2) | Substitute the linear term into the definitions | The displayed proof is the same short chain of identities | H fails; it is a theorem lookup |
| Complete a balanced non-affine component to a Boolean permutation (Theorem 3.1) | Partition the inputs by the component bit and assign two permutations | Exactly the two-step construction in the proof | H fails; at `n=8` it directly writes 256 outputs |
| Return one of the best coefficient pairs in Section 5 | Scan 65,536 pairs and perform the missing repair search | Read one of the three printed pairs | H fails and the fixed answer set is not an unlimited family |
| Find the 64 output replacements producing DU 8 and NL 102 | Unspecified combinatorial search; at least `64!` assignments after positions are fixed | None supplied | **G fails; Track B unavailable** |

Artificially choosing huge exponents with a specially planted sparse modular
inverse could create a no-tool congruence puzzle from the cyclic-group observation
in the proof of Theorem 4.1. That structure, its hard distribution, and its compact
decoding route are not in this paper; it would be a new benchmark construction
that discards the S-box repair and cryptographic criteria. It therefore is not used
to claim coverage of this paper.

## Gate outcome

| Requirement | Outcome | Evidence |
|---|---|---|
| G -- generatable | **Fails for the native strong-S-box family** | Section 5 omits the duplicate-replacement algorithm and does not print a repaired truth table; arbitrary repairs are not theorem-certified. |
| H -- Track A structural hardness | **Fails / unsupported** | No hardness theorem or hard generated distribution appears in the paper; the coefficient results are an 8-bit exhaustive experiment. |
| H -- Track B no-tool compression | **Fails for every generatable candidate considered** | Theorems 3.1, 4.1, and 4.2 make their witnesses direct; the only large search, the repair, has no compact route. |
| V -- exact verification | Would pass | Enumerate the truth table, derivative distribution table, and Walsh spectra using exact finite-field and integer operations. |
| G7/G8/G9 | Cannot be reached honestly | The cryptographically strong construction is fixed at 8x8 and supplies neither scalable certified repairs nor canonically distinct transformed instances. |

The family is therefore rejected at Step 0. No module, self-test report, or oracle
transcript was produced: running the hardening loop cannot turn an unspecified
certificate search into inverse generation or a theorem-backed construction.
