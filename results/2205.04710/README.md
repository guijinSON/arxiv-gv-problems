# Matrix Waring witness generator (arXiv:2205.04710)

This module turns Krishna Kishore and Anupam Singh's [*Matrix Waring Problem -- II*](https://arxiv.org/abs/2205.04710) into a search task.  An instance gives a prime `p`, an exponent `k`, and a dense `2 x 2` target matrix `T` over `F_p`; the solver must return two matrices `A,B` with `A^k+B^k=T`.  Verification is exact modular matrix exponentiation, so any valid pair is accepted, not just the planted pair.

## Why this regime is hard

The definition comes from the Introduction and Section 2, and Theorem 1.1 proves universal two-summand representability for sufficiently large finite fields.  Section 3 reduces arbitrary targets to generalized Jordan blocks.  Appendix A, Proposition A.3 supplies the explicit `q>k^16` scalar bound used by the non-nilpotent construction.  Each generated prime has the certified form `p=a*2^(16n)+1`, while `k=2^n`, so `p>k^16` and `gcd(k,p-1)=k`.  A [later strengthening](https://arxiv.org/abs/2306.06588) gives the explicit universal bound `q >= (k-1)^4+6k`, which these fields also exceed.

The fixed-`k` regime is not credible as a hard generator: rational-canonical reduction plus randomized finite-field root finding turns the paper's proof into a polynomial-time search when `k` is constant.  Section 5 is even explicit for regular nilpotent blocks of size at least `2k`.  This generator instead grows `k=2^n`; the direct multiplicative-subgroup search suggested by the construction then needs about `k` trials, exponential in the encoded parameter `n`.  No polynomial-time or closed-form method is known here, but this is a practical hardness argument, not an NP-hardness theorem.

Generation is genuinely inverse: each proposal samples two independent uniform dense matrices first; a symmetric condition on their power sum accepts the pair, and their order is normalized only by the obvious `A/B` symmetry.  A Proth witness proves `p` prime exactly.  Targets are conditioned to have nonzero trace and square-free characteristic polynomial, allowing `canonical_key` to classify exactly under change of basis, transpose, and the homogeneous map `T -> c^k T`.

## Worked shipping example

This is `make_instance(n=24, seed=0)`, the smallest and shipping preset.

<details><summary>Complete rendered problem</summary>

```text
Matrix Waring witness problem over a prime field

Let F_p be the field of integers modulo the prime p=21789309426606147004390309175379418434209095816567392007375406252547884139637957468112089238951358349366065278639669249.  All additions and
multiplications below are performed modulo p, with residues represented by the
integers 0 through p-1 inclusive.

The exponent is k=16777216.  For a square matrix X, X^k means the ordinary matrix
product of exactly k copies of X; it is not entrywise exponentiation.  Matrix
row and column indices are 0-based.  Find two 2 by 2 matrices A and B over F_p
such that

    A^k + B^k = T.

The order of A and B does not matter, repeats are allowed, and every entry must
be an integer in the inclusive range 0..p-1.  The target T is given row by row:

14175138807495755884034221880567633418845132979048678330790507335443495743026879735803675340622954669762290808960210166 15405984074617134972938140494855548971110571682876800072357201239853513843914761308347499196685649453391954374791630773
8508056817680913935074623060826411737738960571156517815435848200859982190695750029309180991141995980205344963641701 12031852266003034401893839138867454833112352155151302395432530216247134506517646328088778376224707750774268493893011717

Your witness must contain exactly two matrices, each with exactly 2 rows and
2 entries per row.  Use JSON with the exact keys "A" and "B".

Give your final answer inside <answer></answer> tags, as
<answer>{"A":[[a00,a01],[a10,a11]],"B":[[b00,b01],[b10,b11]]}</answer>
with the obvious same row shape if the displayed dimension is not 2.
Example of the required syntax: <answer>{"A":[[0,0],[0,0]],"B":[[0,0],[0,0]]}</answer>
Output nothing else inside the tags.
```

</details>

The planted answer is:

```json
{"A":[[5645591862710384849770895249580774629850658484298830321019545178513459452970265044182769153851162705996489277465247072,14267494072803849501332680122019867860586196311755940554096344864054849447273139460803569548370967542215400887362208553],[10501476027534311262887849307910947725341689962669293543640764481738216985833555507161424107998759916630071362265146018,3682037476109086385592167387711213481305566684893431121476440255210951210221039634235400780433327670733186283950030028]],"B":[[11607343113075299806801070445025076371166012179313104989410901458952038887302665813783620993461446589771998949486598217,7558150639779647083211095027468045290280514803905172457005949741429671031180984323950219755314347842874246484422479109],[6063053459690534831793992601795686296223704237361825393053061136098292195325330524591384378895996946347964939738603868,16940883299741363096715775285104965783975885186214437439591159371503942526499417785239148253180226802242347906680650320]]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Replacing `A[0][0]` by `p` returns `(False, "A[0][0] is outside the inclusive range 0..p-1")`.

## Difficulty presets

| Preset | `n` | `k` | Approx. field bits | Status |
|---|---:|---:|---:|---|
| `hard` | 24 | 16,777,216 | 394 | **ships; oracle held** |
| `harder` | 28 | 268,435,456 | 453 | available, not needed |
| `extreme` | 32 | 4,294,967,296 | 520 | available, not needed |

`escalate()` adds four to `n`, multiplying the obvious subgroup-search cost by 16.  No preset was rejected by a local gate.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 9/9 planted witnesses verified (3 presets x 3 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | prose + Markdown + tagged JSON round-tripped |
| G4 | 0/200,000 uniform dense unordered guesses; ordered naive space has 947 decimal digits |
| G5 | 400/160,801 exact scalar-control candidates valid (`0.0024875`) |
| G6 | magnitude split 0/8; greedy 0/8; 128 trace restarts on each of 8 seeds, 0 precursor hits |
| G7 | doubled `n=48` built and verified; field grew from 394 to 774 bits |
| G8 | 160/160 invariant transformations and witness maps, including composed power-scalings; 20/20 unrelated keys distinct |

## Oracle loop

All calls used reasoning effort `medium`; every response parsed, so none of these failures is a parser artifact.

| Preset | Model | Seed | Result | Why |
|---|---|---:|---|---|
| `hard` | `x-ai/grok-4.6` | 1871878543 | failed | returned zero matrices; trace mismatch |
| `hard` | `google/gemini-3.1-pro-preview` | 1327122241 | failed | parsed square-root strategy candidate; trace mismatch |
| `hard` | `anthropic/claude-sonnet-5` | 323788651 | failed | parsed successive-root strategy candidate; trace mismatch |

Verdict: `hardened`, zero escalations.  Full replies and timings are in `llm_loop_transcript.jsonl`.

## Use

```python
import gen_2205_04710 as gen

inst = gen.make_instance(**gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY], seed=123)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2205.04710 20 hard
```

## Caveats

- The paper proves representability, not computational hardness.  The hardness claim rests on growing subgroup index and the failed attacks/oracle panel; it has no reduction to a standard hard problem.
- The 0/200,000 estimate is only for uniform dense matrix pairs after quotienting the `A/B` swap.  It does not estimate algebraic, Gröbner-basis, discrete-log, meet-in-the-middle, or future matrix-root attacks, nor does it count all answers at shipping size.
- The adversary panel did not implement a full rational-canonical solver, generic polynomial-system solvers, or vendor tools with arbitrary-precision execution.  It did test the paper-inspired scalar trace precursor conservatively: even finding the four-term trace decomposition was counted as an attack success.
- Fixed `k`, `gcd(k,p-1)=1`, explicit nilpotent targets, very small fields, or dimensions large relative to `k` can be easy and are deliberately excluded.  Seeds at the same preset share `p` and `k`, though their dense targets and similarity keys differ.
- Appendix A's stated `C(k,n)` derivation contains an exponent with denominator `n-8`, so it does not directly justify its advertised small-`n` range.  Solvability here never depends on that step because witnesses are planted; the later paper's explicit universal bound independently covers these primes.
- `canonical_key` is exact for generated nonzero-trace, square-free `2 x 2` targets under arbitrary basis change, transpose, and multiplication of the entire equation by a nonzero `k`-th power.  It is intentionally not defined for arbitrary noncyclic matrices outside this generator.
