# Rejected: principal-minor counts in conference-matrix designs

Paper: Gary Greaves and Sho Suda, [*Constructions of \(t\)-designs from
weighing matrices and association schemes*](https://arxiv.org/abs/2402.17528),
arXiv:2402.17528v2.

## Decision

No generator is shipped. The best paper-native candidate was a **Track B**
family: given several determinant-preserving transforms of Paley conference
matrices, return the exact number of 4-subsets whose principal minor is one of
the paper's two distinguished values. It passed theorem-backed generation and
exact verification, and its brute-force/compact cost gap was large. It failed
**H (no-tool compression hardness)** in the mandatory oracle loop.

The oracle pool solved every named rung and the one permitted automatic
escalation. At the final 16-record rung, Grok 4.6 and GPT-5.6 Terra both returned
fully correct 16-integer witnesses; Claude Sonnet 5 exhausted its response
budget without an answer. The script-owned verdict was
`too_easy` after all three allowed escalations. The prompt forbids further
manual escalation or shipping a family tuned past that result.

## What the paper actually defines

Section 1.4 defines

\[
\mathfrak H_A(v,k,a)=([v],\{\alpha\in\tbinom{[v]}k:
\det A[\alpha]=a\}).
\]

Theorem 2.2 proves that this determinant-defined hypergraph is a
\(t\)-design when the \(k\)-principal minors take two values and the specified
characteristic-polynomial coefficients of vertex-deleted principal
submatrices are constant. Its proof also gives the incidence parameter
\(\lambda\) exactly.

Section 2.2 defines conference matrices and the Paley construction. Table 1
shows that a symmetric Seidel matrix has 4-principal minors in \(\{-3,5\}\),
while Table 2 gives \(\{1,9\}\) in the skew-symmetric case. Examples 2.3 and
2.4 then give the exact 3-design parameters:

| conference order | target minor | resulting 3-design parameter |
|---|---:|---:|
| \(4m+2\), symmetric | \(5\) | \(\lambda=3m\) |
| \(4m+2\), symmetric | \(-3\) | \(\lambda=m-1\) |
| \(4m\), skew-symmetric | \(9\) | \(\lambda=m\) |
| \(4m\), skew-symmetric | \(1\) | \(\lambda=3(m-1)\) |

For a Paley matrix built from a prime \(q\), its order is \(v=q+1\).
Simultaneously permuting rows and columns and applying a diagonal \(\{\pm1\}\)
congruence preserve every principal determinant. These transformations allowed
seeded instances without changing the held certificate. Finally, counting
incident pairs `(triple, block)` gives the number of blocks

\[
b=\lambda\binom v3/\binom43=\lambda\binom v3/4.
\]

Thus G was theorem-backed rather than obtained by solving generated instances,
and V used only exact primality/congruence checks and integer arithmetic.

## Step-0 algorithm and measured costs

The honest reference algorithm constructs each specified Paley matrix and
classifies every 4-subset by its exact 4-by-4 principal determinant. Its cost is

\[
\Theta\!\left(\sum_j \binom{q_j+1}{4}\right)
\]

constant-size determinant tests, hence polynomial in explicitly expanded
matrix order. The determinant calculation was implemented exactly: a
three-term Pfaffian squared in the skew case and the corresponding exact
three-term formula in the symmetric case.

Two measured points establish both sides of the Track B comparison:

| candidate level | reference work | measured wall time | compact route |
|---|---:|---:|---:|
| named hard, 12 records | 33,210,178 minors; 324,551,975 small arithmetic operations | 4.02 s | at most 96 operations |
| final escalation, 16 records, oracle seed 371954008 | 106,751,009 minors; 860,929,495 small arithmetic operations | 12.34 s | at most 128 operations |

For the final seed, exhaustive counts for both allowed determinant classes at
every prime agreed with the theorem-derived formulas. The serialised answer
was 123 characters and 16 atomic elements, so answer length and transcription
were not the cause of oracle failure or success.

The mechanical/compact gap is therefore real: about 107 million minor tests
versus 128 integer operations. What fails is the *discovery* part required by
Track B. Once a solver notices that the supplied affine relabellings and sign
switchings are determinant-invariant, the remaining route is the paper's
displayed 3-design parameter followed by one standard double count. Multiple
models found and executed this route without tools. The compact route is too
accessible to support the requested no-tool hardness claim, despite replacing
a large mechanical computation.

## Mandatory hardening evidence

`scripts/harden.py` was run without a hint. API stalls were not counted as
failures: the one 900-second Grok stall at medium was recorded as an error and
redrawn against Terra.

| rung | parameters | valid solves | other completed outcomes |
|---|---|---:|---|
| easy | `n=5, records=3, pool=6` | 2/3 | Claude emitted no answer after using its token budget |
| medium | `n=13, records=7, pool=12` | 2/3 | Claude emitted no answer; one Grok API stall was redrawn |
| hard | `n=37, records=12, pool=18` | **3/3** | none |
| automatic escalation | `n=53, records=16, pool=24` | **2/3** | Claude emitted no answer after using its token budget |

The final successful witnesses came from two vendors and verified exactly.
The meta-verdict was `too_easy`, with `escalations_used: 3`. Because even the
bare prompt failed Step 4, the G9 hinted and placebo arms were not run: a
structural hint cannot repair a family already solved without one.

## Why nearby paper-native alternatives do not rescue the paper

- Asking only for the incidence parameter \(\lambda\) is strictly easier: it
  is written explicitly in Examples 2.3 and 2.4.
- Asking for one valid 4-block fails guess resistance. In these 3-designs the
  two determinant classes occupy constant-order fractions of all 4-subsets,
  so independent guesses are not rarities.
- Asking for the entire block collection violates G9(c). The output has
  \(\Theta(v^4)\) blocks rather than at most 256 atomic elements.
- Section 3.4's signed-hypercube PBIBD parameters are given explicitly in
  Lemma 3.9 and Theorem 3.10; recovering those displayed formulas is no harder
  than the rejected conference-matrix count route.
- Theorem 3.12 likewise displays the three PBIBD parameters obtained from a
  balanced generalised weighing matrix.
- Theorem 4.2 gives the regular pairwise-balanced design parameter
  \(v^2-v\) explicitly, so its count version has the same short substitution
  route. Section 4.2 is a finite case-by-case table for strongly regular graphs
  of order at most 27, not an unlimited generative regime; using it would be a
  classification lookup.
- The existence questions that could be genuinely difficult are open rather
  than generatable. In particular, Question 5.1 asks for which orders
  skew-symmetric conference matrices exist, while Questions 5.2--5.4 ask for
  higher-strength, larger-block, or symmetric designs. The paper supplies no
  unlimited answer-first construction or bounded negative certificate for
  those questions.
- A matrix-completion or hidden-entry task could be invented around a
  conference matrix, but that is not one of the design constructions studied
  in the paper and would move the benchmark away from its native problem.

The paper also identifies an explicitly trivial regime in Remark 2.6: when a
two-eigenvalue Seidel matrix has minimum eigenvalue multiplicity one, the block
family is all \(k\)-subsets. That regime was avoided; avoiding it was not enough
to make the count task hard.

## Gate outcome

| requirement | result | evidence |
|---|---:|---|
| G -- generatable | Pass | Theorem 2.2 and Examples 2.3--2.4 provide the certificate; determinant-preserving transforms carry it. |
| H -- Track A | Not claimed | The paper gives exact formulas; pretending no efficient method exists would be false. |
| H -- Track B | **Fail** | Every rung was solved; 2/3 vendors solved the final 16-record escalation exactly. |
| V -- verifiable | Pass | Exact integer formula evaluation, with exhaustive agreement checked on the benchmark seeds. |
| G9 size/effort caps | Pass in isolation | 123 answer characters, 16 elements, and 128 intended operations at the final rung. |
| Step 4 | **Fail** | Script-owned verdict `too_easy` after three escalations. |
| Overall | **Rejected** | G, H, and V do not hold simultaneously. |

The attempted generator, self-test report, README, and oracle transcript are
not shipped because leaving an easy module beside this decision would make it
look like a valid release artifact. The quantitative results above are enough
to reproduce the rejection, and no passing gate has been claimed for the
failed family.
