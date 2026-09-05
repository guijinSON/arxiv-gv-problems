# Supersingular 2-isogeny walk generator (arXiv:1912.00701)

| profile field | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | `number_theory` |
| Object regime | `finite_field` |
| Computational core | `graph` |
| Certificate form | `exact_symbolic` (a binary isogeny word) |
| Intended intuition | `search pruning` through the marked dual kernel and bidirectional collision search |
| Domain essentiality | `native`; `reduction_kind=none` |

## What the problem is and why the construction is trustworthy

This module instantiates the elliptic base problem used throughout Costello and
Smith, [*The supersingular isogeny problem in genus 2 and beyond*](https://arxiv.org/abs/1912.00701).
The solver receives two explicit supersingular elliptic curves over
`F_(p^2)`, plus the incoming kernel that orients the source. It must return a
fixed-length non-backtracking sequence of degree-2 kernel choices reaching the
target. The answer is sampled first; exact degree-2 Vélu quotients are then
composed to construct the target. Generation never solves its own instance.

Checking is deterministic and exact. The verifier replays the quotient formula
over `F_p[i]/(i^2+1)` and compares the resulting and target j-invariants. It
accepts every word reaching the target, not merely the planted word. The module
uses only the standard library because `gvlib` has no finite-field isogeny
layer.

## Why Track A is the honest claim

Section 2 defines `Gamma_1(ell;p)` and the isogeny path problem. It quotes
Pizer's theorem that the supersingular graph is Ramanujan and gives the best
generic classical path-finding cost as `O~(sqrt(p))`. Section 3 gives the CGL
binary encoding used here: mark the incoming 2-isogeny and choose between the
other two kernels. At shipping size `p=2^127-1`, generic path finding costs
about `2^63` graph operations; exploiting the promised 64-step length with
meet-in-the-middle still needs about `2^32` midpoint states.

Theorem 1 is not a polynomial certificate producer: for `g>1` it gives the
paper's recursive `O~(p^(g-1))` attack. This family stays at its elliptic base
case. It also avoids the easy regimes identified in the paper: no endpoint
endomorphism rings are supplied (Section 3 says those make shortest paths
efficient), no higher-dimensional product node exposes a factorization, and no
SIDH torsion-point images are present. The claim is distribution-specific:
random oriented sources, random 64-bit non-backtracking words, and independent
affine source/target models.

## Worked demo

For `make_instance(seed=123, **DIFFICULTY["demo"])`, the complete mathematical
data rendered to the solver is:

```text
Recover a non-backtracking supersingular 2-isogeny walk.

All arithmetic below is exact. Let F be the field F_p[i] with i^2=-1;
p=31. A pair (a,b) denotes a+b*i, with both coordinates reduced modulo p.
The curve is E: y^2=(x-r0)(x-r1)(x-r2).
Source roots: (10,22), (6,10), (27,11)
Source forbidden root: (10,22)
Source j-invariant: (2,0)
Target roots: (28,19), (28,11), (28,3)
Target j-invariant: (23,0)

At each step sort the two non-forbidden roots lexicographically. Bit 0 chooses
the first and bit 1 the second. For chosen r and other roots s,t, put
A=2*r-s-t and B=(r-s)*(r-t); if q is the lexicographically smaller square root
of B, the quotient roots are (0,0), A+2*q, A-2*q and (0,0) is next forbidden.
Return exactly four bits inside <answer></answer> tags.
```

The planted answer is `<answer>0000</answer>` and `verify(inst, "0000")`
returns `(True, "ok")`. Changing its first bit gives `1000`, for which the
verifier returns `(False, "endpoint mismatch: the word does not reach the target
j-invariant")`. This demo has 16 words and 3 valid answers, so it is genuinely
hand-scale, although checking still requires arithmetic in a 31-element base
field.

## Difficulty presets

| preset | field bits | answer bits | hidden prewalk | candidate words | status |
|---|---:|---:|---:|---:|---|
| demo | 5 | 4 | 4 | 16 | hand example; not shipped |
| easy | 127 | 64 | 16 | `2^64` | **shipping preset** |
| medium | 521 | 80 | 20 | `2^80` | available escalation |
| hard | 607 | 96 | 24 | `2^96` | available escalation |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified; all answers JSON-native |
| G2 | pass | empty, short, long, invalid-symbol, and swapped answers rejected with 5 distinct reasons |
| G3 | pass | tagged answer recovered through surrounding prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware random valid-shape words verified; 1,000.11 s under shared CPU load |
| G5 | pass | shipping density estimate 0/200,000; demo exact count 3/16; strongest attack 23.04 s |
| G6 | pass | all four attacks below had 0/8 successes |
| G7 | pass | named ladder, doubled requested `n`, and post-ladder escalation all built and verified |
| G8 | pass | 80/80 relabelling invariance and transported-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 66 characters, 17 estimated tokens, 64 atoms, 64 quotient steps |

| G6 attack | successes | attempts | recorded operations |
|---|---:|---:|---:|
| endpoint-coordinate low bits | 0 | 8 | 512 |
| greedy j-coordinate distance | 0 | 8 | 1,024 |
| random restart (64 words) | 0 | 8 | 512 restarts |
| bidirectional meet-in-the-middle, 65,536 cap | 0 | 8 | 262,144 expanded states total |

## Oracle loop and G9 arms

The required harness was invoked, but the shared OpenRouter key returned HTTP
403 `Key limit exceeded (total limit)` on every redraw. Those API errors are
correctly recorded as errors, not model failures. There is therefore no valid
hardening verdict yet and the two additional G9 arms cannot be claimed as run.

| arm | solved / attempts | current conclusion |
|---|---:|---|
| bare | 0 / 0 valid calls | blocked by provider key limit |
| structural hint | 0 / 0 valid calls | blocked by provider key limit |
| placebo hint | 0 / 0 valid calls | blocked by provider key limit |

`hinted - placebo` is not measurable yet. The local G9(c) cap is unaffected:
the answer has 66 serialized characters (17 approximate tokens), 64 atomic
symbols, and the certificate route has 64 exact quotient steps.

## Use

From the repository root:

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "gen_1912_00701", "results/1912.00701/gen_1912_00701.py"
)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
inst = gen.make_instance(seed=42, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
assert gen.verify(inst, inst["answer"]) == (True, "ok")
question = gen.render(inst)
```

The repository scripts use the same file-based import because the arXiv-id
directory contains dots. Emit instances with:

```bash
bash scripts/emit.sh 1912.00701 20 easy
```

## Caveats

This is the paper's elliptic base case, not a genus-2 Jacobian instance. It is
native isogeny arithmetic, but it does not exercise the paper's genus-reduction
attack. Track A is a best-known-algorithm claim, not a lower bound. The 0/200,000
figure estimates density under uniform fixed-length non-backtracking words; it
does not estimate a solver that exploits graph collisions, endomorphism rings,
or future supersingular-isogeny algorithms. The meet-in-the-middle attack was
resource-capped rather than run to its projected `2^32` frontier. No Magma,
endomorphism-ring, quantum, or large-memory Pollard implementation was run.

The binary answer is short, but independently replaying all 64 quotients entails
more low-level field multiplications than the 64 high-level steps reported for
G9. Finally, the structural hint names only the already-relevant dual-kernel
orientation; it may provide no measurable advantage. That diagnostic remains
unknown until the provider key limit is cleared and all three oracle arms run.
