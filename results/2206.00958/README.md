# Hilbert–90 generator for arXiv:2206.00958

**Status: `cap_bound`; retained, not rejected, and not eligible to ship under the
current 300-operation no-tool cap.** The local correctness gates pass, but the
bare oracle loop solved 1/3 instances at the strongest admissible rung. The next
extension degree would require 303 intended-route operations.

| profile field | value |
|---|---|
| `TRACK` | B — no-tool compression |
| native domain | algebra |
| object regime | finite field |
| computational core | linear algebra |
| certificate form | exact symbolic: one fixed-width hexadecimal field element |
| intuition | change of variables: detect and remove one repeated rank-one discrepancy, then follow a Frobenius cycle |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

The source is Faruk Göloğlu’s [*Classification of \((q,q)\)-biprojective APN
functions*](https://arxiv.org/abs/2206.00958). Section 2.1 defines the trace and
finite-field Hilbert–90 equation, and the paragraph after Lemma 2.4 explains how
zeros of `a*x^q-b*x+c` reduce to `x^q-x`. Lemma 2.3 is where linearized systems
characterize the derivatives of biprojective APN maps. Theorem 1.1 itself makes
“classify this APN function” a short lookup, so this generator does not pretend
that classification is hard.

An instance gives the exact normal-basis coordinates of a rank-one output-mixed
equation `x^(2^k)+x=c` over `GF(2^n)` and asks for its unique solution with
coordinate `x_0=0`. Generation is inverse: it samples that solution first,
evaluates the Frobenius equation, and applies the invertible transvection
`M=I+u*v^T`, where `v^T*u=0`. Verification independently recomputes every binary
parity and never reads `inst["answer"]`. The output mixing is the generator’s
structure-preserving hardening transformation; it is not claimed as a new APN
construction from the paper.

## Why Track B, and why it is parked

Track A would be false. Exact Gaussian elimination solves the displayed binary
system in `O(n^3)` bit operations; at the cap-edge `n=59` preset it solved 8/8,
averaging 38,445 counted operations and 0.000229 seconds. The compact route spots
that each altered row differs from its Frobenius-cycle row by the same mask,
undoes the rank-one transvection, and uses two cyclic XOR recurrences. Its
conservative arithmetic count is `2 + 4(n-1) + n = 293` operations.

That gap is a legitimate Track B compression target, but it did not survive the
required oracle bar: one of three no-tool oracles solved `n=59`. Raising the next
fixed-length ambient dimension to `n=61` would make the compact route 303
operations, above G9(c). Accordingly the script recorded `cap_bound`. Its generic
metadata text mentions the answer-output cap; here the measured binding cap is
specifically the **intended-route effort cap**, while the answer is only 17 JSON
characters.

## Worked demo

This is the complete `render(make_instance(n=7, k=2, seed=0))` output:

```text
Solve an exact output-mixed Hilbert--90 equation over GF(2^7).

Let L=GF(2^7) and choose a normal basis
  beta_e = theta^(2^e),  e=0,...,6,
where exponent labels are reduced modulo 7.  Thus raising a field element to
q=2^2 moves normal-basis coordinates around the single cycle e -> e+2
(mod 7); gcd(2,7)=1.  The linearized polynomial from finite-field
Hilbert 90 is T(x)=x^q+x.  Its kernel is {0,1}, and in a normal basis the
coordinate word of 1 is all ones.

Write x=sum_e x_e beta_e with x_e in GF(2).  An unknown nonsingular linear
change of OUTPUT coordinates has been applied to T(x)=c.  The resulting exact
binary system Bx=d is printed below.  This output mixing changes no solution.
The rows are deliberately shuffled; labels r0,...,r6 identify their
unshuffled output coordinates.

Each line has the form "row-label: rhs | mask".  A mask is exactly 2
hexadecimal digits.  Bit e of its integer value (least significant bit is bit
0) is the coefficient of x_e.  A row is satisfied when the parity of the
selected x_e equals rhs.  There are no omitted or implicit rows.

  r0: 0 | 28
  r6: 0 | 59
  r1: 1 | 42
  r2: 1 | 05
  r5: 1 | 21
  r3: 1 | 0a
  r4: 0 | 1d

Find the unique solution normalized by x_0=0.  Return x as exactly 2
lowercase hexadecimal digits encoding the integer sum_e x_e*2^e.  Leading
zeros are required; unused high bits (if any) are zero.  The row order is not
the coordinate order, and hexadecimal bit 0 is the least significant bit.

Give your final answer inside <answer></answer> tags, as that one hexadecimal word.
Example format: <answer>00</answer>
Output nothing else inside the tags.
```

The answer is `<answer>6c</answer>`:

```python
verify(inst, "6c")  # (True, "ok")
verify(inst, "4c")  # (False, "equation r0 has parity 1, expected 0")
```

The seven-coordinate demo is genuinely hand-solvable by elimination or by the
rank-one recurrence.

## Difficulty and gates

| preset | n | k | normalized space | answer | compact ops | bare oracle | disposition |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 7 | 2 | `2^6` | 2 hex digits | 33 | skipped | hand example |
| easy | 55 | 13 | `2^54` | 14 hex digits | 273 | 3/3 solved | defeated |
| medium | 57 | 17 | `2^56` | 15 hex digits | 283 | 2/3 solved | defeated |
| hard | 59 | 23 | `2^58` | 15 hex digits | 293 | 1/3 solved | cap edge; retained only |

`SHIPPING_DIFFICULTY="hard"` identifies the strongest audited candidate for
future replay; the `cap_bound` verdict means it is **not currently shipped**.

| gate | result | measured evidence at the cap edge |
|---|---|---|
| G1 | pass | 16/16 planted witnesses across all presets verify; JSON round-trip passes |
| G2 | pass | drop, swap, duplicate, empty, and genuinely out-of-range answers rejected with 5 distinct reasons |
| G3 | pass | tagged uppercase answer amid prose/fences parses and verifies |
| G4 | pass | 0/200,000 structure-aware guesses; language size `2^58` |
| G5 | pass | exact density `2^-58`; demo exact count 1; measured reference and restart costs recorded |
| G6 | pass | six failing attacks, each 0/8; Gaussian reference 8/8; compact route 8/8 |
| G7 | pass | doubled `n=118` instance builds and verifies; space exponent grows 58→117 |
| G8 | pass | 140/140 tested relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9(c) | pass at `n=59` | 17 characters, 1 atom, about 5 tokens, 293 exact operations |

The six failed attacks are dense-row voting, reading the RHS as the answer,
display-order greedy assignment, ignoring the mixing, using the discrepancy
indicator as the answer, and 256 uniform restarts. Gaussian elimination is
reported separately as Track B’s successful reference algorithm.

## Oracle loop and G9 diagnostics

| preset | model | seed | result | verifier evidence |
|---|---|---:|---|---|
| easy | Terra | 1242031474 | solved | `ok` |
| easy | Gemini | 613125925 | solved | `ok` |
| easy | Gemini | 1437208142 | solved | `ok` |
| medium | Terra | 1603035922 | failed | wrong parity at `r53` |
| medium | Gemini | 716355130 | solved | `ok` |
| medium | Terra | 1211338999 | solved | `ok` |
| hard | Terra | 1995980066 | failed | wrong parity at `r16` |
| hard | Gemini | 1121454403 | failed | empty length-limited response |
| hard | Gemini | 1633079927 | solved | `ok` |

| G9 arm at `hard` | solved/attempts | conclusion |
|---|---:|---|
| bare | 1/3 | the cap-edge level did not harden |
| structural hint | 0/0 | not run after `cap_bound` |
| placebo hint | 0/0 | not run after `cap_bound` |

Hinted minus placebo is therefore unavailable, not zero. In accordance with the
task’s “cap_bound is not a rejection” stop rule, no new diagnostic calls were
made. The existing `g9_hinted_transcript.jsonl` and
`g9_placebo_transcript.jsonl` are retained script-written HTTP-403 logs from an
older, obsolete parameterization; they contain zero scored attempts and support
no claim.

## Use

```python
from gen_2206_00958 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
question = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
```

After a future larger-cap hardening run returns `hardened`, emit from the repo
root with `bash scripts/emit.sh 2206.00958 20`. Do not emit this parked result as
a hardened benchmark today.

## Caveats

This family covers the paper’s Hilbert–90/linearized-polynomial engine, not its
full APN classification. It is trivial with linear-algebra tools and becomes
easy by hand once the repeated discrepancy is recognized; one top-rung oracle
did exactly that. The random-guess figure is uniform over normalized field words
and says nothing about a solver with this structural prior. I did not run
Wiedemann-style sparse linear algebra, SAT/SMT encodings, or learned pattern
detectors because generic elimination already settles tool-assisted difficulty.

The canonical key quotients equation-row reorderings, elementary output-row
operations, and Frobenius-conjugate cyclic shifts of the designated normal-basis
frame. It does not quotient arbitrary unlabelled changes to a different normal
basis; the displayed ordered coordinate frame is treated as part of the instance.
That scope is explicit because quotienting every linear representation would
collapse most instances of this linear problem into very few isomorphism classes.
