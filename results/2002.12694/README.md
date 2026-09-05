# Edge-disjoint temporal branchings — verified generator

| profile field | value |
|---|---|
| Track | **B** — no-tool compression |
| Native domain | `combinatorics` |
| Object regime | `finite_field` |
| Computational core | `csp_sat` |
| Certificate form | `polynomial` |
| Intended intuition | `invariant`: block-code XORs expose the kernel of one GF(2) linear form |
| Domain essentiality | `licensed_reduction` |
| Reduction | `paper_licensed`, Section 3.2, Theorem 3 |

## What the problem is

This generator instantiates the star-snapshot reduction in Campos, Lopes, Marino, and Silva, [*Edge-Disjoint Branchings in Temporal Graphs*](https://arxiv.org/abs/2002.12694), Theorem 3. The solver receives a finite temporal DAG whose base graph is a directed star. It must give a fixed-weight affine polynomial over GF(2); the polynomial assigns each base edge to one of two branchings. The checker expands that compact object into actual temporal edges and exactly checks unique root reachability at every active vertex and base-edge disjointness. It never reads the planted answer.

The paper's reduction maps positive NAE-3-SAT to two base-edge-disjoint temporal-spanning branchings. Here, every four-source block is expanded into its four three-source NAE clauses. Those four clauses are satisfied precisely when the block has two sources of each colour. Public binary labels and the polynomial answer are a benchmark-added compression layer; the temporal graph, branchings, and the NAE-to-star reduction are the paper's objects.

## Why this is Track B

Theorem 3 proves NP-completeness for every fixed `k >= 2`, even when the base graph is a DAG with star underlying graph and every snapshot has constant size; under ETH it also rules out `O*(2^o(T))` algorithms in the lifetime. That is a worst-case result, not an average-case claim about this generator.

This generated distribution has an efficient exact method and therefore is **not Track A**. Build the overlap graph of four-source blocks, try the six balanced colours of one block, propagate exact-two constraints, and fit the public affine form by GF(2) elimination. Its complexity is `O(B^2 + n*w^2)`. At the shipping preset it solved 8/8 instances, averaging 159,978 counted primitive operations (maximum 218,950) and about 0.005 seconds in the final selftest.

The compact route is different: the first `w-1` displayed blocks have code XORs forming a shuffled sparse basis of the planted kernel. Singleton directions identify zero coefficients, while two-bit directions join the one coefficients. Recovering the 30-position support takes at most 297 counted exact operations and the constant may be either value. This is just within the no-tool cap, while the reference calculation is roughly 700 times larger.

The easy regimes were deliberately avoided. Section 3.1 reduces temporal-edge-disjoint temporal-spanning branchings to Edmonds' polynomial static problem. Theorem 4 is also polynomial when every vertex's active times form one consecutive interval, including eternal vertices and lifetime two. Generated appearances instead occur in separated odd snapshots, and disjointness is over base edges.

## Worked demo

The smallest supported preset is hand-solvable: XOR the four codes in each of the first three block rows, infer the two support positions, and choose either constant. For `seed=17`, `render()` produces the complete statement below.

```text
TWO BASE-EDGE-DISJOINT TEMPORAL-SPANNING BRANCHINGS

A temporal vertex is a pair (vertex,time) at which that vertex is active.
A temporal edge (u,t)->(v,t') may be used only when t<=t'. A temporal
walk follows temporal edges forward in time and may wait from (v,t) to
(v,t+1) only when v is active at both consecutive times.

A branching rooted at a set R of temporal vertices must have exactly one
temporal walk from R to every active temporal vertex. Two branchings are
base-edge-disjoint when no directed edge u->v of the base digraph has
any temporal appearance in both branchings.

This instance has centre T and 8 positive sources v0..v7, each
with a negative mate ~v0..~v7. Its lifetime is 55.
Only odd times are nonempty; every even time is empty, so no waiting
between nonempty snapshots is possible. All edges below are instantaneous
source->T edges. Every active source, but never T, is in both root sets.

The variable snapshots come first, in source-id order. Snapshot i has
active vertices v_i, ~v_i, T and edges v_i->T, ~v_i->T.

Each positive source has a distinct 4-bit public code. Bit 0 is the
least significant bit. Codes are hexadecimal; leading zeroes are included:
  v2=0x4  v6=0xb  v5=0x6  v4=0xe  v7=0x8  v1=0x3
  v3=0x0  v0=0x1

After the variable snapshots come the four clause snapshots for each
displayed block, in displayed block order. If a block row is [a,b,c,d],
its four snapshots have respectively the three positive sources obtained
by omitting a, then b, then c, then d; each has those three edges to T.
The order of sources within a row is significant only for this omission
order. Repeated block rows are distinct later temporal demands.

Blocks (5 rows):
  0: [v1,v3,v0,v7]
  1: [v6,v0,v1,v7]
  2: [v4,v1,v0,v7]
  3: [v1,v5,v3,v0]
  4: [v1,v2,v6,v7]

Your answer is a GF(2) linear polynomial L on the public codes.
The integer constant is 0 or 1. The support is a strictly increasing
list of exactly 2 distinct bit positions in the inclusive range
0..3. For a source with code x, define

  L(x) = constant XOR (the listed bits of x),

where XOR means addition modulo 2.

The certificate expands to two concrete branchings as follows.
Branch 1 owns v_i->T when L(code(v_i))=1 and owns ~v_i->T otherwise.
Branch 2 owns the other one of those two base edges. In each variable
snapshot each branch uses its owned edge. In each clause snapshot each
branch uses the owned active positive-source edge having the smallest
public code (source id breaks a tie, although codes here are distinct).

The polynomial is valid exactly when this expansion gives two temporal-
spanning branchings and their sets of used base edges are disjoint. Any
polynomial in the stated bounded language with that property is accepted.

Give your final answer inside <answer></answer> tags as one JSON object
with keys constant and support, exactly in the format just defined.
Example: <answer>{"constant":0,"support":[0,1]}</answer>
Output nothing else inside the tags.
```

The planted answer is `{"constant":1,"support":[1,3]}` and `verify` returns `(True, "ok")`. Dropping position 3 gives `{"constant":1,"support":[1]}` and returns `(False, "wrong support size: expected exactly 2 bit positions")`.

## Difficulty presets

`B` is the number of four-source rows; each row represents four constant-size clause snapshots. The shipping rung is **easy**, the first rung held by all three bare oracle attempts.

| preset | sources `n` | code bits `w` | support | blocks `B` | ships? |
|---|---:|---:|---:|---:|---|
| demo | 8 | 4 | 2 | 5 | no; illustration |
| easy | 64 | 60 | 30 | 61 | **yes** |
| medium | 128 | 60 | 30 | 125 | no; not needed |
| hard | 256 | 60 | 30 | 253 | no; not needed |

No preset was rejected by a gate. `escalate()` first adds fresh distinct exact-two rows (tightening the constraints at fixed answer length); after three crowding layers it doubles `n` and resets the layer count. Both axes leave the 30-position answer unchanged.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 20/20 planted certificates verified across four presets |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON round-trip succeeded; garbage returned `None` |
| G4 | pass | 0/250,000 structure-aware guesses; language size 236,529,163,129,722,848 |
| G5 | pass | shipping density 0/250,000; demo exact count 2/12; reference maximum 218,950 operations and about 0.005 s |
| G6 | pass | low-bit, frequency-outlier, 8-row partial-XOR, 8-swap greedy, and 256-restart attacks each scored 0/8; reference method solved 8/8 |
| G7 | pass | `n: 64 -> 128`, blocks `61 -> 125`, reference operations `179,494 -> 498,299`, answer atoms unchanged at 31 |
| G8 | pass | 20/20 relabelling invariance, 20/20 carried-witness checks, 20/20 composed checks, and 20/20 unrelated keys distinct |
| G9 | pass | 110 characters, about 28 tokens, 31 atoms, and 297 intended-route operations |

## Bare oracle loop

The local `harden.py` pool on 2026-09-05 contained two vendors/models and made three attempts, drawing one model twice. All calls used medium reasoning effort.

| preset | model | seed | solved | outcome |
|---|---|---:|---|---|
| easy | `google/gemini-3.8-flash` | 2127272984 | no | output ended at the length limit before answer tags |
| easy | `openai/gpt-5.6-terra` | 867629403 | no | parsed support failed block 0 |
| easy | `openai/gpt-5.6-terra` | 1156975366 | no | parsed support failed block 0 |

Verdict: `hardened`, with zero escalations.

## G9 hint diagnostic

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural | 0 / 3 | hardened |
| placebo | 0 / 3 | hardened |

`hinted - placebo = 0.0`. Naming the kernel invariant bought no verified solves in this small sample. The transcripts suggest that models often began finding sparse bit relations but lost reliability in the exact bookkeeping; thus the current evidence does not isolate invariant discovery from execution cost. The measured answer is 110 characters, approximately 28 tokens, and 31 atoms; the intended route is 297 exact operations.

## Use

From this directory:

```python
import gen_2002_12694 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
print(g.render(inst))
answer = g.parse_answer('<answer>{"constant":0,"support":[...]}</answer>')
ok, reason = g.verify(inst, answer)
```

From the repository root, emit 20 shipping instances with:

```bash
scripts/emit.sh 2002.12694 20 easy
```

## Caveats

- This is a Track B compression benchmark. The polynomial-time reference algorithm is fast on a computer (milliseconds), so neither Theorem 3's worst-case hardness nor the huge certificate-language cardinality supports an average-case Track A claim.
- The GF(2) labels and polynomial witness are not in the paper. They compactly specify genuine Theorem 3 temporal branchings, and verification operates on those branchings, but they impose additional structure on the generated distribution.
- The 0/250,000 guess result samples uniformly from fixed-weight affine polynomials. It does not model a solver that has recognized the sparse-kernel construction, and zero observed hits is not a claim of zero true density.
- The compact route is at 297 of the allowed 300 operations. Because structural and placebo hints both scored 0/3, some oracle failures may measure lengthy exact bit bookkeeping as much as discovery of the invariant.
- No external SAT/SMT or ILP package was run. The implemented exact-two propagation plus GF(2) elimination is complete for this constructed overlap-tree distribution and succeeded 16/16 across the separately measured G5 and G6 samples; the cheap attack panel is not evidence against other learned or construction-aware heuristics.
- The required harness documentation describes a four-vendor pool, but the checked-in script used for these transcripts currently defines a two-model, two-vendor pool. The metadata and tables report the pool that actually ran.
