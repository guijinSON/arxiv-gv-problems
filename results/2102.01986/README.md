# Exact-value labelled-cycle generator

This module turns Gollin, Hendrey, Kawarabayashi, Kwon, and Oum's [*A unified half-integral Erdős–Pósa theorem for cycles in graphs labelled by multiple abelian groups*](https://arxiv.org/abs/2102.01986) into a witness-search problem. The solver receives a simple undirected graph whose edges are labelled in `Z/(2^b)` and must return one simple cycle of a stated length whose edge-label sum is a stated residue. Verification only checks distinct IDs, graph edges, length, and a modular sum.

## Why this is the paper's problem, and why it is hard

Section 2.4 fixes the important convention: labels are on undirected edges and a cycle's value is their unoriented sum. Corollary 1.4 explicitly covers cycles of one specified value in a finite abelian group; the extra exact-length condition is another labelled-cycle property discussed in Section 1. Every long cycle in this generator chooses one of two paths through each of `n` diamonds. After subtracting one baseline branch, the requested cycle is exactly a modular subset-sum witness.

The worst-case format is NP-hard by a direct reduction from SUBSET SUM: give stage `i` branch totals `0` and `a_i`, choose a power-of-two modulus larger than `sum(a_i)`, and request residue `T`. Verification remains linear. In shipped instances the modulus has `n` bits, so the obvious residue dynamic program has `2^n` states and meet-in-the-middle has `2^(n/2)` states.

The paper itself is structural, not a complexity paper, and proves no average-case hardness. Theorem 1.1 has bounded `m` and bounded forbidden-set size `omega`; an exact target forbids every other residue, so here `m=1` but `omega=2^b-1` grows. This avoids Section 7's small-forbidden-set choice argument (Lemma 7.4 and Corollary 7.5), but it also means there is no uniform Erdős–Pósa bound from the main theorem for this sequence. A fixed `b` would make residue DP polynomial in `n`, so the generator never keeps `b` fixed while increasing `n`.

The plant is sampled before the graph labels. All four labels in every diamond are independent uniform residues, and selected and unselected branches therefore have the same distribution. Vertex IDs, edge order/orientation, and cycle presentation are shuffled.

## Worked example

For `make_instance(n=3, seed=7, min_bits=8)`, `render` gives the following complete instance:

```text
Exact-value cycle in an edge-labelled graph

The graph is finite, undirected, and simple.  Its vertices are the integers
0 through 12.  Every edge has a label in the cyclic
additive group Z/256Z.  The value of a cycle is the sum of the
labels of all its edges, reduced modulo 256; edge traversal
direction does not change a label.

A simple cycle uses distinct vertices and returns from its last listed vertex
to its first.  Find any simple cycle containing exactly
7 distinct vertices whose value is exactly
65 modulo 256.

There are 16 edges.  Each following line is
"endpoint endpoint label".  Endpoints are 0-based.  Edge order and endpoint
order carry no meaning.

0 5 214
4 7 24
12 0 222
6 2 19
12 9 35
8 12 109
3 10 248
6 12 44
10 4 63
7 2 37
11 4 217
1 4 48
4 5 46
1 2 187
2 8 29
5 9 123

Represent the cycle as a JSON array of exactly 7
distinct vertex IDs in cyclic order.  Do not repeat the first vertex at the
end.  Any starting vertex and either direction are allowed; repeats are not.

Give your final answer inside <answer></answer> tags, as one JSON array of
integers.
Example: <answer>[3, 17, 42]</answer>
Output nothing else inside the tags.
```

The planted witness is `[12, 9, 5, 4, 1, 2, 8]`:

```python
verify(inst, [12, 9, 5, 4, 1, 2, 8])
# (True, "ok")
verify(inst, [12, 9, 5, 4, 1, 2])
# (False, "cycle must list exactly 7 vertices")
```

## Difficulty presets

| preset | stages `n` | modulus bits | structural choices | status |
|---|---:|---:|---:|---|
| `standard` | 96 | 96 | `2^96` | **ships; oracle held** |
| `hard` | 128 | 128 | `2^128` | available; oracle not needed |
| `extreme` | 160 | 160 | `2^160` | available; oracle not needed |

An earlier candidate at `n=64`, 48 modulus bits held against a preliminary three-vendor oracle run but was rejected afterward: a four-list generalized-birthday attack solved 8/8 seeds in roughly 0.2 seconds each. It is deliberately absent from `DIFFICULTY`. `SHIPPING_DIFFICULTY` is the revised density-one `standard` preset.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified (3 presets × 4 seeds) |
| G2 | empty, dropped, duplicated, out-of-range, and swapped corruptions all rejected with 5 distinct reasons |
| G3 | 193-vertex tagged JSON witness recovered from prose and a Markdown fence |
| G4 | 0/200,000 hits under a uniform prior over all `2^96` structurally possible long cycles |
| G5 | exactly 1/1,048,576 structural cycles valid for each of seeds 2, 3, and 5 at `n=20` |
| G6 | numeric-outlier 0/8; residual-greedy 0/8; one-flip restart 0/8; capped four-list birthday 0/8. The rejected `n=64,b=48` calibration was birthday-solved 8/8 |
| G7 | doubling `n` from 96 to 192 raises modulus bits from 96 to 192; the plant still verifies |
| G8 | 80/80 invariant keys, 80/80 carried witnesses verified, and 20/20 unrelated keys distinct |

The complete machine-readable measurements are in `selftest_report.json`.

## Oracle hardening loop

| preset | seed | model | solved? | recorded reason |
|---|---:|---|---|---|
| standard | 59855215 | Google Gemini 3.1 Pro Preview | no | parsed list had the wrong length |
| standard | 1122475016 | xAI Grok 4.6 | no | valid-shaped cycle had the wrong modular value |
| standard | 691743716 | OpenAI GPT-5.6 Terra | no | valid-shaped cycle had the wrong modular value |

The script verdict was `hardened`, with zero escalations. The untouched evidence is in `llm_loop_transcript.jsonl` and `.meta.json`.

## Use

```python
import random
import gen_2102_01986 as gen

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer("<answer>[0, 1, 2]</answer>")
ok, reason = gen.verify(inst, candidate)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit a corpus with:

```bash
bash scripts/emit.sh 2102.01986 20 standard
```

Run the gates directly with `python3 results/2102.01986/gen_2102_01986.py`.

## Caveats

The NP-hardness reduction is worst-case evidence, not proof that this planted random distribution is average-case hard. G4's `0/200000` is empirical for the honest structural prior—uniform branch choices—and says nothing about a solver using full meet-in-the-middle, lattice reduction, SAT/SMT, or an uncapped specialized modular-subset-sum algorithm. Those expensive attacks were not run. The adversary panel covers a numeric per-branch outlier, deterministic residual greedy, 64 × 256 one-flip local search, and a four-list birthday attack capped at 16,384 sampled subsets per list on each of eight seeds. The uncapped four-list attack is exactly what killed the smaller calibration preset.

The graph intentionally exposes its diamond decomposition; secrecy of the reduction is not part of the hardness claim. Smaller `n`, a fixed or small modulus, correlated branch labels, or a target with a planted numerical signature would make the family easier. The two pendant marker paths are structurally obvious but lie on no cycle and carry no information about which branch was planted. `canonical_key` is exact for the generated topology and the tested vertex, input-order, branch-swap, and affine label symmetries; it is not offered as a general graph-isomorphism canonicalizer.
