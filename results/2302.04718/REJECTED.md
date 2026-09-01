# Rejected: arXiv 2302.04718

Paper: Sam Adriaensen, [*A note on small weight codewords of projective geometric codes and on the smallest sets of even type*](https://arxiv.org/abs/2302.04718).

## Decision

The proposed projective-incidence-code family satisfies **G (inverse generation)** and **V (cheap exact verification)**, but it fails **H (hardness)**. The paper gives both a closed-form construction of a valid witness and, in the highlighted regime `q in {4, 8}`, a complete classification of all minimum witnesses. I therefore stopped at Step 0, before writing a generator, fabricating gate measurements, or running the LLM hardening loop.

## Exact problem in the paper

Section 2 defines `C_k(n,q)` over the prime field `F_p`, where `q = p^h`, as the row span of the point-versus-`k`-space incidence matrix of `PG(n,q)`. A vector is in the dual precisely when its coordinate sum on every `k`-space is zero in `F_p`.

For even `q`, Section 3.2 specializes this to binary vectors. The support of a dual codeword of `C_1(n,q)` is a **set of even type**: a point set meeting every projective line in an even number of points. Result 3.4 states that a smallest nonempty such set has exactly

```text
(q + 2) q^(n - 2)
```

points. Thus a natural witness would be a list of exactly that many point labels, checked by counting its intersection with every supplied line modulo two. That check is deterministic, exact, and does not need the planted answer.

## Why the proposed family is easy

Construction 3.5 explicitly constructs a minimum set of even type for every even `q`: choose a plane `pi`, an `(n-3)`-space `tau` skew to it, and a hyperoval `O` in `pi`; then return the union of the joins `<P,tau>` for `P in O`, with `tau` removed. For `q in {4,8}`, the paper gives the regular hyperoval directly as

```text
{(s^2, s t, t^2) : (s,t) in PG(1,q)} union {(0,1,0)}.
```

Consequently, a solver does not have to recover the planted codeword. It can independently construct another correct answer from the instance's projective coordinates.

This is not merely one easy subfamily. Theorem 1.1 proves that for `q in {4,8}` every minimum set of even type is a hypercylinder over a regular hyperoval. Result 3.1 reduces minimum dual codewords for general `k` to the line case, and Corollary 3.16 says that the minimum codewords are exactly characteristic vectors of these embedded hypercylinders. The same corollary gives their count and states that they form one automorphism orbit. The paper's classification therefore exposes, rather than hides, the complete structure of the requested witnesses.

Randomly renumbering points would not repair H. Relabelling is a symmetry, not a new mathematical instance. With point-line incidence supplied, one may choose a plane, find one of its constant-size hyperovals for fixed `q = 4` or `8`, and build the cone using incidence. Brute force inside the plane is constant work with respect to growing `n`; all remaining incidence operations are polynomial in the explicitly listed geometry. Supplying standard coordinates makes the displayed formula an even more immediate solution.

## Why nearby formulations do not qualify

- **Use larger even `q`.** Construction 3.5 still supplies a regular hyperoval and hence a minimum hypercylinder in closed form. Section 5 notes that non-regular hyperovals exist for even `q > 8`, but asking for *any* minimum witness remains easy.
- **Require a non-hypercylinder.** Problem 5.1 asks whether minimum even sets different from hypercylinders exist for `q = 2^h > 8`. Their existence is not guaranteed by the paper, so an inverse generator cannot know such a witness in general; this fails G.
- **Use odd, non-prime `q`.** Problems 5.2 and 5.3 leave the minimum weight and structure open. The paper does not provide an answer-first construction in the unknown minimum regime. Making minimum weight or optimality part of the submitted claim is also forbidden by the task's witness contract.
- **Ask for a small primal-code word.** Section 4 proves that every nonzero word of `C_(n-1)(n,q)` of weight at most `2 q^(n-1)` is a scalar hyperplane characteristic vector or a scalar difference of two such vectors. These are again closed-form witnesses.
- **Replace projective geometry by an arbitrary planted binary matrix.** Section 2 uses general incidence structures for definitions, but the paper proves no computational-hardness result or hard planted distribution for arbitrary matrices. That substitution would be a generic planted low-weight-codeword problem, not a parameter regime established by this paper, and the planting mechanism would need an independent average-case hardness analysis.

## Gate outcome

| requirement | result |
|---|---|
| G — sample a witness first | Pass: sample a plane, vertex, and regular hyperoval, then form its hypercylinder |
| H — no known polynomial-time or closed-form method | **Fail: Construction 3.5 is closed form, and Theorem 1.1 classifies all minimum witnesses for `q in {4,8}`** |
| V — cheap exact witness check | Pass: check the required cardinality and every line-intersection parity |

No `gen_2302_04718.py`, `selftest_report.json`, `README.md`, or `llm_loop_transcript.jsonl` was created. Running `scripts/harden.py` after the analytical H rejection would contradict the instruction to stop when any of G, H, or V fails.
