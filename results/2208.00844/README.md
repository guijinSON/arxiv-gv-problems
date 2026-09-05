# 2208.00844 — structured dense quadratic systems over a prime field

| profile field | value |
|---|---|
| hardness track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | linear algebra |
| certificate form | integer tuple (a native finite-field point) |
| intended intuition | change of variables: recognize the Walsh–Hadamard basis on equations |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

This generator is based on [Hauke, Lamster, Lüftenegger, and Rechberger, *A Signature-Based Gröbner Basis Algorithm with Tail-Reduced Reductors (M5GB)*](https://arxiv.org/abs/2208.00844). It hands the solver the paper's own kind of object: a dense, overdefined quadratic system over a finite field. The solver must return one common zero. `verify` substitutes the proposed point into every displayed polynomial and compares exact residues; it does not read the planted answer.

Generation is inverse. A pairwise-distinct root is sampled first. Independent homogeneous quadratic parts are sampled and their constants are set to make them vanish at that root; coordinate equations force the root to be unique, and an invertible Walsh–Hadamard transform mixes all equations. Finally, each equation receives an independent nonzero scaling. No Gröbner basis or root finder is run to obtain the certificate. Both transformations preserve the common-zero set.

## Why this is Track B

Track A would be false. Section 2 describes Gröbner and signature reductions, its cited S-pair criterion explains correctness, and Theorem 2 proves that M5GB's `Reduce` routine terminates with a Sig-normal form. Section 4.2 evaluates dense quadratic systems over \(\mathbb F_{101}\), normally with \(M=2N\), and Section 4.3 says both tested implementations' cost roughly doubles per added variable. The source data report about 918 million M5GB reduction steps at \(N=16\) on the paper's generic benchmark distribution.

This generated distribution has an even stronger specialist attack, and the claim discloses it: degree-2 Macaulay preprocessing row-reduces the quadratic coefficient matrix, exposes the hidden linear equations, and solves them. Its complexity is \(O(M^2(\binom{N+1}{2}+N))\); at the shipping preset it averages 133,601 modular operations and 0.062 seconds in the eight-seed panel. Once the normalizing column and Walsh character basis are recognized, the compact route normalizes 32 constants, identifies the fifteen character slots, applies a length-32 fast transform, and reads the coordinate equations: 297 field operations. The benchmark tests recognition of that basis, not computational intractability.

The paper also identifies regimes to avoid. Section 4.3 reports that M5GB often trails SB on canonical systems such as `katsura`, `eco`, and `cyclic`; tail-reduced reductors pay off mainly when they are reused. It reports an advantage for sufficiently overdefined dense systems, empirically once \(M\ge 1.8N\). The generator therefore stays dense and uses at least \(2N\) equations. Its additional Walsh structure is why the actual reference attack above, rather than the paper's generic runtime, is the operative hardness baseline.

## Worked demo

The `demo` preset is hand-solvable. Here is the complete seed-0 instance:

```text
Find a common zero over F_101 in variables x0,x1. Each row is
label | constant | coefficients of x0,x1 | coefficients of x0^2,x0*x1,x1^2.

2 | 17 | 81 64 | 18 95 98
3 | 85 | 15 48 | 37 12 41
0 | 64 | 76 80 | 28 58 29
1 | 59 | 61 74 | 65 32 42
```

The answer is `<answer>[49, 97]</answer>`. `verify(inst, [49, 97])` returns `(True, "ok")`; swapping the coordinates returns `(False, "equation 0 evaluates to nonzero residue 19")`. On paper, divide each row by its `x0*x0` coefficient, reorder by the two-bit label, apply the four-point Walsh transform, and solve the two exposed linear equations.

## Difficulty presets

| preset | variables \(N\) | equations \(M\) | field | status |
|---|---:|---:|---:|---|
| demo | 2 | 4 | 101 | hand-scale illustration |
| easy | 15 | 32 | 101 | shipping preset |
| medium | 15 | 32 | 211 | fixed-length escalation |
| hard | 15 | 32 | 431 | fixed-length escalation |

`escalate` continues by increasing the prime while keeping the fifteen-coordinate witness fixed. Its bounded language includes a sequence of known Mersenne primes through \(2^{127}-1\); the next listed known Mersenne prime would push fifteen serialized coordinates past the answer cap, at which point it returns `cap_bound`. A separate G7 check doubles the variable count to 30 and still builds and verifies.

## Gate results

| gate | result at shipping preset |
|---|---|
| G1 planted verifies | 12/12 across every preset and three seeds |
| G2 corruption | empty, dropped, swapped, duplicated, and out-of-range answers all rejected with distinct reasons |
| G3 round trip | tagged JSON recovered through prose and a Markdown fence |
| G4 structure-aware guessing | 0/200,000; candidate space is \(101\cdot100\cdots87\) |
| G5 density and baseline | 0/200,000 sampled shipping density; demo has exactly 1 solution; reference elimination 132,895 operations on the measurement seed |
| G6 attacks | 0/8 for each of four attacks; disclosed reference algorithm solves 8/8 |
| G7 scaling | \(N=30,M=64\) verifies; fixed-witness prime escalation verifies |
| G8 canonicalization | 20/20 composed variable permutations, row reorderings, and row rescalings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9 size/effort | 15 coordinates, at most 18 serialized tokens; 297 intended field operations |

The four failing attacks are a per-coordinate single-row ratio/outlier guess, greedy row-wise linearization after using the anchor normalizer, 256 structure-aware random restarts, and the in-context attempt to find a pair of displayed equations whose quadratic parts cancel. Every displayed row is a global mix, so neither a single normalized row nor a pair exposes a coordinate equation. The separate degree-2 elimination is expected to solve and is recorded under `reference_algorithm`, as Track B requires.

## Oracle loop and G9 diagnostic

The required harness was invoked, but the shared OpenRouter credential returned account-wide HTTP 403 `Key limit exceeded` before any model produced an answer. Those errors are preserved by `harden.py` and are not counted as model failures. The run must be repeated when the credential is funded; until then there is no external hardness verdict.

| arm | solved / valid attempts | status |
|---|---:|---|
| bare | 0 / 0 | infrastructure blocked |
| structural hint | 0 / 0 | infrastructure blocked |
| placebo hint | 0 / 0 | infrastructure blocked |

The hinted-minus-placebo difference is therefore undefined rather than evidence. The measured shipping answer has 15 atoms, 59 JSON characters, and about 15 tokens; the declared worst-case bound is 18 tokens. The intended route uses 297 exact field operations, below the 300-operation cap, and `selftest` independently executes that route and verifies its result.

## Use

From this directory:

```python
import gen_2208_00844 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 2208.00844 20
```

## Caveats

- This is deliberately not a complexity-hard distribution. Exact row elimination solves every instance, and any solver that recognizes Walsh characters can use the intended shortcut. The benchmark is only defensible as Track B.
- `P(guess)` samples uniformly from pairwise-distinct residue vectors, incorporating the answer-format constraint. It establishes resistance to that prior, not resistance to algebraic inference.
- The attack panel does not include a full M5GB, F4/F5 implementation, XL at degrees above two, SAT/SMT bit-blasting, or a learned pattern detector. Degree-2 Macaulay elimination is stronger for this construction and is measured explicitly, but optimized implementations could be much faster than this Python reference.
- The canonical key exactly handles the tested row reorderings/rescalings and generic variable permutations by coefficient refinement. Highly symmetric adversarial instances could tie the variable-refinement signatures and are not exhaustively canonically labelled; random dense instances made all 20 tested keys unambiguous.
- `gvlib` is not used: its polynomial helpers are over \(\mathbb Q\), while this family requires modular arithmetic over a prime field. The module remains standard-library-only.
- The external oracle and G9 conclusions remain unmeasured while OpenRouter returns 403. The preserved error transcript is infrastructure evidence, not hardness evidence.
