# arXiv 2001.01948 — cyclic NAE certificates for proper connection

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (a normalized core bit vector) |
| Intended intuition | invariant |
| Domain essentiality | licensed reduction |
| Reduction | Section 2, Theorem 2.1: NAE-3SAT to deciding `pc(G)=2` |

This is representational coverage of the paper's central reduction, not native
coverage of arbitrary graph-colouring search: the solver is shown a symbolic
description of the reduction graph, but the search is carried by its NAE-3SAT
source formula. The discarded information is the expanded list of hundreds of
thousands of graph edges and their full two-colouring; the compact answer expands
deterministically to the NAE witness used by the theorem.

## Problem and trust model

[Huang and Li, *Hardness results for three kinds of colored connections of
graphs*](https://arxiv.org/abs/2001.01948) define a proper path as one whose
adjacent edges have different colours. Their Theorem 2.1 constructs a graph
`G_F` with proper connection number two exactly when a given NAE-3SAT formula
`F` is satisfiable.

An instance here gives `F`, occurrence slots that completely specify `G_F`, a
reference variable fixed to zero, and an ordered set of core variables. The
solver returns the core bits. Every omitted variable occurs in exactly two
clauses; the verifier assigns it the smaller locally valid bit and then checks
every NAE clause exactly. It never reads the planted answer. Generation is
inverse: sample the core answer first, compose a full-rank cyclic 3-XOR system,
write each XOR as four ordinary clauses, and turn every ordinary clause into two
NAE clauses. Thus the certificate is known by construction, not found by solving.

## Why Track B

Theorem 2.1 is worst-case NP-completeness and does **not** prove this generated
distribution hard. In fact, this distribution has an efficient algorithm:
pair frequency-two auxiliary variables, recover the parity quartets, and run
Gaussian elimination over GF(2), in `O(C+n^3)`. On eight hard-preset seeds that
algorithm solved 8/8, used at most 39,881 counted Boolean operations, and averaged
0.001555 s. Plain DPLL with unit propagation also solved 8/8; it needed 4–7 nodes,
up to 63,453 literal-level operations, and averaged 0.021530 s.

The compression target is the invariant those routines obscure: the recovered
three-variable supports overlap in one tight cycle. Once noticed, a second-order
GF(2) recurrence obtains the 59-bit witness in 298 exact Boolean operations. The
paper's easy regime is also explicit: Section 5, Theorem 5.2 computes the
`k`-colour connection number of trees in linear time, so this family does not use
trees. The paper also states in Theorem 2.1's proof that checking a proposed
two-colouring for proper connectivity is polynomial-time.

## Worked demo

The `demo` preset with seed 3 is genuinely hand-solvable: pair the variables that
occur twice, collapse each pair to an ordinary clause, group four sign patterns
on each core triple, and solve the resulting five-equation cycle. It is tedious
enough to illustrate the encoding but only has 32 possible core vectors.

```text
Number of output core bits n: 5
Number of formula variables q: 26
Number of NAE clauses: 40
Reference variable R: X_8
Core variables in mandatory output order: [13,6,3,4,18]

C1: [-18@11,+14@1,+4@9]
C2: [-24@2,-6@12,-8@5]
C3: [+1@1,-8@4,-3@3]
C4: [+22@1,+6@8,-3@9]
C5: [+4@7,+18@2,-10@2]
C6: [-13@6,+3@5,+21@1]
C7: [+4@6,-3@11,+19@2]
C8: [-15@1,-13@2,-18@1]
C9: [-8@17,-26@2,+18@10]
C10: [-4@4,+5@1,+18@8]
C11: [-8@8,-5@2,+13@1]
C12: [-3@1,-6@10,-25@1]
C13: [-8@11,-20@2,-4@8]
C14: [+8@19,-18@7,-11@2]
C15: [-6@5,-21@2,+8@15]
C16: [+3@12,-8@6,-7@1]
C17: [-3@6,-4@1,+2@2]
C18: [-9@1,-8@2,+18@3]
C19: [+18@12,-3@7,+20@1]
C20: [-8@12,+13@4,+22@2]
C21: [-16@1,-3@8,-6@2]
C22: [-13@5,-6@4,-11@1]
C23: [+9@2,+6@6,+13@12]
C24: [+13@8,+17@1,+18@4]
C25: [+6@1,-2@1,-8@20]
C26: [+16@2,+8@16,-4@10]
C27: [+8@3,-17@2,+4@5]
C28: [+4@3,-23@1,+8@9]
C29: [-13@11,+25@2,-8@13]
C30: [+18@9,-4@11,-12@2]
C31: [+10@1,-13@9,-8@1]
C32: [-6@7,+4@12,-1@2]
C33: [+3@2,+4@2,+26@1]
C34: [+15@2,-8@7,+6@3]
C35: [-24@1,+18@5,-13@10]
C36: [+8@14,-19@1,+18@6]
C37: [-14@2,+13@3,-8@10]
C38: [+6@9,-3@10,+23@2]
C39: [+13@7,-7@2,-6@11]
C40: [-3@4,-12@1,-8@18]

Answer: <answer>[0,0,1,1,0]</answer>
verify(instance, answer) -> (True, "ok")
verify(instance, [1,0,1,1,0])
  -> (False, "parity constraint on [X_4,X_13,X_18] is violated")
```

The complete rendered statement additionally defines every graph gadget, the
NAE semantics, auxiliary expansion, indexing, and output contract.

## Difficulty presets

| Preset | Core bits | Encoding copies | Formula variables | NAE clauses | Compact operations | Ships? |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 1 | 26 | 40 | 28 | no; illustration |
| easy | 23 | 1 | 116 | 184 | 118 | no |
| medium | 41 | 1 | 206 | 328 | 208 | no |
| hard | 59 | 2 | 532 | 944 | 298 | **provisional shipping preset** |

No preset was rejected by a local gate. `hard` is provisional because the
required external oracle pool was unreachable; there is no script-owned
`hardened` verdict yet. Escalation first grows `n`, then increases encoding
copies at fixed 59-bit answer length.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 planted verifies | pass | 12/12 preset × seed combinations |
| G2 corruption | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 round-trip | pass | fenced model-style response parsed; garbage rejected |
| G4 guessing | pass | 0/200,000; exact probability `2^-59 = 1.7347e-18` |
| G5 density/cost | pass | exactly 1 normalized solution; 0/200,000 sampled; 2,048-restart baseline failed in 0.077627 s |
| G6 adversaries | pass | four attacks each 0/8; Gaussian and DPLL references each 8/8 |
| G7 scaling | pass | doubled `n=118` instance built and verified in 0.067887 s |
| G8 canonical key | pass | 100/100 relabellings invariant and verified; 20/20 unrelated keys distinct |
| G9 caps | pass | 119 chars, 120 estimated tokens, 59 atoms, 298 operations |

## Oracle loop

The mandated harness ran, but OpenRouter rejected every request with HTTP 403
`Key limit exceeded (total limit)`. Errors do not count as model failures, so
the run establishes no oracle hardness claim.

| Preset | Seeds | Calls | Valid attempts | Solved | Outcome |
|---|---|---:|---:|---:|---|
| easy | 1144046949, 2089573778, 1655134721, 1733024730 | 4 | 0 | 0 | pool unreachable; no verdict |

## G9 arms

| Arm | Preset | Solved / valid attempts | Recorded outcome |
|---|---|---:|---|
| bare | easy | 0/0 | four HTTP 403 errors |
| structural hint | hard | 0/0 | four HTTP 403 errors |
| placebo hint | hard | 0/0 | four HTTP 403 errors |

`hinted − placebo` is therefore undefined, not zero, and no conclusion about the
hint can be drawn. The measured non-oracle G9 values are 119 answer characters,
59 atomic elements, about 120 tokens, and 298 intended-route operations.

## Use

```python
import gen_2001_01948 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
answer = inst["answer"]                 # only for generator-side demonstration
assert g.parse_answer(f"<answer>{answer}</answer>") == answer
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, after a valid oracle run exists:

```bash
bash scripts/emit.sh 2001.01948 20 hard
```

## Caveats

- This is Track B, not evidence that its generated distribution is
  complexity-theoretically hard. Both Gaussian elimination and DPLL solve it.
- The zero-hit estimate samples uniformly from the already normalized 59-bit
  core language and deterministically fills auxiliaries. It does not model a
  solver prior that has recognized the overlap cycle.
- The canonical key is a 12-round signed occurrence-incidence
  Weisfeiler-Lehman invariant. It is invariant under all tested syntactic
  relabellings but is not a complete graph-isomorphism canonical form and may
  over-collapse rare non-isomorphic instances.
- No industrial CDCL SAT solver, SMT solver, or external graph-isomorphism
  package was run. The tested domain-standard attacks were exact Gaussian
  elimination and an in-module DPLL with unit propagation.
- The full edge-colouring expansion was not made the answer: even small
  reduction graphs exceed the 256-atom cap. Correctness therefore relies on
  the paper-licensed NAE-to-proper-connection transformation, while the checker
  directly validates the complete expanded NAE assignment.
- Most importantly, the oracle evidence is incomplete because the configured
  OpenRouter key had exhausted its total limit. Re-run all three arms before
  submission; do not interpret the error-only transcripts as hardness evidence.
