# Trapdoored binary matrix–vector products

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | matrix certificate (an `n×1` binary column encoded canonically as a bitstring) |
| Intended intuition | change of variables: associate `Mv` as `L(Hv)+Sv` |
| Domain essentiality | native |
| Reduction | none |

This generator turns [Braverman and Newman, *Practical Secure Delegated Linear Algebra with Trapdoored Matrices*](https://arxiv.org/abs/2502.13060) into an exact problem family.  A solver receives a dense binary matrix `M`, a binary vector `v`, and the paper's native trapdoor data `L,H,S` satisfying `M=LH+S`, where `L` has inner dimension two and `S` has one nonzero per row.  The required witness is the binary vector `Mv`.  `verify` independently recomputes every dense parity inner product over `F_2`, so any correct vector is accepted and no planted answer is read.

## Why this is Track B

Definition 5 and Section 6 supply the object and the identity `A(LH+S)=(AL)H+AS`; transposing the orientation gives the generated task's `Mv=L(Hv)+Sv`.  Ordinary dense multiplication is the reference algorithm: it is `O(nm)`, succeeds 8/8, and at the shipping shape `128×320` costs 81,792 conventional field operations (about 0.00020 s for one Python bit-packed run; 0.00136 s across the eight reference runs).  The trapdoor route for the measured shipping instance costs 271 XORs.  The gap is therefore meaningful only in the stated no-sandbox/no-tool setting, not as computational hardness.

The family makes no LPN-security claim.  Section 5's cryptographic regime has `n_1=delta*n` and Bernoulli sparse noise.  Here the inner dimension is two, the trapdoor is public, and `S` has exactly one nonzero in each row.  Section 7 explicitly warns that subsampling and Gaussian elimination become efficient when `delta*mu <= 1/n`; this structured benchmark deliberately lives on the easy side and tests use of the factorization, not trapdoor recovery.

## Worked demo

For `make_instance(n=6, columns=12, inner=2, seed=0)`, the complete instance is:

```text
M rows:
0: 000110101100
1: 110001010100
2: 000110101100
3: 111110011000
4: 011110111000
5: 101001010100
L row codes: 2 1 2 3 3 1
H rows:
0: 111001010100
1: 000111101100
S_support: 5 2 5 6 0 1
v: 101100101010
```

Codes 1, 2, and 3 mean `[1,0]`, `[0,1]`, and `[1,1]`; `S_support[i]` is the zero-based position of row `i`'s sole correction bit.  The answer is `<answer>111000</answer>`.  `verify(inst, "111000")` returns `(True, "ok")`, while changing its first bit gives `verify(inst, "011000") == (False, "incorrect product bit at row 0")`.  The demo's trapdoor route takes only eight XORs and is comfortably solvable by hand.

## Difficulty presets

| Preset | Rows `n` | Columns `m` | Answer bits | Dense operations | Trapdoor XORs at seed 73311 | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 6 | 12 | 6 | 138 | 10 | hand example; oracle skipped |
| easy | 96 | 192 | 96 | 36,768 | 186 | old medium was solved 3/3 |
| medium | 128 | 256 | 128 | 65,408 | 233 | old hard was solved 1/3 |
| hard | 128 | 320 | 128 | 81,792 | 271 | **ships; held 0/3** |

The bare loop first solved the discarded 64×128 rung 2/3, then 96×192 3/3, then 128×256 1/3.  It hardened after a fixed-answer-length column escalation to 128×320, so the ladder was slid upward as required.  `escalate` next raises only the column haystack to 384 while retaining the 128-bit answer.

## Gate results

| Gate | Result |
|---|---|
| G1 planted verifies | 16/16; every preset over four seeds |
| G2 corruption | 5/5 rejected with five distinct reasons |
| G3 round trip | 128-bit planted answer recovered from prose and a fenced tagged block |
| G4 random guess | 0/200,000 from the exact `2^128` shaped language |
| G5 density and baseline | shipping sampled fraction 0/200,000; demo has exactly 1/64 valid answers; dense baseline 81,792 operations |
| G6 adversaries | five attacks, each 0/8; dense reference solves 8/8 |
| G7 scaling | 256×640 builds and verifies; search entropy rises 128 to 256 bits |
| G8 canonical key | 80/80 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 caps | 130 serialized chars, 128 conservative tokens/elements, 271 intended XORs |

## Bare oracle loop

| Run label | Shape | Seeds | Solved | Outcome |
|---|---|---|---:|---|
| easy (pre-slide) | 64×128 | 1623364389, 2023174985, 1981111027 | 2/3 | escalate |
| medium (pre-slide) | 96×192 | 827985405, 1020254868, 376312350 | 3/3 | escalate |
| hard (pre-slide) | 128×256 | 239295215, 452797077, 1426915313 | 1/3 | escalate |
| escalated / shipping hard | 128×320 | 2075708387, 963775505, 257305305 | 0/3 | hardened |

All scored failures either gave an incorrect exact bit or, in one placebo call below, made no parseable answer; provider errors did not count.

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`.  The structural hint bought no measured improvement.  That is unsurprising and slightly weakens the claimed “change of variables” diagnostic: the relation `M=LH+S` must already be stated for the problem to be self-contained, so the remaining difficulty is accurate execution of 271 XORs rather than discovery of a concealed theorem.  It remains within the explicit 300-operation cap.

## Use

```python
from gen_2502_13060 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer(f"<answer>{inst['answer']}</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 2502.13060 20 hard
```

## Caveats

This is a deliberately non-cryptographic Track B subdistribution.  It would be easy with any programming language, bitset calculator, or CAS, and the measured Python wall time confirms that; it must not be cited as evidence for LPN hardness or trapdoor secrecy.  The 0/200,000 guess result measures a uniform prior over well-formed 128-bit output vectors, not a solver informed by the factorization.  The attack panel tried row-weight thresholding, majority over active columns, a first-active-column proxy, omission of the sparse correction, and 256 legal restarts; it did not benchmark optimized SIMD/GPU multiplication or every possible arithmetic shortcut because those are expected to solve the task and belong with the successful reference algorithm.

The canonical key removes all generated row and column permutations and all six `GL(2,F_2)` trapdoor-basis changes.  It keys on the supplied factor data because exact bipartite canonicalization of arbitrary dense matrices is outside this module; an exotic alternative factorization producing the identical `(M,v)` but not related by `GL(2,F_2)` could therefore be over-counted.  Generation also conditions balanced factors to avoid degenerate heuristic wins, so it does not reproduce Section 5's uniform/Bernoulli LPN distribution.
