# arXiv 2105.06349 — certified line-graph connected subgraphs

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete (a finite line graph with an exact GF(2) encoding) |
| Computational core | CSP/SAT |
| Certificate | integer tuple (a binary rail-choice vector) |
| Intended intuition | reduction recognition: expose and invert a cyclic parity operator, then reverse the XOR circuit |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 3 Lemma 4 |

## Problem and trust status

The family instantiates [*Disjoint Paths and Connected Subgraphs for H-Free Graphs*](https://arxiv.org/abs/2105.06349), specifically the explicit 3-SAT-to-line-graph construction in Section 3, Lemma 4. The solver receives the complete rail-and-clause specification of a claw-free line graph (L(B)), terminal sets (Z_1,Z_2), and GF(2) equations whose four falsifying rows are the construction's 3-CNF clauses. It must return input-rail choices. Those bits deterministically expand to two concrete, vertex-disjoint connected sets in (L(B)). `verify` evaluates every parity equation, constructs both sets as base-graph edges, and checks terminal containment, disjointness, and line-graph connectivity exactly.

Generation is inverse: it samples the input bits first, evaluates a random reversible XOR circuit, derives the cyclic checks, expands each ternary parity equation into four clauses, and carries the sampled assignment through Lemma 4. It never solves the instance it just made. Local correctness, corruption, density, adversary, scaling, and canonicalisation gates pass. **The required multi-vendor oracle run is not complete:** the refreshed run established that the 8/12, 16/48, and 32/160 parameter levels are defeated, but OpenRouter then returned HTTP 403 `Key limit exceeded` while the script was finishing the 32/160 level. The script-owned partial transcript is retained and must be replaced by a clean run before submission.

## Why Track B, not Track A

The paper's exact definition is in Section 1. The fixed-(k) Disjoint Paths suggestion from the initial triage is unsuitable for Track A: Theorem 1.1 gives a polynomial algorithm for every fixed (k). For connected terminal sets, Theorem 1.2 and Lemma 4 show NP-completeness already for (k=2), (|Z_1|=2), on line graphs; line graphs are claw-free. The easy side that must also be recorded is Lemma 3: for (H\subseteq_i sP_1+P_4), fixed-(k) Disjoint Connected Subgraphs is polynomial. Theorem 6.2 additionally gives a general (O(3^N k m)) exact algorithm.

Worst-case NP-completeness does not make this generated distribution hard. Its displayed clause blocks are XOR equations, so exact Gaussian elimination over GF(2) solves the intended shipping system in (O(V^3)). Across eight self-test seeds it used about 263,454 XOR/pivot operations and 0.023 seconds for (V=268), succeeding 8/8 as expected. The compact route notices that the CHECK rows encode (I+T+T^{n/2}) on one cycle. For power-of-two (n), its inverse is (T^{n/2-2}+T^{n-2}+T^{n-1}); applying that identity and reversing the linear XOR gates costs 300 XORs. This mechanical/compact gap is the Track B claim. It is deliberately disclosed rather than mislabeled as structural hardness.

## Worked demo

This is `make_instance(n=4, gates=4, seed=3)` in full. A person can solve it on paper by checking at most 16 inputs, or more directly by XOR elimination.

```text
Find a compressed witness for two disjoint connected subgraphs in a claw-free line graph.

All graphs here are finite, simple, and undirected. A vertex set is connected
when the subgraph induced by it has a path between every two of its vertices;
two vertex sets are disjoint when they share no vertex. A claw is the four-
vertex star K1,3, and claw-free means having no induced claw.

All bits below are in GF(2): XOR is addition modulo 2. Wire labels v0,
..., v7 are identifiers, not an ordering. Every displayed equation has three
distinct wires. Its four listed 3-bit codes are exactly the falsifying rows, in
clause-slot order. A code abc creates the 3-CNF clause that is false at (a,b,c):
use a positive literal for code bit 0 and a negated literal for code bit 1.

The graph is specified exactly as follows. Make a positive and a negative rail
for every wire, in the displayed RAIL ORDER. On a rail, place that literal's
clause occurrences in increasing (equation id, clause slot) order. Join
consecutive vertices of each rail. Between consecutive wire gadgets join both
rail ends to both next rail starts. Join the two starts of the first gadget by
edge e and the two ends of the last gadget by edge f. For each clause make one
clause vertex and join it to its three occurrence vertices. Call this base graph
B. The problem graph is the line graph L(B): each edge of B is a vertex, and two
such vertices are adjacent exactly when their B-edges share an endpoint. Thus
L(B) is claw-free.

Terminal set Z1 is {e,f}. Terminal set Z2 is every B-edge from a clause
vertex to an occurrence vertex. A witness bit 0 chooses the positive rail
and bit 1 the negative rail for S1. Concretely, S1 contains e, f, every
B-edge along each chosen rail, and between consecutive gadgets the one
connector B-edge joining the two chosen rails. S2 contains every B-edge
along the complementary rails, their corresponding connector B-edges, and
all Z2 vertices, but not e or f. The gate rows extend the input bits in step
order. The CHECK rows must all hold. Thus the bits specify concrete vertex
sets S1,S2 in L(B); validity means they are disjoint, connected, and contain
Z1,Z2, respectively.

Number of input bits: 4
Input wires in answer order:
  v6 v0 v2 v7
Rail order:
  v0 v4 v3 v5 v6 v1 v2 v7

GATE rows (semantic form z = a XOR b XOR rhs):
  step 000, E2: v4 = v2 XOR v0 XOR 0; codes=010,100,111,001
  step 001, E0: v1 = v4 XOR v7 XOR 0; codes=111,010,001,100
  step 002, E1: v5 = v1 XOR v2 XOR 0; codes=001,010,100,111
  step 003, E6: v3 = v4 XOR v6 XOR 0; codes=001,100,010,111

CHECK rows (the operand order shown is part of the data):
  E4: v3 XOR v4 XOR v5 = 1; codes=101,000,110,011
  E7: v4 XOR v5 XOR v1 = 0; codes=100,010,111,001
  E3: v1 XOR v3 XOR v4 = 0; codes=001,111,010,100
  E5: v5 XOR v1 XOR v3 = 0; codes=001,100,111,010

Return exactly 4 bits, one for each input wire in the listed
answer order: the first bit is for the first listed wire. Only 0 and 1 are
allowed; no separators, spaces, repeats, or ellipsis may occur in the string.

Give your final answer inside <answer></answer> tags, as that bit string.
Example: <answer>0101</answer>
Output nothing else inside the tags.
```

The answer is `<answer>0011</answer>`, parsed as `[0, 0, 1, 1]`; `verify` returns `(True, "ok")`. Dropping the last bit gives `[0, 0, 1]`, for which it returns `(False, "too few bits: expected 4, got 3")`.

## Difficulty presets

Counts below use seed 3; graph sizes are seed-independent at fixed parameters. The ladder was advanced after the partial oracle run defeated every old named rung. `hard` is the intended shipping preset, pending a clean required oracle run.

| preset | inputs | XOR gates | system variables | vertices of (L(B)) | answer space | compact XORs | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 4 | 4 | 8 | 238 | (2^4) | 12 | hand-solvable illustration |
| easy | 32 | 160 | 192 | 5,758 | (2^{32}) | 224 | defeated in partial run: 1 solve / 2 completed calls |
| medium | 32 | 192 | 224 | 6,718 | (2^{32}) | 256 | not yet oracle-scored |
| hard | 32 | 236 | 268 | 8,038 | (2^{32}) | 300 | intended ship; clean oracle run pending |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset-seed instances; exact expanded witnesses; executable claw check on demo/hard samples |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged model-style response round-trips and verifies |
| G4 | pass | 0/200,000 structure-aware uniform binary guesses; exact density (1/2^{32}\approx2.33\times10^{-10}) |
| G5 | pass | demo exact count 1; shipping sample 0/200,000; 64-restart attack about 0.057 s; Gaussian reference about 0.023 s / 263,454 operations |
| G6 | pass | five failing attacks, each 0/8; Gaussian reference succeeds 8/8 as Track B requires |
| G7 | pass | doubled instance: 64 inputs, 384 variables, planted witness verifies |
| G8 | pass | 620/620 invariant transformation compositions, 620/620 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 96 JSON characters, 24 estimated tokens, 32 atoms, 300 intended operations |

## Oracle loop and G9 arms

No hardness verdict is claimed from the present run. The completed calls below are useful negative evidence for the discarded rungs, but the run ended in an API quota error before producing a verdict.

| arm / preset | solved / attempts | result |
|---|---:|---|
| bare / old 8 inputs, 12 gates | 3 / 3 | defeated; all three solved |
| bare / old 16 inputs, 48 gates | 2 / 3 | defeated; two solved |
| bare / 32 inputs, 160 gates (now `easy`) | 1 / 2 completed | defeated by one verified solve; quota errors prevented the third call and escalation |
| structural hint / intended `hard` | 0 / 0 countable attempts | prior isolated run had four HTTP 403 quota errors; must be rerun |
| placebo hint / intended `hard` | 0 / 0 countable attempts | prior isolated run had four HTTP 403 quota errors; must be rerun |

Consequently hinted-minus-placebo is presently undefined. The structural hint only names the cycle/antipode invariant; it does not state the inverse or a procedure. Answer size and compact-route cost are 96 characters / 32 atoms and 300 XORs.

## Use

```python
import random
import gen_2105_06349 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
question = g.render(inst)
candidate = g.parse_answer("<answer>" + "".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.random_candidate(inst, random.Random(1)) is not inst["answer"]
```

From the repository root, after a valid hardening transcript exists:

```bash
bash scripts/emit.sh 2105.06349 20 hard
```

## Caveats

- This is not a Track A average-case claim. Gaussian elimination is a complete, fast solver for this generated XOR subdistribution; the benchmark tests whether a no-tool solver discovers the shorter cyclic inverse.
- The NP-completeness of Lemma 4 is worst-case evidence for the surrounding line-graph problem, not evidence about these sampled instances.
- The (P(guess)) measurement is uniform over every stated length-32 binary witness. It correctly incorporates all obvious answer-shape constraints, but it does not model a solver prior that has already recognized the cyclic construction. There is exactly one valid vector.
- The graph is given by an exact implicit rail-and-clause constructor rather than a 5,758-row adjacency list. Verification expands it; deleting that graph structure would delete the certificate check, but the search itself is carried by the paper-licensed SAT source.
- The adversary panel does not include an industrial SAT solver, ILP, or arbitrary symbolic algebra. Gaussian elimination is stronger and complete on the exposed parity system and is therefore reported separately as the successful Track B reference algorithm.
- `canonical_key` is a normal form for the generator's rail-and-clause representation, not a complete canonical form for arbitrary line-graph isomorphism. It normalizes wire names, answer-coordinate order, record order, independent rail swaps, whole-rail reversal, and all their compositions; an unrecognized graph isomorphism could still make two encodings receive different keys.
- The current external quota failure must be cleared and the bare, structural-hint, and placebo script-owned runs completed before this result is submission-ready.
