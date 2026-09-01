# Rejected: arXiv 2604.05459

Paper: [There are infinitely many Hilbert cubes of dimension 3 in the set of squares](https://arxiv.org/abs/2604.05459), Andrew Bremner, Christian Elsholtz, and Maciej Ulas.

## Decision

No problem generator is shipped because no problem family native to this paper satisfies G, H, and V simultaneously. The prior-triage proposal—sample parameters from the paper's construction and ask for a dimension-3 Hilbert cube—passes generation and verification but fails hardness.

| Candidate task | G | H | V | Reason |
|---|---:|---:|---:|---|
| Find positive `a0,a1,a2,a3` whose eight subset sums are squares | yes | **no** | yes | Section 4.1, especially equation (6) and the one-parameter specialization in the proof of Theorem 1.5, explicitly constructs such witnesses by polynomial evaluation. Increasing the integers' bit length only increases arithmetic cost; it does not create a search problem. |
| Complete fixed `a0,a1` to a dimension-3 cube | possible on planted inputs | **no defensible hardness regime** | yes | Lemma 3.1 and Algorithm 1 in Section 3 reduce every completion to divisor pairs of `a1` and give an exhaustive algorithm. A generator based on the Section 4.1 parametrization would also imprint the same formulas it asks a solver to recover. The paper proves no computational-hardness result for this inversion problem. |
| Find a reduced cube for an arbitrary fixed square `a0=n^2` | **no** | unknown | yes | Section 7 states this only as a conjecture. Without reducedness there is the immediate scaled witness `H(n^2;528n^2,840n^2,840n^2)`, so that version also fails H. |
| Find a dimension-4 cube in the squares | **no** | plausibly hard/open | yes | Question 1.2 and Section 7 say that no such cube is known. The paper constructs only partial “pseudo-4-cubes,” so answer-first generation is unavailable. |

## Exact definition checked

The paper defines

`H(a0; a1,...,ad) = {a0 + sum(e_i*a_i) : e_i in {0,1}}`.

For the main regime, `d=3`, all `a_i` are taken positive, and a cube is *reduced* when `gcd(a0,a1,a2,a3)=1`. Membership in the squares is cheaply and exactly verifiable by enumerating the eight choices of the three binary coefficients and applying an integer-square test.

## Why the triage hypothesis fails

Theorem 1.5 is an existence/counting theorem (`H_3(N) >> N^(1/8)`), not a search-hardness theorem. Its proof specializes the full parametrization to explicit polynomials `a0(t),...,a3(t)` that are positive for every integer `t >= 7`. Thus the proposed generator would expose a family for which the paper itself supplies a closed-form witness manufacturer—the disqualifier in gate H.

The obvious route to a harder regime is dimension 4, but the paper explicitly reports that the authors were unable to find a dimension-4 cube. That regime therefore cannot be inverse-generated and fails gate G.

## Artifacts intentionally not created

Per Step 0 of the task, rejection ends the run before implementation and hardening. Consequently there is no `gen_2604_05459.py`, `selftest_report.json`, or `llm_loop_transcript.jsonl`. The pre-existing run-level `.meta.json` was left untouched; it contains no fabricated hardening verdict. Creating the other artifacts would falsely imply that the mandatory gates or oracle loop had run.
