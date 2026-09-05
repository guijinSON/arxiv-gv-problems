# Weight-six words in binary self-dual codes

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | linear algebra |
| certificate form | integer tuple (the natural support of a codeword) |
| intuition | ansatz: test the parity of the complete displayed row basis |
| domain essentiality | native |
| reduction | none |

This is a generator for a native problem from Harada and Munemasa,
[“Classification of self-dual codes of length 36”](https://arxiv.org/abs/1012.5464).
The solver receives several binary `18 x 36` generator matrices for self-dual
codes and must give a block number plus the six coordinates supporting a
weight-six codeword.  `verify()` checks the selected generator's rank and all
pairwise inner products over GF(2), then checks the proposed support against
all 18 generator rows.  Since a self-orthogonal 18-space in `GF(2)^36` is its
own dual, those parity checks decide membership exactly.  The checker neither
reads the planted answer nor searches for a codeword.

## Why this is Track B

Section 1 supplies the exact definitions of duality and equivalence.  Section
2.1 makes generator matrices, row-basis changes, and coordinate permutations
the classification objects.  Section 4 and Figure 1 give a self-dual
`[36,18,6]` code explicitly; its first displayed generator row has weight six,
and the reported `(gamma,delta)=(12,4)` weight enumerator has exactly 12 such
words.  The generator carries that known row through invertible basis and
coordinate transformations.  Its decoys mix three elementary direct-sum
self-dual codes with representatives of both extremal weight-enumerator
classes from the authors' linked
[electronic database](https://www.math.is.tohoku.ac.jp/~munemasa/research/codes/data/2/36-d8.magma).
Every decoy enumerator has zero weight-six coefficient.  Selftest enumerates
all `2^18` words of all six base-code types and checks those enumerators.  At
least half the decoys are extremal `[36,18,8]` codes, so detecting weight-four
words does not isolate the target.

This is not a Track-A hardness claim.  The strongest reference route first
uses pair-syndrome collisions to remove minimum-distance-four decoys, then
forms the syndrome of every triple in the surviving blocks and looks for two
disjoint triples with the same syndrome.  It is `O(b * 36^3)` for `b`
displayed blocks, solved 8/8 shipping instances as expected, and used at most
63,098 counted XOR/collision operations (about 0.025 s maximum in the recorded
local run).  Five blocks survive the prefilter.  The compact route is to try
the XOR of the complete 18-row basis in each block.  Recognizing that ansatz
reduces the shipping preset to at most 144 exact 36-bit XOR/weight-test operations.
Theorem 1's complete list of 519,492 equivalence classes would itself be a
finite lookup; this family does not misrepresent that classification as a hard
search.

## Worked demo

The demo uses the Figure-1 generator with one fixed reversal of its last 18
coordinates (a code-equivalence transformation), so a person can solve it on
paper by noticing that row 0 already has weight six.  This is the complete
rendered instance for `seed=0`:

```text
Weight-six word in binary self-dual codes

All arithmetic is over GF(2): addition is XOR (1+1=0). For binary
vectors u,v of length 36, their inner product is the parity of the
coordinates where both have a 1. A binary linear code is the set of
all XORs of the rows of its generator matrix. Its dual consists of
all vectors orthogonal to every codeword. A code is self-dual when it
equals its dual.

Below are 1 independent 18-by-36 binary generator
matrices. In every matrix the 18 rows are independent and mutually
orthogonal, so they generate a self-dual code of length 36. At least
one displayed code contains a word of Hamming weight exactly 6.

Find any one such word. Coordinates are numbered 0 through 35 from
left to right within a row; block numbers are 0-based. A support means
six distinct coordinate numbers whose incidence vector belongs to the
row span of the selected block. Order the six coordinates increasingly.

BLOCK 0
00: 100000000000000000010001010000001100
01: 010000000000000000101101010000001100
02: 001000000000000000101011100000011000
03: 000100000000000000011000100000011000
04: 000010000000000000101001100000000100
05: 000001000000000000100110010000000100
06: 000000100000000000111111000100011101
07: 000000010000000000001111111011011101
08: 000000001000000000011001001000100011
09: 000000000100000000011010110111010011
10: 000000000010000000110011000110110010
11: 000000000001000000111100111010001110
12: 000000000000100000000000111001110100
13: 000000000000010000110000000101110111
14: 000000000000001000101001111101000010
15: 000000000000000100010110111110111101
16: 000000000000000010010101111011111011
17: 000000000000000001011001110111110100

Give your final answer inside <answer></answer> tags, as exactly seven
comma-separated integers: block,c1,c2,c3,c4,c5,c6.
Example: <answer>2, 1, 5, 9, 14, 23, 31</answer>
Output nothing else inside the tags.
```

The answer is `<answer>0, 0, 19, 23, 25, 32, 33</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the last
coordinate returns `(False, "answer must contain exactly seven integers")`.

## Presets and measured gates

| preset | blocks | presentation | status |
|---|---:|---|---|
| demo | 1 | visible Figure-1 basis | hand-solvable illustration |
| easy | 8 | 180 row-mixing rounds and coordinate permutations | **shipping; held by the bare oracle pool** |
| medium | 12 | 220 mixing rounds | unscored |
| hard | 16 | 260 mixing rounds | unscored |

No preset was rejected by a local gate.  A seventeenth block would make the
compact scan 306 operations, above G9's 300-operation cap.  Post-hard
`escalate()` therefore increases row-mixing rounds at the fixed 16-block count,
so the seven-integer witness and the compact-route bound do not grow.

| gate | result |
|---|---|
| G1 planted verifies | 12/12 preset/seed cases; six base enumerators checked by 262,144-word enumeration each |
| G2 corruption | 5/5 rejected with five distinct reasons |
| G3 round trip | realistic tagged response recovered exactly |
| G4 guessing | 0/200,000; exact density `12 / 15,582,336 = 7.7010276251e-7` |
| G5 baseline | two-row-sum attack 0/8 over 10,944 combinations; reference maximum 63,098 operations |
| G6 panel | four attacks each 0/8; reference algorithm 8/8 as expected |
| G7 scaling | 16-block instance built and verified; witness stayed at 7 atoms |
| G8 canonical key | 100/100 row/basis/coordinate/block relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) caps | worst answer 28 chars / 7 estimated tokens / 7 atoms; compact route at most 144 operations |

## Oracle loop and G9 diagnostics

The required bare harness held the easy preset: all three scored attempts
failed, so `harden.py` recorded `verdict: hardened` with no escalation.  The
clean structural and placebo runs also held 0/3.  Each diagnostic was run in
its own scratch directory with escalation disabled, so the retained files
contain exactly three scored calls at the shipping preset.

| bare preset | seed | model | solved | reason |
|---|---:|---|---|---|
| easy | 1095829820 | `google/gemini-3.8-flash` | no | emitted no answer before its 32,000-token completion limit |
| easy | 1857283393 | `openai/gpt-5.6-terra` | no | parsed support failed an exact parity check |
| easy | 1284869599 | `google/gemini-3.8-flash` | no | emitted no answer before its 32,000-token completion limit |

| run | preset | scored solved/attempts | API errors | conclusion |
|---|---|---:|---:|---|
| bare | easy | 0/3 | 0 | hardened |
| structural hint | easy | 0/3 | 0 | hardened |
| placebo hint | easy | 0/3 | 0 | hardened |

`hinted - placebo` is `0`.  The structural sentence bought the sampled oracle
pool no measurable help, so these runs do not establish that failures are
specifically caused by failure to notice the claimed ansatz; the diagnostic is
honestly inconclusive.  G9(c), the gated part, passes: the worst answer is 28
characters, about 7 tokens and 7 atoms, while the intended shipping route takes
at most 144 exact 36-bit vector operations.  The bare Step-4 hardness evidence
is complete.

## Use

From this directory:

```python
import random
import gen_1012_5464 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + ",".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
decoy = g.random_candidate(inst, random.Random(1))
```

From the repository root, after a successful hardening run:

```bash
bash scripts/emit.sh 1012.5464 20
```

## Caveats

- The family deliberately has an efficient solver and claims only Track B.
  Exhaustive enumeration of all `2^18` codewords per block and standard
  information-set/codeword-search methods were not included in the failing
  attacks; the faster pair-prefilter-plus-triple-collision method was included
  as the successful reference algorithm.
- The guessing probability is exact for a uniform prior over a displayed block
  and a sorted six-subset.  It says nothing about a solver using code structure.
- The target's row basis is conditioned so its complete parity is a weight-six
  word.  Decoy bases are otherwise mixed in the same manner.  The reference
  attack explicitly tests the obvious minimum-distance-four signature and the
  extremal decoys defeat that shortcut, but a stronger statistical classifier
  over full row-weight/intersection distributions was not tested.
- `canonical_key()` uses the multiset of complete weight enumerators.  It is
  invariant under row, coordinate, and block relabelling and correctly merges
  this generator's transformed copies, but weight enumerators are not complete
  invariants for arbitrary code equivalence and can over-collide outside this
  controlled family.
- The G9 arms have only three attempts apiece, and their observed `0/3 - 0/3`
  hinted-minus-placebo difference gives no evidence that the structural hint
  isolated the source of difficulty.
- Two of the three bare failures were empty, length-limited Gemini responses;
  `harden.py` deliberately scores such completed calls as unsolved, but they are
  weaker evidence than an explicit invalid witness.  The remaining Terra
  response did contain a parsed witness and failed exact verification.
