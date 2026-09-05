# arXiv 2407.19344 — verified king-box domination signatures

Status: the generator and every local gate pass, but the required cross-vendor oracle run is **not complete**. Two valid bare/easy calls both solved their instances; OpenRouter then returned HTTP 403 `Key limit exceeded (total limit)` in the third slot, before the harness could escalate. The script-written transcript is retained. This is neither a hardened verdict nor a `too_easy` verdict, and the result must not be submitted until the bare loop and both diagnostic arms are rerun with working quota.

## Profile

| field | value |
|---|---|
| track | B — no-tool compression |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | polynomial |
| native objects | free-boundary multidimensional king graphs; domination polynomials |
| intended intuition | invariant: side-two blocks pair dominating sets of opposite parity |
| domain essentiality | native |
| reduction | none |

## The problem and why the checker is trustworthy

This family comes from Moore and Mertens, [*Domination by kings is oddly even*](https://arxiv.org/abs/2407.19344). An instance gives an ordered batch of dimension vectors. Each vector defines a free-boundary multidimensional king graph. For every graph, the solver must find its domination-polynomial value at `z=-1`; those signs become the coefficients of one exact univariate signature polynomial.

Section 1 defines a dominating set and the king graph. Section 2, Theorem 1 proves the two-dimensional result by a sign-reversing involution. Section 4, Theorem 2 proves for side lengths `L_i` that

`D_K(-1) = (-1)^(product_i ceil(L_i/2))`.

`make_instance` applies this theorem directly; it never searches the graph it created. `verify` independently reduces every side modulo 4 and compares every submitted coefficient exactly. It does not read `inst["answer"]`. A candidate is valid exactly when it has one `±1` coefficient at every exponent, the promised sign balance, and all theorem evaluations agree.

## Why this is Track B

The efficient reference algorithm is Theorem 2's formula. It takes `O(n*d)` exact operations. At the hard preset it uses about 240 modular/Boolean steps; the recorded 1,000-repeat benchmark averaged 0.000050 seconds per evaluation and solved 8/8 instances, as expected. This algorithm is deliberately reported under `reference_algorithm`, not disguised as a failed attack.

The mechanical alternative is literal exact domination-polynomial enumeration: visit the `2^N` vertex subsets, test domination, and add their signs. On the fixed shipping seed used by `selftest`, even the smallest of the 48 boxes has `N=43,378,319,368,944` vertices, so this route begins at `2^43,378,319,368,944` subset visits. The compact route is short only after noticing the side-two cancellation invariant; the rendered task does not give the formula. Thus the benchmark tests discovery of the compression, not computational complexity of the restricted instances.

The paper itself identifies the boundaries of this route. Section 3 shows that cylinders and tori do not obey the `±1` formula because the free-boundary scan has no first block. Section 5 says values at general real or complex `z` remain open. The generator therefore uses only free boundaries and only `z=-1`.

Batching is necessary and explicit: one native evaluation has only two possible answers and fails guess resistance. The polynomial combines 48 independent native evaluations while keeping the intended route below the 300-operation and output-size caps.

## Worked demo

For `make_instance(seed=7, n=4, dimensions=2, side_min=1, side_max=3)`, the complete rendered instance is:

```text
KING-BOX DOMINATION SIGNATURE

For a positive integer L, write [L]={1,2,...,L}.  A d-dimensional
free-boundary king graph K(L1,...,Ld) has vertex set
[L1] x ... x [Ld].  Two distinct vertices u and v are adjacent exactly
when max_i |u_i-v_i| = 1.  There is no wrap-around at a boundary.

A set S of vertices is dominating when every vertex is either in S or
adjacent to a vertex in S.  Its domination polynomial is
D_K(z) = sum z^|S|, summed once over every dominating set S.

Below are 4 ordered 2-dimensional boxes.
For box j (0-indexed), let c_j = D_K(-1).  Every c_j is promised to be
exactly -1 or +1, and exactly half of the c_j values are -1.
Return the exact polynomial Q(x)=sum_j c_j*x^j.

BOXES (j: [L1,...,Ld]):
0: [3,1]
1: [1,3]
2: [2,1]
3: [2,1]

Represent Q as a JSON list of terms [coefficient,[exponent]]. Include
every exponent 0 through n-1 exactly once; term order does not matter.
Coefficients must be JSON integers -1 or 1. Repeats are not allowed.

Give your final answer inside <answer></answer> tags in that exact JSON format.
Example: <answer>[[-1,[0]],[1,[1]]]</answer>
Output nothing else inside the tags.
```

The answer is `[[1,[0]],[1,[1]],[-1,[2]],[-1,[3]]]`. The exact calls are:

```python
verify(inst, inst["answer"])
# (True, "ok")

verify(inst, [[-1,[0]],[1,[1]],[1,[2]],[-1,[3]]])
# (False, "coefficient mismatch at exponent 0")
```

A person can solve this demo on paper: the largest graph has only three vertices, so its dominating sets can be listed directly. The side-two invariant is quicker but not required.

## Difficulty presets

| preset | boxes `n` | dimensions `d` | side range | structure-aware candidates | compact operations | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 4 | 2 | 1–3 | 6 | 12 | hand-scale, not hardened |
| easy | 24 | 2 | 20–99 | 2,704,156 | 72 | 2/2 completed calls solved; third slot blocked by quota |
| medium | 36 | 3 | 50–999 | 9,075,135,300 | 144 | not reached |
| hard | 48 | 4 | 1,000–9,999 | 32,247,603,683,100 | 240 | provisional shipping preset; local gates pass |

`escalate` first raises `d` to 5 at fixed answer length (288 compact operations), then raises `n` from 48 to 50 (300 operations). It stops there because every remaining meaningful size axis would exceed the no-tool effort cap.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 20/20 preset–seed constructions verify and JSON-round-trip; 13/13 tiny boxes match independent exhaustive enumeration |
| G2 | pass | 5/5 corruption classes rejected with 5 distinct reasons |
| G3 | pass | tagged prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 balanced guesses; exact unique-witness probability `1/32,247,603,683,100` |
| G5 | pass | demo exact count 1/6; shipping density 0/200,000; strongest failing attack ran 8,192 restarts in 0.71 s |
| G6 | pass | 0/8 successes for each of five attacks; theorem reference algorithm solves 8/8 in about 0.000050 s each |
| G7 | pass | doubled `n=96` builds and verifies; candidate space grows to 6,435,067,013,866,298,908,421,603,100 |
| G8 | pass | 60/60 invariance and preservation checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 447 chars, about 112 tokens, 96 atomic elements, 240 intended operations |

The exact timings are machine-load sensitive; `selftest_report.json` is authoritative for this run.

## Oracle loop and G9 diagnostics

The latest bare run completed two valid easy-preset calls, and both solvers returned verified polynomials. The third required slot hit the account-level HTTP 403; its four retries are errors, do not consume an attempt, and cannot be counted as a model failure. Because the harness aborted before finishing the easy level, it produced no verdict and never reached medium or hard. The earlier isolated G9 runs also contain only quota errors.

| run | preset | seed | model | solved | why |
|---|---|---:|---|---|---|
| bare | easy | 253,023,423 | GPT-5.6 Terra | yes | parsed and verified `ok` |
| bare | easy | 2,063,521,126 | Gemini 3.8 Flash | yes | parsed and verified `ok` |
| bare | easy | 1,960,207,309 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| bare | easy | 904,964,645 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| bare | easy | 1,704,343,639 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| bare | easy | 1,493,664,200 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| structural hint | hard | 90,028,508 | Gemini 3.1 Pro Preview | error | HTTP 403 key limit |
| structural hint | hard | 1,604,622,910 | Gemini 3.1 Pro Preview | error | HTTP 403 key limit |
| structural hint | hard | 1,395,920,230 | Gemini 3.1 Pro Preview | error | HTTP 403 key limit |
| structural hint | hard | 479,601,292 | Grok 4.6 | error | HTTP 403 key limit |
| placebo hint | hard | 879,839,276 | GPT-5.6 Terra | error | HTTP 403 key limit |
| placebo hint | hard | 819,602,071 | GPT-5.6 Terra | error | HTTP 403 key limit |
| placebo hint | hard | 93,021,339 | GPT-5.6 Terra | error | HTTP 403 key limit |
| placebo hint | hard | 753,193,794 | Claude Sonnet 5 | error | HTTP 403 key limit |

| G9 arm | solved/valid attempts | diagnostic verdict |
|---|---:|---|
| bare at shipping preset | 0/0 | unavailable; bare run stopped at easy |
| structural hint | 0/0 | unavailable |
| placebo hint | 0/0 | unavailable |

The hinted-minus-placebo value is therefore undefined, not evidence of zero effect. The structural diagnostic asks the solver to focus on parity of the side-two block count; the placebo only asks for careful indexing. The two successful easy calls show that the initial rung is too easy, but the harness—not this README—must decide whether a later rung holds. All three runs must be completed after OpenRouter access is restored.

## Use

```python
import random
import gen_2407_19344 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 32_247_603_683_100
_ = g.random_candidate(inst, random.Random(9))
```

From the repository root, after a successful hardening rerun:

```bash
python3 results/2407.19344/gen_2407_19344.py
python3 scripts/harden.py results/2407.19344/gen_2407_19344.py
bash scripts/emit.sh 2407.19344 20
```

## Caveats

- This is not a Track A complexity claim. Anyone who recalls or rediscovers Theorem 2 solves it quickly; that is the intended compact route.
- Batching amplifies a two-valued native quantity into a writable polynomial certificate. It preserves the paper's objects but tests repeated application of one insight after discovery.
- The `0/200,000` estimate samples uniformly from the promised balanced-sign language. It says nothing about a theorem-aware or residue-aware solver, and the exact uniqueness calculation is the stronger statement about blind guessing.
- The attack panel tried coordinate-sum and volume outliers, odd-side and XOR ansätze, and 1,024 balanced restarts on each of eight seeds. It did not implement transfer-matrix, BDD/ZDD, SAT, or specialized `#SAT` enumeration; those would still be mechanically irrelevant at the displayed volumes, while the paper formula is separately timed as the successful reference algorithm.
- The brute-force figure is a mathematical subset-count lower bound, not a completed timing experiment; running that enumeration is impossible at shipping scale.
- `canonical_key` quotients axis permutations and box reorderings, which are the relevant presented symmetries. It does not attempt general graph isomorphism on arbitrary graphs; the shipping boxes have all side lengths greater than one.
- Most importantly, STEP 4 and the three-arm G9 diagnostic remain blocked by the exhausted OpenRouter key. Local correctness is verified, but no claim that the four-vendor pool failed to solve this family is currently justified.
