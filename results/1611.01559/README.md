# Offline-verified tensor-decomposition generator for arXiv:1611.01559

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | integer lattice |
| Computational core | linear algebra |
| Certificate | binary matrix specifying an exact rank-one decomposition |
| Intended intuition | symmetry: Walsh characters isolate latent summands |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

[Yaroslav Shitov, *How hard is the tensor rank?*](https://arxiv.org/abs/1611.01559) defines the rank of an order-three tensor as the least number of rank-one outer products whose sum is the tensor (Section 2).  This generator hands the solver an integer tensor in direct-sum blocks and public factor codebooks.  The solver returns two binary XOR shifts per block; those shifts specify all rank-one summands.  `verify` expands the summands over the integers and compares every tensor entry exactly.  The generator samples the shifts first and composes the tensor, so it never solves its output.

Theorem 3 identifies general tensor-rank decision with polynomial-system feasibility, and Observation 8 plus Corollary 5 give worst-case NP-hardness.  Those results do **not** establish hardness of this planted distribution, so this module makes no Track-A claim.  Its promised structure has an efficient exact solver: invert the first-mode Walsh character matrix with a fast Walsh-Hadamard transform.  That algorithm costs

`O(2 * blocks * n * log2(n))` exact arithmetic operations,

and the shipping implementation measured 966 operations (about 0.0002 s per run).  The compact route uses only the common-sign coefficient corresponding to latent `x=0`: two length-`n` sums and two exact divisions per block, or 192 operations at shipping size.  Recognizing that symmetry avoids the two full transforms, but carrying out the remaining sums without tools is still the intended challenge.  Section 3's slice lemma and Sections 4–5 also explain why exposed slice structure must not be presented as distributional hardness.

## Worked demo

This is `make_instance(n=4, blocks=1, value_bits=4, seed=7)` in full:

```text
Here n=4=2^2 and there is one direct-sum block.  For x,i in {0,1,2,3},
chi_i(x)=(-1)^popcount(i AND x).

B_code: [-2,-5,-1,4]
C_code: [-7,-6,2,6]
Tensor slices T[i,:,:], in arbitrary displayed order:
i=3: [[0,3],[-8,5]]
i=2: [[0,-21],[10,17]]
i=0: [[4,-5],[-4,-51]]
i=1: [[0,-5],[-2,57]]

Find s,t such that
T = sum_x chi(x) tensor (1,B_code[x XOR s]) tensor (1,C_code[x XOR t]).
Return [little-endian bits of s, little-endian bits of t].
```

The answer is `[[0,1,0,0]]`, meaning `s=2,t=0`:

```python
>>> verify(inst, [[0, 1, 0, 0]])
(True, 'ok')
>>> verify(inst, [[1, 0, 0, 0]])
(False, 'block 0 second-mode zero coefficient mismatch')
```

A person can solve this demo on paper by adding the four `(1,0)` entries and the four `(0,1)` entries, dividing by four, and locating the two results in the codebooks.

## Difficulty presets

| Preset | n | Blocks | Coefficient bits | Answer space | Status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 1 | 4 | 16 | hand example |
| easy | 8 | 2 | 6 | 4,096 | oracle run blocked before scoring |
| medium | 16 | 2 | 8 | 65,536 | not reached |
| hard | 32 | 3 | 12 | 1,073,741,824 | intended shipping preset; oracle evidence pending |

`SHIPPING_DIFFICULTY` is provisionally `hard`.  It cannot be released until the required bare and hinted oracle runs complete.

## Offline gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted decompositions verified |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged fenced JSON round-tripped; answer JSON-native |
| G4 | pass | 0/200,000 structured guesses; exact density `1/2^30` |
| G5 | pass | demo has exactly 1/16 valid answers; shipping reference cost 966 operations; 256-restart attack failed in about 0.01 s |
| G6 | pass | all four attacks 0/8; reference transform 8/8 as expected |
| G7 | pass | `n=64` builds and verifies; search entropy grows 30 to 36 bits |
| G8 | pass | 180/180 keys invariant, 180/180 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | answer 67 characters, about 17 tokens, 30 atoms; compact route 192 operations |
| G9(a,b) | **pending** | OpenRouter quota prevented all scored attempts |

The failing G6 panel consists of a maximum-code-magnitude outlier, a nearest-raw-marginal greedy rule, 256 random restarts, and a by-hand raw-sign ansatz.  Random codebooks were introduced specifically because monotone binary code values made the raw Walsh signs disclose every shift bit.

## Oracle loop and G9 arms

The required harness was invoked on 2026-09-05.  Every call returned HTTP 403 `Key limit exceeded (total limit)`.  The harness correctly recorded these as API errors and aborted; they are **not** model failures and therefore provide no hardness evidence.

| Preset | Seed | Model | Outcome | Reason |
|---|---:|---|---|---|
| easy | 779440774 | Grok 4.6 | error | OpenRouter total key limit |
| easy | 9896332 | Grok 4.6 | error | OpenRouter total key limit |
| easy | 649445160 | Gemini 3.1 Pro | error | OpenRouter total key limit |
| easy | 13138351 | Gemini 3.1 Pro | error | OpenRouter total key limit |

| G9 arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 0 scored | pending |
| hinted | 0 / 0 scored | pending |
| placebo | 0 / 0 scored | pending |

The hinted-minus-placebo diagnostic is undefined until both arms run.  No conclusion about the hint's value is claimed.

## Use

```python
import gen_1611_01559 as g

inst = g.make_instance(**g.DIFFICULTY["hard"], seed=123)
question = g.render(inst)
candidate = g.parse_answer("<answer>...</answer>")
ok, reason = g.verify(inst, candidate)
```

After valid hardening transcripts exist, emit from the repository root with:

```bash
bash scripts/emit.sh 1611.01559 20 hard
```

The module is standard-library-only; `gvlib` is unnecessary because all arithmetic is exact integer addition and multiplication.

## Caveats

- This is a Track-B benchmark, not evidence that the generated distribution inherits Corollary 5's NP-hardness.  A Walsh-Hadamard implementation solves every promised instance quickly.
- The `1/2^30` guess probability is for the declared prior: a uniform, shape-valid binary shift matrix.  It says nothing about a candidate distribution informed by a new algebraic attack.
- The full tensor-decomposition algorithms used in numerical practice (Jennrich-type methods, alternating least squares, Gröbner methods, and tensor-specific relaxations) were not benchmarked.  Exact Walsh inversion dominates them on this promise.
- `canonical_key` is proved invariant under displayed-row and block reorderings, independent XOR translations of both codebooks, arbitrary invertible GF(2) changes of bit basis, a latent global translation, independent integer translations/reflections of both scalar codebooks, their compositions, and swapping the last two tensor modes.  It uses normalized code-value and signed-slice multisets as a cheap invariant and may over-collapse a rare pair of non-isomorphic arrays; 20 unrelated seeds produced 20 distinct keys.
- The hard preset has passed every offline gate but has not passed G9(b) or the four-vendor loop because the external OpenRouter quota was exhausted.  `selftest_report.json` therefore truthfully has `G9.pass=false` and `all_passed=false`; this directory is not submission-ready.
