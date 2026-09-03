# Certificate families — **PROPOSED PROMPT ADDENDUM**

> **This is not a reconstruction and it is not history.** No version of this text
> was used to build `papers/papers.jsonl`. It is a proposed addition to a future
> triage prompt, written now, in response to the coverage gap measured in
> `triage/taxonomy.json`.
>
> It exists so the eval in `triage/README.md` has something to compare a base
> prompt against:
>
> ```bash
> python3 triage/evaluate_triage.py --prompt triage/stage1_prompt.md
> python3 triage/evaluate_triage.py --prompt triage/stage1_prompt.md triage/certificate_families.md
> ```
>
> Read the warning about the `vocab` classifier in `triage/README.md` before
> drawing a conclusion from that pair. Against `vocab`, this addendum improves
> per-family recall *by construction* and that comparison proves nothing on its
> own. The pair is only informative against a real classifier (`--classifier cmd`).

<!-- PROMPT-BEGIN -->

## The certificate is the answer — including when the object is continuous

When you ask "what object would the solver produce?", do not stop because the
paper is about real numbers, functions, manifolds or trajectories. A problem
over a continuous object is still in scope whenever a **finite, exactly
checkable certificate** exists for it. The certificate is what the solver
returns; the object may stay continuous.

Keep a paper when you can name a certificate of one of these kinds — this list
is not exhaustive, and naming a kind not listed here is a good outcome:

| certificate | what the solver returns | how it is checked |
|---|---|---|
| **rational sum of squares (SOS)** | polynomials with rational coefficients over a declared monomial basis, or a rational PSD Gram matrix | expand, compare coefficients exactly over ℚ |
| **Positivstellensatz** (Putinar, Schmüdgen, Handelman, Krivine) | SOS or nonnegative multipliers, one per constraint, of bounded degree | expand the representation, compare coefficientwise |
| **Nullstellensatz** (including the combinatorial one) | multiplier polynomials of bounded degree | expand Σ βᵢ fᵢ and compare against 1 |
| **Farkas / LP duality** | a nonnegative rational multiplier vector | two exact dot products and a sign test |
| **Gram matrix / Seidel matrix** | a rational PSD matrix of declared rank with a prescribed entry pattern | exact LDLᵀ, exact rank, entrywise match |
| **algebraic number** | a minimal polynomial plus an isolating rational interval | irreducibility, plus a Sturm count of exactly one root in the interval |
| **Lyapunov function / barrier certificate** | a polynomial with rational coefficients plus its SOS witness | exact polynomial identity and PSD checks |
| **primal-dual optimality** | a feasible primal and dual pair, i.e. a dual certificate | feasibility of both, complementary slackness, and a zero duality gap, exactly over ℚ |
| **symbolic identity / antiderivative** | an expression over a declared operator set with bounded depth | differentiate, normalise, compare exactly |
| **telescoping (Gosper, Zeilberger, creative telescoping)** | a rational certificate, or a telescoper–certificate pair of bounded order and degree | clear denominators, compare numerator coefficients |
| **exact geometric coordinates** | rational or integer coordinates realising a prescribed configuration or order type | exact orientation determinants and sign comparison |
| **certified residual / interval bound** | a rational box plus rational bounds on residual and Jacobian inverse | recheck the enclosure in exact rational interval arithmetic |

### The rule these share

An answer that is *infinite* becomes finite once its **language is bounded**. An
antiderivative is an infinite space; an antiderivative over a fixed operator set
with depth ≤ 4 and coefficients under 2¹⁶ is a finite, countable, samplable one.
So when the paper's object is continuous, ask the bounded-language question
before you drop it:

> Is there a degree, a depth, a rank, a denominator height or an operator set
> that makes the answer a finite object, without weakening the check?

If yes, keep, and name the bound.

### Do not convert to keep

Do **not** rescue a continuous paper by restating it as a graph, a SAT instance,
a finite-field system or an integer program. A discretised surrogate is a
different problem, and recording it as coverage of the paper's own domain is the
specific failure this addendum exists to prevent. If the only way you can
imagine generating instances is by discretising, say so in `reason` and mark the
paper `weak` rather than describing the surrogate as if it were the paper.

<!-- PROMPT-END -->

---

## Provenance — *not part of the prompt*

Every row of the table is grounded in something in this repo:

- The twelve certificate kinds are the twelve `certificate_family` values in
  `triage/gold_coverage_set.jsonl`, chosen because `triage/taxonomy.json`
  measures the pool as carrying almost none of them: 0 papers mentioning
  Lyapunov functions, barrier certificates, symbolic integration, telescoping,
  Gosper, Zeilberger, interval arithmetic, complementary slackness or a duality
  gap; 1 mentioning Farkas; 3 Positivstellensatz; 3 minimal polynomials or
  isolating intervals; 7 Nullstellensatz; 16 Gram matrix.
- "The certificate is the answer" and the bounded-language rule are compressed
  from the `CERTIFICATE_LANGUAGE` block of `prompts/codex_task.md`, added in
  commit `3ac35cd`.
- "Do not convert to keep" is compressed from the STEP 0 surrogate rules added
  in commit `331102c`, and from the four real failures quoted in `AUDIT.md`
  (`2104.04330`, `2404.18447`, `2411.04916`, `2311.15057`).

**Untested.** No model has been run against this addendum. Whether it changes
what a screen selects is exactly the open question; `triage/evaluate_triage.py
--classifier cmd` is how to find out.
