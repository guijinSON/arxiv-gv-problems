# Rejected at Step 0: no G/H/V witness family

Paper: Thomas F. Bloom, Will Sawin, Carl Schildkraut, and Dmitrii Zhelezov,
[_The sum-product conjecture is false for real numbers_](https://arxiv.org/abs/2605.28781),
arXiv:2605.28781v1.

I read the complete paper, including the proofs and variants, rather than relying
on the abstract. The strongest interpretation of the triaged candidate is:

> Given parameters for a ring/field and cardinality bounds, output a finite set
> \(A\) whose sumset \(A+A=\{a+b:a,b\in A\}\) and product set
> \(AA=\{ab:a,b\in A\}\) meet the stated bounds.

This does not satisfy the required combination of G, H, and V.

| gate | assessment | paper evidence |
|---|---|---|
| G - generatable | **Fails under the requested module contract.** The real-number construction needs an unbounded supply of high-degree totally real number fields with bounded root discriminant, exact embeddings, algebraic-integer lattice enumeration, and unit-group enumeration. Theorem 3.2 supplies the fields existentially, but the paper gives no deterministic standard-library algorithm producing defining polynomials and integral/unit bases for arbitrary sizes. The finite-field and function-field variants likewise depend on pro-2 towers or asymptotically good curves and line bundles rather than a self-contained elementary generator. | Theorem 3.2; Sections 3, 4, 7. |
| H - hard | **Fails decisively.** Once a suitable field is supplied, the paper itself gives the witness directly: Lemma 4.1 takes \(G=B^\times(Y)\), \(P=X+B^+(\epsilon X)\), and \(A=GP\). The many-sums/products construction is even more direct: Lemma 4.2 takes \(A=B^\times(Y)\). The paper proves extremal cardinality bounds, not computational search hardness, and contains no NP-hardness or comparable complexity theorem. Making the solver reproduce the paper's constructed set would test access to algebraic-number-theory machinery, not an intractable witness search. | Section 4, especially Lemmas 4.1 and 4.2. |
| V - verifiable | **Potentially passes only after changing the representation.** For an explicitly represented finite-field set, recomputing all pairwise sums and products and comparing cardinalities is cheap and exact. For the paper's real-algebraic construction, a self-contained exact checker would additionally need canonical algebraic-number representations and equality/arithmetic code. V alone cannot rescue the failures of G and H. | Definition in Section 1; finite-field variant in Section 7.2. |

Other possible witnesses do not fix the problem:

- Asking for a pair that realizes a stated sum or product is a two-table lookup
  after enumerating \(A+A\) or \(AA\), hence polynomial-time.
- For the paper's fixed \(k\), membership in \(kA\) or \(A^{(k)}\) is decidable by
  enumerating \(|A|^k\) tuples, which is polynomial for fixed \(k\). Letting \(k\)
  grow would leave the theorem's fixed-\(k\) regime and would import a different
  subset-sum-style problem not established by this paper.
- Sections 1.2 and 6 prove that certain multiplicative groups have exponentially
  many unit-equation solutions. Their proofs obtain solutions by pigeonhole and
  energy arguments; they do not provide inverse generation of a planted exact
  solution, nor a search-hardness result. The abundance of witnesses also works
  against an unsupported guess-resistance claim.

Section 5 makes the computational mismatch sharper: the quantified real
construction uses roughly \(X=\lfloor e^{1,140,402}\rfloor\) and \(Y=1,140,402\)
to obtain the displayed exponent saving, and the authors explicitly retain
asymptotic \((1+o(1))^d\) losses. Those are existence-scale parameters, not a
usable finite generator window with exact per-instance guarantees.

Therefore I stopped at Step 0 as required. I did **not** create
`gen_2605_28781.py`, `selftest_report.json`, or `llm_loop_transcript.jsonl`, and I
did not run the LLM hardening loop. Creating those files would falsely imply that
the mandatory gates had been reached and passed.
