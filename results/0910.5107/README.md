# Iterated strict-dominance generator for arXiv:0910.5107

> **Status:** the module passes every local gate, but Step 4 is externally
> incomplete. All bare, structural-hint, and placebo oracle requests were rejected
> before inference with OpenRouter HTTP 403 `Key limit exceeded (total limit)`.
> These service errors are preserved in the required transcripts and are not counted
> as model failures or evidence of hardness.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core | other: exact iterated dominance propagation |
| Certificate | exact symbolic strict-dominance elimination word |
| Native objects | a two-player normal-form game over payoffs `{-1,0,1}` and its active strategy sets |
| Intuition | invariant: distinguish a target-cone predecessor by whether its own input column touches an ALL1 row |
| Domain essentiality | licensed reduction |
| Reduction | paper-central, Section 6, Theorem 6.6 (MCV1 to `3-Strict`) |

## Problem and trust model

Arno Pauly's [*The Complexity of Iterated Strategy
Elimination*](https://arxiv.org/abs/0910.5107) asks whether a designated strategy
can disappear through iterated deletion of dominated strategies. This family hands
the solver one of the paper's three-payoff bimatrix games. The solver must write a
47-step alternating word; every step names a victim and an active same-player
strategy whose payoff is strictly greater against **every** currently active opposing
strategy. The final victim is the designated row.

Generation is inverse. A true monotone-circuit spine and its elimination word are
built first. Randomly sized false circuit branches are attached to all spine OR gates,
then both players' strategy labels and every displayed record are shuffled. This is
exactly the payoff construction in Theorem 6.6, not a convenience graph surrogate.
The game is rendered sparsely but completely: its rules define every entry of both
payoff matrices. `verify` ignores `inst["answer"]`, reconstructs those integer payoffs,
and replays every strict comparison and deletion.

## Why this is Track B

The family is deliberately **not** a Track A claim. Section 6, Theorem 6.1 proves
that strict-dominance elimination is in P: repeatedly find any strictly dominated
strategy, delete it, and use order independence. Together with Theorem 6.6's
P-hardness for three payoff values, this is the paper's P-complete regime. The easy
cases are even stronger in Section 5: `2-Z-Strict` is in L (Theorem 5.1), while
`2-Strict` and `3-Z-Strict` are NL-complete (Theorems 5.2 and 5.3). The generator does
not pretend those algorithms are absent.

At the shipping preset (`R=175`, `C=262`), the bit-parallel implementation of the
Theorem 6.1 scan solved 8/8 instances in 1.63 seconds mean wall-clock and represented
348,009,727 exact payoff-coordinate comparisons on average. Its direct worst-case
bound is `O((R+C)(R^2 C + C^2 R))`. A solver who notices the construction invariant
needs only 70 local incidence checks: in the target dependency cone, the true
predecessor's preceding input has no ALL1 row, while each false branch exposes one.
That compression gap—hundreds of millions of mechanical comparisons versus a short
structural trace—is the Track B claim.

## Worked demo

`make_instance(n=1, depth=2, seed=7)` gives the smallest supported instance. A person
can solve it on paper by first deleting the input-free row, then its enabled OR
column, then the target.

```text
Find a strict-dominance elimination word in a finite bimatrix game.

Definitions.
There are two players. The row player chooses one row strategy and receives
the integer payoff A(row,column); the column player chooses one column strategy
and receives B(row,column). At any moment only the not-yet-deleted strategies
are active. A row Rd strictly dominates a different active row Rv exactly when
A(Rd,c) > A(Rv,c) for EVERY active column c. A column Cd strictly dominates a
different active column Cv exactly when B(r,Cd) > B(r,Cv) for EVERY active row
r. One legal step deletes the dominated strategy. All inequalities are strict.

Rows and columns below are indexed from 0, with inclusive ranges
R0..R4 and C0..C6. The target is
R4. The two complete payoff matrices are specified exactly by
the following rules; no data outside this statement is needed.

A payoff rules:
* Every ALL1 row has A(r,c)=1 for every column c.
* Every other row appears under AND-INPUTS. It has A(r,c)=1 exactly at its
  listed input columns, and A(r,c)=0 at every other column. A dash means no
  input columns.

ALL1 ROWS:
  R0 R3
AND-INPUTS:
  R1: -
  R2: C1
  R4: C4

B payoff rules:
* Each row has the unique mate column printed under MATES. At a mate column c,
  B(r,c)=1 when c is r's own mate and B(r,c)=0 otherwise.
* Every non-mate column appears under OR-INPUT-ROWS with exactly two rows.
  At such a column c, B(r,c)=0 for either listed input row and B(r,c)=-1 for
  every other row.

MATES:
  R0: C5
  R1: C6
  R2: C3
  R3: C2
  R4: C0
OR-INPUT-ROWS:
  C1: R3 R0
  C4: R1 R2

Output exactly 3 legal deletion steps as a JSON list of
strings. Steps must alternate row, column, row, column, and so on; the last
step must delete target R4. A row token Rv<Rd means "delete Rv,
strictly dominated by active Rd". A column token Cv<Cd has the analogous
meaning. Indices are decimal and 0-based. A victim may not repeat, the victim
and dominator must differ, order matters, and the dominator must still be
active. Other valid words of this exact prescribed shape are accepted.

Give your final answer inside <answer></answer> tags, as that JSON list.
Syntax-only example: <answer>["R0<R1","C0<C1","R4<R0"]</answer>
Output nothing else inside the tags.
```

The answer is:

```json
["R1<R3", "C4<C3", "R4<R3"]
```

The exact checker returns:

```python
verify(inst, ["R1<R3", "C4<C3", "R4<R3"])
# (True, "ok")
verify(inst, ["R3<R1", "C4<C3", "R4<R3"])
# (False, "step 1 is not strict row dominance at column C0")
```

## Presets and gates

Only false-branch volume changes after `easy`; witness depth remains 24 and the
answer remains 47 strings.

| Preset | False branch pairs `n` | Depth | Rows | Columns | Status |
|---|---:|---:|---:|---:|---|
| demo | 1 | 2 | 5 | 7 | hand-scale illustration |
| easy | 64 | 24 | 175 | 262 | intended shipping preset; oracle unavailable |
| medium | 128 | 24 | 303 | 454 | harder fallback |
| hard | 256 | 24 | 559 | 838 | hardest named rung |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted words verified; all answers JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged, fenced, prose-surrounded JSON round-tripped and verified |
| G4 | 0/200,000 structure-aware random words verified |
| G5 | demo: exactly 4 valid of 2,016; shipping density sample: 0/200,000; reference mean 348,009,727 comparisons and 1.63 s |
| G6 | payoff outlier, low-label greedy, high-label greedy, and 64 random backward traces: each 0/8; reference scan 8/8 as expected |
| G7 | `n=64 -> 128` increased the candidate space, built and verified, while the answer stayed at 47 strings |
| G8 | 60/60 independent/composed relabellings preserved the key and carried witness; 20/20 unrelated instances had distinct keys |
| G9(c) | 506 characters, about 127 tokens, 47 atoms, 70 intended operations |

## Oracle loop and G9 diagnostics

No row below is a model failure: every call stopped at the service boundary. The bare
transcript contains four schema-valid error records (seeds `1463288653`, `1523518310`,
`1693557800`, and `35633845`), all at `easy` and all HTTP 403. There is therefore no
`hardened`, `too_easy`, `cap_bound`, or `budget_bound` verdict to interpret.

| Bare preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| easy | 1463288653 | `openai/gpt-5.6-terra` | error | HTTP 403 key total limit exceeded |
| easy | 1523518310 | `x-ai/grok-4.6` | error | HTTP 403 key total limit exceeded |
| easy | 1693557800 | `x-ai/grok-4.6` | error | HTTP 403 key total limit exceeded |
| easy | 35633845 | `x-ai/grok-4.6` | error | HTTP 403 key total limit exceeded |

| Arm | Usable solved / attempts | Service errors | Result |
|---|---:|---:|---|
| bare | 0/0 | 4 | unreachable |
| structural hint | 0/0 | 4 | unreachable |
| placebo hint | 0/0 | 4 | unreachable |

`hinted - placebo` is undefined because neither arm reached a model. The structural
hint names only the ALL1-grandparent invariant; it does not provide a procedure. The
answer and intended route independently satisfy G9(c): 506 serialized characters,
47 atomic strings, and 70 local checks.

## Use

The implementation is standard-library-only. It optionally imports `gvlib` when the
repository is present, but this finite symbolic certificate does not require it.

```python
import gen_0910_5107 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=12345, **params)
question = gen.render(inst)
answer = gen.parse_answer('work... <answer>["R0<R1"]</answer>')
ok, reason = gen.verify(inst, answer)
```

After a funded OpenRouter run produces a genuine `hardened` verdict, emit from the
repository root with:

```bash
bash scripts/emit.sh 0910.5107 20 easy
```

## Caveats

- Track B makes no distributional intractability claim. The generic polynomial scan
  and a construction-aware monotone-circuit evaluation both solve these instances.
  The benchmark tests whether a no-tool solver finds the shorter local invariant.
- G4 samples uniformly from exact-length alternating words that already have distinct
  victims, in-range active dominators, and the target last. Zero hits estimates that
  prior only; it says nothing about a game-aware or theorem-aware solver.
- The attack panel did not test an optimized parallel fixed-point implementation,
  symbolic model checking, SAT/SMT encodings, or learned circuit-recognition methods.
  Those are expected to solve with tools and do not contradict Track B.
- The sparse display exposes the ALL1 rows because those rows are part of the complete
  payoff definition. The claimed difficulty is connecting that local feature through
  the shuffled target cone, not discovering the row type itself.
- The reference wall time uses bit-parallel Python integers; its operation count is
  the exact number of payoff-coordinate comparisons represented by those mask tests,
  not the number of CPU instructions executed.
- `canonical_key` is a target-rooted Merkle normal form of the full construction tree.
  It passed all generated relabellings, but, like any fixed-width hash, has a
  theoretical collision possibility.
- Most importantly, no oracle inference occurred because the configured OpenRouter
  key had exhausted its total limit. The family must not be submitted as hardened
  until the bare loop and both diagnostic arms are rerun with a funded key.
