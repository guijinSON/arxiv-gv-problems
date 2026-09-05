# Verified generator for arXiv:2204.04104

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | exact symbolic (a depth-one strategy tree) |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

This module turns Will Rosenbaum's [*Finding a Winning Strategy for Wordle is NP-complete*](https://arxiv.org/abs/2204.04104) into exact, self-contained two-round Wordle instances.  The solver receives the alphabet encoding, target list, game length, and a finite dictionary specified by a polynomial-time rule.  It must return a first dictionary word and the target to guess on every possible feedback branch.  The checker reconstructs that word, computes Definition 2.2 feedback exactly, proves that its feedback classes are singletons as in Proposition 2.4, and replays the second guess against every target.  It never reads `inst["answer"]`.

Generation is inverse, not a hidden solve.  A seed is sampled first; invertible affine substitutions are assembled so their composition sends that seed to zero.  Fermat's identity makes exactly that seed's query separate all target words.  Random target order, physical-position order, and per-position alphabet encodings are applied while carrying the strategy through them.  Remark 4.3 explicitly licenses the implicit dictionary representation, so this remains a native Wordle object rather than a graph surrogate.

## Why Track B

Track A would be false.  Section 3, Theorem 1 and Algorithm 2 give exhaustive recursive search in \(|WI|^{O(g)}\); fixed `g=2` is polynomial in the expanded dictionary size.  The reference implementation specializes that algorithm by enumerating legal query seeds and testing exact feedback partitions.  On the shipping instance it examined 201,773 seeds, made 440,241 feedback calls, counted 26,854,305 exact operations, and took about 3.3 seconds.

The compact route notices that the 24 displayed substitutions compose to one affine map `A*s+B (mod M)`, solves its unique zero, and writes the induced branch table.  This is bounded by 156 exact operations.  A script does it immediately; a no-tool solver must first recognize the compression and then carry out many six-digit modular products without an arithmetic engine.  This measured mechanical/compact gap—not the paper's worst-case NP-completeness theorem—is the hardness claim.

## Worked demo

The `demo` preset is intentionally hand-scale.  For `seed=7`, `make_instance` renders the complete following problem (line wrapping aside):

```text
Two-round Wordle strategy certificate

This is the generalized Wordle game below; no outside word list is used.
There are 5 possible target words, every word has length d=8, and at most
g=2 guesses may be made.  Positions and target rows are 0-based.  Repetition is
allowed unless a rule below says otherwise.

Alphabet and feedback.  A printed entry v at physical position i denotes the
position-tagged alphabet symbol (i,v).  Thus equal printed values in different
positions are different letters.  For a guessed word u and target w, feedback
is a length-8 vector in {0,1,2}: 2 means u[i]=w[i]; after all 2s are removed,
1 marks an unmatched occurrence of u[i] elsewhere in w, using occurrences from
left to right; 0 means absent.  Position tags imply that this instance actually
uses only 0 and 2 feedback, but the rule is the ordinary exact Wordle rule.

At each physical position, enc maps a logical value 0,...,5 to the printed
symbol.  Active and filler positions are:
  0: active j=3; enc=[1,2,4,0,5,3]
  1: filler k=1; enc=[1,5,2,0,3,4]
  2: filler k=0; enc=[3,5,2,0,4,1]
  3: filler k=2; enc=[4,3,2,5,1,0]
  4: active j=0; enc=[4,0,5,1,3,2]
  5: active j=4; enc=[3,5,0,1,2,4]
  6: active j=2; enc=[1,3,5,4,0,2]
  7: active j=1; enc=[0,5,2,3,1,4]

Target list W (also legal guesses).  The x label is part of the instance data:
  0: x=0; word=[0,4,1,0,4,2,5,5]
  1: x=1; word=[5,4,1,0,0,3,4,2]
  2: x=4; word=[4,4,1,0,3,1,3,0]
  3: x=3; word=[2,4,1,0,1,0,1,1]
  4: x=2; word=[1,4,1,0,5,5,0,3]

Implicit dictionary D.  Besides the 5 target words, D contains exactly one
word Q_s for each integer seed s with 0 <= s < M=101.  Compute Q_s as
follows.  Start z0=s and perform these substitutions in order:
  z1 = (20*z0 + 50) mod 101
  z2 = (84*z1 + 6) mod 101
  z3 = (10*z2 + 29) mod 101
Let z be the final value and set

  delta = (1 - z^(M-1)) mod M,  c = s mod 5.

For an active position labelled j, Q_s has logical value
((1+delta)*j+c) mod 5.  For filler k it has logical value floor(s/5^k)
mod 5.  Apply that position's enc list to obtain each printed entry.  M is
prime, so delta is exactly 1 when z=0 and exactly 0 otherwise.  The filler
digits make all Q_s distinct; logical value 5 occurs in every target filler
and never in a Q_s filler.

Required witness.  Give a concrete depth-one strategy tree.  Its JSON object
has exactly three keys:

  seed   the seed s of the first guess Q_s;
  query  all 8 printed entries of Q_s, in physical-position order;
  next   8 integers.  If the first feedback has its sole 2 at physical
         position i, next[i] is the 0-based target-row guessed second.  At a
         filler position next[i] must be -1.

The verifier recomputes dictionary membership, exact feedback for every target,
and every second guess.  It accepts any seed whose supplied tree wins against
all targets; it does not compare with a stored answer.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys seed, query, and next.  Example syntax:
<answer>{"seed":7,"query":[1,4,0],"next":[2,0,-1]}</answer>
Output nothing else inside the tags.
```

