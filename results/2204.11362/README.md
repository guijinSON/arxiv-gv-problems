# Error-correcting identifying-code generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT (a 3-XOR source compiled through the paper's 3SAT reduction) |
| Certificate form | integer tuple / Boolean detector choices, written as a fixed-width hexadecimal mask |
| Intended intuition | reduction recognition: recover the hidden cycle in the parity-block hypergraph |
| Domain essentiality | licensed reduction |
| Reduction | Section 3, Theorem 3.1; paper-central 3SAT-to-ERR-IC gadgets |

## What the problem is and why it is trustworthy

[Jean and Seo, *Error-correcting Identifying Codes* (arXiv:2204.11362)](https://arxiv.org/abs/2204.11362) define a detector set `S` by two exact local conditions: every closed neighborhood contains at least three detectors, and the detector-neighborhoods of every two vertices have symmetric difference at least three (Theorem 2.1). A solver receives the paper's ten-vertex variable gadgets and eight-vertex clause gadgets, represented without loss by parity blocks whose four-clause 3CNF expansion is stated in the prompt. It must return one `T_i`/`F_i` choice per variable; all gadget-forced detectors are implicit in the hexadecimal notation.

Generation is inverse: a uniformly random assignment is sampled first, a randomly relabelled cyclic system `x_i XOR x_(i+1) XOR x_(i+2) = b_i` is evaluated on it, and each parity equation is expanded into four clauses before applying Theorem 3.1. No search or elimination occurs in `make_instance`. `verify` does not read `inst["answer"]`: it checks every parity block, expands the exact graph, checks the represented set has size `9N+8M`, and recomputes all 3-domination and 3-distinguishing conditions with integer bitsets.

## Why Track B, not Track A

Theorem 3.1 proves minimum ERR-IC NP-complete on arbitrary graphs, but that worst-case statement does **not** establish hardness for this structured distribution. Moreover, Theorem 2.3 makes mere ERR-IC existence polynomially recognizable—the full vertex set is a code whenever four elementary conditions hold—so existence was deliberately not used.

An efficient algorithm is known and disclosed: Gauss-Jordan elimination over GF(2) solves the exposed square parity system in `O(n^3)` scalar bit operations. Across eight shipping instances, the reference implementation solved 8/8 in a mean 0.006338 s and 661,865 counted scalar operations (595,295–762,990). The compact route is to notice that pairs repeated in two triples recover a hidden cycle; adjacent parity equations then give a step-three recurrence, which a parallel-prefix XOR executes in 108 conservatively counted exact wide-word operations. That shortcut also solved 8/8 in self-test. Without tools, however, a model still has to reconstruct a randomly relabelled 251-cycle and transcribe 251 exact output bits. This mechanical-versus-structural gap is the Track B claim.

## Worked demo

The `demo` preset with seed 7 renders the following complete instance (the repeated gadget definitions are the same at every size):

```text
Find an error-correcting identifying code in the graph defined below.

Exact ERR:IC definition.
For a vertex u, N[u] is u together with every neighbor of u. For a detector set S, write N_S[u]=N[u] intersect S.
S is an error-correcting identifying code (ERR:IC) exactly when |N_S[u]|>=3 for every vertex u and |N_S[u] symmetric-difference N_S[v]|>=3 for every two distinct vertices u,v.
The graph is simple and undirected. All indices below are zero-based.

Variable gadgets.
There are n=5 Boolean variables v0,...,v4.
For every i make ten vertices T_i,F_i,y_i,z_i,a_i,b_i,l_i,m_i,r_i,s_i and the fifteen edges
  T_i-F_i, y_i-T_i, y_i-z_i, y_i-l_i, z_i-F_i, z_i-s_i, T_i-a_i, F_i-b_i,
  a_i-b_i, l_i-m_i, r_i-s_i, l_i-a_i, m_i-b_i, a_i-r_i, b_i-s_i.

Parity blocks and clause gadgets.
A listed block (p,q,r ; h) means v_p XOR v_q XOR v_r = h over GF(2).
Expand it to the four 3CNF clauses that forbid the four assignments to (v_p,v_q,v_r) having XOR different from h.
Equivalently, for every forbidden triple (e_p,e_q,e_r), make the clause whose v_j literal is +v_j when e_j=0 and -v_j when e_j=1.
Repeat that set of four clauses exactly 'copies' times; repeated clauses create distinct gadgets.
For each resulting clause q make eight new vertices L_q,M_q,N_q,R_q,U_q,V_q,D_q,C_q and the ten internal edges
  L_q-M_q, M_q-N_q, N_q-R_q, L_q-U_q, U_q-N_q, M_q-V_q, V_q-R_q, L_q-D_q, D_q-C_q, C_q-R_q.
For each of the clause's three literals, join C_q to T_i for +v_i and to F_i for -v_i.
There are no edges except those just specified.

The 5 parity blocks are:
  P000: (1,0,4 ; 0) copies=1
  P001: (2,4,3 ; 1) copies=1
  P002: (0,2,4 ; 1) copies=1
  P003: (2,1,3 ; 1) copies=1
  P004: (1,0,3 ; 1) copies=1

Required witness.
The expansion has M=20 clause gadgets, 210 vertices, and threshold K=205.
Your answer is a fixed-width hexadecimal mask w with exactly ceil(n/4) digits and integer value below 2^n. Leading zeroes are required. Binary bit i of w (least significant bit is i=0) represents the detector set S(w): include y_i,z_i,a_i,b_i,l_i,m_i,r_i,s_i for every variable gadget; include all eight vertices of every clause gadget; and include exactly T_i if bit i=1 or F_i if bit i=0.
Thus |S(w)|=K. Find any w for which S(w) satisfies the exact ERR:IC definition above. Bits are in public order v0 through v(n-1), repeats are not allowed, and every position is required.

Give your final answer inside <answer></answer> tags as exactly ceil(n/4) lowercase hexadecimal digits, without a 0x prefix.
Example format for n=5 (bits 0,1,3 selected): <answer>0b</answer>
Output nothing else inside the tags.
```

The answer is `<answer>12</answer>`. `verify(inst, "12")` returns `(True, "ok")`; the same-shape corruption `verify(inst, "13")` returns `(False, "parity block P000 leaves one of its clause gadgets unsatisfied")`. A person can solve this demo by checking its 32 masks or by reconstructing the five-cycle.

## Difficulty presets

`copies` is the inclusive upper bound on independently sampled clause-gadget multiplicity; it changes graph crowding without changing the witness grammar.

| Preset | `n` | `copies` | Answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 5 | 1 | 5 | hand-solvable illustration; skipped by hardening |
| easy | 251 | 3 | 251 | **ships; bare oracle pool held** |
| medium | 253 | 4 | 253 | reserve escalation rung |
| hard | 254 | 5 | 254 | reserve escalation rung |

No preset was rejected. Further growth in `n` would exceed the 256-semantic-atom answer cap, so `escalate` returns `"cap_bound"` after the named ladder rather than pretending hexadecimal packing makes a longer bit vector atomic.

## Gate results

| Gate | Result at the shipping preset |
|---|---|
| G1 | 12/12 planted certificates verified across all presets |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | 63-hex-digit witness recovered from prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; bounded space `2^251` |
| G5 | sampled density 0; construction proves exactly 1 bounded-language answer; strongest failing attack was greedy bit-flip, 504,008 trial evaluations at most and 1.976980 s across 8 seeds |
| G6 | five attacks each 0/8; Gaussian reference and compact route each 8/8 as expected for Track B |
| G7 | doubled `n=502` instance built and exactly verified (`36,796` vertices for the measured seed) |
| G8 | 80/80 relabelling checks invariant; carried witness verified; 20/20 unrelated keys distinct |
| G9 | pass: hinted pool held; 65 chars, 17 estimated tokens, 251 semantic atoms, 108 intended exact operations |

## Oracle loop

The script-selected shipping level is `easy`, parameters `n=251, copies=3`. API errors are retained in the transcript but excluded from the three scored attempts.

| Preset | Seed | Model | Result | Why |
|---|---:|---|---|---|
| easy | 1186994093 | Grok 4.6 | error, unscored | 900 s total deadline |
| easy | 715041188 | Grok 4.6 redraw | failed | wrong mask; parity block P079 failed |
| easy | 2104786200 | GPT-5.6 Terra | failed | wrong mask; parity block P002 failed |
| easy | 524238033 | Gemini 3.1 Pro Preview | failed | wrong mask; parity block P000 failed |

## G9 arms

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0/3 | shipping statement held |
| structural | 0/3 | polarity-flipped G9(b) gate passed |
| placebo | 0/3 | control held |

`hinted - placebo = 0.0`. The structural sentence neither improved nor harmed observed success at this sample size, so the diagnostic does not show detectable hint benefit; importantly, it names only the repeated-triple cycle invariant and does not give the recurrence or prefix algorithm. The hinted scratch copy labelled the sole rung `hard`, but its parameters are exactly the shipping pair `n=251, copies=3`.

## How to use it

From this directory:

```python
import random
import gen_2204_11362 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
question = gen.render(inst)
candidate = gen.parse_answer("Reasoning... <answer>12</answer>")
assert gen.verify(inst, candidate) == (True, "ok")
assert gen.random_candidate(inst, random.Random(1)) is not None
```

From the repository root, emit fresh shipping instances with:

```bash
bash scripts/emit.sh 2204.11362 20 easy
```

The module is standard-library-only and performs no file I/O, network access, or import-time printing.

## Caveats

- This is a Track B benchmark. Any sandbox, SAT tool, or a few milliseconds of bit-packed Gaussian elimination makes it easy; no average-case or cryptographic hardness is claimed.
- The 0/200,000 estimate samples uniformly from the solver-aware language of exactly one optional detector per variable gadget. It does not estimate density among all subsets of the roughly 19,000 graph vertices, a space the prompt rules out for the required threshold witness.
- Random clause-gadget multiplicities diversify isomorphism classes but do not make the parity system harder; the difficulty comes from the 251-variable relabelled cycle.
- The attack panel tried incidence outliers, all-zero, greedy bit flips, 8,192 random restarts per seed, and the tempting public-order recurrence. It did not run an external SAT/ILP package; Gaussian elimination is the stronger standard attack for these exposed XOR constraints and is reported as successful.
- Coverage is of the paper's central, licensed Section 3 reduction. It does not benchmark the cubic-graph extremal constructions of Section 4.
