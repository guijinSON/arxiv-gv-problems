# Levenshtein sequence reconstruction generator (arXiv:2211.08812)

Status: **hardened and locally verified**. The shipping preset held against the
script-owned oracle pool on 3/3 bare attempts. All local gates pass.

| profile field | value |
|---|---|
| Track | B — the efficient reference algorithm is disclosed and measured |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra over GF(2) |
| Certificate | exact symbolic hexadecimal payload for a repeated codeword |
| Intended intuition | invariant: even block-error parity cancels under XOR |
| Domain essentiality | native; no reduction |

## Problem and trust model

The source is Junnila, Laihonen, and Lehtilä,
[*The Levenshtein's Sequence Reconstruction Problem and the Length of the
List*](https://arxiv.org/abs/2211.08812). Section 1 defines the feasible list as
`T(Y) = C ∩ ⋂_{y∈Y} B_t(y)`. An instance supplies a binary repetition code `C`
and a set of distinct received words `Y`; the solver returns a payload whose
repeated codeword is within Hamming radius `t` of every received word.

Generation is inverse. A uniformly random payload and its codeword `x` are
sampled first. Exact bipartite degree-sequence realizations then construct an
error array in which every row has weight `t`, every physical column has a
strict correct majority, and every logical coordinate has even error parity
across the odd number of repetition blocks in each row. Thus all outputs are
valid by construction, while XORing the blocks of any one output returns the
payload. `verify` independently repeats a candidate and checks every Hamming
distance; it accepts any valid witness and never reads `inst["answer"]`.

Uniqueness does not rely on sampling. Section 6, Theorem 28 says that its
observable minority-count inequality places every feasible transmitted word
within `k` of the same majority word. The generated inequality holds with
`k=e=4`. The repetition code has minimum distance nine, so radius-four balls
around its codewords are disjoint. Construction supplies one feasible word;
therefore there is exactly one.

## Why Track B

Track A would be false. Section 6 explicitly gives coordinatewise majority in
optimal `Theta(Nn)` time. Shipping contains 9,288 received bits. A stronger
construction-aware implementation can majority only one 24-bit repetition
block, but it still reads 1,032 bits; it solved 8/8 instances in about 0.0004
seconds total. The paper's full scan costs 9,288 bit observations.

The compact route is qualitatively different: notice that each row's nine error
blocks XOR to zero, then XOR its nine six-hex-digit blocks. Because nine is odd,
the codeword contribution is one copy of the payload. This takes 48
single-hex-digit XORs. The easy regimes explicitly kept out of the hardness
claim are `t<=e` (Section 1 says one channel suffices), the high-channel
list-size regimes of Theorems 4 and 6, and the Section 6 decoder itself, which is
reported as the successful Track-B reference rather than hidden in `attacks`.

## Worked demo

This is the complete rendered `demo` instance for seed 31415:

```text
Levenshtein sequence reconstruction over GF(2)

A payload is exactly p=1 hexadecimal digits, including leading zeroes and
without a 0x prefix. Each hexadecimal digit denotes four bits in the usual
most-significant-digit-first convention, so a payload has d=4
bits. Letter case is ignored.

The binary code C consists of the words formed by repeating one payload exactly
B=3 times. Spaces below separate the B consecutive blocks and are
not bits. Thus every codeword has n=B*d=12 bits. The Hamming distance
d(u,v) is the number of bit positions where u and v differ, equivalently the
number of 1 bits in u XOR v. Distinct codewords of C differ in at least B bits,
so C corrects e=1 substitution errors.

An unknown codeword x in C was sent through N=11 channels. The
N outputs below are distinct, and every output differs from x in at most
t=2 bit positions (so ell=t-e=1). The numbered lines form
an unordered set: line order and line numbers carry no information. Block order
within each line is left to right as displayed; repeated blocks and repeated
payload digits are allowed.

Received words:
  1: 8 8 9
  2: 1 9 1
  3: 9 8 8
  4: b b 9
  5: d d 9
  6: 1 1 9
  7: 8 9 8
  8: b 9 b
  9: 9 1 1
  10: d 9 d
  11: 9 d d

Find any p-digit payload a such that the B-fold repetition c of a satisfies
d(c,y)<=t for every displayed received word y. Equality at distance t is
allowed. The answer is the payload a, not the full repeated codeword.

Give your final answer inside <answer></answer> tags, as exactly 1
hexadecimal digits with no 0x prefix.
Example format: <answer>0</answer>
Output nothing else inside the tags.
```

The three blocks of line 1 XOR to `8 XOR 8 XOR 9 = 9`, so the answer is
`<answer>9</answer>`. A person can solve and check this demo on paper.

```text
verify(inst, "9") -> (True, "ok")
verify(inst, "8") -> (False, "payload 8 exceeds radius 2 at channel 2 (distance 5)")
```

## Difficulty presets

| preset | n | N | t | answer bits | one-block majority | compact XOR | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 12 | 11 | 2 | 4 | 44 bit reads | 2 digit XORs | hand example; skipped by harden |
| easy | 216 | 43 | 104 | 24 | 1,032 bit reads | 48 digit XORs | **ships; bare oracle 0/3** |
| medium | 288 | 83 | 140 | 32 | 2,656 bit reads | 64 digit XORs | local gates pass; not needed |
| hard | 576 | 163 | 284 | 64 | 10,432 bit reads | 128 digit XORs | local gates pass; not needed |

The first 16-bit version of `easy` also held 0/3 but was rejected locally because
its exact guess probability was `1/65,536`, above G4's `1e-6` threshold. Its
script-owned evidence is retained as `preg4fix_llm_loop_transcript.jsonl`; the
current 24-bit rung was rerun from scratch. `escalate()` raises only `N`, keeping
the answer and 48-operation intended route fixed.

## Gate results

| gate | measured shipping result |
|---|---|
| G1 | 16/16 planted witnesses verify across all presets; Theorem 28 inequality 16/16 |
| G2 | 8 corruption classes rejected with 8 distinct reasons |
| G3 | tagged prose/fence round-trip passes; answer is JSON-native |
| G4 | 0/200,000 uniform valid-shape guesses; exact prior success `1/2^24 = 5.96e-8` |
| G5 | exactly 1 answer among 16,777,216; sampled 0/200,000; reference cost 1,032 bit observations |
| G6 | six attacks each 0/8; disclosed reference 8/8; compact route 8/8 |
| G7 | channels 43→83, input 9,288→17,928 bits; answer and 48-op route fixed |
| G8 | 100/100 invariant-key checks, 100/100 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 8 serialized characters/tokens upper bound, 24 bit atoms, 48 operations |

## Oracle loop and G9 arms

The bare shipping run used two vendors at medium effort. Every reply parsed;
all were wrong witnesses rather than parser failures.

| model | seed | result | exact reason |
|---|---:|---|---|
| `openai/gpt-5.6-terra` | 728643016 | failed | channel 2 distance 105 > 104 |
| `google/gemini-3.8-flash` | 497730708 | failed | channel 1 distance 107 > 104 |
| `openai/gpt-5.6-terra` | 246703390 | failed | channel 2 distance 108 > 104 |

| G9 arm | solved / attempts | errors | conclusion |
|---|---:|---:|---|
| bare | 0/3 | 0 | held |
| structural hint | 3/3 | 0 | invariant made the task easy |
| placebo hint | 0/3 | 0 | mere hint-like phrasing did not help |

`hinted - placebo = 1.0`. This sharply supports the declared intuition: the
difficulty is finding the invariant. It is diagnostic, not a gate. The hinted
scratch copy deliberately had one rung and disabled escalation; its terminal
`cap_bound` label is a harness side effect, while its three shipping call rows
are the evidence used here.

## Use

```python
import importlib.util

spec = importlib.util.spec_from_file_location(
    "g", "results/2211.08812/gen_2211_08812.py"
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + inst["answer"] + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2211.08812 20 easy
```

## Caveats

This is deliberately Track B and becomes easy with a sandbox; the 0.0004-second
reference measurement makes that explicit. The Section 6 probabilistic analysis
assumes uniform draws from a Hamming ball, whereas this generator uses the
paper's adversarial Section 1 setup and only the deterministic implication of
Theorem 28. The 0/200,000 guess result describes a uniform prior over all
well-formed payloads, not a model's structure-sensitive prior; the exact density
is the more informative number.

The panel does not include SAT/SMT, belief propagation, or learned distinguishers.
Those are unnecessary for the Track-B baseline claim because majority already
solves every generated instance, but stronger pattern learners may discover the
block invariant. The construction has higher-order correlations by design. The
canonical key uses complete row-distance profiles plus physical-column minority
counts; it is invariant under every tested code symmetry but can theoretically
collide on nonisomorphic arrays. No `gvlib` helper is needed: all finite-field
and Hamming checks use exact standard-library integer operations.
