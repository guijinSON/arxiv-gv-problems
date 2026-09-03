# Verified zero-sum subsequence generator

This directory turns Kevin Zhao's [*On zero-sum subsequences in a finite abelian group of length not exceeding a given number*](https://arxiv.org/abs/2506.21383) into an answer-first witness-search family.

| Axis | Value |
|---|---|
| Native domain | `number_theory` |
| Computational core | `subset_sum` |
| Objects | sequence over `C_q direct-sum C_q`; index subsequence |
| Intended intuition | zero-sum modular cancellation |
| Reduction | none - the solver receives the paper's own objects |

## The problem and why it is checkable

An instance gives `n` labelled pairs modulo a public integer `q`. The solver returns a nonempty set of distinct 0-based indices, of length at most `q`, whose two coordinate sums are both `0 mod q`. Named presets always have `n < q`, so every nonempty subset has the permitted length and the real task is the simultaneous modular cancellation. Verification is exact integer addition and reduction modulo `q`; it accepts any valid subsequence, not only the planted one.

`make_instance` samples the index witness first. It then samples uniform nonzero pairs for all but one uniformly chosen planted position and fixes that final pair to make the planted sum zero. A symmetric whole-instance rejection removes zeros, duplicates, and opposite pairs, eliminating one- and two-term shortcuts without marking the planted positions.

## Hard and easy regimes

Definition 1.1 and Section 2 fix the exact sequence/subsequence language. Here `G=C_q direct-sum C_q`, so `exp(G)=q` and `D(G)=2q-1`, while the requested bound is `k=q`. This is inside the paper's studied interval `[exp(G),D(G)-1]`. Lemma 1.5 gives the rank-two identity `s_{<=q}(G)=3q-2`; our `n<q` instances lie far below that universal-existence threshold, so the theorem does not reveal a witness. The planted witness supplies satisfiability.

The underlying relation contains ordinary SUBSET SUM: for positive inputs `a_i` and target `T`, choose a modulus larger than their total and append `-T`; a nonempty zero-sum subset must include `-T` and its other terms sum to `T`. Thus binary-encoded modular zero-sum search has the usual NP-hard worst-case core. The named presets make `q` exponential in `n` and keep `log2(|G|)` just below `n`, avoiding pseudo-polynomial dynamic programming and the proven low-density regime of the classical Lagarias-Odlyzko lattice attack. This paper itself proves extremal existence results, not computational or average-case hardness; the evidence for this planted distribution is therefore the measured attack panel and oracle loop, not a theorem from the paper.

Easy cases deliberately avoided include `k>=D(G)`, which the paragraph after Definition 1.1 identifies with the ordinary Davenport constant; small/fixed cases tabulated in Lemma 1.7; lengths at or above `3q-2`, where Lemma 1.5 guarantees a short zero-sum subsequence for every input; and moduli small enough for dynamic programming over `q^2` group states.

## Worked demo

The `demo` preset with `seed=5` renders in full as:

```text
SHORT ZERO-SUM SUBSEQUENCE IN A FINITE ABELIAN GROUP

The group is C_q direct-sum C_q for q = 113.  Concretely, a group element is
an ordered pair (x,y) of integers modulo q.  Addition is coordinatewise modulo
q, and the zero element is (0,0).

Below is a sequence of 8 labelled occurrences.  Occurrences are indexed from
0 through 7, inclusively.  Equal values, if present, would still be
different occurrences; the displayed index is what an answer selects.

A subsequence here means a subset of the displayed indices: order does not
matter and an index may not be repeated.  Find a NONEMPTY subsequence of length
at most 113 whose first coordinates sum to 0 modulo 113 and whose second
coordinates also sum to 0 modulo 113.  Since 8 < 113, the numerical length
bound permits every nonempty subset, but the two exact zero-sum conditions must
still hold.

INDEX: X Y
0: 31 83
1: 6 20
2: 62 36
3: 14 47
4: 60 111
5: 31 48
6: 69 13
7: 73 31

Give your final answer inside <answer></answer> tags, as one JSON array of 1 to
8 distinct integer indices.  Indices are 0-based, order is irrelevant, and
all bounds are inclusive.
Example: <answer>[0, 3, 7]</answer>
The example shows syntax only; it is not an answer to this instance.
Output nothing else inside the tags.
```

The answer is `<answer>[2, 4, 5, 7]</answer>`: both coordinate totals are `226 = 2*113`. The exact calls are:

