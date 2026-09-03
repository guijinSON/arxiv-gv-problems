# Rejected: arXiv 2412.18598

Paper: Noah Kravitz, [*Relative sizes of iterated sumsets*](https://arxiv.org/abs/2412.18598), arXiv:2412.18598v3.

## Decision

No problem generator is shipped because no problem family native to this paper
satisfies G, H, and V simultaneously. The prior-triage proposal—given prescribed
relative orders, find finite integer sets realizing them—passes inverse generation
but fails **H**: the paper's main contribution is an explicit construction for
exactly that search problem. Depending on how arbitrary candidate sets are encoded,
cheap exact verification can also fail **V**.

I read the full v3 LaTeX source, including all proofs in Sections 2–4, rather than
relying on the abstract. The paper contains no computational-hardness theorem,
complexity reduction, FPT boundary, or average-case hardness claim.

## Exact definition and proved regimes

For a positive integer `h` and a subset `A` of an abelian group, the paper defines

\[
hA=\{a_1+\cdots+a_h:a_1,\ldots,a_h\in A\}.
\]

Repetitions are allowed. For sets `A_1,...,A_n`, a permutation records the relative
order of the cardinalities `|hA_1|,...,|hA_n|` when those cardinalities are distinct.

Theorem 1.1 states that for every finite list of arbitrary permutations
`sigma_1,...,sigma_H`, sufficiently large abelian groups contain finite sets
realizing those orders at every `h=1,...,H`. Proposition 2.2 gives the integer
case. Theorem 1.2 strengthens the integer result to prescribed ties and a prescribed
eventual order for all `h>H`.

These are existence results with constructive proofs:

- Proposition 2.3 assembles one building-block family per `h` by Cartesian products;
  sufficiently increasing multiplicities make the `h`th block dominate.
- Section 2.3 explicitly takes `B_i=X(s_i,t)`, where `X(s,t)` consists of vectors
  with at most `s` nonzero coordinates, and even gives
  `t=h(h+1)(n-1)` and `s_i=h(n-1)+i-1`.
- Section 2.4 explicitly takes
  `B_i=Y(u_i,v)=[0,u_i] union [v-u_i,v]` in the integer model, followed by a
  finite-order Freiman embedding from the Cartesian product into the integers.
- Section 3 uses the displayed four-interval blocks `Z(u,v,w)`, a direct product,
  and the explicit base-`wH+1` map `phi` to realize ties and the limiting order.
- Proposition 4.5 supplies closed formulas
  `gamma_r=(10n)^(10r)` and generalized-arithmetic-progression scales determined
  directly by the requested permutations; Theorem 4.1 turns them into integer sets.

Thus increasing `n`, `H`, the ambient group, or the integer bit lengths enlarges a
known construction. It does not create a hard witness search.

## Candidate tasks considered

| Candidate task | Gate result | Reason |
|---|---|---|
| Given permutations for `h=1,...,H`, output finite sets with those sumset-size orders | **H fails** | Sections 2.2–2.4 give explicit building blocks, product assembly, and an integer embedding for every requested pattern. |
| Also prescribe equalities and the eventual order | **H fails** | Theorem 1.2 and Section 3 explicitly construct these sets with `Z(u,v,w)` blocks and `phi`. |
| In the weaker integer theorem, output the scales or sets realizing orders at selected `h_r` | **H fails** | Proposition 4.5 and Theorem 4.1 give the scales and sets by displayed formulas. |
| Given arbitrary sets, output their relative iterated-sumset-size orders | **V fails in the potentially hard regime** | This is a unique invariant computation, not a cheaply checked witness search. An exact checker must itself compute the cardinalities of the sumsets; direct expansion grows exponentially when `h` grows. If `h` is fixed so expansion is polynomial, the intended hardness disappears. |
| Find a smallest realization | Disallowed / **V fails** | The answer would be an optimum whose optimality is the claim, expressly forbidden by the task, and the paper gives no cheap optimality certificate. |
| Realize the Section 3 extension in every infinite abelian group | **G fails** | The paper explicitly leaves this analogue open; there is no answer-first construction for the open regime. |
| Given `A,h,t`, output a representation of `t` in `hA` | Not a paper-native result | This grafts a generic subset-sum search problem onto the introductory definition. The paper neither studies its complexity nor provides a planted distribution with justified average-case hardness. Calling it a generator from this paper would make the paper irrelevant. |

## Easy and impossible regimes that matter

Section 1 explains two limitations, neither of which creates a usable hard regime.
For any fixed finite set, Khovanskii's result makes `|hA|` eventually polynomial in
`h`, so relative orders eventually stabilize. In a finite group, `|hA|` is constant
for `h >= |G|`, and groups that are too small cannot realize every requested pattern.
Those observations only make some targets impossible; an unsatisfiable instance is
not an allowed witness problem.

Conversely, every finite prescribed pattern in a sufficiently large group is in the
paper's explicitly constructible regime. The stronger equality/limiting-order
construction is open for general infinite abelian groups, so moving outside the
constructible integer regime sacrifices G rather than rescuing H.

## Gate outcome

| Gate | Outcome |
|---|---|
| G — inverse-generatable | Passes for the paper's proved realization problems; fails for the only stated open extension. |
| H — no known polynomial-time or closed-form method | **Failed.** The proofs themselves provide direct constructions for the proved regimes. |
| V — cheap exact witness checking | Potentially passes only for deliberately small/fixed expansion regimes; fails for arbitrary succinct large-`h` cardinality claims. |

Per Step 0, rejection stops the run before module implementation, mandatory gates,
or the LLM hardening loop. Therefore `gen_2412_18598.py`,
`selftest_report.json`, and `llm_loop_transcript.jsonl` were intentionally not
created; fabricating them would falsely claim that an invalid family passed the
required tests.
