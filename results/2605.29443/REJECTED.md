# Rejected at STEP 0: no defensible hardness track

Paper: [Garoufalidis–Kashaev–Suzuki, *Combinatorial description of closed
3-manifolds via ordered ideal triangulations*](https://arxiv.org/abs/2605.29443)
(arXiv:2605.29443v1).

## Decision

The proposed move-sequence family clears **G** and **V** but fails **H**. It is
not acceptable on either Track A or Track B, so no `gen_2605_29443.py` was built.
This decision is based on the complete 16-page paper and its LaTeX source, not
the abstract.

| gate | result | reason |
|---|---:|---|
| G — generatable | pass | Apply legal ordered Pachner/pure-sliding moves to a known normal o-graph and retain the move list. This is transformation of a known instance. |
| V — verifiable | pass | Replay the finite move list, check every local template and the global circuit condition for each sliding move, and compare the final E-datum. |
| H — Track A | **fail** | The paper proves connectivity/equivalence, not hardness of recovering a path for any generated distribution. There is no theorem, parameter regime, lower bound, or average-case evidence that would support `hardness_basis`. |
| H — Track B | **fail** | For the only explicit certificate family supplied by the paper, the mechanical and compact routes have the same constant cost. For random-walk endpoints, the paper supplies no efficient reference algorithm or compact route at all. |

## What the paper actually proves

Sections 2 and 3 define the native objects: ordered ideal triangulations and
their dual normal o-graphs, with 20 ordered 2–3 move types and 6 ordered 0–2
move types. Theorem 1 in the introduction (Theorem 4.2 plus Corollary 4.7 in the
normal-o-graph formulation) says that an ordered MP or bumping MP move can be
expressed using one preferred move and sliding moves. Theorem 2 in the
introduction (Theorem 4.5) identifies closed oriented 3-manifolds with the
resulting equivalence classes. These are completeness statements for a move
calculus; none is a computational-hardness result.

Proposition 4.4 is the constructive step eliminating the CP move. Its proof in
Section 4.3 writes down the certificate completely in E-data: 14 displayed
local moves reduce the CP left-hand side to a common E-datum, and 6 displayed
moves reduce the right-hand side to the same E-datum. Reversing the second list
gives the stated 20-move path.

## STEP 0 cost comparison

### Paper-native explicit decomposition

- **Mechanical cost:** recognize the fixed CP local pattern and instantiate the
  displayed Section 4.3 list: exactly **20 local move applications**, constant
  time apart from relabelling and replay.
- **Compact route:** recognize the same CP local pattern and use Proposition 4.4:
  exactly **20 local move applications**. The witness itself contains all 20,
  so it cannot be produced in fewer output steps.
- **Gap:** **20 versus 20** (ratio 1). Relabelling creates no new family under
  the required canonical equivalence. Disjoint composition changes both costs
  to `20k`, so it creates transcription work rather than a no-tool insight gap.

The analogous “decompose one ordered 2–3 move” task is also finite lookup: the
paper lists only 20 move types, and Section 4.2 connects those types by a fixed
relation diagram. Enlarging a surrounding triangulation does not enlarge the
local certificate problem.

### Prior-triage random-walk proposal

- **Certificate construction:** choose a legal move, apply it, and retain it;
  after length `L`, this costs exactly **L move applications** and is valid
  inverse generation/transformation.
- **Verification:** sequence replay costs **L legality checks** plus final exact
  comparison.
- **Mechanical discovery from endpoints:** generic path enumeration has up to
  exponential cost in `L` (roughly `b^L` for move-graph branching factor `b`),
  but the paper gives no complexity theorem or distributional evidence for the
  planted random-walk instances.
- **Compact route:** **none supplied**. Recovering the generator's hidden random
  choices is the same unstructured path-search problem. Adding visible
  breadcrumbs would instead make recovery a linear **L-step** scan, eliminating
  the claimed gap.

Thus the random-walk variant cannot be Track A (no theorem-backed hardness for
its distribution) and cannot be Track B (no efficient reference algorithm with
a substantially shorter structural route). Sequence replay establishes V; it
does not establish H.

## Easy regimes and other exclusions

The paper contains no algorithmic hard/easy parameter classification, FPT
result, approximation result, or path-length bound to steer a generator around.
What it does make easy is precisely the finite local replacement problem:
ordered 2–3 moves have 20 types, ordered 0–2 moves have 6 types, and the CP
replacement is the displayed 20-step identity. Asking for those certificates is
a classification-table/identity-replay exercise.

No discrete surrogate was considered. A graph/SAT encoding could manufacture a
separate hard search problem, but no such reduction is central to this paper; it
would be a convenience reduction and would discard the ordered-triangulation
and normal-o-graph move calculus that constitutes the paper's contribution.

## Reconsideration criterion

This paper could be reopened if an external result supplies either (a) hardness
for a precisely specified distribution of bounded ordered-Pachner path instances
(Track A), or (b) an efficient endpoint-to-path algorithm whose measured shipping
cost is large while these planted instances admit a genuinely shorter visible
invariant or decomposition (Track B). Neither ingredient appears in this paper.
