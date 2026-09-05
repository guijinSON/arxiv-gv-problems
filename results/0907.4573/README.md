# MAX-3-SAT above a tight lower bound — arXiv:0907.4573

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | logic / finite discrete |
| Computational core | exact linear algebra over GF(2) |
| Certificate | integer tuple: one Boolean truth assignment |
| Intended intuition | invariant: the encoded coefficient operator squares to the identity |
| Domain essentiality | native |
| Reduction | paper-licensed — Section 4.3, direct-kernel proof of Theorem 1 |
| Outcome | **parked — `cap_bound`; no preset held against all three oracle attempts** |

## What the family is

[Alon et al., *Solving MAX-r-SAT Above a Tight Lower Bound*](https://arxiv.org/abs/0907.4573) defines an exact $r$-CNF as a multiset of clauses, each containing exactly $r$ distinct literals. For $r=3$, $m$ clauses, and the paper's scaled surplus $k$, the question is whether some truth assignment satisfies at least $(7m+k)/8$ clauses. This family sets $k=m$, so a witness must satisfy every clause.

The solver receives the native signed 3-CNF. For each group of four clauses it also receives the exact GF(2) parity equation that the group enforces; this is redundant data obtained by the paper's own Section 4.3 transformation, not an external surrogate. The answer is one bit per variable. `verify` checks its shape, evaluates the clauses exactly, and compares the satisfied count with the target without reading `inst["answer"]`.

Generation is inverse. A uniformly random assignment $x$ is sampled first. For $n=2h$, the core uses a hidden cycle $p$ and $A=I+N$, where both rows belonging to pair $i$ have the same $N$-part `x[p(i)] XOR x[h+p(i)]`. Hence $N^2=0$ and $A^2=I$. The generator computes $b=Ax$, randomly renames variables, adds same-format consistent decoy rows on unused pairs, and expands every parity row into the four clauses from the proof of Theorem 1. The core is invertible, so the satisfying assignment is unique.

## Why this is Track B

This is not a distributional Track-A claim. Section 4.3, Theorem 1 gives a general $O(m)+2^{O(k^2)}$ algorithm and an $O(k^2)$-size kernel for fixed $r$. The paragraph immediately after its proof explains how to recover a witness using a bounded-independence sample space in the large-polynomial case and exhaustive search in the kernel case. Section 5 gives the still stronger $3k-1$-variable kernel for reduced Max-2-SAT. Those are the easy regimes this family must disclose; it uses $r=3$ and $k=m$, which grows with the instance.

An efficient distribution-specific algorithm also exists. Read the parity blocks and run exact Gaussian elimination over GF(2): expected $O(m+n^3)$. On eight hard instances it solved 8/8, averaging **268,382 counted bit/scalar operations and 0.002022 seconds** (maximum 307,750 operations and 0.002220 seconds). It is reported as `reference_algorithm`, not disguised as a failed attack.

The compact route is to recognize the repeated two-variable supports, reconstruct the paired core operator, notice $A^2=I$, and evaluate $x=Ab$. The two variables in a source pair share the same destination-pair parity, so caching it costs three XORs per pair: **216 XORs** at the named hard preset and 300 at $n=200$. Finding the row pairing still requires scanning the summaries, a limitation recorded below.

## Worked demo

`make_instance(n=6, decoy_rows=0, seed=7)` renders the following complete problem:

```text
Find a truth assignment meeting the stated Max-3-SAT threshold.

There are Boolean variables x1 through x6. In a clause, a positive
integer j denotes xj and a negative integer -j denotes NOT xj.
Each line below is one clause (the OR of its three distinct literals).
The formula is the multiset of all lines, so repeated clauses would count
separately. Variable indices are 1-based. A clause is satisfied when at
least one of its literals is true.

For r=3 and m clauses, the tight guaranteed lower bound is 7m/8.
This instance uses the paper's scaled surplus parameter k and requires
at least (7m+k)/8 satisfied clauses. Here n=6, m=24, k=24, so the
required exact integer target is 24 satisfied clauses.
Every answer entry must be exactly 0 (false) or 1 (true).
For readability only, clauses on the same unsigned variable triple are
consecutive, with a blank line between different triples; ordering does
not change the clause multiset.
Each Block header also states the exact GF(2) parity equation jointly
enforced by its following four clauses. XOR is addition modulo 2, so an
XOR is 1 exactly when an odd number of its input bits are 1.

Clauses:
Block B001: x2 XOR x3 XOR x6 = 0
C0001: -6 -2 -3
C0002: -2 +3 +6
C0003: -3 +6 +2
C0004: -6 +2 +3

Block B002: x4 XOR x5 XOR x6 = 0
C0005: -6 -5 -4
C0006: +6 +4 -5
C0007: +4 +5 -6
C0008: -4 +5 +6

Block B003: x2 XOR x4 XOR x5 = 1
C0009: -5 -4 +2
C0010: +4 +5 +2
C0011: -2 +5 -4
C0012: -2 +4 -5

Block B004: x1 XOR x2 XOR x6 = 1
C0013: -1 -6 +2
C0014: +6 +1 +2
C0015: +1 -2 -6
C0016: -1 -2 +6

Block B005: x1 XOR x3 XOR x5 = 1
C0017: +1 -5 -3
C0018: -1 -3 +5
C0019: -1 +3 -5
C0020: +1 +3 +5

Block B006: x1 XOR x3 XOR x4 = 1
C0021: -3 +4 -1
C0022: +1 -4 -3
C0023: +3 -1 -4
C0024: +4 +3 +1

Give your final answer inside <answer></answer> tags as one JSON list
of exactly 6 bits in the order [x1,x2,...,x6].
Example format: <answer>[0,1,0,1]</answer>
The example is syntax only and does not have the required length.
Output nothing else inside the tags.
```

The answer is `<answer>[0,1,1,0,0,0]</answer>`, and `verify` returns `(True, "ok")`. Flipping its first bit returns `(False, "threshold missed: clause 16 is false, but all 24 clauses are required")`. This smallest setting is genuinely hand-solvable by XOR elimination.

## Presets and gate results

| Preset | Variables | Decoy rows | Clauses | Status |
|---|---:|---:|---:|---|
| demo | 6 | 0 | 24 | hand-scale |
| easy | 32 | 4 | 144 | local gates pass |
| medium | 80 | 16 | 384 | local gates pass |
| **hard** | **144** | **40** | **largest named preset; local gates pass, oracle solved 2/3** |
| escalated | 200 | 40 | 960 | cap edge; oracle solved 1/3 |

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify across all presets |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | prose plus fenced/tagged JSON round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 uniformly sampled, correctly shaped 144-bit candidates verify |
| G5 | pass | exactly one solution by $A^2=I$, density $2^{-144}$; measured baseline 288,535 operations on the fixed G5 seed |
| G6 | pass | six attacks are 0/8 each; the disclosed Gaussian reference is 8/8 |
| G7 | pass | a 288-variable, 1,472-clause doubled instance builds and verifies |
| G8 | pass | 20/20 composed symmetries invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 289 characters, about 73 tokens, 144 atoms, 216 exact route operations |

The G6 panel includes literal majority, occurrence outlier, greedy clause repair, 32-restart parity-aware local repair with $8n$ flips per restart, short public-period search, and local parity-RHS voting. Each failed on all eight hard seeds. The parity repair remained 0/8 through 40 decoy rows but rose to 3/8 at 48, so the generator does not escalate past that measured safe crowding boundary.

## Oracle loop and G9 diagnostics

The required bare harness completed normally and returned **`cap_bound`**. Easy, medium, hard, and the $n=200$ escalation were each solved by at least one oracle. At $n=200$ the intended involution route costs exactly 300 binary XORs; increasing $n$ crosses G9(c)'s effort cap, while raising the consistent-decoy count past 40 made the parity-repair attack succeed. This is therefore a parked result, not a hardened family and not a rejection of the paper.

| Preset | Seed | Model | Solved? | Why |
|---|---:|---|---|---|
| easy | 1423594314 | GPT-5.6 Terra | yes | verified witness |
| easy | 848672449 | Gemini 3.8 Flash | yes | verified witness |
| easy | 2099445773 | GPT-5.6 Terra | no | candidate falsified clause 108 |
| medium | 1292840996 | Gemini 3.8 Flash | yes | verified witness |
| medium | 975964129 | GPT-5.6 Terra | yes | verified witness |
| medium | 15304712 | Gemini 3.8 Flash | yes | verified witness |
| hard | 603184429 | GPT-5.6 Terra | yes | verified witness |
| hard | 746373954 | Gemini 3.8 Flash | yes | verified witness |
| hard | 854522175 | GPT-5.6 Terra | no | candidate falsified clause 21 |
| escalated ($n=200$) | 1832543334 | Gemini 3.8 Flash | yes | verified witness |
| escalated ($n=200$) | 495597129 | GPT-5.6 Terra | no | answer was six bits short |
| escalated ($n=200$) | 1791154821 | GPT-5.6 Terra | no | answer had one extra bit |

The G9 arms use the declared hard preset, $n=144$, and are diagnostics only.

| G9 arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 2/3 | declared hard preset was defeated |
| structural | 2/3 | matched the bare and placebo success counts |
| placebo | 2/3 | matched the bare success count |

The measured hinted-minus-placebo rate is **$2/3-2/3=0$**. On this small, model/seed-varying sample, the structural hint bought nothing over the placebo, so it provides no evidence that the claimed invariant is what controls oracle success. The answer is 289 characters (about 73 tokens), 144 atomic bits, and the post-insight route is 216 exact XORs.

## Use

From the repository root:

```python
import importlib.util, json

path = "results/0907.4573/gen_0907_4573.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
candidate = g.parse_answer(
    "<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

If a future certificate format or compact route removes the cap and a rerun hardens, emit 20 instances with:

```bash
bash scripts/emit.sh 0907.4573 20 hard
```

`gvlib` is imported through the required repository-root setup when present, but this Boolean family uses only standard-library exact operations and degrades cleanly without it.

## Caveats

Any XOR-aware implementation solves the family efficiently; Gaussian elimination is the explicit reference algorithm. The instance is at the full-satisfiability extreme $k=m$, not close to the tight lower bound that motivates the paper. The 0/200,000 guess result is only for the uniform prior on syntactically valid bit vectors and says nothing about CDCL, learned SAT heuristics, Gröbner-basis methods, or other algebraic attacks. No external SAT package was run, although the more structure-specific exact Gaussian solver and a substantial parity-aware randomized repair were run.

The 216-operation figure counts exact XORs after the involution and row pairing are recognized; scanning 184 summaries to discover repeated pairs is additional comparison work. The canonical key is a stable color-refinement invariant, not a complete hypergraph-isomorphism test, so rare collisions remain possible. The decoys are sampled as consistent parity rows like the core rows, but their support distribution is not identical to the cyclic core distribution; the outlier and repair attacks are empirical checks, not a proof of indistinguishability. The harness has only one `cap_bound` sentinel; here the binding G9(c) limit at $n=200$ is the **300-operation effort cap**, not the 2,000-character or 256-atom answer cap. Finally, `SHIPPING_DIFFICULTY="hard"` is retained as the required measurement anchor, but nothing should be emitted from it: the oracle solved 2/3 hard instances and the harness parked the family at the next legal rung.
