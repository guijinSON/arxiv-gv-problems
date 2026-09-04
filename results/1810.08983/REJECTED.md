# Rejected at Step 0

Paper: Pedro Hecht, [*PQC: Triple Decomposition Problem Applied To
GL(d, Fp) - A Secure Framework For Canonical Non-Commutative
Cryptography*](https://arxiv.org/abs/1810.08983), arXiv:1810.08983v2.

## Decision

No generator is shipped.  The paper's native computational TDP family fails
hardness gate **H**.  A private-key component is recovered by finite-field
linear algebra from the public matrices, so inverse-generating secret factors
would plant a witness for a polynomial-time-solvable distribution.  This is
exactly the disqualifying case in the Step 0 certificate-cost test.

`TRACK = "A"` would be false: the paper supplies no hardness theorem for this
distribution, only a brute-force cardinality argument in Section 6, and the
linear public equations admit a direct polynomial-time attack.  `TRACK = "B"`
would also be inappropriate: at the paper's proposed parameters `d=8, p=251`,
the attack is tiny (measured below), while executing the native dense change of
basis needed to obtain the purported compact route already exceeds the
300-operation no-tool cap.  Publishing the already-transformed matrices would
instead create a simpler augmented problem not posed by the paper, and its
row/column-scaling formula would be the obvious solution rather than a hidden
structural shortcut.

## Exact definition checked

Section 3 defines Alice's public matrices as

```text
u = a1 x1
v = x1^-1 a2 x2
w = x2^-1 a3
```

Appendix I specializes the relevant subgroups of `GL(d,F_p)` to

```text
x2 = S^-1 diag(x) S
a3 = Q^-1 diag(a) Q,
```

where the bases `Q` and `S` are public and every diagonal entry is nonzero.
The paper's Computational TDP asks for *any component* of the private key, so
recovering `a3` is sufficient.  Merely asking for three unrestricted factors
of one product would be even less suitable: `(I, I, product)` is always a
trivial answer and does not encode the paper's subgroup constraints.

## Polynomial-time certificate-producing attack

From `w = x2^-1 a3`, multiply by `x2` and change to the two public bases.  Set

```text
M = S w Q^-1
N = S Q^-1.
```

Then the unknown diagonal entries obey

```text
diag(x) M = N diag(a),
```

or, entry by entry,

```text
x_i M_ij = N_ij a_j                 for all i,j.
```

These are `d^2` homogeneous **linear** equations in only `2d` unknown field
elements.  Gaussian elimination recovers the solution space.  On the generic
instances produced by Appendix I, the common nonzero support of `M` and `N`
is connected, so one may instead normalize one coordinate and propagate the
remaining row and column scalings directly.  The planted solution guarantees
an all-nonzero solution.  Reconstruct

```text
x2 = S^-1 diag(x) S
a3 = Q^-1 diag(a) Q;
```

then exact multiplication verifies `x2 w = a3`.  This already recovers the
private component requested by Computational TDP.  It also extends to a full,
directly checkable decomposition: form `c = v x2^-1` and apply the same
row/column-scaling calculation to

```text
R c P^-1 = diag(x1)^-1 (R P^-1) diag(a2).
```

This recovers `x1` and `a2`, after which `a1 = u x1^-1`.  A checker only has
to test subgroup membership and the three displayed public equations.  Thus
the attack outputs precisely the finite witness the benchmark would request;
it does not merely distinguish instances or recover an unrelated session
value.

With straightforward standard-library Python over `F_251`, this attack
recovered and exactly verified the **full five-matrix witness** on **100/100**
independently generated `d=8` instances in **0.086532 s total**, or **0.8653
ms/instance** on this runner.  Its cost is `O(d^3)` field operations when
exploiting diagonal equivalence (matrix inversion and multiplication), or
polynomial time by ordinary elimination on the displayed
`d^2`-by-`2d` systems.

## Paper-level corroboration

- Section 6 of the source paper itself displays equations (4)--(6), singles
  out equation (5) as quadratic, and bases its security conclusion on that
  observation plus a `249^32` brute-force count.  A large candidate space does
  not survive the linear attack above.
- The same author's follow-up paper,
  [*PQC: Extended Triple Decomposition Problem (XTDP) Applied To GL(d,
  Fp)*](https://arxiv.org/abs/1812.05454), states in its abstract that the
  Algebraic Span Attack focuses on the original protocol's linear equations
  and that this appears to break the previous work; XTDP is presented as a
  countermeasure.
- Ben-Zvi, Kalka, and Tsaban,
  [*Cryptanalysis via Algebraic Spans*](https://eprint.iacr.org/2014/041),
  Sections 4--5, give a polynomial-time algebraic-span cryptanalysis of the
  Triple Decomposition key exchange protocol, with a stated upper bound
  `O(k n^6)` for the general matrix representation.  The diagonal-conjugate
  specialization in arXiv:1810.08983 permits the simpler attack above.

## Gates not run

G1--G9 and the oracle hardening loop were intentionally not run.  The task
requires stopping at Step 0 when G, H, or V fails, and H already fails by a
standard exact algorithm.  Consequently there is no
`gen_1810_08983.py`, `selftest_report.json`, or oracle transcript: creating
those artifacts would misrepresent a rejected Track A family and waste the
builder run the Step 0 rule is designed to avoid.
