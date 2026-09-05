# arXiv 2409.08037 — cyclic multiple orthogonal vectors

**Status: locally verified, but not shippable yet.** Every deterministic gate
passes. The required bare, structural-hint, and placebo OpenRouter runs each made
four redraws, but all calls returned HTTP 403 `Key limit exceeded`; errors count as
neither attempts nor model failures. The script-owned transcripts are preserved.

| profile field | value |
|---|---|
| track | B — an efficient exact algorithm exists and is measured |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | CSP/SAT |
| certificate form | integer tuple of local vector-row indices |
| intuition | invariant: parity quartets overlap on one hidden tight cycle |
| domain essentiality | native |
| reduction | none; Definition 3.10's binary-vector objects are posed directly |

## Problem and trust boundary

The source is Künnemann and Redzic,
[*Fine-Grained Complexity of Multiple Domination and Dominating Patterns in
Sparse Graphs*](https://arxiv.org/abs/2409.08037). Definition 3.10 in Section 3.2
defines `r`-Multiple `k`-Orthogonal Vectors: select one binary vector from each
set so that every coordinate has a zero in at least `r` selected vectors. This
family uses `r=1`, exactly `k`-OV. Lemma 3.11 makes these objects central rather
than a convenience surrogate by reducing them to sparse multiple-domination
graphs.

The generator samples a Boolean assignment first, constructs a full-rank cyclic
3-XOR system satisfied by it, replaces every XOR equation by its four exact CNF
clauses, and partitions variables into complete assignment blocks. Each block
assignment is one binary vector. Thus the planted rows have coordinatewise AND
zero by composition of identities; no generated instance is solved to obtain
its certificate. `verify` ignores `inst["answer"]`, range-checks the row indices,
and intersects the selected vectors as exact integers. Every block contains all
assignments, so planted and decoy rows have the same distribution.

## Why Track B

Lemma 3.15 proves a conditional full-product lower bound for general fixed-`k`,
`r <= k-2` instances, not for this structured distribution. The paper also
identifies easy or faster regimes: Theorem 1.1 gives the matrix-product algorithm
for `r <= k-2` domination, Theorem 1.3 handles `r=k-1` through unbalanced clique,
and Section 1 observes that `r>=k` is trivial. The shipping construction therefore
makes no Track-A claim.

For these instances, a standard exact route groups the parity quartets and runs
Gauss–Jordan elimination over `GF(2)`. Its complexity is
`O(C log C + n^3)`; over eight hard instances it solved 8/8, used at most 33,001
counted Boolean operations, and averaged 0.004576 seconds in the final audit
(0.0005--0.0046 seconds across repeated local audits). Plain DPLL with unit
propagation also solved 8/8, but reached 445 search nodes and 808,167 literal
operations. The compact route
recognizes that the equation triples form one two-overlap cycle, decodes one
right-hand side per quartet, and follows the cyclic recurrence. It solved 8/8 in
298 exact bit operations. The benchmark tests recognition of that invariant,
not resistance to software.

## Worked demo

For `make_instance(n=5, block_bits=2, copies=1, seed=3)`, the full statement is:

```text
Find a witness for this 1-Multiple k-Orthogonal Vectors instance.

There are k ordered sets A_1,...,A_k of equal-length binary vectors.
Choose exactly one vector from each set.  The choice is valid exactly
when, in every coordinate, at least r=1 chosen vector has bit 0;
equivalently, the coordinatewise Boolean AND of all chosen vectors is
the all-zero vector.

The vectors are specified exactly and compactly below.  Variables are
Boolean.  A signed integer +j is variable x_j and -j is its negation;
variables in clauses are 1-indexed.  Every clause is the OR of its three
listed literals.  Each clause is one vector coordinate.  A row in A_i
is a partial assignment to A_i's displayed variables, in that displayed
order.  Its bit in a clause-coordinate is 0 iff one or more literals of
that clause belonging to A_i is made true by the row; otherwise it is 1.
Thus all vector bits are fixed by the data below, with no omitted edges,
conditions, or conventions.

Number of variables n: 5
Number of vector sets k: 3
Number of coordinates (indexed clauses): 20

Vector sets.  Local row indices are zero-based.  A bit string gives the
partial assignment in the exact variable order printed for that set:
A_1 variables [4,1] | 0:11 1:10 2:01 3:00
A_2 variables [2,3] | 0:10 1:11 2:01 3:00
A_3 variables [5] | 0:0 1:1

Coordinates, one signed JSON triple per line:
c1: [2,-3,4]
c2: [-5,4,-1]
c3: [1,-5,2]
c4: [-5,4,3]
c5: [-2,-3,1]
c6: [2,-3,-1]
c7: [-4,5,-1]
c8: [3,-4,5]
c9: [-4,3,2]
c10: [2,1,3]
c11: [3,4,-2]
c12: [-2,5,1]
c13: [3,-2,-1]
c14: [-2,-4,-3]
c15: [5,2,-1]
c16: [-5,-4,-3]
c17: [-2,-1,-5]
c18: [1,5,4]
c19: [-3,4,5]
c20: [1,-4,-5]

Return a JSON list of exactly k local row indices, in A_1,...,A_k
order.  The row for A_i must lie from 0 through |A_i|-1 inclusive.
Row numbers are local, so repetitions across different sets are allowed;
the order of the k output positions is mandatory.

Give your final answer inside <answer></answer> tags, as a JSON list of integers.
Example format for three sets: <answer>[2,0,3]</answer>
Output nothing else inside the tags.
```

The answer `<answer>[1,2,0]</answer>` gives `(True, "ok")`. Dropping its
last row gives `(False, "answer has too few row indices: expected 3, got 2")`.
A person can solve this five-variable illustration on paper by regrouping its 20
clauses into five parity quartets.

## Difficulty presets

| preset | Boolean variables | block bits | vector sets | coordinates | answer atoms | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 2 | 3 | 20 | 3 | hand-solvable; hardener skips it |
| easy | 23 | 2 | 12 | 92 | 12 | oracle unavailable before attempt 1 |
| medium | 41 | 4 | 11 | 164 | 11 | deterministic gates pass |
| **hard** | **59** | **5** | **12** | **236** | **12** | candidate shipping rung; oracle evidence pending |

`SHIPPING_DIFFICULTY` is provisionally `hard`. Larger `n` still builds and
verifies, but the intended exact route costs `5n+3`; `escalate()` returns
`cap_bound` above 59 because the next useful rung would exceed G9(c)'s
300-operation limit, not because the paper or construction has failed.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify; answers JSON-round-trip; every `A_i` is a set |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose/fence round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `2^-59` |
| G5 | pass | shipping count 1; 2,048 restarts fail in 0.176069 s; demo count 1/32 |
| G6 | pass | four attacks each 0/8; Gaussian, plain-DPLL, and compact solvers each 8/8 |
| G7 | pass | doubled `n=118` builds and verifies; route cap reported honestly |
| G8 | pass | 120/120 relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | pass | 37 worst-case chars (32 planted), 26 estimated tokens, 12 atoms, 298 operations |

## Oracle loop and G9 arms

No row below is a counted attempt. The harness correctly records API errors as
errors, so there is no hardened/too-easy verdict and no evidentiary hardness
claim yet.

| arm | requested preset | seeds | counted solved/attempts | result |
|---|---|---|---:|---|
| bare | easy | 498922367, 699428317, 1942611219, 849194255 | 0/0 | four HTTP 403 quota errors |
| structural | hard | 1109354919, 241986199, 264458136, 1671357656 | 0/0 | four HTTP 403 quota errors |
| placebo | hard | 1740976084, 1487632940, 1019245926, 2129490344 | 0/0 | four HTTP 403 quota errors |

Hinted minus placebo is undefined because both denominators are zero. Therefore
the transcripts support no conclusion about whether the structural hint helps.

## Use

```python
from gen_2409_08037 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=19, **DIFFICULTY["hard"])
assert verify(inst, inst["answer"]) == (True, "ok")
prompt = render(inst)
```

After restoring OpenRouter quota, rerun the bare harness and both scratch-directory
G9 arms, then update the oracle fields and shipping preset. From the repository
root, a completed result emits with:

```bash
bash scripts/emit.sh 2409.08037 20 hard
```

## Caveats

This distribution is deliberately easy with tools: parity recovery plus Gaussian
elimination is complete. G4 samples uniformly from the stated in-range row tuple
language, which is exactly uniform over all `2^59` Boolean assignments, but it does
not model an XOR-aware solver. The 298-operation count includes right-hand-side
decoding and recurrence arithmetic; it excludes reading, sorting quartet labels,
discovering the overlap cycle, and looking up final rows. Those bookkeeping costs
could contribute to no-tool failure.

No industrial SAT/SMT solver or specialized `k`-OV package was run. Plain DPLL
with unit propagation was tested and solved 8/8, but needed as many as 445 nodes
and 808,167 literal operations; exact Gauss–Jordan is the stronger domain-aware
reference. The canonical key
covers row, coordinate, literal, variable, group, Boolean-complement, within-group,
rotation, reversal, and their composed relabellings for this generated family, but
does not claim general `k`-OV isomorphism. Most importantly, the mandatory
multi-vendor oracle evidence is absent until the API calls complete successfully.
The current repository hardener is configured for two vendors, although the task
specification still describes a four-vendor pool; this run used the script unchanged.
