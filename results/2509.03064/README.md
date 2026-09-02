# Exact 3-uniform word-representation generator

This directory turns [Das and Hariharasubramanian, *Word-Representable Co-Bipartite Graphs: Vertex Ordering, Representation Number, Speed, and Entropy*](https://arxiv.org/abs/2509.03064) into a witness-search generator. A solver receives a labelled simple graph and must return a word containing each vertex exactly three times. For every pair of vertices, deleting all other symbols must leave an alternating sequence exactly when that pair is an edge. Checking a witness is an exact scan of its multiplicities and all vertex pairs.

The generator samples a uniformly shuffled balanced word **before** deriving its graph, then retains connected graphs. Thus every generated instance is satisfiable. All letters and occurrences use the same exchangeable distribution; there is no separate plant/decoy population. The shipped `easy` preset passed all local gates and held against three distinct oracle vendors.

## Why this is hard, and what was avoided

Section 2, Definitions 1–3 give the exact alternation and uniform-word definitions. Proposition 11 states that deciding whether a graph has a (k)-uniform representation is NP-complete for (3 \le k \le \lceil |V|/2\rceil); every non-demo preset uses (k=3) in this regime. The witness space at the shipped size is about (1.29\times10^{85}) balanced words before alternation constraints.

The paper's title class was deliberately **not** used. Section 3 characterizes word-representable co-bipartite graphs by an ordering, and Section 4, Theorem 20 gives an explicit algorithm constructing their 3-uniform words. That would make the suggested co-bipartite search family directly constructive. The 2-uniform regime is also avoided: Theorem 5 identifies it with non-complete circle graphs. The complete-graph `demo` is intentionally easy and exists only for the worked example and first oracle rung.

## Worked example

`make_instance(n=4, k=3, mode="demo", seed=0)` renders:

```text
Exact 3-uniform word representation

The undirected simple graph has vertices labelled 0 through 3 inclusive.
Its 6 edges are listed below, one unordered pair per line.
Pairs not listed are non-edges; the order of edges and of endpoints is irrelevant.

0 1
1 3
1 2
2 3
0 2
0 3

Find a word of exactly 12 integer symbols in which every vertex label from
0 through 3 occurs exactly 3 times. Repetitions are required, and order matters.

For two distinct labels x and y, delete every symbol other than x and y.
They alternate exactly when every consecutive pair in this length-6 subword
is different. Alternation must agree exactly with the listed edges.

Give the final comma-separated word inside <answer></answer> tags.
```

The planted answer is `<answer>2, 0, 1, 3, 2, 0, 1, 3, 2, 0, 1, 3</answer>`.

```python
>>> verify(inst, inst["answer"])
(True, "ok")
>>> verify(inst, [0, 2, 1, 3, 2, 0, 1, 3, 2, 0, 1, 3])
(False, "pair mismatch at (0,2): expected edge/alternation, but the symbols do not alternate")
```

## Difficulty presets

| Preset | Vertices | Word length | Construction | Status |
|---|---:|---:|---|---|
| `demo` | 4 | 12 | Complete graph from a repeated permutation | Rejected as hard: all three demo oracles solved it |
| `easy` | 24 | 72 | Connected graph from a random balanced word | **Shipping; hardened** |
| `medium` | 64 | 192 | Same distribution | Available; oracle loop stopped earlier |
| `hard` | 128 | 384 | Same distribution | Available; oracle loop stopped earlier |

`escalate()` doubles the vertex count, switches to the connected random distribution, and stops beyond 512 vertices.

## Gate results at shipping difficulty

| Gate | Result |
|---|---|
| G1 planted verifies | 16/16 preset–seed combinations |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round trip | 72/72 symbols recovered from prose/fences |
| G4 structured guessing | 0/200,000 uniformly sampled balanced words |
| G5 exact sparsity | 24/369,600 on complete (K_4), fraction (6.49\times10^{-5}) |
| G6 outlier attack | 0/8; best candidates still had 71–104 pair errors |
| G6 insertion greedy | 0/8; 11–22 pair errors |
| G6 random-restart local swaps | 0/8; 28–39 pair errors |
| G7 scale | 24 to 48 vertices; doubled plant verifies and remains connected |
| G8 canonical key | 80/80 invariant, 80/80 carried witnesses valid, 20/20 unrelated keys distinct |

Full per-seed data is in [`selftest_report.json`](selftest_report.json).

## Oracle hardening loop

The script used master seed `16877338269413027520`, medium reasoning effort, and stopped with `verdict: hardened` at `easy`.

| Preset | Model | Seed | Outcome | Why |
|---|---|---:|---|---|
| demo | GPT-5.6 Terra | 1231579728 | solved | Witness verified |
| demo | Grok 4.6 | 325869853 | solved | Witness verified |
| demo | Claude Sonnet 5 | 1081766768 | solved | Witness verified |
| easy | Grok 4.6 | 295362015 | error | 900 s hard deadline; not scored |
| easy | Grok 4.6 | 1872927205 | error | 900 s hard deadline; not scored |
| easy | Grok 4.6 | 1011726790 | error | 900 s hard deadline; not scored |
| easy | Gemini 3.1 Pro Preview | 205921153 | failed | Parsed word had a pair mismatch |
| easy | Claude Sonnet 5 | 736983194 | failed | Used the 32k-token budget in reasoning and emitted no answer |
| easy | GPT-5.6 Terra | 496284045 | failed | Parsed word had a pair mismatch |

The script-owned [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl) contains replies, timings, parse outcomes, and exact verifier reasons. Deadline errors were redrawn and were not counted as model failures.

## Use

```python
import random
import gen_2509_03064 as gen

inst = gen.make_instance(seed=42, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2509.03064 20
```

Run the local gates with `python3 results/2509.03064/gen_2509_03064.py`.

## Caveats

NP-completeness is a worst-case statement, not a proof that this planted distribution is hard. The oracle and attack results are empirical. The 0/200,000 guess result is the observed rate under a **uniform balanced-word prior**; it does not establish a statistical upper bound below (10^{-6}), and it does not model an informed solver. Cyclic rotations and reversal preserve a representation, so the reported naive balanced space overcounts essentially equivalent witnesses; other representations may also exist.

Only degree/spacing reconstruction, sampled insertion greedy, and bounded local-swap restarts were tried. No SAT/constraint-programming encoding, exact branch-and-bound search, genetic search, or large restart budget was benchmarked. Claude's oracle failure was length-limited rather than an incorrect emitted witness, which is weaker evidence than the Gemini and GPT verifier failures.

The canonical key is a deterministic 1-dimensional Weisfeiler–Leman refinement trace plus final colour-quotient edge counts. It is proven invariant here under arbitrary vertex relabelling, edge ordering, endpoint reversal, and their compositions, but it is not a complete graph-isomorphism canonical form; rare non-isomorphic colour-refinement collisions can be over-collapsed. Instances become easy if they are complete, fall into a known constructive subclass such as the ordered co-bipartite class of Section 4, or admit exploitable component structure; random presets therefore require connectedness.
