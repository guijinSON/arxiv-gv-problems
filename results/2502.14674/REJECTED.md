# Rejected: arXiv 2502.14674

Paper: [*Some new results on permutation trinomials over finite fields with even characteristic*](https://arxiv.org/abs/2502.14674), Kirpa Garg, Sartaj Ul Hasan, and Chandan Kumar Vishwakarma.

## Decision

This paper does not supply a problem family satisfying G, H, and V simultaneously. The prior triage suggestion—ask for parameters of a permutation trinomial and verify that it permutes the field—fails both **H (hardness)** and, under direct checking, **V (cheap verification)**. I therefore stopped before writing a generator or running the LLM hardening loop, as required by Step 0.

## What the full paper actually proves

Section 2 defines a permutation polynomial as one whose evaluation map is a bijection of the entire field. Its unit-circle criterion (Lemma 2.2) reduces permutation of

\[
X^r h(X^{q-1}) \quad\text{on } \mathbb F_{q^2}
\]

to a gcd test and permutation of a rational map on the order-\(q+1\) unit circle.

Section 3 does not present an open-ended search space. It proves exact classifications for three fixed exponent triples:

| polynomial over \(\mathbb F_{q^2}\), \(q=2^m\) | exact condition |
|---|---|
| \(X^{11}(X^{10(q-1)}+X^{4(q-1)}+1)\) | \(m\not\equiv0\pmod5\) |
| \(X^9(X^{8(q-1)}+X^{6(q-1)}+1)\) | \(m\) odd |
| \(X^7(X^{7(q-1)}+X^{5(q-1)}+1)\) | \(m\) even and \(m\not\equiv0\pmod3\) |

Thus a solver asked to return a valid \((r,\alpha,\beta)\) can choose among only three published constants and apply a congruence test. Increasing \(m\) increases the field but does not enlarge or conceal the answer. This is a closed-form lookup, so **H fails** and the answer space is far too small to be guess-resistant.

## Why nearby witness formulations also fail

- **“Return a polynomial that permutes the field.”** Knowing the answer first is easy using Section 3, but the same theorem makes finding it trivial. Directly verifying bijectivity by evaluating all \(2^{2m}\) field elements is exponential in the natural input length \(m\), so it is not the requested cheap substitution-style verifier. Using the Section 3 theorem as the checker restores cheap verification only by turning the task into the same three-entry lookup.
- **“Return a preimage under one of the permutation trinomials.”** A submitted preimage is cheaply checked, and it can be planted by choosing \(x\) before computing \(F(x)\). However, Lemma 2.2 reduces inversion first to a fixed-degree equation on the unit circle and then to a fixed-degree field equation. Standard finite-field polynomial root finding solves those equations in randomized polynomial time in \(m\). Hence **H fails**.
- **“Return a collision for the non-permutation trinomial.”** Section 5 studies the fixed map with \((r,\alpha,\beta)=(9,7,3)\). A collision is cheaply checked, but finding one again reduces to roots of an explicit bounded-degree polynomial over a finite field. For \(7\mid m\), the proof even gives the immediate source of collisions: roots of \(X^7+X^3+X^2+X+1\). For the remaining cases the paper proves existence via an absolutely irreducible curve and the Hasse–Weil bound, but finite-field root/factor algorithms still defeat the bounded-degree search formulation. It also does not provide an answer-first inverse generator for arbitrary sampled collisions without changing the paper's fixed family.
- **“Return a QM-equivalence witness.”** Section 4 defines the witness as an exponent \(d\) and two nonzero scalars, but exponent supports have size three, so all six support matchings can be tried with modular arithmetic. More decisively, Section 6 explicitly computes the relevant \(d\) using CRT. This is polynomial-time/closed-form, so **H fails**.
- **Factorizations or irreducibility proofs.** The factorizations used in Section 3 are bounded-degree and computable by standard algebra algorithms. The absolute-irreducibility argument in Section 5 is a proof, not the bounded structured witness required by the task.

## Gate outcome

| requirement | result |
|---|---|
| G — inverse-generatable | Possible only for formulations that fail H or V |
| H — no known polynomial/closed-form method and large answer space | **Fail** |
| V — cheap exact witness verification | Collision/preimage witnesses pass V; permutation recognition by exhaustive evaluation does not |

No `gen_2502_14674.py`, `selftest_report.json`, or oracle transcript was created. Running `harden.py` would be inappropriate after the analytical H/V rejection and would contradict the task's instruction to stop when a family fails G, H, or V.
