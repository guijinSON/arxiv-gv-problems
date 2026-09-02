# Bounded-hop independent-set reconfiguration generator

This directory turns Hatano, Kitamura, Izumi, Ito, and Masuzawa’s [*Independent Set Reconfiguration Under Bounded-Hop Token Jumping*](https://arxiv.org/abs/2407.11768) into a deterministic witness generator. A solver receives an implicitly specified chordal graph, initial and target independent sets, a hop bound `k=3`, and an exact move budget. It returns a bit-string preimage that canonically expands to a complete token-move sequence. `verify` evaluates the circuit, reconstructs the exact 3-CNF and Section 5 graph, and replays all moves, checking occupancy, a concrete path of at most three graph edges, independence, and the final set. It accepts every preimage producing the target, not only the planted one.

## Why this is the hard regime

Section 2 defines one `k`-Jump as replacing exactly one occupied vertex by an empty vertex at graph distance at most `k`, while preserving independence. Section 5.1 gives the E3-SAT gadgets used here. Lemma 12 in Section 5.2 proves that the constructed chordal graph, of diameter at most `2k+1`, has a sequence of at most `2(m+n)` moves exactly when the E3-SAT formula is satisfiable; Lemma 14 supplies the canonical sequence encoded by the answer.

Plain reachability would not be credible here. Theorem 1 (Section 3) makes reachability for every `k>=3` equivalent to unrestricted Token Jumping, and Tables 1–2 record polynomial algorithms on chordal/even-hole-free graphs for that reachability regime and for shortest Token Jumping. The generator therefore fixes the NP-complete bounded length from Lemma 12. Its satisfiable formula encodes preimage search for two independently tapped, nonlinear multi-round Boolean mixing branches. There is no known polynomial-time or closed-form inversion method for this circuit family; the named ladder starts at a `2^48` answer space.

An earlier planted NAE-3-SAT design is not shipped: bounded min-conflicts solved 8/8 medium instances. The replacement samples the preimage before the taps, outputs, or clauses and exposes only the two final mixed states. This removed the clause-local planted gradient; the measured attacks below all failed.

## Worked example (`easy`, seed 0)

The following is the complete output of `render(make_instance(seed=0, **DIFFICULTY["easy"]))`:

```text
Bounded-hop independent-set reconfiguration witness

First invert these two fully specified Boolean mixing branches.  Their shared
secret input is S[0],...,S[47].  Each branch starts from that input.  In each
round use the three integer offsets a,b,c listed below and simultaneously
compute, for every i=0,...,47 (all subscripts modulo 48):

    A[i] = S[i+a] AND S[i+b]
    X[i] = S[i] XOR S[i+c]
    S_new[i] = A[i] XOR X[i]

Read S[0]...S[47] after the final round of branch 0 and then after the final
round of branch 1, and concatenate them.  The required
96-bit output is:
001001001011000011000100001010001000011000011001000100100011001001010100011101101011010001000111

Branch/round offsets (a b c):
B0R0: 21 37 11
B0R1: 47 8 29
B0R2: 36 14 31
B0R3: 30 6 29
B0R4: 21 38 37
B0R5: 19 12 23
B0R6: 12 3 19
B0R7: 32 5 25
B1R0: 45 10 7
B1R1: 3 6 13
B1R2: 47 34 37
B1R3: 35 16 25
B1R4: 45 39 19
B1R5: 38 18 41
B1R6: 32 44 43
B1R7: 6 21 35

Here is the exact E3-SAT formula and graph implied by that circuit.  This also
defines the reconfiguration witness encoded by your preimage.  Formula variable
IDs are 1-based.  Inputs use IDs 1,...,48.  Two free padding variables are
z=49 and w=50.  Then, in increasing branch, round, and i order,
allocate three fresh IDs A[i], X[i], S_new[i], in that order.  Each branch begins
again with input IDs 1,...,48.  A signed integer q denotes
variable q when positive and NOT variable |q| when negative.  Append clauses in
the order shown by these macros, preserving literal order:

AND(a,b,y): (-a,-b,+y), (+a,-y,+z), (+a,-y,-z),
            (+b,-y,+z), (+b,-y,-z)
XOR(a,b,y): (-a,-b,-y), (-a,+b,+y), (+a,-b,+y), (+a,+b,-y)
FORCE(l):   (+l,+z,+w), (+l,+z,-w), (+l,-z,+w), (+l,-z,-w)

For each circuit assignment append AND then XOR then XOR macros in the same
order as the three equations.  Finally append FORCE(output-wire) when its target
bit is 1 and FORCE(-output-wire) when it is 0, from output index 0 upward.  This
creates exactly 2354 variables and 10368 clauses, each with
exactly three distinct literals.

Construct the paper's graph as follows.  Clauses are indexed 0,...,10367
in append order and literal positions are 0,1,2.  For clause i create a path
v(i,0),...,v(i,6).  Its gates are g(i,1)=v(i,3) and new vertices g(i,0),
g(i,2).  Join g(i,0) and g(i,2) to v(i,2) and v(i,4), and make all
31104 gates over all clauses one clique.  For formula variable j create
a path u(j,0),...,u(j,2) and vertices s(j,0),s(j,1), each joined to u(j,0).
Write t(j,0)=u(j,0), t(j,1)=u(j,2).  A positive literal +j in position p
joins g(i,p) to s(j,0) and t(j,0); a negative literal -j joins it to s(j,1) and
t(j,0).  There are no other edges.

Initially every v(i,0), s(j,0), and s(j,1) has a token.  The target consists of
every v(i,6), t(j,0), and t(j,1).  A token set is independent iff no two
occupied vertices share an edge.  One 3-Jump replaces exactly one occupied
vertex by one empty vertex at shortest-path distance at most 3, and the new set
must be independent.

Your preimage encodes exactly 25444 moves.  Evaluate every circuit
wire, set z=w=0, and choose the leftmost true literal (position 0, then 1, then
2) in each clause.  First, in increasing variable-ID order, move s(j,0) to
t(j,1) for a true variable and s(j,1) to t(j,1) for a false variable.  Next, in
increasing clause order, move v(i,0) to the chosen gate and that gate to
v(i,6).  Finally move the remaining s vertex of each variable to t(j,0),
again in increasing variable order.  The checker reconstructs and replays every
move; it never compares your preimage with a planted one.

All ranges are inclusive, strings are in increasing index order, and repeats are
not allowed where the construction says "fresh".  Any 48-bit preimage producing
the target is accepted.

Give your final answer inside <answer></answer> tags, as one JSON object with the
single key "preimage", whose value is exactly 48 binary characters.
Example of the required shape: <answer>{"preimage":"000000000000000000000000000000000000000000000000"}</answer>
Output nothing else inside the tags.
```

The planted witness is `{"preimage":"110111111001001010011011101110001011010000010011"}`. `verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping its last bit returns `(False, "preimage is too short: 47 < 48")`.

## Difficulty presets

| preset | hidden bits `n` | rounds/branch | structured space | status |
|---|---:|---:|---:|---|
| `easy` | 48 | 8 | `2^48` | **ships; 3/3 oracle failures** |
| `medium` | 64 | 10 | `2^64` | local gates pass; oracle escalation not needed |
| `hard` | 80 | 12 | `2^80` | local gates pass; oracle escalation not needed |
| `extreme` | 96 | 14 | `2^96` | local gates pass; oracle escalation not needed |

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted witnesses verified (4 presets × 4 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | prose/fence/tag round-trip passed; garbage returned `None` |
| G4 | 0/200,000 structure-aware uniform preimages verified (`n=48`) |
| G5 | exact audit: 1 valid preimage / 4,194,304 = `2.384185791015625e-7` |
| G6 | outlier 0/8, greedy 0/8, bounded random restart 0/8 |
| G7 | doubled `n=96` built and verified; moves grew 25,444 → 50,884 |
| G8 | invariance 20/20, carried witnesses 20/20, unrelated keys 20/20 distinct |

## Oracle hardening loop

All calls used reasoning effort `medium`; every response parsed as the requested JSON but produced the wrong circuit output.

| preset | model | seed | solved | reason |
|---|---|---:|---|---|
| `easy` | Gemini 3.1 Pro Preview | 1883275592 | no | wrong circuit output |
| `easy` | GPT-5.6 Terra | 2066049 | no | wrong circuit output |
| `easy` | Grok 4.6 | 306236146 | no | wrong circuit output |

Harness verdict: `hardened`, zero escalations, shipping parameters `n=48, rounds=8, k=3`. See `llm_loop_transcript.jsonl` and `.meta.json` for complete replies and timings.

## Use

```python
import random
import gen_2407_11768 as gen

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
answer = gen.parse_answer('<answer>{"preimage":"...48 bits..."}</answer>')
ok, reason = gen.verify(inst, answer)
candidate = gen.random_candidate(inst, random.Random(9))
```

From the repository root, emit 20 fresh, deduplicated shipping instances with:

```bash
bash scripts/emit.sh 2407.11768 20 easy
```

## Caveats

- The paper proves worst-case NP-completeness for all E3-SAT images, not average-case hardness of this nonlinear-circuit subdistribution. Hardness here combines that theorem, the absence of a known inversion formula for these circuits, the local gates, and three oracle failures; it is not a cryptographic proof.
- G4 samples uniformly from all correctly shaped 48-bit preimages—the complete free choice in the compact witness. `0/200,000` demonstrates resistance to that prior but is not an estimate of a vanishing true probability and says nothing about guided SAT search.
- The panel did not run CDCL, Gröbner-basis/algebraic solvers, GPU brute force, spectral attacks, or dedicated cryptanalysis. Random restart was bounded to 4 starts × `8n` steps and scored every one-bit neighbor.
- Outputting two final branch states may make most instances uniquely invertible, but uniqueness is neither assumed nor proved. `verify` accepts any preimage that works.
- `canonical_key` uses stable color refinement of the signed formula-incidence graph. Exact signed-formula/graph isomorphism is intractable in general, so the key can conservatively collide. It was tested under arbitrary formula-variable renaming, independent polarity flips, literal and clause reordering, and against 20 unrelated seeds.
- The huge gate clique and formula are represented by exact construction rules rather than materialized edge lists. This keeps generation and checking practical; changing those rules would change the problem.
