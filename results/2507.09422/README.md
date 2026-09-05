# Exact algebraic Nash equilibria from arXiv:2507.09422

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | algebra / real algebraic |
| Computational core / certificate | polynomial identity / exact symbolic polynomial vector |
| Intended intuition | decomposition: split a coefficient tensor over disjoint variable sets |
| Domain essentiality | native; no reduction |
| Shipping preset | `easy` (`n=12`, dense-mask width 2) |

This generator is based on Orzech and Rinard, [*Nash Equilibria with Irradical Probabilities*](https://arxiv.org/abs/2507.09422). It hands the solver a two-action normal-form game represented by exact multilinear payoff-advantage polynomials. The witness gives every player's action-0 probability as a polynomial in one exactly isolated degree-six algebraic number. `verify` checks the isolating interval, proves every probability is strictly in `(0,1)`, substitutes into the displayed game polynomials, and reduces the results exactly modulo the defining polynomial. There are no floats, and any valid witness in the declared affine codebook is accepted.

## Construction and Track B claim

Section 2, Equation (1) and Lemma 2.1 fix the payoff-advantage convention and exact fully mixed Nash condition. Proposition 4.1 supplies the four-player equilibrium; Appendix A certifies its selected root with a Sturm sequence. Proposition 6.6 and Lemma 6.2 license product composition. The generator composes four-player copies, applies invertible affine coordinate substitutions, independently relabels actions and players, and multiplies each advantage polynomial by an independently sampled dense polynomial that is at least 1 on the probability cube. The planted identities and best-response signs are therefore carried through the construction; no emitted instance is solved while generating it.

This is explicitly not Track A. The paper computes the core certificate with a Mathematica Gröbner basis and exact root isolation. On this distribution, the successful reference algorithm splits each displayed coefficient table as a rank-one tensor over disjoint variable sets, then tries 11 scales and the `4!·2^4=384` role/action symmetries. At the shipping preset its complexity is `O(n(C(s,2)+C(s,3))2^s + 4224n)` for at most `s=5` variables per equation; the final 8-seed run measured at most 307,436 coefficient probes and 1.239 seconds per instance, solving 8/8 as expected. A generic SymPy 1.12 F5B Gröbner calculation took 0.00993 s on the demo but exceeded 120 s on shipping seed 9000. Once the tensor split is noticed, the intended bookkeeping costs at most 156 exact operations.

The easy regimes matter. Two-player rational games admit rational equilibria through linear programming, and Proposition 3.2 proves that every integer-payoff `2×2×2` three-player game has an equilibrium expressible with rationals and square roots. This family stays in products of the paper's four-player irradical construction. An earlier generator version used two fixed linear masks and was invalidated: five aggregate coefficient statistics recovered all 12 planted values on 8/8 seeds. Independent dense positive masks were introduced specifically to defeat that leak; the same attack is now 0/8.

## Worked demo

For `make_instance(n=4, mask_width=0, value_slots=4, seed=0)`, the complete mathematical core is:

```text
16299411/250000000000 < z < 13039529/200000000000
P(z)=244140625*z^6-1679687500*z^5+3919921875*z^4
     -1061484375*z^3+134165625*z^2-6665425*z+434 = 0

F1=y2*y3*y4+2*y2*y3-2*y3*y4-2*y2+1
F2=3*y1*y3*y4-3*y1*y3-y3*y4+y1+y3-y4
F3=y1*y4-y1-2*y4+1
F4=-y1*y2*y3+3*y1*y3-y2*y3+y2-1
```

The exact answer is:

```json
{"values":[[4081027,7178107,-70409025,354696875,-155593750,22890625],[4136044,-958696,-1157300,-3700000,1937500,-312500],[6612577,32137,8653225,-397446875,184406250,-27890625],[2500000,437500,0,0,0,0]],"selector":[1,2,0,3]}
```

Here `[c0,...,c5]` denotes `c0/7812500 + Σ(k=1..5) ck*z^k/437500`. A person can solve and check this smallest setting on paper by reducing four polynomial identities modulo `P`, although the elimination is substantial. `verify(inst, inst["answer"])` returns `(True, "ok")`; swapping the first two selector entries returns `(False, "player 3 payoff advantage is nonzero")`.

## Presets and gates

| preset | players | mask width | seed-0 displayed terms | answer chars |
|---|---:|---:|---:|---:|
| demo | 4 | 0 | 20 | 223 |
| easy **(ships)** | 12 | 2 | 336 | at most 686 over 200 measured seeds |
| medium | 16 | 3 | 880 | 887 at seed 0 |
| hard | 20 | 4 | 2,240 | 1,106 at seed 0 |

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified; all answers JSON-native |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | tagged JSON round-trip passed; garbage returned `None` |
| G4 | 0/200,000 structure-aware guesses; exact probability `1/98,373,462,462,399,553,228,800` |
| G5 | shipping density 0/200,000 sampled; exact valid encodings `12!`; reference 307,436 probes / 1.239 s |
| G6 | coefficient fingerprint, displayed-equation greedy, 256 random restarts, cyclic ansatz: each 0/8; reference 8/8 |
| G7 | doubling to 24 players raised terms 328→672 and reference probes 247,811→327,438; certificate verified |
| G8 | 60/60 invariance and carried-certificate checks; 20/20 unrelated keys distinct |
| G9(c) | 676 chars, 84 atoms, about 169 tokens, 156 intended operations — within every cap |

## Oracle loop and G9 arms

The required external hardness evidence is **not complete**. The final `harden.py` run used the current two-provider pool, but every draw returned OpenRouter HTTP 403 “total key limit exceeded.” The harness correctly aborted instead of counting provider errors as model failures. Its script-owned diagnostic transcript is preserved, but there is no `hardened` verdict and this result must not be submitted until a funded key reruns all three arms.

| preset | seed | model | scored result / reason |
|---|---:|---|---|
| easy | 2100852341 | Gemini 3.8 Flash | error; OpenRouter total key limit exceeded |
| easy | 970415566 | Gemini 3.8 Flash | error; OpenRouter total key limit exceeded |
| easy | 44819310 | GPT-5.6 Terra | error; OpenRouter total key limit exceeded |
| easy | 2055990601 | Gemini 3.8 Flash | error; OpenRouter total key limit exceeded |

| G9 arm | solved / scored attempts | diagnostic conclusion |
|---|---:|---|
| bare | 0 / 0 | four provider errors; unrun |
| structural hint | 0 / 0 | four provider errors; unrun |
| placebo | 0 / 0 | four provider errors; unrun |

`hinted − placebo` is therefore not measurable. The structural hint names only the disjoint-variable tensor invariant, not a procedure.

## Use

```python
from gen_2507_09422 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

From the repository root, emit examples with `bash scripts/emit.sh 2507.09422 20`. Once OpenRouter quota is available, rerun `python3 ../../scripts/harden.py gen_2507_09422.py` here; run structural and placebo copies in separate scratch directories before updating the G9 measurements.

## Caveats

The public affine codebook makes this a structure-recognition benchmark, not a request to rediscover the paper's degree-six probabilities. Tensor factoring plus template recognition solves the distribution efficiently and is disclosed above. The `0/200,000` estimate is for uniform codebook subsets and assignment permutations; it says nothing about a learned or construction-aware prior. Mathematica, Magma, SMT solvers, and alternative symbolic factorization packages were not run; only the reported SymPy probe and exact in-module reference were measured. `canonical_key` canonicalizes block permutations, player labels, and action swaps using the strongest cheap construction invariant, but it is not a general normal-form-game isomorphism solver. Most importantly, no LLM hardness claim exists until the exhausted OpenRouter key is replaced and the script returns a valid verdict.
