# Hidden false-twin certificates

**Status: locally verified, but not shippable yet.** The strengthened family
passes G1–G9(c), but the required OpenRouter runs returned HTTP 403 `Key limit
exceeded` before any scored attempt. Provider errors are not hardness evidence.

| profile axis | declaration |
|---|---|
| track | `B` — no-tool compression; an efficient reference algorithm exists |
| native domain | `combinatorics` |
| object regime | `finite_discrete` |
| computational core | `graph` |
| certificate form | `integer_tuple` (two vertex labels) |
| intuition | `change of variables` — invert bijective coordinate chains |
| domain essentiality | `native` |
| reduction | none |

## Problem and trust basis

The generator turns Estrada-Moreno, Rodríguez-Velázquez, and Yero's
[*The k-metric dimension of a graph*](https://arxiv.org/abs/1312.6840) into an
exact witness problem. The solver receives a succinct but complete adjacency
rule for a connected graph and must return its unique false-twin pair. False
twins are nonadjacent vertices with identical open neighborhoods. Only the two
twins distinguish each other, while the endpoints of any vertex pair distinguish
that pair; the witness therefore proves that the maximum metric multiplicity is
exactly 2. `verify` reconstructs the two base coordinates exactly and never reads
`inst["answer"]`.

Generation is inverse. It first samples an exceptional canonical index `e` and
an internal path coordinate `f`. It then publishes only their images under four
random bijections: prime-field maps `y -> y^a+b` for `e`, and affine maps modulo
`n-1` for `f`. A final affine permutation hides the public vertex labels. Removing
`e` leaves a path indexed `0..n-2`; `e` receives the same base coordinate as `f`,
so the planted vertices are false twins by construction.

Section 1 fixes the definition. Theorem 2.2 identifies the largest feasible `k`
as `min |D_G(x,y)|`; Corollary 2.3 says a connected graph is 2-metric dimensional
exactly when it has twins. That corollary is also the easy-regime warning: Track A
would be false. On Track B, forward preimage enumeration is polynomial,
`O(n * rounds * log n)`. At shipping seed 314159 it examined 911,574 coordinates,
counted 28,306,454 modular operations, and took 0.52 s. The compact route uses
the validated inverse parameters to reverse the two chains and relabel the two
preimages in 152 counted exact operations.

## Worked demo (`seed=0`)

The demo has `n=13`, `m=12`, public relabelling `v=8x+5 (mod 13)`, and:

```text
special chain: y <- y^5 + 4 (mod 13), inverse exponent 5, target 2
fold chain:    z <- 7z + 4 (mod 12), inverse multiplier 7, target 5
```

Reversing gives `e=7` and `f=7`. Since deleting canonical index 7 shifts path
rank 7 to ordinary canonical index 8, the two public labels are
`8*7+5 = 9 (mod 13)` and `8*8+5 = 4 (mod 13)`. Thus the answer is
`<answer>[4, 9]</answer>`. `verify(inst, [4, 9])` returns `(True, "ok")`;
`verify(inst, [4])` returns
`(False, "wrong number of vertices: expected 2, got 1")`. This smallest preset
is hand-solvable.

## Difficulty presets

| preset | prime vertices `n` | rounds per chain | answer atoms | status |
|---|---:|---:|---:|---|
| `demo` | 13 | 1 | 2 | hand example only |
| `easy` | 1,000,003 | 4 | 2 | proposed shipping; oracle blocked |
| `medium` | 2,000,003 | 4 | 2 | local construction verified |
| `hard` | 3,000,017 | 4 | 2 | local construction verified |

`SHIPPING_DIFFICULTY` is provisionally `easy`. Escalation enlarges the virtual
graph while keeping the witness and inverse-chain length fixed.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified; all answers JSON-round-trip |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | prose plus fenced JSON round-tripped both entries |
| G4 | 0/200,000 structure-aware guesses; exact density `1/500002500003` |
| G5 | one valid pair; reference scan 0.52 s, 911,574 coordinates, 28,306,454 operations |
| G6 | six attacks failed 0/8; Track B reference scan solved 8/8 |
| G7 | doubled instance had 2,000,029 vertices and still verified with two atoms |
| G8 | 40/40 re-encodings invariant, 40/40 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 15 chars, 4 estimated tokens, 2 atoms, 152 intended-route operations |

The six failing attacks were: choose the two path endpoints, choose labels 0 and
1, try 256 random pairs, treat both targets as preimages, undo only the final
translations, and undo only the final full updates. The separate forward scan is
the expected successful Track B reference algorithm.

## Oracle loop and G9 diagnostics

The current bare transcript contains only four error retries:

| preset | seed | solved | why |
|---|---:|---|---|
| `easy` | 939775839 | error | HTTP 403 key total limit exceeded |
| `easy` | 196524617 | error | HTTP 403 key total limit exceeded |
| `easy` | 892803054 | error | HTTP 403 key total limit exceeded |
| `easy` | 784863765 | error | HTTP 403 key total limit exceeded |

| arm | solved / scored attempts | result |
|---|---:|---|
| bare | 0 / 0 | quota blocked |
| structural hint | 0 / 0 | quota blocked |
| placebo hint | 0 / 0 | quota blocked |

Hinted minus placebo is undefined, so the runs support no conclusion about the
claimed intuition. The error-only transcripts are retained to document the
blocker, not as hardness evidence.

## Use

```python
import gen_1312_6840 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer("<answer>[123, 456]</answer>")
ok, reason = gen.verify(inst, candidate)
```

After restoring OpenRouter quota, rerun the bare loop here and the two G9 modes
in isolated directories, then emit from the repository root:

```bash
python3 ../../scripts/harden.py gen_1312_6840.py
bash scripts/emit.sh 1312.6840 20 easy
```

The module is standard-library-only; this integer graph certificate does not
need `gvlib`.

## Caveats

- A calculator or CAS makes the intended inverse route easy; this is explicitly
  Track B, not a claim that finding twins is computationally intractable.
- G4 samples uniformly from all unordered public vertex pairs. Its tiny density
  says nothing about a solver that recognizes and reverses either coordinate
  chain.
- The graph is represented by an exact adjacency rule rather than a million-row
  edge list. This preserves the native graph object but makes representation-aware
  algebraic attacks central.
- The panel did not count full symbolic inversion as a failing attack: it is the
  intended successful route. It also did not materialize and sort one million
  explicit neighborhoods; the forward collision scan is the cheaper exact
  reference method for this representation.
- An earlier affine-only version was solved at every tested size and reached the
  harness's escalation budget. The power-map version fixes that concrete weakness,
  but its hardness remains unverified until real oracle attempts complete.
