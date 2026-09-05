# arXiv:1507.06286 — graph-derangement generator

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | exact symbolic affine rule, or explicit permutation |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

The solver receives a finite simple connected undirected graph and must give a
fixed-point-free vertex permutation that sends every vertex to a neighbor. This
is exactly the graph derangement defined in Section 2 of Galanter, Silva,
Rowell, and Rychtář, [“The Territorial Raider Game and Graph
Derangements”](https://arxiv.org/abs/1507.06286). Proposition 3.1 turns every
such map into a strict Territorial Raider equilibrium for `h<1`, and Theorem
3.3 proves the converse. The generator therefore stays in the paper's native
graph and vertex-function objects.

The certificate is known before the graph exists. Split a vertex into bit
blocks `(u,v)` and sample `a,C,d` with `a != 0` and `C*a=0`; then
`f(u,v)=(u XOR a, v XOR C*u XOR d)` is a fixed-point-free involution. Its pairs
are inserted as edges. Other rules sampled from the same distribution each
have one globally reserved edge withheld, while a shuffled Hamilton cycle
guarantees connectedness. Verification expands a compact rule (or accepts any
explicit permutation), checks injectivity and fixed points, and performs exact
edge lookups. It never consults the planted answer.

## Why this is Track B

This paper supplies no distributional hardness theorem. Its Introduction
states the equivalent spanning `Q`-factor and Hall-type neighborhood
conditions, which expose the easy mechanism: make left and right copies of the
vertices and find a perfect matching. Hopcroft–Karp solves every generated
instance in `O(E sqrt(V))`, so a Track-A claim would be false. Complete graphs
are easier still and attain the paper's maximum number of derangements.

At shipping `n=128`, eight reference runs solved 8/8 and averaged 10,769.75
edge scans, 2.75 BFS phases, and 0.00093 seconds (maximum 12,613 scans and
0.00109 seconds on this host). A solver with graph tools should use that
algorithm. The no-tool route instead notices the two bit blocks and a persistent
affine XOR displacement, then writes the few rule parameters; the conservative
post-insight bound is 136 exact operations. The claimed difficulty is only the
gap between thousands of mechanical matching operations and recognizing that
compact coordinate rule from a crowded edge list.

## Worked demo

For `make_instance(seed=0, n=8, near_rules=2, u_bits=2)`, the complete graph is:

```text
vertices: 0 1 2 3 4 5 6 7
0: 3 4 5 7
1: 2 4 5 6
2: 7
3: 5 6
4: 6 7
5: 6
6:
7:
```

Each row lists only larger neighbors. The compact answer is
`{"kind":"affine_xor","a":2,"rows":[0],"d":1}`. It expands to a
permutation and `verify(inst, inst["answer"]) == (True, "ok")`. Dropping the
last entry from its expanded table gives `(False, "table length must be exactly
8")`. A person can solve this demo on paper: the rule is simply the high-block
XOR shift `2` together with a low-bit XOR shift `1`.

## Difficulty presets

| preset | vertices | near rules | high bits | status |
|---|---:|---:|---:|---|
| demo | 8 | 2 | 2 | hand-solvable illustration |
| easy | 32 | 8 | 2 | oracle run not scored (quota error) |
| medium | 64 | 18 | 3 | not reached by oracle ladder |
| hard | 128 | 42 | 3 | configured shipping preset; local gates pass |

`hard` is configured but is **not yet externally hardened**: OpenRouter rejected
every required call with HTTP 403 `Key limit exceeded (total limit)`. That is an
infrastructure blocker, not evidence that the oracles failed the problem.
`escalate()` first raises near-rule crowding at fixed answer length.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 20/20 planted witnesses verify and JSON round-trip |
| G2 | pass | five corruptions rejected for five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware legal guesses |
| G5 | pass | shipping density 0/200,000; demo has 83 valid encodings; reference cost above |
| G6 | pass | six attacks each 0/8; Hopcroft–Karp 8/8 as expected |
| G7 | pass | doubled `n=256` verifies; compact answer stays at 7 atoms |
| G8 | pass | 20/20 arbitrary relabels plus edge-order/endpoint reversals; 20/20 unrelated keys distinct |
| G9(c) | pass | 51 chars / 7 atoms / about 13 tokens; intended route 136 operations |

The six failing attacks are copying the format example, a constant-XOR
frequency outlier, low-degree greedy assignment, a first-neighbor basis ansatz,
a modal affine-displacement ansatz, and 512 uniform fixed-point-free permutation
restarts. The generator
withholds a non-planted, non-Hamiltonian edge if the union of near-rules happens
to complete one of the five deterministic ansatzes.

## Oracle loop and G9 diagnostics

The script-owned bare run made four redraws at `easy`; all were HTTP 403 errors,
so it correctly aborted without scoring an attempt. The four final-run seeds
were `1524942750`, `1263835443`, `1196647397`, and `212270751`.
No preset was solved or held.

| arm | scored solved / attempts | script calls | conclusion |
|---|---:|---:|---|
| bare | 0 / 0 | 4 errors | blocked by key quota |
| structural hint | 0 / 0 | 4 errors | blocked by key quota |
| placebo hint | 0 / 0 | 4 errors | blocked by key quota |

Thus `hinted - placebo` is unavailable, not zero. The error-only transcripts
are preserved because they were written by `harden.py`; they are not a hardness
claim. The structural hint names only the persistent affine displacement and
does not state a recovery procedure.

## Use

```python
import gen_1507_06286 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
question = g.render(inst)
candidate = g.parse_answer(
    '<answer>{"kind":"affine_xor","a":1,"rows":[0,0,0,0],"d":0}</answer>'
)
ok, reason = g.verify(inst, candidate)
```

After the external hardening run succeeds, emit from the repository root with:

```bash
bash scripts/emit.sh 1507.06286 20 hard
```

## Caveats

The 0/200,000 figure is for the declared union language: uniform explicit
derangements dominate it overwhelmingly. It does not model a solver already
conditioned on affine-XOR rules, so it should not be read as that solver's
posterior success probability. Hopcroft–Karp makes the family easy whenever a
matching tool is available; noticing the affine rule also makes it easy by
hand. Conversely, the graph may contain non-affine witnesses that none of the
six cheap attacks targets.

The attack-aware edge withholding is deliberately construction-specific and
may overfit those exact heuristics; production SAT/ILP solvers, equilibrium
learning (such as the Exp3 direction mentioned in the Introduction), spectral
probes, and broader affine backtracking were not run. `canonical_key` is an
eight-round 1-WL graph fingerprint, invariant under tested relabellings but not
a complete graph-isomorphism canonical form. Most importantly, the external
oracle quota failure leaves STEP 4 incomplete. Re-run all three arms with a
working OpenRouter allowance before treating `hard` as a shippable benchmark.
