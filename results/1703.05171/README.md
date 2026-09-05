# Anchored constant-weight code completion

Status: **locally verified, externally blocked**. All local gates G1–G9(c)
pass. The official bare hardening loop solved `easy` and `medium`, then the
OpenRouter key hit its total spending limit before any `hard` attempt completed.
The hinted and placebo arms therefore have not been run. This is neither a
hardness verdict nor a rejection.

| profile field | value |
|---|---|
| Track | B — an efficient algorithm is disclosed |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | integer tuple (candidate IDs naming binary words) |
| Intended intuition | symmetry |
| Domain essentiality | native |
| Reduction | paper-licensed, Section 1.2 coordinate-permutation action |

## Problem and construction

The family follows the native definition in Sven Polak's
[“Semidefinite programming bounds for constant weight codes”](https://arxiv.org/abs/1703.05171).
The solver receives fixed-weight binary words, a coordinate permutation, and a
mandatory anchor. It must select exactly `k` words including the anchor, with
every pair at the stated minimum Hamming distance. The verifier reads those
words and exactly recomputes weight and every pairwise distance; it accepts any
valid selection, not only the planted one.

Section 1 defines words, weights, Hamming distance, and constant-weight codes.
Section 1.2 says simultaneous coordinate permutations preserve weight,
distance, and cardinality. The generator first makes a full orbit of the anchor
under such a permutation. Every orbit word selects one coordinate from each
cycle, so the words have disjoint supports and form a certified code. It then
adds independently sampled, incomplete two-phase orbit fragments as decoys.
The certificate is carried through the final candidate ordering; the generator
never solves the completed instance. The reduction citation is explicit because
the paper has mixed `math.CO`, `math.OC`, and `math.RT` categories; the binary
words themselves remain visible to the solver and verifier.

## Why Track B

This cannot honestly be Track A. Proposition 1.1 maps a known code to feasible
SDP data, and the paragraph after equations (2)–(3) says `A_k` is computable in
polynomial time for fixed `k` after symmetry reduction. Section 1.2 also reports
that the largest `B_4(22,8,10)` SDP took about three weeks, so “polynomial” does
not make the mechanical route suitable for a no-tool solver. The proposed Golay
triage route was not used: filtering the 2,048 words of one fixed shortened
Golay code is cheap and does not make an unlimited scalable distribution.

For this generated family, full candidate indexing followed by anchor-orbit
lookup is an `O(NL+kL)` exact algorithm. Across eight shipping instances it
performed 2,825,984 bit inspections and took 0.0035–0.0457 seconds across
recorded audits (0.021976 seconds in the final selftest).
Domain-standard Algorithm X also solved 8/8, using 4,297 nodes and 3,798,441 row
checks (3,802,738 counted operations) in 2.024765 seconds in the final selftest.
Once the Section 1.2 orbit invariant is recognized, the intended route is six
permutation steps and
sorted-table lookups, counted as 294 coordinate lookups/comparisons. The task is
finding and accurately executing that compact symmetry route without tools.

## Worked demo

`make_instance(n=3, code_size=3, decoy_orbits=2, seed=123)` renders:

```text
Anchored constant-weight binary code completion

A binary word of length L is a string of L zero/one bits. Its Hamming weight is
the number of 1 bits. The Hamming distance between two words is the number of
coordinates on which they differ. A constant-weight code of size k, weight w,
and minimum distance d is a set of exactly k distinct length-L words, every one
of weight w, such that every pair has Hamming distance at least d.

Choose a code from the candidate table below. Candidate IDs are 0-based. Your
code must contain the mandatory anchor ID 1. The answer is a
strictly increasing list of exactly 3 distinct IDs; order has
no mathematical meaning, and increasing order is the required canonical output.

Parameters:
  L = 9
  k = 3
  w = 3
  d = 6

Words are written as exactly 3 lowercase hexadecimal digits,
including leading zeroes. Coordinate i is bit i counted from the RIGHT starting
at i=0. Thus XOR followed by an exact 1-bit count gives Hamming distance.

The following supplied coordinate permutation maps old coordinate i to the
entry at position i. It is instance data and may be useful:
[8,5,3,6,0,7,2,1,4]

Candidate table (ID: hexadecimal word), sorted by hexadecimal word:
0: 016
1: 038
2: 043
3: 098
4: 0c1
5: 106
6: 1c0

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 3 strictly increasing 0-based candidate IDs.
Example format (not necessarily a solution): <answer>[0, 1, 2]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[1, 4, 5]</answer>`.
`verify(inst, [1, 4, 5]) == (True, "ok")`, while
`verify(inst, [1, 4]) == (False, "wrong number of IDs: expected 3, got 2")`.
A person can solve this demo by following the anchor through the nine-entry
permutation twice.

## Difficulty and gates

| preset | blocks `n` | code size | decoy orbits | word length | candidates | structured space |
|---|---:|---:|---:|---:|---:|---:|
| demo | 3 | 3 | 2 | 9 | 7 | 6 |
| easy | 8 | 5 | 12 | 40 | 53 | 91,390 |
| medium | 16 | 7 | 60 | 112 | 367 | 1,085,371,516,236 |
| hard (intended shipping) | 38 | 7 | 220 | 266 | 1,327 | 2,507,831,816,322,196 |

Easy and medium were rejected by the bare oracle loop because at least one
attempt solved each. Hard remains the intended shipping preset but has not yet
received a valid oracle attempt.

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; orbit recovery matched each |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged and fenced prose round-trip; garbage rejected |
| G4 | pass | 0/200,000 structured guesses; space 2,507,831,816,322,196 |
| G5 | pass | demo exactly 1/6; strongest failed attack used 5,602,667 steps / 11.452707 s |
| G6 | pass | four attacks each 0/8; both reference algorithms solved 8/8 |
| G7 | pass | doubled 532-bit instance verifies with the same 7-ID answer |
| G8 | pass | 60/60 invariance, 60/60 carried witnesses, 20/20 distinct keys |
| G9(c) | pass | 30 chars, 8 estimated tokens, 7 atoms, 294 operations |

## Oracle evidence and G9 arms

| preset | seed | model | result | reason |
|---|---:|---|---|---|
| easy | 907709477 | Gemini 3.8 Flash | solved | verified answer |
| easy | 192180635 | GPT-5.6 Terra | solved | verified answer |
| easy | 1922590910 | GPT-5.6 Terra | failed | one pair had distance 14 < 16 |
| medium | 141933958 | Gemini 3.8 Flash | solved | verified answer |
| medium | 1776717483 | GPT-5.6 Terra | failed | one pair had distance 18 < 32 |
| medium | 828345701 | GPT-5.6 Terra | failed | one pair had distance 26 < 32 |
| hard | four distinct seeds | both vendors | error | OpenRouter HTTP 403 total-limit errors |

| G9 arm at hard | solved / valid attempts | verdict |
|---|---:|---|
| bare | 0 / 0 | pending; four API errors do not count as attempts |
| structural hint | 0 / 0 | not run |
| placebo hint | 0 / 0 | not run |

`hinted - placebo` is undefined. No conclusion about the claimed symmetry
intuition is drawn until both arms run. The measured output and route remain
within the G9(c) caps: 30 characters, 8 estimated tokens, 7 atomic elements,
and 294 exact operations.

## Use

```python
import gen_1703_05171 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
prompt = gen.render(inst)
candidate = gen.parse_answer("<answer>[0, 1, 2]</answer>")
ok, reason = gen.verify(inst, candidate)
```

After the OpenRouter key is replenished, rerun the bare loop from this directory:

```bash
python3 ../../scripts/harden.py gen_1703_05171.py
```

Only after a hard rung holds, run the structural and placebo copies in separate
scratch directories and copy their transcripts back. Emission from the repository
root is then `bash scripts/emit.sh 1703.05171`.

## Caveats

Hashing or text search makes orbit lookup trivial; that is the declared Track B
algorithm. G4 samples uniformly from anchored subsets after filtering every word
that visibly fails against the anchor. It measures that explicit prior, not all
plausible solver priors and not a complexity theorem. The attack panel omits a
general ILP/CP package, though it includes the more direct exact-cover Algorithm X
and the faster construction-specific orbit solver. The canonical key is a strong
color-refinement invariant, not a complete isomorphism algorithm for arbitrary
colored set systems. Finally, external hardness and both hint diagnostics remain
unverified because the paid oracle budget ended; trusting this as a shipped hard
family before those runs would be unwarranted.