```python
verify(inst, [2, 4, 5, 7])
# (True, "ok")
verify(inst, [2, 4, 5])
# (False, "subsequence sum is (40,82), not (0,0) modulo 113")
```

There are only 255 nonempty candidates and exactly one solution, so this demo can be solved and exhaustively checked by hand, albeit tediously.

## Difficulty presets

The modulus is freshly sampled per seed with the displayed exact bit length; the planted weight is `n/2`.

| Preset | `n` | modulus bits | planted items | certificate space | Status |
|---|---:|---:|---:|---:|---|
| `demo` | 8 | 7 | 4 | 255 | hand-scale; not shipped |
| `easy` | 64 | 30 | 32 | `2^64-1` | **shipping; oracle held** |
| `medium` | 96 | 46 | 48 | `2^96-1` | available, not needed by oracle |
| `hard` | 128 | 62 | 64 | `2^128-1` | available, not needed by oracle |

No preset was rejected: the hardening loop stopped at `easy` because all three deciding vendors failed there.

## Gate results at the shipping preset

| Gate | Measured result |
|---|---|
| G1 planted verifies | 12/12 across four presets and three seeds |
| G2 corruption rejection | 5/5 rejected; 5 distinct reasons |
| G3 parser round-trip | 32/32 planted indices recovered from prose plus a fenced JSON answer |
| G4 structure-aware guessing | 0/200,000; observed fraction `0.0`; candidate space `2^64-1` |
| G5 density and cost | shipping density 0/200,000; demo exact count 1; strongest baseline 3.293735 s over 8 seeds and 38,217 LLL steps |
| G6 adversaries | all five attacks 0/8: centered-norm outlier, greedy, 256-restart local search, 250k-node meet-in-the-middle, and completed centered LLL |
| G7 scaling | `n=128` double-size build verified; modulus grew from 30 to 62 bits |
| G8 canonical key | 120/120 composed permutation/automorphism checks, 120/120 carried witnesses, 20/20 unrelated keys distinct |

The complete numeric record is in `selftest_report.json`.

## Oracle loop

The script-owned run used master seed `3858628248662780355`, effort `medium`, and returned `hardened` at `easy` with zero escalations.

| Model | Instance seed | Parsed | Solved | Verification result | Seconds |
|---|---:|---:|---:|---|---:|
| `openai/gpt-5.6-terra` | 1464222832 | yes | no | sum `(259217872,437336912)` mod `594512959` | 82.11 |
| `google/gemini-3.1-pro-preview` | 517099765 | yes | no | sum `(659751804,678632921)` mod `1066504627` | 18.14 |
| `x-ai/grok-4.6` | 1550365140 | yes | no | sum `(419673050,279934436)` mod `1003215907` | 400.56 |

The full replies and required schema fields are preserved in `llm_loop_transcript.jsonl`; none of these failures was a parse failure or API error.

## Use

From this directory:

```python
import random
import gen_2506_21383 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
candidate = g.parse_answer("<answer>[0, 2, 9]</answer>")
ok, reason = g.verify(inst, candidate)
```

From the repository root, emit fresh, deduplicated shipping instances with:

```bash
bash scripts/emit.sh 2506.21383 20 easy
```

## Caveats

- Worst-case NP-hardness does not prove this answer-first distribution is average-case hard. The paper supplies no such claim; the attack panel and three-model oracle run are empirical evidence only.
- `0/200,000` is the observed success fraction under a uniform prior on all nonempty subsets. It does not estimate a solver's informed prior, and it is not an exact count of shipping solutions. The exact demo count is reported separately.
- The centered Decimal LLL attack completed ordinary LLL reduction on every seed, but no BKZ, commercial lattice suite, GPU search, Wagner/dissection algorithm, or full `2^32`-per-half meet-in-the-middle was run. The bounded collision attack visited 250,000 states per seed. Highly optimized specialist code may therefore solve `easy` faster than these measurements suggest; `medium` and `hard` are provided for that reason.
- The generator knows a weight-`n/2` solution, and the LLL/local-search attacks were intentionally given that construction-specific fact even though the rendered statement does not reveal it.
- `canonical_key` is invariant under all `GL(2,Z/qZ)` coordinate changes and occurrence permutations tested, but its ideal histograms are not a complete isomorphism invariant. It may merge unrelated instances. Seed-dependent public moduli made all 20 unrelated test keys distinct; the key never hashes the seed, rendering, or answer.
- The modulus need not be prime. This is still exactly the finite abelian group `C_q direct-sum C_q` covered by the paper, and all verification uses exact arithmetic modulo the displayed `q`.
