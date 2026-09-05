# Verified generator for arXiv:1003.3704

> **Status: rejected.** The retained generator is an audit artifact, not a
> shippable family.  A strengthened standard DPLL attack solved the
> oracle-evidenced 180-variable preset; see `REJECTED.md`.

| profile field | value |
|---|---|
| track | attempted **A — structural hardness** (failed) |
| native domain | logic |
| object regime | finite discrete |
| computational core | CSP/SAT |
| certificate | integer partition (`left`, `right`) |
| intuition | constraint propagation through a balanced two-cell refinement of a hidden 5-colouring |
| domain essentiality | native; no reduction |

## Problem and trust model

The family is the paper's native **5-colourable Monotone NAE-3SAT** search
problem.  The solver receives triples of distinct, unnegated variables and must
partition every variable into two nonempty sides so every triple meets both
sides.  The co-occurrence graph is promised 5-colourable, and no variable
occurs more than seven times.  `verify` checks the partition and scans every
clause using exact integer/Boolean operations; it does not read the planted
answer.

The source is Peiyush Jain, [*On a variant of Monotone NAE-3SAT and the
Triangle-Free Cut problem*](https://arxiv.org/abs/1003.3704).  Section 2.1 fixes
the monotone three-distinct-variable definition and the co-occurrence graph.
Section 4, Theorem 2 proves NP-completeness for `k >= 5` even with at most seven
occurrences per variable.  The easy boundary matters: Section 2.1 states that
the 4-colourable case is in P, so this generator stays at five hidden colours.

Generation is inverse, not solution by search.  It samples ten equal hidden
roles (five proper colours crossed with two planted truth values), then applies
the complete orbit of colour-distinct NAE clause templates.  Complement-paired
extra templates raise every shipping variable to occurrence seven without
changing the distribution of the two truth populations.  Consequently the
hidden truth partition is a certificate by construction and the hidden colour
coordinate proves the co-occurrence graph is 5-colourable.

## Why the Track-A attempt was rejected

The paper offers a polynomial reduction, not an algorithm that recovers the
certificate.  The general mechanical route is exponential SAT search.  The
candidate preset is inside Theorem 2's regime: 180 variables, 420 monotone
clauses, exactly seven occurrences per variable, and a 5-colourable primal
graph.  A first NAE-DPLL panel stopped at 10,000 nodes and misleadingly scored
0/8.  The strengthened 50,000-node audit recovered verified witnesses at
31,963 and 40,162 nodes on two of three checked seeds.  Track A requires zero
standard-algorithm successes, so the family is rejected.  Occurrence outliers,
greedy assignment, 64-restart NAE-WalkSAT, and a bottom-eigenvector relaxation
plus local repair still solved 0/8, but those failures cannot override DPLL.

The 240-variable rung exhausted 50,000 DPLL nodes on 8/8 audited seeds, but the
OpenRouter key reached its total limit before fresh bare and hinted oracle runs
could be obtained at that rung.  It is retained as a possible restart point,
not silently substituted as shipping evidence.  This outcome illustrates why
worst-case NP-completeness cannot establish average-case hardness for a planted
distribution.

## Worked demo (seed 7)

The hand-scale instance has variables `0..9` and these ten clauses:

```text
1: (1, 3, 6)    2: (2, 3, 4)    3: (2, 6, 7)    4: (0, 6, 8)
5: (1, 5, 7)    6: (5, 8, 9)    7: (2, 3, 7)    8: (4, 5, 9)
9: (0, 4, 9)   10: (0, 1, 8)
```

One answer is:

```json
{"left":[0,3,4,5,6],"right":[1,2,7,8,9]}
```

`verify(inst, answer)` returns `(True, "ok")`.  Dropping vertex 6 returns
`(False, "the partition is missing at least one vertex")`.  A person can solve
this demo by short trial and clause propagation; it is illustrative rather
than a difficulty level.

## Difficulty presets

| preset | n | clauses | occurrence regime | status |
|---|---:|---:|---:|---|
| demo | 10 | 10 | exactly 3 | hand example; never shipped |
| easy | 180 | 420 | exactly 7 | oracle-hardened, then rejected by stronger DPLL |
| medium | 210 | 480 | 6 or 7 | available escalation |
| hard | 240 | 560 | exactly 7 | available escalation; 240 answer atoms |

After all variables reach occurrence seven, further escalation must grow `n`;
at 240 variables the 256-atom output cap is the limiting axis and `escalate`
returns `"cap_bound"`.

## Gate results

| gate | result |
|---|---|
| G1 planted verifies | pass, 12/12 preset-seed instances; 12/12 JSON round trips |
| G2 corruption | pass, drop/swap/duplicate/empty/out-of-range all rejected with five distinct reasons |
| G3 parse round trip | pass, fenced JSON with surrounding prose recovered exactly |
| G4 guess resistance | pass, 0/200,000 uniform nontrivial oriented partitions; space `2^179-1` |
| G5 density + baseline | pass on the fixed seed: density 0/200,000 and DPLL exhausted 50,001 nodes; demo has 37 valid answers among 511 candidates |
| G6 adversaries | **fail**: 50,000-node DPLL solved 2/8; four cheap/construction probes remain 0/8 |
| G7 scaling | pass, 360 variables / 840 clauses built and verified |
| G8 canonical key | pass, 60/60 invariance and witness-preservation checks; 20/20 unrelated keys distinct |
| G9 suitability | pass, hinted verdict hardened; 630 characters, 158 estimated tokens, 180 atoms, 180 post-insight membership writes |

## Oracle loop

The script-owned bare run held the first tested rung, but that rung does **not**
ship because the stronger algorithmic audit supersedes the oracle-only signal.

| preset | model | seed | solved | verifier outcome |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 1539794601 | no | clause 8 monochromatic |
| easy | Gemini 3.1 Pro Preview | 2145202994 | no | clause 15 monochromatic |
| easy | Claude Sonnet 5 | 1665983950 | no | empty length-limited response after reasoning budget |

## G9 arms

| arm | solved / completed attempts | status |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened; Grok timeout was excluded and redrawn |
| placebo | 0 / 1 | incomplete after OpenRouter key total limit; non-gating diagnostic |

On completed attempts the structural hint bought no observed success over the
placebo (`hinted - placebo = 0.0`).  The placebo comparison is underpowered:
after one completed Claude failure, a Grok timeout was correctly redrawn, but
the account then returned HTTP 403 key-limit errors.  The partial transcript is
preserved rather than filled in by hand.  G9(b), the gated arm, is complete at
0/3.  The answer measures 630 compact-JSON characters (158 estimated tokens),
180 atomic entries, and 180 exact side-membership writes after the global split
has been identified.

## Use

From the repository root:

```python
import importlib.util

spec = importlib.util.spec_from_file_location(
    "rejected_gen_1003_3704", "results/1003.3704/rejected_gen_1003_3704.py"
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=7, **g.DIFFICULTY["demo"])
text = g.render(inst)
candidate = g.parse_answer('<answer>{"left":[0,3,4,5,6],"right":[1,2,7,8,9]}</answer>')
print(g.verify(inst, candidate))  # (True, "ok")
```

The numeric directory name precludes ordinary dotted import syntax, so this
uses the same `importlib` route as the repository scripts.  Because the family
is rejected, do not emit it into the corpus; the command below is shown only
for reproducing the retained artifact:

```bash
bash scripts/emit.sh 1003.3704
```

## Caveats

- Theorem 2 is worst-case.  It does not prove that this inverse-generated
  regular distribution is average-case hard; the attack panel and oracle runs
  are finite evidence only.
- The structure-aware G4 prior is uniform over all nontrivial oriented
  partitions.  It correctly enforces the answer grammar and complement
  convention, but it does not model a learned or spectral prior.
- No external CDCL SAT solver, belief propagation, survey propagation, SDP, or
  higher-order tensor method was run.  The included standard attack is bounded
  NAE-DPLL (50,000 nodes); the included spectral attack uses one bottom
  eigenvector and deterministic local repair.
- Revealing the ten hidden colour/truth roles would make the answer immediate;
  revealing only a 5-colouring need not reveal its truth refinement.  The
  generator intentionally publishes only the promise required by the paper.
- `canonical_key` uses co-occurrence closed-walk traces and multiplicity
  multisets.  It is invariant under tested relabellings but is not a complete
  hypergraph-isomorphism canonizer, so rare cospectral collisions are possible.
- The 180-operation G9 route count measures writing the partition after the
  global split is recognized; it does not pretend that recognizing the split
  is an arithmetic routine.  The incomplete placebo arm is retained and
  disclosed above.
