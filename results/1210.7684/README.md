# arXiv 1210.7684 problem generator

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple (the true-variable set) |
| Intended intuition | invariant: noncooccurrence classes |
| Domain essentiality | native |

This generator covers the **Positive and Minimum Intersecting 1-in-3 SAT**
problem defined in Section 3 of Farzad and Karimi,
[“Square-Root Finding Problem In Graphs, A Complete Dichotomy Theorem”](https://arxiv.org/abs/1210.7684).
The solver receives positive three-variable clauses, no two of which share more
than one variable, and must list exactly the variables made true so that every
clause has exactly one true member. Verification is an exact clause scan. This
is the paper's native source problem for Lemma 3, but it is deliberately **not**
a generated graph-square instance; it therefore covers the paper's logical CSP
object, not its graph-root target.

## Why Track B

Theorem 2 states NP-completeness of the unrestricted source problem, and Lemma
3 carries its witnesses to girth-five square roots; Theorems 3–4 establish the
girth-five graph result. That worst-case theorem does not make this generated
distribution hard. In fact, its algorithm is explicit: build cooccurrence sets,
then take all variables that never cooccur with a chosen variable. This succeeds
in `O(q^2)` time. At shipping `q=64`, it solved 8/8 instances in 12,608 counted
operations each, averaging 0.00587 seconds. The compact insight is that
noncooccurrence is an equivalence relation with three classes; focusing on one
variable's incidences leaves at most 256 marking/output operations, whereas a
mechanical pass processes 4,096 shuffled clauses. Section 1's `O(|V||E|)`
algorithm for roots of girth at least six is another easy regime, so no Track-A
claim is made.

## Worked demo

The `demo` preset with seed 0 renders the complete hand-scale instance:

```text
There are variables 0,...,5 and exactly 2 must be true.
Clauses: [4,3,2] [2,1,0] [4,0,5] [5,1,3]
```

`<answer>1, 4</answer>` gives `verify(inst, [1, 4]) == (True, "ok")`.
Dropping 4 gives `(False, "expected exactly 2 true-variable IDs, got 1")`.
A person can solve this four-clause demo by hand.

## Presets

| preset | q | variables | clauses | answer atoms | candidate-space bits |
|---|---:|---:|---:|---:|---:|
| demo | 2 | 6 | 4 | 2 | 4 |
| easy | 16 | 48 | 256 | 16 | 42 |
| medium | 32 | 96 | 1,024 | 32 | 85 |
| **hard (ships)** | **64** | **192** | **4,096** | **64** | **173** |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged, fenced prose response round-tripped |
| G4 | pass | 0/200,000 uniform fixed-weight guesses |
| G5 | pass | shipping density 0/200,000; demo exact count 3/15; 2,048 restart candidates measured |
| G6 | pass | five attacks, each 0/8; reference algorithm 8/8 as expected |
| G7 | pass | doubled `q=128` instance built and verified; candidate bits 173→349 |
| G8 | pass | 20 relabeling/composition checks, 20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 293 chars, 74 estimated tokens, 64 atoms, 256 intended operations |

## Oracle loop and G9 arms

The required harness was run, but OpenRouter returned HTTP 403 “Key limit
exceeded (total limit)” on every redraw. Errors do not count as oracle attempts,
so there is no honest hardened/too-easy verdict yet.

| run | preset | scored | errors | outcome |
|---|---|---:|---:|---|
| required hardening loop | easy (first ladder rung) | 0/0 | 4 | oracle pool unreachable |
| bare G9 arm | hard | 0/0 | 4 | oracle pool unreachable |
| structural hint | hard | 0/0 | 4 | oracle pool unreachable |
| placebo hint | hard | 0/0 | 4 | oracle pool unreachable |

Thus `hinted − placebo` is not estimable, not evidence of zero effect. The
script-owned error transcripts are retained. Re-run all three arms with a funded
OpenRouter key before submission.

## Use

```python
import gen_1210_7684 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
answer = g.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 1210.7684 20
```

## Caveats

- This is Track B: the reference algorithm is fast. It benchmarks discovery of
  the invariant in a long no-tool prompt, not computational intractability.
- The 0/200,000 figure uses the strongest free prior stated in the prompt—a
  uniform `q`-subset. It does not model a solver already hypothesizing Latin
  incidence classes.
- Locating all incidences of one variable in the shuffled text still demands
  attention; the 256-operation compact count begins once those occurrences are
  identified in context. This boundary is the weakest part of the no-tool claim.
- The panel includes construction-aware heuristics but not an industrial SAT or
  ILP solver; the exact cooccurrence algorithm already dominates them on this
  distribution and is reported rather than suppressed.
- `canonical_key` uses Pasch-participation invariants, not complete Latin-square
  isomorphism, so rare nonisomorphic collisions are possible despite the 20/20
  diversity test.
- Oracle hardness is currently unverified because of the external key limit.
