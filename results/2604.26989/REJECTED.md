# Rejected: arXiv 2604.26989

Paper: Anthony Kable, Melissa Mills, and David J. Wright, [*Subgroups of
Finite Fields As Cap Sets*](https://arxiv.org/abs/2604.26989), arXiv:2604.26989.

## Decision

The proposed family passes inverse generation (G) and exact verification (V),
but fails the required hardness condition (H). No generator module is shipped,
and the LLM hardening loop was not run, because Step 0 requires stopping as soon
as one of G/H/V fails.

## Definition and regimes checked

Definition 1 in Section 1 says that a cap in `F_(3^m)` contains no three
**distinct** elements whose sum is zero, while a cap in `F_(2^m)` contains no
four **distinct** elements whose sum is zero.

Theorem 1 proves that the following explicitly defined multiplicative subgroups
are caps:

- `G_(81,20)`, `G_(243,22)`, and `G_(729,28)` in characteristic 3;
- `G_(2^(2m), 2^m+1)` in characteristic 2 for every `m`;
- `G_(2^(2m), 2^m+1) union {0}` when `m` is even.

The paper defines `G_(q,d)` as the unique order-`d` subgroup of `F_q^*`, both as
the roots of `x^d = 1` and as the image of an explicit power map. Corollary 2
observes that its multiplicative cosets are caps as well.

## Why H fails

There is no hard witness search here. Given a primitive element `g`, the subgroup
is simply

```text
{g^((q-1)j/d) : 0 <= j < d}.
```

Thus the candidate answer suggested by the triage is a closed-form construction,
not a witness hidden in a large search space. A coset is just a scalar multiple
of the same list. Section 7 even supplies primitive polynomials and explicit
coordinate tables for the `F_81` and `F_64` examples. Section 4 states that all
the paper's theorems can be checked by relatively simple and fast computer
algebra calculations.

The paper proves structural cap properties, maximality/completeness facts in a
few fixed small fields, and an infinite explicit construction. It does **not**
prove NP-hardness or any other computational lower bound for finding these sets,
nor does it identify a parameter regime in which this construction becomes a
hard search problem. Increasing `m` only enlarges an explicitly enumerable
subgroup; it does not remove the formula.

Trying to hide a subgroup among decoys would define a new planted-recovery
problem for which the paper supplies no hardness result. Asking for a forbidden
additive tuple instead is also unsuitable: such a tuple can be found by standard
sum-table searches in polynomial time in the listed set size. Asking for a
maximum or complete cap would violate the required witness/optimality contract
and, in the fixed cases treated here, would not provide an unlimited scalable
family.

## Gate assessment

| Condition | Result | Reason |
|---|---:|---|
| G | pass | Sample a field representation and subgroup/coset, then enumerate the known cap. |
| H | **fail** | The witness has an explicit power-enumeration formula and no hard search theorem applies. |
| V | pass | Check size/distinctness, field membership, and all forbidden 3- or 4-term sums exactly. |

Because H fails before implementation, reporting G1-G8 measurements or an oracle
transcript would give false assurance rather than evidence for an acceptable
problem family.
