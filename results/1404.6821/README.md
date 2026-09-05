# Verified generator for arXiv:1404.6821

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate form | exact symbolic |
| Intended intuition | invariant |
| Domain essentiality | native |
| Reduction | none |

This generator turns Meng, Puleo, and Zhu's [*On (4,2)-Choosable
Graphs*](https://arxiv.org/abs/1404.6821) into a witness problem in the
paper's own objects. The solver receives a succinctly labelled cycle with a
few chords and the four-colour list `{0,1,2,3}` at every vertex. It must give
an affine parity formula that assigns `{0,1}` or `{2,3}` to every vertex so
that adjacent pairs are disjoint. Verification pulls the proposed parity
mask exactly through the reversible GF(2) label circuit and checks every
chord; it uses no floats and never reads the planted answer.

## Why this family is trustworthy—and why it is Track B

Section 1 defines an `(L,2)`-colouring as two listed colours per vertex with
disjoint pairs across every edge. Generation begins with the
binary-reflected Gray cycle, whose total coordinate parity alternates, and
carries that already-known covector through a reversible CNOT/SWAP relabelling.
Odd-distance chords preserve the bipartition. This is a structure-preserving
transformation of a known certificate, not a search over the finished graph.

Track A would be false. Lemma 2.2 gives a constructive linear traversal for
paths, Sections 4–5 reduce the paper's positive theta/cycle arguments to six
endpoint choices, and Section 8's program explicitly enumerates signatures,
path tags, and partial colourings. For this succinct family an efficient
algorithm also exists: compile the 32-by-32 circuit matrix and run exact GF(2)
Gaussian elimination. At the shipping preset it solved 8/8 instances in
25,674 counted bit operations and 0.00075 seconds mean wall-clock. The compact
route recognizes total Gray parity and transports one mask through 288 gates.
That route fits the 300-operation cap, but executing 288 exact bit updates
without a tool is the intended no-tool challenge. A literal application of
the paper's path traversal would instead expose `2^32` vertices.

## Worked demo (`seed=2`)

The smallest preset is hand-solvable: eight gate updates recover the mask.
Here is its complete rendered instance (the standard output instructions are
included).

```text
Find an exact symbolic (L,2)-colouring of the graph below.

An (L,2)-colouring assigns each vertex exactly two colours from its four-colour
list, with no colour shared by the two assigned pairs at the ends of any edge.

Vertex set and labels:
- n = 4; there are N = 2^n = 16 vertices.
- Bit positions are numbered 0 through n-1 from least significant to most.
- For a cycle position i in 0,...,N-1, start with g(i)=i XOR (i >> 1).
- Apply every mixer gate below in the displayed order. `C c t` replaces bit t
  by bit t XOR bit c. `S a b` swaps bits a and b.
- Finally XOR the result with label_offset = 8. The resulting
  n-bit integer x is the public vertex label at position i.

Mixer gates, in order (semicolon-separated):
C 2 0; C 2 1; C 0 3; C 3 2; S 2 3; S 2 0; S 2 1; S 3 1

Edges:
- Consecutive cycle positions are adjacent, including positions N-1 and 0.
- In addition, the following pairs of cycle positions are joined by chords:
  (1,4)

Every vertex has the same permissible list L(x)={0,1,2,3}.

Your answer must be one affine parity formula. For your n-bit integer `mask`
and bit `offset`, define b(x) = (popcount(mask AND x) mod 2) XOR offset.
Assign colours {0,1} when b(x)=0 and colours {2,3} when b(x)=1.
The formula must give disjoint pairs on every cycle edge and every added chord.
`mask` is an integer in [0,2^n-1], and `offset` is exactly 0 or 1.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the two integer fields shown by this example:
<answer>{"mask": 3, "offset": 0}</answer>
Output nothing else inside the tags.
```

The planted answer is `{"mask": 6, "offset": 0}`.
`verify(inst, answer)` returns `(True, "ok")`. Flipping its low bit gives
`{"mask": 7, "offset": 0}`, which returns
`(False, "affine parity rule does not alternate on every cycle edge")`.

## Difficulty presets

| preset | n | vertices | mixer gates | chords | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 16 | 8 | 1 | hand-scale illustration |
| easy | 28 | 268,435,456 | 272 | 5 | oracle-solved in the original ladder |
| medium | 30 | 1,073,741,824 | 280 | 6 | oracle-solved in the original ladder |
| hard | 32 | 4,294,967,296 | 288 | 7 | **ships; bare hardened** |

The original `n=24` and `n=26` rungs were also oracle-solved and were dropped
when the ladder was slid upward. Answer length stays two atomic fields at
every rung.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified; all JSON-native |
| G2 | pass | 6/6 corruptions rejected with six distinct reasons |
| G3 | pass | prose + fenced JSON round-tripped exactly |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `2^-32` |
| G5 | pass | 2 valid formulas in `2^33`; strongest failing attack used 4,096 restarts in 0.108 s |
| G6 | pass | five attacks at 0/8; reference algorithm 8/8 |
| G7 | pass | all rungs strictly grow; doubled `n=64` instance verified |
| G8 | pass | 120/120 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | 30 chars, 8 estimated tokens, 2 atoms, 288 intended operations; hinted 0/3 |

The five failing G6 attacks were gate-frequency outliers, chord-only Gaussian
elimination, 512 random affine restarts, constant/single-coordinate/label-parity
ansätze, and a 64-gate truncated pullback. The successful generic
circuit-matrix algorithm is reported separately, as Track B requires.

## Bare oracle loop

| rung | seed | model | solved? | exact outcome |
|---|---:|---|---|---|
| n=24 | 847125567 | Grok 4.6 | no | empty length-limited reply |
| n=24 | 151188835 | GPT-5.6 Terra | no | proposed mask failed cycle parity |
| n=24 | 381122034 | Claude Sonnet 5 | yes | verified |
| n=26 | 1325084765 | Gemini 3.1 Pro | yes | verified |
| n=26 | 578723221 | Claude Sonnet 5 | no | empty length-limited reply |
| n=26 | 1466312139 | GPT-5.6 Terra | no | proposed mask failed cycle parity |
| n=28 | 1022099766 | Gemini 3.1 Pro | yes | verified |
| n=28 | 1885368294 | Claude Sonnet 5 | no | empty length-limited reply |
| n=28 | 2057184420 | Grok 4.6 | no | proposed mask failed cycle parity |
| n=30 | 1283566248 | GPT-5.6 Terra | no | proposed mask failed cycle parity |
| n=30 | 1267517370 | Grok 4.6 | yes | verified |
| n=30 | 210480170 | Gemini 3.1 Pro | yes | verified |
| n=32 | 1318568697 | Claude Sonnet 5 | no | empty length-limited reply |
| n=32 | 1902443728 | Grok 4.6 | no | proposed mask failed cycle parity |
| n=32 | 829831963 | GPT-5.6 Terra | no | proposed mask failed cycle parity |

## G9 arms

| arm | solved / scored attempts | conclusion |
|---|---:|---|
| bare | 0/3 | shipping rung held |
| structural hint | 0/3 | gated arm held; naming Gray parity did not break the family |
| placebo | 0/2 | both scored calls failed; diagnostic incomplete |

The observed hinted-minus-placebo solve-rate difference is `0.0`. The
structural hint bought no measured solves, which indicates that exact
288-operation execution, not merely naming the invariant, contributes to the
difficulty. The placebo arm is honestly short of its requested third scored
attempt: after two clean failures OpenRouter returned account-wide HTTP 403
`Key limit exceeded` on every script-controlled redraw. Those errors are kept
in `g9_placebo_transcript.jsonl` and were not counted as model failures. This
does not affect G9(b), whose structural arm is complete, but it weakens the
three-arm diagnostic.

## Use

```python
from gen_1404_6821 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
prompt = render(inst)
answer = parse_answer('<answer>{"mask": 1, "offset": 0}</answer>')
ok, reason = verify(inst, answer)
```

From the repository root, emit dataset rows with:

```bash
bash scripts/emit.sh 1404.6821
```

## Caveats

This is a Track B no-tool benchmark, not evidence that the generated
distribution is NP-hard. Any solver that can execute reversible-circuit
algebra gets the answer quickly; the measured generic algorithm takes only
about 0.75 ms on this machine. Likewise, exposing the transported mask, using
few enough gates, or allowing a CAS makes the task easy. `P(guess)=2^-32`
refers only to uniform sampling from the declared affine-mask language; it
does not model a solver that exploits circuit equations. The succinct graph
is native list-colouring data but is more structured than arbitrary list
assignments in the paper. I did not test SAT/SMT packages, BDDs, GPU-parallel
gate execution, or learned circuit solvers; the exact GF(2) reference
algorithm is stronger and already demonstrates tool-assisted ease. Finally,
the incomplete placebo arm limits conclusions about prompt-only effects, as
described above.
