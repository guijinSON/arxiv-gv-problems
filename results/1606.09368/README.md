# Pinned seminormalized-Hadamard completion

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact linear algebra |
| Certificate | integer tuple: one balanced `+/-1` SH vector |
| Intended intuition | change of variables to Walsh characters and an affine frequency block |
| Domain essentiality | native; no reduction |

This generator turns [Suksmono, *Probabilistic Construction and Analysis of
Seminormalized Hadamard Matrices*](https://arxiv.org/abs/1606.09368) into an
exact completion problem. The solver receives a partial, pairwise-orthogonal
system of balanced sign columns, plus prescribed coordinates, and must supply
one more balanced sign vector orthogonal to every displayed column. `verify()`
checks the alphabet, balance, pins, and integer inner products directly. It
never reads the planted answer.

## Why the instances are known, and why this is Track B

Definition 1 and Equation (1) give the exact Hadamard condition; the paragraph
after Lemma 1 fixes seminormalization; Definitions 9 and 11 and Section 3's
Algorithms 1–2 give the SH-vector selection problem. Equation (3) and Lemma 1
give Sylvester's Kronecker construction at every power-of-two order. Generation
uses its Walsh-character form, removes an affine block of frequencies, and
carries a randomly chosen balanced quotient truth table through row/column
reordering and non-unity column negations. The certificate is therefore known before the
public instance exists.

This is explicitly not Track A. A computer solves the pinned orthogonality
equations by exact modular Gauss–Jordan elimination in `O(n^3)`. At shipping
`n=128`, that reference algorithm solved 8/8 instances at a measured mean of
1,018,271 modular operations and about 0.037 s (maximum 1,093,837 operations).
After recognizing the Walsh block, the pinned table is copied across four
coordinate blocks and two copies are negated: 64 exact sign negations. The
paper's easy routes that must be acknowledged are Sylvester's explicit formula,
Algorithm 1's exhaustive enumeration, Algorithm 2's random vector selection
(RVS), and Section 3.3's simulated annealing. The paper's Table 1 already shows
RVS reaching 84,081 trials for only its twelfth selected vector at order 24.

An earlier arbitrary-deletion draft was rejected during construction: a random
Walsh character solved 89/1000 instances in one guess and 975/1000 with 32
guesses. The shipped affine-block design instead draws a non-character balanced
quotient table from `C(32,16)=601,080,390` possibilities.

## Worked demo (`seed=1`)

The smallest instance is hand-solvable and is reproduced in full:

```text
PINNED SEMINORMALIZED HADAMARD-VECTOR COMPLETION
n=8; column identifiers: 101 001 111 100 000 110
prescribed output-label signs: 001=+ 111=-

output : tag | six displayed signs
010 : 010 | ++--++
011 : 111 | +--++-
110 : 110 | -++++-
000 : 100 | -+-+++
111 : 000 | +++-+-
001 : 001 | ----+-
101 : 011 | --+-++
100 : 101 | +-++++
```

The answer, in increasing output-label order, is
`[-1, 1, 1, -1, 1, -1, 1, -1]`.

```python
verify(inst, [-1, 1, 1, -1, 1, -1, 1, -1])
# (True, "ok")
verify(inst, [2, 1, 1, -1, 1, -1, 1, -1])
# (False, "entry 0 is outside the +/-1 alphabet")
```

## Difficulty and measured gates

| preset | `n` | absent-block bits | pins | status |
|---|---:|---:|---:|---|
| demo | 8 | 1 | 2 | exact count 1/20; hand example |
| easy | 32 | 3 | 8 | first oracle rung |
| medium | 64 | 4 | 16 | escalation rung |
| hard | 128 | 5 | 32 | current shipping preset |

| gate | measured result |
|---|---|
| G1 | 20/20 planted answers verified across all presets |
| G2 | 6/6 corruptions rejected with six distinct reasons |
| G3 | fenced tagged JSON round-trips exactly |
| G4 | 0/200,000 pinned-and-balanced guesses; language size `6.435e27` |
| G5 | demo exact count 1/20; shipping reference solve 1,148,263 operations, 0.065874 s |
| G6 | seven attacks each 0/8; reference elimination 8/8 |
| G7 | doubled order 256 builds and its carried answer verifies |
| G8 | 160/160 invariance and 160/160 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 321 chars, 161 estimated tokens, 128 atoms, 64 intended operations |

## Oracle loop and G9 diagnostics

The mandated harness was invoked for all three arms, but OpenRouter rejected
every request before a model ran with HTTP 403 `Key limit exceeded (total
limit)`. API errors are not model failures, so there is no hardness verdict yet.

| arm/run | rung | scorable solved/attempts | errors | conclusion |
|---|---|---:|---:|---|
| bare | easy | 0/0 | 4 | infrastructure blocked |
| structural hint | hard-only copy | 0/0 | 4 | infrastructure blocked |
| placebo hint | hard-only copy | 0/0 | 4 | infrastructure blocked |

Thus hinted minus placebo is not measurable. The structural hint only names the
invariant: “The omitted identifiers are an affine Walsh-frequency block whose
quotient values are the pins.” It does not give a procedure. The answer/effort
caps pass independently, but this result must not be called script-hardened
until the three harness runs complete with scorable model replies.

## Use

```python
import importlib.util, json

path = "results/1606.09368/gen_1606_09368.py"
spec = importlib.util.spec_from_file_location("hadamard_gen", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
text = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1606.09368 20 hard
```

## Caveats

The public binary metadata deliberately makes this a Track B compression task;
a solver that recognizes the Walsh representation can solve it efficiently.
The `0/200,000` estimate is only for the declared uniform prior over sign vectors
that already satisfy balance and every pin; it is not an average-case hardness
proof. Simulated annealing was not separately implemented because exact linear
elimination is the stronger successful reference algorithm here. The canonical
key exactly handles the tested presentation permutations, sign changes, output
renumberings, bit-basis permutations, and tag translations; its weighted-graph
component is still an invariant rather than a complete isomorphism test, so
unseen nonisomorphic collisions are possible. Most importantly, the external
four-vendor oracle evidence is absent because the supplied key has exhausted
its limit; local gates passing does not replace that required evidence.
