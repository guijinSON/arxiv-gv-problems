# Verified generator for arXiv:2602.13970

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | other (exact finite-set witness) |
| Certificate form | exact symbolic JSON object containing three sets |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

This generator uses a proof object from Hu and Xu, [*The strong fractional choice
number of triangle-free planar graphs*](https://arxiv.org/abs/2602.13970), rather than
turning the headline graph theorem into an unrelated CSP. Remark 1(3) in Section 2.1
uses three colour sets `A,B,C` and requires sets
`S ⊆ A\C`, `T ⊆ B\C`, and `R ⊆ A∩B∩C`. Lemma 11 in Section 2.3 proves that
`|A|+|B| ≥ |C|+m` guarantees a choice with `|S|+|T|+|R|=m`. This is the paper's
two-neighbour “saving” operation for extending a partial multiple-list colouring.

An instance gives the three finite sets exactly, as six Venn-atom intervals after a
displayed reversible relabelling of an `n`-bit universe. A witness is the JSON object
`{"S":[...],"T":[...],"R":[...]}`. Verification decodes each fixed-width word,
recomputes its atom with exact integer operations, checks membership and duplicates,
and compares the total cardinality. It never consults the planted answer.

The scope is deliberately precise: this is native coverage of Lemma 11's set objects
and saving witness, not a generator for the paper's full triangle-free planar graph
multicolouring theorem. The reversible presentation is a benchmark representation of
finite sets; it is not claimed as a construction from the paper.

## Why Track B is honest

Lemma 11's proof exposes the easy generic algorithm: enumerate `A\C`, `B\C`, and
`A∩B∩C`, then take `m` elements. For the succinct shipping instance, the reference
implementation scans all `2^20=1,048,576` labels. Across eight seeds it solved 8/8,
using exactly 35,651,584 word operations and averaging 1.563374 seconds. Its complexity
is `O(2^n · rounds)` for this representation.

The compact route notices that the displayed coordinate map is Feistel-reversible.
The three useful intervals contain exactly eight coordinate words, so reversing eight
rounds on those words constructs the witness in 275 counted exact word operations.
The generator knows the same witness by composition of inverse identities; it never
scans or solves its emitted instance. The task is therefore not a Track A complexity
claim. It measures whether a no-tool solver finds and correctly executes the change of
variables. The explicit-list regime would be easy, and that is exactly why it was not
mislabelled Track A.

## Worked demo

The demo is hand-solvable. With `seed=42`, the complete rendered instance is:

```text
Three-set saving witness (arXiv:2602.13970, Section 2.3, Lemma 11)

The universe U is all n-bit integers x with 0 <= x < 2^n, where n=4; thus
|U|=16.  In answers, write every x as exactly 1 lowercase
hexadecimal digits, including leading zeroes.

Three finite sets A, B, C are defined through a coordinate y=P(x).  All arithmetic
below is exact. XOR is bitwise exclusive-or. rotl_w(q,s) rotates the w-bit word q
left by s positions, with wraparound. Here w=2.

To compute P(x):
  1. Replace x by x XOR 0.
  2. Split it into the high w-bit word ell and low w-bit word r.
  3. For each listed round, replace (ell,r) simultaneously by
       (r, ell XOR (rotl_w((r+key) mod 2^w, rotate) XOR constant)).
  1: key=0, rotate=1, constant=0
  4. Join ell as the high half and r as the low half, then XOR
     2. The resulting n-bit integer is y=P(x).

Use the unique half-open interval [lo,hi) containing y to obtain its Venn atom:
  [0, 7): AC
  [7, 12): NONE
  [12, 13): B
  [13, 14): BC
  [14, 15): ABC
  [15, 16): A
The atom labels mean NONE (in no set), A (only A), B (only B), AC (in A and C
but not B), BC (in B and C but not A), and ABC (in all three sets). Consequently
|A|=9, |B|=3, |C|=9, and the promised
tight identity |A|+|B|=|C|+m holds for m=3.

Find three subsets S,T,R such that S is a subset of A\C, T is a subset of B\C,
R is a subset of A intersection B intersection C, and |S|+|T|+|R|=3. Order
inside each list does not matter. Repetitions within a list are forbidden. S,T,R
may have different sizes, including zero; only their total size is fixed.

Give your final answer inside <answer></answer> tags as one compact JSON object
with exactly the keys S, T, R and lists of fixed-width lowercase hexadecimal words.
Example of the syntax only: <answer>{"S":["0"],"T":[],"R":[]}</answer>
Output nothing else inside the tags.
```

The answer is `{"S":["b"],"T":["7"],"R":["f"]}` and `verify` returns
`(True, "ok")`. Dropping `b` returns
`(False, "the three list lengths do not sum to m")`.

## Difficulty presets

| Preset | n | Universe | m / answer words | Rounds | Oracle result |
|---|---:|---:|---:|---:|---|
| demo | 4 | 16 | 3 | 1 | skipped; hand example |
| easy | 16 | 65,536 | 8 | 4 | defeated, 1/3 solved |
| medium | 18 | 262,144 | 8 | 6 | defeated, 2/3 solved |
| **hard (ships)** | **20** | **1,048,576** | **8** | **8** | **held, 0/3 solved** |

The initial bits-only ladder was discarded before shipping because its hardened
32-bit scan could not be measured end-to-end honestly. The finalized ladder grows
permutation crowding as well as the universe and was rerun from scratch; only the
finalized transcript is shipped.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified; inverse checked on boundary/sample words |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged, fenced, prose-surrounded JSON round-tripped |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `4.2049e-48` |
| G5 | pass | one mathematical answer; scan 35,651,584 ops, 1.563374 s mean |
| G6 | pass | four attacks, 0/8 successes each; reference and compact routes 8/8 |
| G7 | pass | doubled `n=40` builds/verifies; answer remains 8 words |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 distinct keys |
| G9 | pass | 83 chars, 21 estimated tokens, 8 atoms, 275 operations |

`random_candidate` samples uniformly from an `m`-subset of three tagged copies of
the universe. It already enforces the JSON shape, valid word range, no within-list
repetitions, and total size. The shipping language has
237,818,127,289,509,243,242,201,197,685,175,961,551,566,929,920 candidates.

## Bare oracle loop

| Preset | Seed | Model | Solved | Recorded reason |
|---|---:|---|---|---|
| easy | 1023768428 | Gemini 3.8 Flash | no | proposed `S` word failed membership |
| easy | 270845391 | GPT-5.6 Terra | yes | `ok` |
| easy | 774085808 | Gemini 3.8 Flash | no | proposed `S` word failed membership |
| medium | 1355598884 | Gemini 3.8 Flash | yes | `ok` |
| medium | 1964314743 | GPT-5.6 Terra | no | proposed `T` word failed membership |
| medium | 818297742 | GPT-5.6 Terra | yes | `ok` |
| hard | 1790365206 | Gemini 3.8 Flash | no | proposed `S` word failed membership |
| hard | 900671616 | GPT-5.6 Terra | no | proposed `S` word failed membership |
| hard | 1304517638 | GPT-5.6 Terra | no | proposed `S` word failed membership |

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict at shipping |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 1/3 | too easy (diagnostic only) |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is `1/3 = 0.3333`. The single hinted solve, against no placebo
solves, is evidence that naming the Feistel symmetry can expose the intended change
of variables; it does not gate shipping. The answer is 83 characters / 8 atoms, and
the intended route is 275 exact word operations.

## Use

From the repository root:

```python
import importlib.util

path = "results/2602.13970/gen_2602_13970.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))
wire = "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
print(g.verify(inst, g.parse_answer(wire)))  # (True, "ok")
```

The results directories are not Python packages, so `importlib` is the portable loader
used by the repository scripts. Emit twenty instances with:

```bash
bash scripts/emit.sh 2602.13970 20
```

## Caveats

- This benchmark covers the paper's Lemma 11 saving witness, not Theorem 3's full
  triangle-free planar graph or the 31-page reducibility/discharging proof.
- The reversible succinct encoding is synthetic. If the Venn atoms were explicitly
  listed, Lemma 11 would be immediately easy; if a solver recognizes and executes
  Feistel reversal, this family is intentionally easy. That is the Track B claim.
- The `P(guess)` figure is for the declared uniform, shape-aware prior. It says nothing
  about a solver using the displayed permutation, and it is not a complexity lower
  bound.
- The adversary panel tried numeric outliers, a 512-label prefix scan, 4,096 random
  probes, and the plausible but wrong “forward equals inverse” ansatz. It did not run
  an SMT/bit-vector solver, symbolic execution, or a custom Feistel recognizer; those
  are expected to solve the instance efficiently and are not concealed.
- The third hinted Gemini call returned an empty, provider-marked response and was
  scored according to `harden.py`'s published empty-response rule. The other two
  hinted calls include one verified solve and one explicit invalid witness, so the
  diagnostic conclusion does not depend on treating that empty reply as a solve.
- `canonical_key` uses all eight labelled Venn-atom sizes, a complete invariant for
  triples of finite sets. The executable test covers XOR relabelling, input-block
  reordering, and their composition; completeness under arbitrary bijections follows
  from the Venn-atom classification rather than exhaustive permutation testing.
- Only the Python standard library is needed; `gvlib` is unnecessary for these exact
  integer/set operations.
