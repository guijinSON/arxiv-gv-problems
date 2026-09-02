# Rejected: arXiv 2306.00850

Paper: Marija Bliznac Trebješanin and Pavao Radić, [*On extensions of
\(D(4)\)-triples by adjoining smaller elements*](https://arxiv.org/abs/2306.00850),
v2 (2024).

## Decision

The proposed family—construct a \(D(4)\)-quadruple, reveal its three larger
members, and ask for the smaller member—fails requirement **H (hard)**. The
only unlimited planted construction supported by the paper produces regular
quadruples, and the hidden answer then has an exact closed-form recovery.

No generator module, self-test report, or LLM hardening transcript was created.
The task explicitly requires stopping after Step 0 when G, H, or V fails.

## What the paper actually defines

Section 1 defines a \(D(4)\)-\(m\)-tuple as a set of distinct positive integers
such that \(xy+4\) is a perfect square for every two distinct members \(x,y\).
For a \(D(4)\)-triple \(\{x,y,z\}\), it gives

\[
d_{\pm}(x,y,z)=x+y+z+\frac{xyz\pm
\sqrt{(xy+4)(xz+4)(yz+4)}}{2}.
\]

The \(d_+\) value is an explicit larger extension and defines a *regular*
quadruple. Section 1 also explains that \(d_-\), when positive, gives the
companion smaller extension.

## The fatal solver

Suppose inverse generation starts from \(a<b<c\) and plants the regular value
\(d=d_+(a,b,c)\). The rendered problem would reveal \(b,c,d\) and ask for
\(a<b\). A solver computes, using exact integer arithmetic,

\[
a=b+c+d+\frac{bcd-
\sqrt{(bc+4)(bd+4)(cd+4)}}{2}=d_-(b,c,d).
\]

All three factors under the square root are promised squares, so the root is
exact and inexpensive to compute with integer square root. This is not merely
a statistical planting leak: it is the paper's defining formula, applied in
reverse. It succeeds on every regular planted instance. For example,
\(\{1,5,12,96\}\) is regular, and \(d_-(5,12,96)=1\).

Thus G and V would be straightforward, but H fails regardless of numeric size.
Increasing `n` only increases operand bit lengths; it does not remove the
closed-form attack.

## Why the harder-looking alternatives do not qualify

- Conjecture 1.2 asks whether one triple can have two different smaller
  extensions. The paper treats such a configuration hypothetically. It gives
  necessary inequalities in Theorem 1.3 and proves in Corollary 1.6 that only
  finitely many can exist, but it does not provide even one scalable planted
  family. Basing a generator on these counterexamples therefore fails **G**.
- Section 2 reduces irregular extensions to intersections of Pellian recurrence
  sequences. It explicitly notes that the relevant Pellian solutions can be
  described for each fixed pair and that the proofs finish bounded cases by
  search. More importantly, the section states that regular solutions occur at
  indices at most 2, while a non-regular solution would require the separate
  high-index regime (Lemma 2.6 in the paper's numbering). The paper supplies no
  inverse construction of unlimited high-index irregular intersections.
- Asking for any extension of a visible \(D(4)\)-triple is also easy: \(d_+\) is
  always explicitly available. Asking for nonexistence, uniqueness, or an
  optimum would violate the required witness contract.

## Gate evidence

The family is rejected before implementation:

| Requirement | Result | Evidence |
|---|---:|---|
| G | pass only for the easy regular regime | sample \(a,b,c\), compute \(d_+\) |
| H | **fail** | deterministic \(d_-\) attack solves 100% of regular plants |
| V | pass | check distinct positivity and the six values \(xy+4\) by integer square root |

Because H fails by a universal algebraic attack, random-guess measurements and
LLM failures could not establish hardness and would be misleading.
