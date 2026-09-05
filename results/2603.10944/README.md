# Verified problem generator for arXiv:2603.10944

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | logic |
| object regime | finite discrete |
| computational core | graph (implication reachability) |
| certificate | integer tuple selecting an implication path |
| intended intuition | invariant: decode directed differences of powers of two |
| domain essentiality | licensed reduction; Section 6.2, Theorem 19 |

## Problem and trust model

This module turns Kullmann and Clewer's [*Simple minimally unsatisfiable
subsets of 2-CNFs*](https://arxiv.org/abs/2603.10944) into exact instances.
The solver receives a succinct layered 2-CNF, specified by modular translation
rules, and must choose one rule per layer. This is a paper-licensed
representational reduction: Theorem 19 is the bridge from the displayed
implication path to the native MUS object, while the modular compression itself
is this generator's notation rather than a construction in the paper. A
successful sequence is a path

`X -> V(1,...) -> ... -> V(n-1,...) -> not X`.

Together with the unit clause `(X)`, that chain is a minimally unsatisfiable
subset (MUS): unit propagation gives a contradiction, while deleting the unit
or any chain link makes the subset satisfiable.  `verify` checks the layer/rule
shape, recomputes the endpoint with exact integer modular arithmetic, derives
the selected clauses, and runs exact 2-SAT on the subset and every
single-clause deletion. It does not read the planted answer or run a search.

Generation is inverse.  A full state chain is sampled first; one exchangeable
rule per layer is made to telescope along it, and identically distributed
decoy rules are shuffled into the other columns.  Thus the certificate is
known by construction.

## Why Track B

Section 2.1 fixes MU/MUS and deficiency; Section 2.3 fixes implication graphs
and nearly regular paths.  Theorem 19 maps a nearly regular path beginning at a
unit literal to exactly the kind of MUS used here.  Corollary 20 is the decisive
Step-0 easy result: an MUS containing a specified unit is found by linear-time
reachability.  Corollary 22 similarly handles all one- or two-unit MUSs in
quadratic time.  Consequently this is not a Track-A family.  Theorems 14 and
15 prove NP-completeness only for no-unit Families III and IV.

On the hard preset the expanded formula has 528,942,025 clauses. Ordinary
reachability is linear in that expanded size. The measured exact
meet-in-the-middle implementation on the succinct table uses about 0.697
million half-path transitions per instance (5.57 million over the eight G6
seeds), takes 0.22 seconds on the recorded shipping seed, and solves 8/8, as Track
B requires. Once the invariant is seen, each first
translation component decodes as one directed difference of powers of two;
following the unique row whose source is current takes 252 counted exact
operations and emits only 18 rule choices.

## Worked demo (`seed=0`)

The complete rendered instance is:

```text
Find a minimally-unsatisfiable implication chain in the following exact 2-CNF.

Definitions. A Boolean literal is a variable X or its negation not X. An
implication A -> B abbreviates the 2-CNF clause (not A OR B). A clause-set
is minimally unsatisfiable when it is unsatisfiable but deleting any one
clause makes it satisfiable.

There are n=4 transitions and d=2 numbered rules
per transition. Coordinates are pairs in Z/31Z x
Z/7Z; addition and subtraction are componentwise
with residues represented by the integers in the indicated ranges.
There is one special variable X. For every internal layer i=1,...,n-1 and
every coordinate z there is a distinct variable V(i,z). Variables in
different layers are distinct even when their coordinates agree.

The 2-CNF F is specified without expanding its repeated clauses:
  * F contains the unit clause (X).
  * At transition 1, rule j with delta D gives X -> V(1,start+D).
  * At transition i=2,...,n-1, rule j with delta D gives, for EVERY
    coordinate z, V(i-1,z) -> V(i,z+D).
  * At transition n, rule j with delta D gives
    V(n-1,target-D) -> not X.
Every displayed implication contributes its single corresponding 2-CNF
clause. F has no other clauses. Thus F is an exact finite clause-set, not
a probabilistic or approximate object.

start  = (8,6)
target = (2,4)
number of clauses in expanded F = 873
Rule table; each line is `layer: j=(delta_q,delta_r), ...`:
1: 1=(29,6), 2=(24,3)
2: 1=(2,0), 2=(7,1)
3: 1=(7,4), 2=(27,0)
4: 1=(3,4), 2=(29,1)

Choose exactly one rule at every layer. Starting at `start`, add the
chosen delta at each layer. Your answer is valid exactly when the final
coordinate equals `target`. The selected implications then form
X -> V(1,.) -> ... -> V(n-1,.) -> not X. Together with (X), these
n+1 clauses are a minimally unsatisfiable subset: the unit forces the
chain to not X, while deleting the unit or any link breaks the only
displayed chain. The grader derives these clauses and runs exact 2-SAT
on the full subset and on every single-clause deletion. Layer numbers
and rule numbers are 1-indexed; order
matters, repetitions of a rule number in different layers are allowed,
and every layer must occur once in increasing order.

Give your final answer inside <answer></answer> tags as a JSON list
[[1,j1],[2,j2],...,[n,jn]].
Example: <answer>[[1,2],[2,1],[3,2],[4,2]]</answer>
Output nothing else inside the tags.
```

Its answer is `[[1,2],[2,2],[3,2],[4,2]]`.
`verify(inst, answer)` returns `(True, "ok")`.  Changing the first choice to
rule 1 returns `(False, "endpoint_mismatch: selected implications end at
(7,0), not target (2,4)")`.  A person can solve this demo by checking its 16
possible rule sequences; it is deliberately hand-scale.

## Difficulty

| preset | n | rules/layer | expanded clauses | candidate paths | compact ops | ships? |
|---|---:|---:|---:|---:|---:|---|
| demo | 4 | 2 | 873 | 16 | 32 | no |
| easy | 10 | 3 | 198,353,263 | 59,049 | 110 | no |
| medium | 14 | 4 | 396,706,521 | 268,435,456 | 196 | no |
| hard | 18 | 4 | 528,942,025 | 68,719,476,736 | 252 | **yes** |

No preset was rejected by a local gate.  `escalate` first enlarges the payload
group without lengthening the witness; after that, another branching increase
would breach the 300-operation compact-route cap and returns `cap_bound`.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 endpoints and exact 2-SAT deletion-minimality checks passed; answers JSON-round-tripped |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 sampled hits; exact 8,847 / 68,719,476,736 = 1.2874e-7 |
| G5 | pass | exact shipping count; strongest failing attack used 4,608 choices in 0.003 s |
| G6 | pass | four attacks 0/8 each; reference search 8/8 |
| G7 | pass | doubling n from 18 to 36 verifies and squares the search exponent |
| G8 | pass | 80/80 genuine relabellings invariant; 20/20 unrelated keys distinct |
| G9(c) | pass | 118 chars, 30 estimated tokens, 36 atoms, 252 operations |

Timing figures are machine-load dependent; exact transition counts are the
reproducible cost measure.

## Oracle loop and G9 diagnostics

The required scripts were run, but the configured OpenRouter account returned
HTTP 403 `Key limit exceeded (total limit)` on every redraw.  Per the harness,
errors do not count as model failures.  Therefore there is **no oracle hardness
verdict**, and this result must be rerun when quota is available.

| run | preset | successful attempts | error records | conclusion |
|---|---|---:|---:|---|
| bare | easy | 0 | 4 | pool unreachable; no verdict |
| structural hint | hard | 0 | 4 | pool unreachable; no verdict |
| placebo hint | hard | 0 | 4 | pool unreachable; no verdict |

The solved/attempts diagnostic is consequently 0/0 for all three arms, and
hinted-minus-placebo is undefined.  Nothing can be concluded yet about whether
the hint isolates the intended invariant.  The transcript files retain the
script-owned HTTP evidence.

## Use

```python
import gen_2603_10944 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 2603.10944
```

## Caveats

- This is an exact but succinct representation of a native 2-CNF. The profile
  conservatively labels the implication-path view a paper-licensed reduction,
  not fully native coverage: the paper licenses the path-to-MUS correspondence,
  but not this modular compression. Complexity measured against the compact
  rule table is different from complexity measured against the 528-million-
  clause expansion.
- The exact G4 prior is uniform over all in-range, layer-ordered rule sequences.
  It accounts for every shape restriction stated to the solver, but it is not a
  prior over insight-driven strategies; the separate attacks address several
  such strategies.
- The tested attacks are minimum-residue outlier selection, target-distance
  greedy selection, 256 random restarts, constant-column trials, exact
  bidirectional search, and the intended invariant decoder.  No generic SAT
  package was available or needed because Corollary 20 reduces the native task
  exactly to reachability, which was run.
- `canonical_key` is invariant under rule reorderings, layer gauges, coordinate
  scalings, and contraposition reversal.  Full isomorphism of succinct layered
  graphs is not attempted; the key is the strongest cheap invariant used here.
- Most importantly, the four-vendor oracle evidence is blocked by account quota.
  Local correctness and attack gates pass, but the required no-tool model claim
  is not established until `scripts/harden.py` completes successfully.
