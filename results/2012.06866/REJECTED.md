# Rejected: arXiv 2012.06866

## Outcome

The built family passes **G** and **V**, but fails **H on Track B**.  It is not a
Track A candidate: the paper proves structural characterizations, not
distributional hardness, and Section 6 explicitly leaves the complexity of the
extendability problem open.  The retained prototype is
`rejected_gen_2012_06866.py`; the script-owned 21-call oracle record is
`llm_loop_transcript.jsonl` with its verdict in `.meta.json`.

The paper is Meidl, Polujan, and Pott, [“Linear codes and incidence structures
of bent functions and their generalizations”](https://arxiv.org/abs/2012.06866).

## Paper triage and the attempted native family

Section 1.1 fixes the native objects: Boolean and vectorial functions over
`GF(2)`, algebraic normal form, Walsh transform, and bentness.  It calls the
Walsh transform the standard tool for computing nonlinearity.  Section 2.2
defines the Walsh dual `f~` by

`W_f(a) = 2^(n/2) (-1)^f~(a)`

and Result 2.8 uses that dual to construct the addition design.  Those sections
license the attempted problem directly; no graph or convenience reduction was
used.

The prototype gives a quadratic bent function
`f_A(x,y)=x^T M_A y`, where `M_A` is a unit triangular Toeplitz matrix over
`GF(2)`.  The answer is the polynomial kernel `C(t)` of the Walsh dual, checked
by exact carryless multiplication as
`A(t)C(t)=1 mod t^n`.  Generation samples complementary Frobenius factors first:
for `n=2^s` and `P=1+u`, it composes `P^(2^s)=1 mod t^n`.  Thus the planted
inverse is known by construction, not obtained by solving the emitted instance.
The checker accepts any polynomial inverse of the required exact shape.

Local gates passed: planted certificates verified 12/12; five corruptions gave
five distinct rejections; parsing round-tripped; structure-aware guesses hit
0/200,000; four attacks were each 0/8; the reference algorithm solved 8/8;
canonical-key invariance and carried witnesses were 140/140; and the largest
shipping answer in 1,000 seeds was 806 characters, 202 estimated tokens, and
128 atomic elements.  The intended route was bounded by 86 exact operations.

## Why H fails, with both costs

The initially declared **mechanical cost** was generic unit-triangular Toeplitz
forward substitution.  It is `O(n^2)` and, at the named shipping preset
`n=4096`, an instrumented run used **16,773,120 binary operations in 0.428899
seconds**; eight runs averaged 0.444204 seconds.  At the final `n=65536` oracle
rung the same count is 4,294,901,760 binary operations.

That is not the strongest algorithm for the generated distribution.  The input
prints the factorization of `A`.  A direct algorithm groups duplicate identity
factors, recognizes the dyadic Frobenius scales, finds the two omitted scales,
and expands the base factor with those two factors.  It uses at most **86 exact
exponent additions/XOR cancellations**, plus a linear scan of the printed
factor list.  This is also the claimed **compact route**.  They are the same
route, so their length is comparable rather than separated: there is no hidden
compression problem left for a no-tool solver to discover.  The generic
`O(n^2)` number therefore cannot support Track B hardness for this distribution.

The oracle loop confirmed the Step 0 diagnosis after construction.  Both
vendors solved every level that mattered, including **3/3 verified answers at
the final rung**:

| round | n | identity-pair decoys | solved / attempts |
|---:|---:|---:|---:|
| 0 | 512 | 4 | 3 / 3 |
| 1 | 2,048 | 12 | 2 / 3 |
| 2 | 4,096 | 24 | 3 / 3 |
| 3 | 8,192 | 48 | 3 / 3 |
| 4 | 16,384 | 96 | 3 / 3 |
| 5 | 32,768 | 192 | 3 / 3 |
| 6 | 65,536 | 384 | 3 / 3 |

The one failure at round 1 was `parse_answer returned None`; it is immaterial to
the verdict because two other independently seeded attempts at that rung
verified.  The final answer still had only 128 atoms.  Three axes (`n`, decoy
pairs, and base-degree range) moved, so the harness correctly returned
`too_easy`, not `cap_bound` or `budget_bound`.

## Why another track was not substituted

- Track A has no theorem here for a hard generated distribution.  Theorem 5.7
  characterizes extendability through the covering radius and metric
  complement, while Section 6 asks for the complexity of extendability as an
  open problem.  Worst-case hardness cannot be inferred from that.
- Known bent/APN constructions make their Walsh magnitudes and the design
  parameters theorem outputs.  Asking only for those values is direct
  evaluation or lookup; a negative or optimal claim would also need a bounded
  executable certificate not supplied by these characterizations.
- Inverse-generating an extendable function would clear G, but for the tractable
  quadratic subclasses the missing component is recovered by the same visible
  linear/factor structure.  H fails for the same reason as the retained
  prototype.  For unrestricted extension search the paper supplies neither a
  distributional hardness result (Track A) nor an efficient certificate-finding
  algorithm with a distinct compact route (Track B).
- The Section 5.2 subdesign condition is only sufficient for nonextendability;
  absence of a subdesign is not itself a short witness that this checker can
  verify without search.

G9 hint/placebo arms were not run after the mandatory bare loop returned
`too_easy`; they cannot rescue a family that fails Step 4.
