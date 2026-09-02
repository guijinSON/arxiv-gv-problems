# Rejected: ternary constant-composition code construction

Paper: Hengjia Wei, Hui Zhang, Mingzhi Zhu, and Gennian Ge,
[*Optimal Ternary Constant-Composition Codes with Weight Four and Distance
Six*](https://arxiv.org/abs/1409.6092), arXiv:1409.6092.

## Decision

The paper does not supply a problem family satisfying **G, H, and V**. Its
natural witness is a constant-composition code, which is cheap to check, but
the paper's contribution is an almost complete classification of the target
sizes together with explicit and recursive constructions attaining them. It
contains no computational-hardness theorem or hard planted distribution.

Consequently **H fails/is unsupported** in every regime where the paper lets a
generator know a witness. The bare length-and-composition problem also fails
the strict answer-first/diversity requirement: a sampled code does not affect
the instance, and all seeds at a fixed length pose the same problem up to
coordinate relabelling. I stopped at Step 0 rather than add completion or
candidate-list constraints that the paper never studies.

## Exact definition from the full paper

Section II.1 defines a ternary code of length `n` as a set
`C ⊆ Z_3^X`, where `|X| = n`. The support of a word is the set of nonzero
coordinates, Hamming distance is the number of coordinates on which two words
differ, and composition `[w1,w2]` means exactly `w1` coordinates contain `1`
and exactly `w2` contain `2`. The paper studies sets in which every distinct
pair has Hamming distance at least six, for the two compositions `[2,2]` and
`[3,1]`. It writes `A_3(n,6,[w1,w2])` for the maximum possible number of
codewords.

The four-coordinate notation used throughout is exact: in
`<a,b,c,d>` the first `w1` listed positions carry symbol `1`, the remaining
listed positions carry symbol `2`, and every other position carries `0`.
Thus, for `[2,2]`, `a,b` carry `1` and `c,d` carry `2`; for `[3,1]`, `a,b,c`
carry `1` and `d` carries `2`.

Section II.4 adds the group-divisible-code constraint: the coordinates are
partitioned into groups and a codeword has at most one nonzero coordinate in
each group. This is a construction tool, not a computational input regime.

## What makes the usable regimes constructive rather than hard

Section II.2 gives Johnson-type upper bounds. Sections III and IV match those
bounds for nearly all lengths using four named operations from Section II.4:
filling groups, adjoining points, the fundamental construction, and inflation.
The many exceptional base cases are not hidden search instances: the paper
prints their base codewords and develops them under stated cyclic
automorphisms.

Several especially tempting subfamilies already have direct existence and
construction rules:

- Section III.1, Lemma 3.1 states the existence range for the required skew
  Room frames, and Proposition 3.2 converts any such frame directly into a
  `[2,2]` group-divisible code.
- Section III.2, Theorem 3.4 classifies the needed `(g,4;1)` difference
  matrices (`g >= 4` and `g` not congruent to `2 mod 4`), and Proposition 3.5
  gives an explicit formula converting the matrix into the code.
- Section IV, Theorem 4.4 constructs `[3,1]` group-divisible codes of type
  `9^t` for every `t >= 4`, first by printed cyclic base cases and then by the
  paper's fundamental construction.
- The two summary theorems in Section V give closed, residue-class formulas
  for `A_3(n,6,[2,2])` and `A_3(n,6,[3,1])` outside explicitly listed
  unresolved lengths. These are the known-witness regimes a generator would
  have to use.

The paper never proves NP-hardness, search hardness, an average-case lower
bound, or even a complexity classification for finding a code. Nor does it
identify a parameter regime in which its own constructions cease to be an
effective way to produce one. A large combinatorial answer space is therefore
not evidence for H.

## Why the apparent generator variants do not qualify

| Candidate task | Why it fails |
|---|---|
| Return the value `A_3(n,6,w)` | It is a number/optimum, not a witness, and Section V makes it a residue-class lookup in the resolved regimes. |
| Return a code of the Section-V size | Verification is cheap, but the paper is devoted to constructions of exactly these witnesses. Shipping a subfamily implemented from those constructions would expose a known construction regime, not a supported hard one. |
| Return one codeword | Any word with the stated composition works, so there is an immediate closed-form answer. |
| Return a difference matrix, Room frame, PBD, GDD, or GDC | The paper uses classified existence ranges and direct transformations to obtain codes. It gives no hardness result for searching for the auxiliary design; several relevant families are explicitly constructed. |
| Complete a partial code | Planting a full code and revealing part of it would give G and V, and might form an interesting CSP, but code completion is not defined or analysed in this paper. No theorem transfers hardness to that planted distribution. |
| Choose `k` words from a supplied candidate list | This is a newly imposed clique/set-packing problem. The candidate list is not part of the paper's code definition, and the paper gives neither a reduction nor an answer-first hard distribution for it. |
| Randomly permute coordinates/symbols of a printed construction | This changes only labels. G8 requires every such instance to have the same canonical key, so it supplies no structural diversity and does not hide the known construction. |

For the natural task the rendered data would only be `(n, composition,
distance=6, required_size)`. At fixed `n`, changing the seed can change the
stored planted code but cannot change the solver's problem. Hence an honest
`canonical_key` would be the same for every seed, and the corpus diversity
check would reject the result.

## Gate outcome

| Requirement | Result |
|---|---|
| G -- sample a witness first and build the problem around it | **Fails for the unmodified paper problem:** sampling a code first does not alter the public instance. It can be forced only by adding partial-code/restricted-universe constraints absent from the paper. |
| H -- no known polynomial-time or closed-form method | **Fails/unsupported:** all known-witness parameter regimes are supplied through explicit base codes and general design constructions; the paper contains no hardness regime. |
| V -- cheap exact verification | Passes in principle: check every word's exact composition and all pairwise Hamming distances (and group intersections for a GDC). |
| G7 -- scalable difficulty | Length scales, but the paper establishes scalable constructions/existence, not scalable search hardness. |
| G8 -- structural diversity | Fails for a fixed length: different planted codes are not part of the problem data, and coordinate/symbol relabellings must collapse. |

Because G/H already fail analytically, the 200,000-sample guess test,
adversary panel, and LLM hardening loop were not run. No generator,
`selftest_report.json`, `README.md`, or oracle transcript was fabricated; doing
so would contradict the instruction to stop after a Step-0 rejection.
