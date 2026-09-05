# Flaps and flips: compact reconfiguration certificates

| Profile field | Value |
|---|---|
| Paper | David Eppstein, [*Computational Complexities of Folding*](https://arxiv.org/abs/2410.07666) |
| `TRACK` | `B` — no-tool compression |
| Native domain | `geometry` |
| Object regime | `integer_lattice` |
| Computational core | `linear_algebra` |
| Certificate form | `matrix_certificate` |
| Intended intuition | `change of variables`: four affine-basis ranks determine a complete geometric traversal |
| Domain essentiality | `native` |
| Reduction | none |

## What the problem is

Section 5.1 of the paper defines *flaps and flips*: congruent square paper flaps are attached to a rigid table by full-edge hinges, and one move changes the side of one flap while preserving a consistent flat state. Section 5.2 and Figure 10 make an edge gadget from a chain of flaps. Reversing that gadget requires flipping its flaps from the uncovered arrowhead to the tail; Lemma 11 carries these chain moves through the NCL reduction.

An instance here is stated in those native objects: exact integer hinge coordinates, the common square side length, and the start and target side of every flap. It is an inverse-generated composition of independent Figure 10 chains. The generator first samples an invertible affine map over `F_q`, uses its `q^3` outputs as a known legal traversal, builds the chains around that traversal, and finally shuffles the flap records. It never solves the resulting instance.

The requested witness is the fixed-size affine description `v -> A*v+b`, not 1,331 typed move labels. The verifier checks the matrix shape and invertibility, derives the induced permutation, recomputes hinge coverage with exact integer comparisons, and checks every forced flip precedence. It never reads `inst["answer"]`. The finite-field wrapper is benchmark-specific and is not claimed to occur in the paper, but the supplied constraints and the verifier remain geometric: removing the flap coordinates removes the problem.

## Why this is Track B

Theorem 4 proves that unrestricted pairwise and global connectivity for integer-coordinate flaps and flips is PSPACE-complete, even at bounded treewidth. That worst-case theorem does **not** make this generated distribution hard: its independent chains have a successful exact reference algorithm. Bucket by row, comparison-sort each row in its legal direction, and interpolate the affine map from traversal ranks `0`, `1`, `q`, and `q^2`. Its complexity is `O(n log n + d^2)`.

At the shipping preset (`n=1331`, `q=11`, `d=3`), eight reference runs solved 8/8 with 99,544 total counted operations, or 12,443 per instance, and 0.03542 seconds total, or 0.00443 seconds per instance on this machine. This is easy with code and infeasible as a manual sort of 1,331 shuffled records. The compact route recognizes that the long constant-spacing chain contains all four affine-basis ranks; converting four labels to base `q`, locating the ranks by their gap, and subtracting the offset costs 26 counted exact operations. The benchmark therefore measures whether a no-tool solver finds and uses that change of variables, not computational hardness.

The main easy regime identified elsewhere in the paper is Theorem 1: flat-foldability with ply `p` and cell-adjacency treewidth `w` is decidable in `(p!)^O(w) n^2`. That theorem concerns flat-foldability rather than this certificate, and the special row-sort above is stronger for this distribution. Theorem 4's hard NCL vertex gadgets are deliberately not claimed here.

## Worked demo

The `demo` preset at seed 0 renders in full as follows and is hand-solvable.

```text
FLAPS AND FLIPS — compact exact reconfiguration certificate

There are 8 congruent square paper flaps of side length 1009 on a rigid table.
Flap labels are 0 through 7. Here n=2^3, and arithmetic below is in F_2.
Each hinge is the vertical closed segment from (x,y) to (x,y+side).
State R places a flap in [x,x+side] x [y,y+side]; state L places it in [x-side,x] x [y,y+side].
Interiors are used: boundary-only contact is not overlap.
A flap covers another hinge when its square interior meets a positive-length part of the other hinge's relative interior.
For these supplied placements, a side assignment is consistent exactly when no two flaps cover each other's hinges; cyclic above-below relations among three flaps are allowed.
A flip toggles one flap between L and R and is legal only when the resulting state is consistent.

Every flap must be flipped exactly once, from the displayed start state to the displayed target state.
Certify a legal order compactly by an affine bijection v -> A v + b over F_q.
For i=0,...,7, write i in exactly 3 little-endian base-q digits v=(v0,v1,v2), so i=v0+q*v1+q^2*v2.
Compute w=A*v+b modulo q and decode the next flap label as w0+q*w1+q^2*w2.
A must be an invertible 3 by 3 matrix, b must have length 3, and entries are integers 0 through 1.
The resulting q^3 labels must be a legal flip sequence. Any affine certificate producing one is accepted.
Rows of A are output digits w0 to w2; columns are input digits v0 to v2.

Flaps are deliberately listed in arbitrary order:
F3: hinge=(-2891,-6430)-(-2891,-5421); start=R; target=L
F1: hinge=(-3473,-3403)-(-3473,-2394); start=L; target=R
F6: hinge=(-1743,-6430)-(-1743,-5421); start=R; target=L
F5: hinge=(-2958,-3403)-(-2958,-2394); start=L; target=R
F4: hinge=(-1169,-6430)-(-1169,-5421); start=R; target=L
F7: hinge=(-2317,-6430)-(-2317,-5421); start=R; target=L
F2: hinge=(-3465,-6430)-(-3465,-5421); start=R; target=L
F0: hinge=(-3989,-3403)-(-3989,-2394); start=L; target=R

Give your final answer inside <answer></answer> tags as one JSON object with keys matrix and offset.
Syntax example only: <answer>{"matrix":[[1,0],[0,1]],"offset":[0,0]}</answer>
Your actual matrix must have 3 rows of 3 entries and offset must have 3 entries, all reduced to 0,...,1.
Output nothing else inside the tags.
```

The answer is:

```json
{"matrix":[[1,1,0],[0,0,1],[0,1,1]],"offset":[0,1,0]}
```

`verify(inst, answer)` returns `(True, "ok")`. Duplicating its first matrix row as the second returns `(False, "matrix is singular modulo q")`. As a separate exhaustive verifier audit, direct state-by-state geometric replay and the precedence checker agreed on all 40,320 permutations for each of three demo seeds; each had 56 legal literal move orders.

## Difficulty presets

| Preset | `n=q^3` | `q` | Chains | Side | Status |
|---|---:|---:|---:|---:|---|
| `demo` | 8 | 2 | 2 | 1,009 | Hand example; hardening skips it |
| `easy` | 125 | 5 | 4 | 100,003 | Oracle solved; escalated |
| `medium` | 343 | 7 | 5 | 100,003 | Oracle solved; escalated |
| `hard` | 1,331 | 11 | 6 | 1,000,003 | **Shipping; held 0/3** |

`escalate()` grows the modulus and ambient traversal while the matrix witness remains twelve entries.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted certificates verified and JSON-round-tripped |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | realistic fenced/prose response round-tripped; garbage returned `None` |
| G4 | pass | 0/200,000 uniform candidates from `GL(3,11) x F_11^3`; language size 2,827,411,356,000 |
| G5 | pass | shipping density 0/200,000; demo has exactly 1 valid affine certificate of 1,344; baseline 99,544 operations over 8 runs |
| G6 | pass | all five attacks scored 0/8; reference algorithm solved 8/8 |
| G7 | pass | `n=4913` (3.691x shipping) built and verified with the same 12-atom answer |
| G8 | pass | 20/20 invariant keys, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 53 characters, about 14 tokens, 12 atoms, 26 intended exact operations |

The five failing attacks were: using the first presented flap as an offset outlier, numeric-label identity order, fitting the arbitrary presentation order, a diagonal affine ansatz after finding the geometric start, and 256 uniform affine restarts.

## Oracle loop

API errors did not count as failed attempts. Easy and medium were escalated because at least one scored attempt solved them; all three scored hard attempts failed.

| Preset | Model | Seed | Outcome | Why |
|---|---|---:|---|---|
| easy | Gemini 3.1 Pro Preview | 1751446220 | failed | illegal flip at step 63 |
| easy | Grok 4.6 | 1686174847 | error | 900-second total deadline; redrawn |
| easy | Claude Sonnet 5 | 1001993916 | failed | illegal flip at step 2 |
| easy | GPT-5.6 Terra | 10067760 | solved | verifier returned `ok` |
| medium | Gemini 3.1 Pro Preview | 314819715 | solved | verifier returned `ok` |
| medium | Grok 4.6 | 1380677209 | failed | empty length-limited response |
| medium | Claude Sonnet 5 | 1848851253 | failed | illegal flip at step 6 |
| hard | Grok 4.6 | 1021547684 | error | 900-second total deadline; redrawn |
| hard | Claude Sonnet 5 | 1992001309 | failed | illegal flip at step 10 |
| hard | GPT-5.6 Terra | 176452470 | failed | illegal flip at step 653 |
| hard | Gemini 3.1 Pro Preview | 209450797 | failed | illegal flip at step 1046 |

## G9 diagnostic arms

| Arm | Scored | Solved | Other harness records | Verdict |
|---|---:|---:|---|---|
| bare | 3 | 0 | one timeout was redrawn | hardened at `hard` |
| structural hint | 2 | 0 | one timeout, then four HTTP 403 account-limit errors | incomplete |
| placebo hint | 0 | 0 | four HTTP 403 account-limit errors | incomplete |

The supplied OpenRouter key reached its total account limit before the diagnostic could complete. Consequently `hinted - placebo` is undefined and no claim about hint effectiveness is made; this is recorded as `null`, not disguised as zero. These arms are diagnostic under the current contract and do not affect G9(c). The measured shipping answer is 53 characters/12 atoms for the sampled gate instance, with a measured worst-case budget of 17 approximate tokens in `PROBLEM_PROFILE`; the compact route uses 26 exact operations.

## Use

From this directory:

```python
import gen_2410_07666 as g

inst = g.make_instance(seed=0, **g.DIFFICULTY["demo"])
question = g.render(inst)
answer = g.parse_answer(
    '<answer>{"matrix":[[1,1,0],[0,0,1],[0,1,1]],"offset":[0,1,0]}</answer>'
)
ok, reason = g.verify(inst, answer)
assert (ok, reason) == (True, "ok")
```

To emit corpus records from the repository root:

```bash
bash scripts/emit.sh 2410.07666 20 hard
```

The module is standard-library-only and performs no file or network I/O.

## Caveats

- This is not a Track A distribution. A sandboxed solver sorts it in milliseconds; the general PSPACE result applies to NCL gadget networks, not these independent chains.
- The affine certificate and finite-field labels are a compact benchmark wrapper, not an origami object introduced by the paper. Native coverage is claimed because the instance contains actual integer-coordinate flaps and exact verification recomputes their geometric hinge interactions, not because the wrapper is native.
- The 0/200,000 density estimate concerns the declared, structure-aware language of invertible affine certificates. It says nothing about arbitrary literal move sequences; the demo already has 56 legal literal orders but only one accepted affine certificate.
- The constant-spacing long row is an intentional structural signature. A stronger pattern-mining tool or simple code recovers it; that is the Track B reference route, not an untested hardness assumption.
- The canonical key uses component lengths and squared hinge-gap sequences, invariant under affine label changes, row permutations/translations, and row reflections. It is tailored to this generated family rather than a complete isomorphism algorithm for arbitrary flap arrangements.
- Full state-graph search, a general SAT/SMT encoding, and tool-augmented LLM attacks were not run. The exact specialized reference algorithm dominates them for this distribution.
- The structural/placebo G9 comparison remains incomplete because of an external API account limit; the script-produced error records are retained in both transcripts.