The planted answer is `{"seed":84,"query":[1,5,4,5,3,0,4,5],"next":[4,-1,-1,-1,2,3,1,0]}`.  `verify` returns `(True, "ok")`.  Removing the last query coordinate returns `(False, "query is missing a coordinate")`.  A person can solve this demo on paper by reversing three small affine maps modulo 101 and filling eight entries.

## Difficulty presets

| Preset | Seed modulus M | Targets | Chain maps | Word length | Route bound | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 101 | 5 | 3 | 8 | 46 | hand example |
| easy | 1,000,003 | 11 | 24 | 17 | 156 | **ships; oracle held** |
| medium | 2,000,003 | 13 | 42 | 19 | 218 | unused after easy held |
| hard | 4,000,037 | 17 | 60 | 23 | 286 | unused after easy held |

The original easy draft used only 100,003 seeds and was discarded locally because its exact density `1/100003` failed G4.  It was never shipped.  Enlarging the seed haystack fixed the gate without lengthening the strategy tree materially.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted strategies verified and were JSON-native |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | prose/fence/tag round-trip recovered the exact object; garbage returned `None` |
| G4 | pass | exact density `1/1,000,003 = 9.99997e-7`; 0 hits / 200,000 structure-aware samples |
| G5 | pass | demo brute-force count 1/101; shipping reference: 201,773 seeds, 440,241 feedbacks, 26,854,305 operations, about 3.3 s |
| G6 | pass | zero successes in 8 attempts for each of 5 attacks; reference algorithm solved as expected |
| G7 | pass | doubling `n` grew 1,000,003 to 2,000,029 candidates; certificate grew only 35 to 37 atoms |
| G8 | pass | 80 invariance and 80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | sampled worst case 117 chars, about 30 tokens, 35 atoms, 156 intended operations |

G6 tested seed zero, the first 64 seeds, 256 uniform restarts, inversion of only the terminal map, and the tempting but incorrect product-of-multipliers/unweighted-sum-of-offsets ansatz.  Every attack was 0/8.  The exact Algorithm 2 specialization is outside `attacks`, under `reference_algorithm`, because success is expected for Track B.

## Oracle loop and G9 arms

The final bare run used the repository harness at medium reasoning effort.  Every response contained a tagged JSON object, so none of these is a parser false negative.

| Preset | Model | Instance seed | Solved | Verification result |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 46,795,346 | no | query did not equal `Q_seed` |
| easy | Google Gemini 3.8 Flash | 2,110,686,556 | no | query did not equal `Q_seed` |
| easy | Google Gemini 3.8 Flash | 1,986,134,196 | no | query did not equal `Q_seed` |

| G9 arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`.  Naming the affine-composition invariant bought no observed solves, so the sampled failures appear to include exact modular execution difficulty in addition to recognizing the change of variables.  This is a diagnostic, not a gate.  Across 1,000 shipping instances the largest sampled answer measured 117 characters, approximately 30 tokens and 35 atomic elements; the intended route bound is 156 exact operations.

## Use

From this directory:

```python
import gen_2204_04104 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
candidate = g.parse_answer('<answer>' + __import__('json').dumps(inst['answer']) + '</answer>')
assert g.verify(inst, candidate) == (True, 'ok')
```

From the repository root, emit JSONL with:

```bash
bash scripts/emit.sh 2204.04104 10 easy
```

The module is standard-library-only.  It attempts the repository `gvlib` import for compatibility but does not require it.

## Caveats

This is deliberately a Track B benchmark, not evidence that this generated distribution is average-case NP-hard or that ordinary English Wordle is difficult.  Its game length is fixed at two, its alphabet is position-tagged (so yellow feedback never occurs), and its dictionary is implicit; all three choices are legal under Definitions 2.1–2.2 and Remark 4.3 but form a narrow Wordle subclass.  Any CAS or short program composes the affine maps in linear time and makes the instance easy—that is the disclosed reference route, not a hidden weakness.

The G4 prior is uniform over legal seed-indexed certificates and deterministically fills the redundant query and branch fields.  It correctly avoids inflating the space with malformed strategy trees, but it does not model an algebra-aware solver; the affine shortcut beats random guessing completely.  The panel did not run a general SMT solver or symbolic modular-algebra package, because those are expected to solve this Track B family.  It also does not test every possible hand shortcut.  Finally, hinted and placebo performance were identical, so the declared `change of variables` intuition is only partially isolated: the remaining exact arithmetic burden is real even though it stays below the stated operation cap.
