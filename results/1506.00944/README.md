# 1506.00944 — retained Track B mixed-cluster editing generator

**Current disposition: `budget_bound`; retained and parked, not rejected and
not shipped.**  The module and all local gates pass, but every bare level through
the harness's sixth escalation was solved while `escalate()` still offered a
larger fixed-answer instance.  The environment also exposed only two oracle
models rather than the requested four-vendor pool.  Do not submit this result;
re-run with a restored pool and a larger `ORACLE_MAX_ESCALATIONS` budget.

| Profile | Value |
|---|---|
| Track | **B** — no-tool compression; no distributional Track A claim |
| Native domain / regime | combinatorics / finite_discrete |
| Core / certificate | graph / exact_symbolic translation-orbit edition set |
| Native objects | bipartite Cayley graph, edge-edition orbits, complete-bipartite components |
| Intended intuition | invariant: adjoining zero should make the connection set XOR-closed |
| Domain essentiality | native; no surrogate reduction |

## Problem and construction

The source is da Silva, Protti, and Szwarcfiter,
[*Parameterized mixed cluster editing via modular decomposition*](https://arxiv.org/abs/1506.00944).
Section 2 defines an `ell`-clique as a connected complete `ell`-partite graph
and an edition set as edge additions/deletions.  Proposition 1 says that an
`L`-cluster graph has no induced `P4`, paw, or `K_(ell+2)-e`.

Here `ell=2`.  The solver receives an exact implicit graph on two copies of
`GF(2)^b`: `(x,0)` and `(y,1)` are adjacent when `x XOR y` is zero or belongs
to the displayed connection set `D`.  One submitted offset denotes a complete
translation orbit of ordinary edge edits.  The solver must add and remove at
most the stated number of offsets so the graph becomes a union of allowed
components.

Generation samples a four-dimensional binary subspace and the missing/extra
offsets first.  It then corrupts the subspace's 15 nonzero elements.  Restoring
the planted offsets makes `D union {0}` a subspace.  Its cosets are checked
exactly: each coset induces a `K_(16,16)` between the two layers and there are
no edges between cosets.  Thus the certificate is known by construction;
`verify` never reads `inst["answer"]`.

## Why Track B

Theorem 4 proves the unrestricted problem NP-complete, but that does not make
this planted distribution hard.  The Introduction gives Cai's
`O((ell+2)^(2k) n^(ell+3))` FPT algorithm and, after the paper's linear-time
`O(ell*k^2)` kernel (Theorem 10), a forbidden-subgraph search running in
`O(6^k+n+m)` for `ell=2`.  Small `k` and already-valid components are the easy
regimes avoided here.

For this symmetric representation, the executable exact reference algorithm
enumerates every four-element basis drawn from `D`, spans it, and checks the
result.  At the shipping preset it solves 8/8 draws, taking at most **41,866
exact operations and 0.012 s**.  That is easy with code and not executable in
context by hand.  The compact route counts pairwise XOR support, spans four
high-support independent offsets, and takes at most **129 operations**.  This
gap—not an unsupported average-case hardness claim—is the Track B basis.

## Worked demo

A person can solve this example on paper.  A three-element nonzero connection
set must become `{a,b,a XOR b}` after one replacement.

```text
Mixed cluster editing on a bipartite Cayley graph (ell = 2).
Vertices are (x,p), 0 <= x < 16 and p in {0,1}.
There are no same-layer edges.  (x,0)-(y,1) is an edge exactly when
x XOR y belongs to {0} union D.

D = [1 7 14]

Add one nonzero offset absent from D and remove one offset in D.
Return {"add":[...],"remove":[...]}.
```

One answer is `<answer>{"add":[9],"remove":[1]}</answer>`, because
`{7,9,14,0}` is XOR-closed.  `verify(inst, answer)` returns `(True, "ok")`.
Dropping `9` returns `(False, "add and remove must have equal lengths")`.
There are three valid one-replacement answers to this demo.

## Presets and local gates

| Preset | Group size `n` | Subspace dim. | Max offset errors | Expanded vertices | Status |
|---|---:|---:|---:|---:|---|
| demo | 16 | 2 | 1 | 32 | hand-solvable |
| easy | 64 | 3 | 1 | 128 | solved 3/3 |
| medium | 1,024 | 4 | 3 | 2,048 | solved 3/3 |
| hard | 4,096 | 4 | 6 | 8,192 | solved 3/3; retained local candidate |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses; JSON 12/12; explicit demo graph scan passes |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | tagged, fenced, prose-surrounded answer round-trips |
| G4 | 0/200,000 structure-aware guesses; 74-bit bounded language |
| G5 | demo exact count 3; shipping density 0/200,000; reference 41,184 operations |
| G6 | four attacks each 0/8; exact reference 8/8; compact decoder 8/8 |
| G7 | doubled graph has 16,384 vertices, verifies, and raises space from 74 to 80 bits |
| G8 | 40/40 relabelling and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 79 chars, 20 estimated tokens, 12 atoms, 129 intended operations |

## Oracle loop and G9 diagnostics

| Round | Parameters | Solved | Result |
|---:|---|---:|---|
| 0 | `n=64, r=3, errors=1` | 3/3 | defeated |
| 1 | `n=1,024, r=4, errors=3` | 3/3 | defeated |
| 2 | `n=4,096, r=4, errors=6` | 3/3 | defeated |
| 3 | `n=8,192, r=4, errors=6` | 3/3 | defeated |
| 4 | `n=16,384, r=4, errors=7` | 2/3 | defeated; one empty length-limited reply |
| 5 | `n=32,768, r=4, errors=7` | 3/3 | defeated |
| 6 | `n=65,536, r=4, errors=7` | 3/3 | defeated; harness budget exhausted |

The script therefore recorded `budget_bound` and a next level of `n=131,072`.
The hard-preset bare arm is 3/3 solved.  Structural and placebo arms were not
run because no shipping rung held, so there is no hinted-minus-placebo
measurement.  The structural hint names XOR closure only; it does not give a
recovery procedure.  The transcript used two accessible models (OpenAI and
Google), not the specified four-vendor pool, which further limits the evidence.

## Use

```python
from gen_1506_00944 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

Emission was tested successfully (20/20 distinct instances).  After a future
successful oracle run, emit from the repository root with:

```bash
bash scripts/emit.sh 1506.00944 20
```

## Caveats

This is an orbit-restricted, implicitly represented subclass of the paper's
native edge-editing problem: one short offset expands to `n` ordinary editions.
It tests recognition of Cayley/subspace structure, not generic mixed-cluster
editing.  The 0/200,000 estimate is under uniform, statement-compliant equal-size
add/remove offset sets; it says blind guessing is poor, not that algebraically
informed guesses have that probability.  Indeed the documented XOR-support
decoder solves every filtered draw.

The panel did not run a production SAT/ILP solver or the paper's expanded
`O(6^k)` obstruction tree; at expanded `k=49,152`, the latter is not a useful
measurement.  The canonical key is invariant under coordinate changes,
translations, layer swaps, and record reordering and includes a binary-dependency
weight enumerator, but it is a strong fingerprint rather than a complete
isomorphism canonizer for all Cayley graphs.  Most importantly, this candidate
is demonstrably easy for the tested oracle models at every attempted size, and
no four-vendor hardness conclusion is justified from the two-model override.
