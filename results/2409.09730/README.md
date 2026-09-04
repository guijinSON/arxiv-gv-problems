# Projective-hyperplane block recovery

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | matrix certificate: one normalized covector over `GF(p)` |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This generator turns Amin Saeidi's [*On point and block primitive designs invariant under permutation groups*](https://arxiv.org/abs/2409.09730) into a block-recovery problem in the paper's own objects. The solver receives `d-1` projective points over `GF(p)` spanning an unknown hyperplane and returns the unique normalized covector defining that hyperplane. Exact modular inner products check any proposed covector cheaply. Lemma 4.1 supplies the point- and block-primitive design from the hyperplane-stabilizer orbit; Remark 1 makes it a 2-design because `PGL(d,p)` is 2-transitive on projective points.

## Why this is Track B

The paper does not establish average-case hardness, so Track A would be unjustified. A standard modular Gaussian elimination solves the displayed `(d-1) x d` nullspace problem in `O(d^3)`. At the shipping preset, the reference implementation solved 8/8 instances using 341,200 field operations total (42,650 average) in 0.0104 seconds total on this machine. That algorithm is deliberately reported as the reference, not as a failed attack.

The compact route notices that the dense square part is `A=(I+3P)^(-1)` for the displayed directed coordinate cycle. Writing the last column as `b`, the equations `Ax+b=0` become `x=-(I+3P)b`. This costs 213 exact field operations after recognition, within the no-tool cap, but requires 71 modular multiply/add/negate calculations to transcribe the full normal correctly. Section 3, Theorem 3.2 makes a supplied block orbit immediate; Lemma 4.1 makes a supplied subgroup orbit immediate; and Proposition 3.3 plus Tables 1–3 are MAGMA classifications. Those easy/lookup formulations were avoided.

Generation is inverse: a uniformly random normalized covector is sampled first, then the dense incident frame is built around it with the finite geometric-series identity for `(I+3P)^(-1)`. No instance is solved during generation.

## Worked demo

For `make_instance(n=5, p=7, seed=3)`, the full mathematical data are:

```text
PG(4,7), normalization h_4=1
points:
0: 2 4 1 2 2
1: 4 2 2 1 1
2: 2 1 2 4 1
3: 1 2 4 2 3
cycle: 0->2 1->3 2->1 3->0
output format: [[h_0,h_1,h_2,h_3,h_4]]
```

The answer is `[[2,4,3,5,1]]`; `verify(inst, answer)` returns `(True, "ok")`. Changing its first entry gives `[[3,4,3,5,1]]`, which returns `(False, "point 0 is not incident with the proposed hyperplane")`. A person can solve this demo on paper by four short equations, or by spotting the cyclic identity.

## Difficulty presets

| preset | `d=n` | `p` | candidate language | status |
|---|---:|---:|---:|---|
| demo | 5 | 7 | `7^4 = 2,401` | hand-scale illustration |
| easy | 48 | 257 | `257^47` | bare hardened, but G9 hint solved 1/3; not shipped |
| **medium** | **72** | **4099** | **`4099^71`** | **shipping; bare and hinted hardened** |
| hard | 96 | 65537 | `65537^95` | available escalation |

Difficulty enlarges both the ambient dimension and the field. `escalate()` first raises the modulus at fixed answer length. A doubled-size `n=144` instance also builds and verifies.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified; JSON round-trip preserved |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON matrix recovered from prose and Markdown |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `4099^-71 = 3.1613e-257` |
| G5 | pass | unique shipping witness by invertibility; demo enumeration found exactly 1/2,401; reference cost above |
| G6 | pass | each of four attacks failed 0/8; elimination solved 8/8 as expected |
| G7 | pass | strictly growing candidate spaces; doubled instance verified |
| G8 | pass | 60/60 relabelling/rescaling checks and 60/60 carried witnesses; 20/20 unrelated keys distinct |
| G9 | pass | hint still hardened; 335 chars, 84 approximate tokens, 72 atoms, 213 intended operations |

The four G6 attacks were one-column outlier fitting, greedy coordinate repair, 256 random restarts per seed, and obvious direct/scaled/one-shift cycle ansatzes. All plants and random candidates use the same uniform normalized-covector distribution.

## Oracle evidence

The shipping bare run is the script-owned [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl).

| arm | model | seed | outcome | checker result |
|---|---|---:|---|---|
| bare | OpenAI GPT-5.6 Terra | 20267098 | failed | parsed; point 0 failed |
| bare | Gemini 3.1 Pro Preview | 1941025324 | failed | parsed; point 0 failed |
| bare | Grok 4.6 | 1265474837 | failed | parsed; point 0 failed |
| structural | Claude Sonnet 5 | 1050756062 | failed | response exhausted its 32k output budget; explicitly recorded |
| structural | OpenAI GPT-5.6 Terra | 2076209963 | failed | parsed; point 0 failed |
| structural | Gemini 3.1 Pro Preview | 2129397759 | failed | parsed; point 22 failed |
| placebo | OpenAI GPT-5.6 Terra | 1786484490 | failed | parsed; point 0 failed |
| placebo | Gemini 3.1 Pro Preview | 1039220862 | failed | parsed; point 0 failed |
| placebo | Claude Sonnet 5 | 1064639463 | failed | response exhausted its 32k output budget; explicitly recorded |

| G9 arm | solved / attempts |
|---|---:|
| bare | 0 / 3 |
| structural hint | 0 / 3 |
| placebo hint | 0 / 3 |

`hinted - placebo = 0.0`. At this three-call resolution, naming the change-of-variables structure bought no measured advantage. The preliminary easy run is retained in `bare_easy_transcript.jsonl` and `g9_hinted_easy_transcript.jsonl`: easy was bare-hardened, but Terra solved the hinted version, which is why the one permitted move to medium was used.

## Use

```python
import gen_2409_09730 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit fresh shipping instances with:

```bash
scripts/emit.sh 2409.09730 20 medium
```

## Caveats

This is not a computational-complexity hardness claim: Gaussian elimination solves it quickly with tools, and inspecting the generator reveals the two-tap inverse. The 0/200,000 guess result measures only the explicitly stated uniform prior over normalized covectors; it does not prove that a structured solver has low success. The attack panel did not test every symbolic matrix-pattern detector or a CAS implementation of circulant inversion—the reference elimination already establishes tractability. The cycle is part of the presentation, so `canonical_key` quotients coordinate relabellings, row order, and projective rescaling, but not arbitrary projective basis changes that would turn the cycle permutation into a general linear map. Finally, one hinted and one placebo oracle failure were output-budget exhaustions rather than wrong submitted matrices; the transcripts expose that distinction.
