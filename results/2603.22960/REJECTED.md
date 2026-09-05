# Rejected: no hard witness family in arXiv:2603.22960

Paper: [J. Chen, P. Hua, C. H. Li, and Y. Wu, *Locally 2-homogeneous block designs*](https://arxiv.org/abs/2603.22960), v2.

## Decision

The paper supports exact, theorem-backed generators and cheap verifiers, so **G** and **V** are available. It does not support an acceptable **H** claim on either track.

- **Track A fails.** The paper is a classification of locally 2-homogeneous designs. Theorem 1.2 lists five explicit infinite geometric families and finitely many table cases. Section 3 constructs the infinite families directly, while the sporadic cases are checked by the five-step Magma procedure following Construction 2.2 and Lemma 2.3. There is no hardness theorem or parameter regime in the paper, and the generated affine/projective instances lie in explicit finite-geometry families with direct linear-algebraic formulas.
- **Track B also fails for the strongest generator attempted.** The retained draft asks for the positive intersection number of two intersecting affine hyperplanes. Lemma 2.4 gives it directly from the displayed design parameters:
  \[
  c=\frac{(k-1)(\lambda-1)}{r-1}+1.
  \]
  For the affine-hyperplane family in Section 3, Example 3.4(2), the still shorter identity is \(c=k^2/v\), equivalently recover \(q=v/k\) and return \(k/q\). Thus the certificate is direct evaluation, not a search witness.

## Required cost comparison

At the draft shipping preset there are 32 design records.

| route | exact work per shipping instance | measured Python time |
|---|---:|---:|
| Mechanical standard method: evaluate Lemma 2.4 independently for every record | 192 arithmetic operations (three subtractions, one multiplication, one exact division, and one addition per record) | 7.35 microseconds/instance, averaged over 200,000 repetitions |
| Compact affine route: use \(c=k^2/v\) for every record | 64 arithmetic operations (one multiplication and one exact division per record) | 4.96 microseconds/instance, averaged over 200,000 repetitions |

The compact route is only a factor of three shorter than the mechanical route, and both are below the task's 300-operation no-tool cap. There is no million-operation-versus-dozen-operation compression gap. Increasing the number of records merely lengthens the answer and arithmetic transcript; it does not create a new insight, and the 256-atom/2,000-character answer cap prevents using repetition as a substitute for hardness. Accordingly this is not a defensible Track B family.

## Other native formulations checked

- Asking which classified family a promised locally 2-homogeneous design belongs to reduces to the classification in Theorem 1.2 and its finite tables; for generated Section 3 instances it is a formula/lookup problem.
- Asking for the parameters or intersection numbers of the projective, affine, Hermitian-unitary, or symplectic families is answered by the displayed formulas in Section 3.
- Asking for a full executable certificate of local 2-homogeneity would require enough concrete group permutations or matrices to certify every stabilizer action. In the growing infinite families that witness grows with the ambient dimension and does not fit the 256-atom answer cap; restricting it to one local mapping gives an ordinary finite-field linear-algebra problem with no paper-backed hardness regime.
- Problem A in the introduction (classify all flag-transitive designs) is open. It cannot be inverse-generated with a complete, cheaply executable classification certificate, so it fails G/V rather than supplying a hard family.

The experimental module is retained as `rejected_gen_2603_22960.py` so this decision can be replayed. It is not a shippable generator: its old adversary panel never tested the direct affine identity \(c=k^2/v\). The omitted attack was run after the audit and solved 8/8 instances at each of `demo`, `easy`, `medium`, and `hard` (32/32 total).
