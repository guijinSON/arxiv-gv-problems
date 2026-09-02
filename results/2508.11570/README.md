# Grand Tour witness generator (arXiv:2508.11570)

This module generates **Grand Tour** instances from Kiatchaipipat and Ruangwises, [“NP-Completeness Proofs of Puzzles using the T-Metacell Framework”](https://arxiv.org/abs/2508.11570). A solver receives a full orthogonal square grid and mandatory (“forced”) edges, then returns one cyclic ordering that visits every vertex exactly once and contains every forced edge. `verify` checks length, range, uniqueness, grid adjacency, closure, and all forced edges in linear time.

## Why this regime is hard

Section 2.1 fixes the definition. Its asymmetric 5×5 forced-edge T-metacell has a unique traversal for each exit choice, which the Section 1.1 framework turns into ASP-completeness; that construction has at least one forced incidence at every vertex. Section 2.1 also proves NP-completeness with an arbitrarily small forced/unforced ratio. This generator samples a Hamiltonian cycle first and publishes one alternating perfect matching of it, giving exactly one forced incidence per vertex. The paper gives no polynomial-time, closed-form, FPT, or approximation algorithm for this regime.

Both extremes are easy. With no forced edges, a full even grid has a direct serpentine tour. Section 2.1 notes that forcing both cycle incidences induces the cycle itself. Exactly one incidence leaves the global problem of choosing a complementary grid perfect matching whose union with the forced matching is one cycle, rather than several cycles.

## Worked shipping instance

The smallest preset is `standard`. Here is `render(make_instance(n=11, seed=0))` in full:

```text
Grand Tour witness problem

The graph is a 22-row by 22-column rectangular grid of 484 vertices.
Rows are 0 through 21, columns are 0 through 21, and the vertex
at (row r, column c) has ID r*22+c.  Thus IDs are 0 through 483.
Two vertices have an available undirected edge exactly when their grid cells share
a side: their coordinates differ by 1 in exactly one coordinate and agree in the
other.  Diagonal and wraparound edges do not exist.

Find one simple closed loop that visits every vertex exactly once and uses every
forced edge below.  A forced edge a-b is undirected.  The forced edges are:
0-22 1-2 3-4 5-6 7-8 9-31 10-32 11-12 13-14 15-16 17-39 18-40 19-20 21-43 23-24 25-26 27-28 29-30 33-34 35-36 37-38 41-42 44-66 45-46 47-48 49-71 50-72 51-52 53-75 54-76 55-77 56-78 57-79 58-80 59-60 61-83 62-84 63-64 65-87 67-68 69-70 73-74 81-82 85-86 88-110 89-111 90-112 91-92 93-115 94-116 95-117 96-118 97-98 99-100 101-123 102-124 103-104 105-106 107-108 109-131 113-114 119-120 121-122 125-126 127-128 129-130 132-154 133-155 134-156 135-157 136-158 137-138 139-140 141-163 142-164 143-165 144-166 145-146 147-148 149-171 150-172 151-173 152-174 153-175 159-160 161-162 167-168 169-170 176-198 177-199 178-200 179-180 181-203 182-204 183-205 184-206 185-186 187-209 188-210 189-211 190-212 191-213 192-214 193-215 194-216 195-196 197-219 201-202 207-208 217-218 220-242 221-222 223-224 225-226 227-249 228-250 229-230 231-232 233-255 234-256 235-257 236-258 237-238 239-240 241-263 243-244 245-246 247-248 251-252 253-254 259-260 261-262 264-286 265-287 266-288 267-289 268-290 269-270 271-293 272-294 273-274 275-297 276-298 277-278 279-280 281-282 283-305 284-306 285-307 291-292 295-296 299-300 301-302 303-304 308-330 309-310 311-312 313-335 314-336 315-316 317-339 318-340 319-341 320-342 321-343 322-344 323-345 324-346 325-347 326-348 327-349 328-350 329-351 331-332 333-334 337-338 352-374 353-375 354-376 355-377 356-378 357-379 358-380 359-381 360-382 361-362 363-364 365-387 366-388 367-389 368-390 369-370 371-372 373-395 383-384 385-386 391-392 393-394 396-418 397-419 398-420 399-421 400-422 401-402 403-425 404-426 405-406 407-408 409-410 411-433 412-434 413-414 415-437 416-438 417-439 423-424 427-428 429-430 431-432 435-436 440-462 441-442 443-465 444-466 445-467 446-468 447-448 449-450 451-452 453-475 454-476 455-456 457-458 459-460 461-483 463-464 469-470 471-472 473-474 477-478 479-480 481-482

Represent the loop by exactly 484 comma-separated vertex IDs v0,...,v483
in cyclic order.  Every ID must occur exactly once.  Consecutive IDs must share an
available edge, including v483 back to v0.  The starting vertex and direction
are arbitrary; do not repeat v0 at the end.

Give your final answer inside <answer></answer> tags, as comma-separated integers.
Example: <answer>0, 1, 5, 4</answer>
Output nothing else inside the tags.
```

One valid answer is:

```text
0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 31, 30, 29, 51, 52, 53, 75, 74, 73, 95, 117, 116, 94, 72, 50, 28, 27, 26, 25, 24, 23, 45, 46, 47, 48, 49, 71, 70, 69, 91, 92, 93, 115, 137, 138, 139, 140, 141, 163, 185, 186, 187, 209, 231, 232, 210, 188, 189, 211, 233, 255, 254, 253, 252, 251, 273, 274, 275, 297, 319, 341, 363, 364, 342, 320, 321, 343, 365, 387, 386, 385, 407, 408, 409, 410, 388, 366, 367, 389, 411, 433, 455, 456, 457, 458, 436, 435, 434, 412, 413, 414, 392, 391, 390, 368, 346, 324, 302, 301, 323, 345, 344, 322, 300, 299, 298, 276, 277, 278, 256, 234, 212, 190, 191, 213, 235, 257, 279, 280, 281, 282, 260, 259, 258, 236, 237, 238, 239, 240, 218, 217, 216, 194, 172, 150, 128, 127, 149, 171, 193, 215, 214, 192, 170, 169, 168, 167, 166, 144, 122, 121, 143, 165, 164, 142, 120, 119, 118, 96, 97, 98, 99, 100, 101, 123, 145, 146, 147, 148, 126, 125, 124, 102, 103, 104, 82, 81, 80, 58, 36, 35, 57, 79, 78, 56, 34, 33, 55, 77, 76, 54, 32, 10, 11, 12, 13, 14, 15, 16, 17, 39, 38, 37, 59, 60, 61, 83, 105, 106, 84, 62, 63, 64, 42, 41, 40, 18, 19, 20, 21, 43, 65, 87, 86, 85, 107, 108, 109, 131, 153, 175, 174, 152, 130, 129, 151, 173, 195, 196, 197, 219, 241, 263, 285, 307, 306, 284, 262, 261, 283, 305, 327, 349, 348, 326, 304, 303, 325, 347, 369, 370, 371, 372, 350, 328, 329, 351, 373, 395, 394, 393, 415, 437, 459, 460, 438, 416, 417, 439, 461, 483, 482, 481, 480, 479, 478, 477, 476, 454, 432, 431, 430, 429, 428, 427, 449, 450, 451, 452, 453, 475, 474, 473, 472, 471, 470, 469, 468, 446, 424, 423, 445, 467, 466, 444, 422, 400, 378, 356, 357, 379, 401, 402, 380, 358, 336, 314, 292, 291, 290, 268, 269, 270, 248, 247, 246, 245, 267, 289, 311, 312, 313, 335, 334, 333, 355, 377, 399, 421, 420, 398, 376, 354, 332, 331, 353, 375, 397, 419, 441, 442, 443, 465, 464, 463, 462, 440, 418, 396, 374, 352, 330, 308, 309, 310, 288, 266, 244, 243, 265, 287, 286, 264, 242, 220, 198, 176, 154, 132, 133, 155, 177, 199, 221, 222, 223, 224, 225, 226, 227, 249, 271, 293, 315, 316, 317, 339, 338, 337, 359, 381, 403, 425, 447, 448, 426, 404, 405, 406, 384, 383, 382, 360, 361, 362, 340, 318, 296, 295, 294, 272, 250, 228, 229, 230, 208, 207, 206, 184, 162, 161, 183, 205, 204, 182, 160, 159, 181, 203, 202, 201, 200, 178, 179, 180, 158, 136, 114, 113, 135, 157, 156, 134, 112, 90, 68, 67, 89, 111, 110, 88, 66, 44, 22
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the final `22` returns `(False, "wrong length: expected 484 vertex IDs, got 483")`.

## Difficulty presets

| Preset | `n` | Grid | Vertices | Structural-space digits | Status |
|---|---:|---:|---:|---:|---|
| `standard` | 11 | 22×22 | 484 | 544 | **ships; oracle held** |
| `hard` | 15 | 30×30 | 900 | 1,133 | available; not reached |
| `extreme` | 20 | 40×40 | 1,600 | 2,215 | available; not reached |

The structural space is `(m-1)!·2^(m-1)` for `m` forced pairs, modulo rotation and reversal. `escalate` safely increases `n`; inverse planting prevents unsatisfiability. An exploratory `n=8` preset was rejected after the 2×2 cycle-merging attack solved 4/8 seeds in 64 restarts, even though the first oracle run had held it.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 9/9 planted instances verified (3 presets × 3 seeds) |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 484-vertex answer recovered from prose and a Markdown fence |
| G4 | **0/200,000** valid random candidates; candidates are complementary grid perfect matchings, so only global one-cycle connectivity is unresolved |
| G5 | At `n=2`, seeds 2/3/5 had 1/2/2 solutions out of 645,120 (`1.55e-6` to `3.10e-6`) |
| G6 | Coarse-2×2 signature, deterministic greedy, 512-restart path greedy, and 64-restart matching/cycle-merging attacks each solved **0/8** shipping instances |
| G7 | Doubling `n` built 1,936 vertices and the plant verified |
| G8 | 160/160 D4-plus-input-order/orientation invariance checks, 160/160 carried-answer checks, and 20/20 unrelated keys distinct |

The machine-readable measurements are in `selftest_report.json`.

## Oracle hardening loop

The required four-vendor-pool harness stopped at round 0 with `verdict: hardened`. An earlier run was discarded after repeated Grok timeouts; the final script-owned transcript contains these rows:

| Preset | Seed | Model | Outcome | Recorded reason |
|---|---:|---|---|---|
| `standard` | 1560898874 | Grok 4.6 | Error; excluded | no complete response in 900 seconds |
| `standard` | 992478894 | Claude Sonnet 5 | Failed | emitted nothing after using all 32,000 completion tokens (`length`) |
| `standard` | 1326953006 | Gemini 3.1 Pro Preview | Failed | parsed 715 IDs; expected 484 |
| `standard` | 494511788 | GPT-5.6 Terra | Failed | parsed 539 IDs; expected 484 |

The Claude row is honestly a length-budget failure, not an incorrect parsed witness. Both visible answers parsed, so neither failure is a parser-contract bug. Full records and timings are in `llm_loop_transcript.jsonl`; `.meta.json` records the final master seed, pool, and verdict.

## Use

```python
import gen_2508_11570 as grand_tour

params = grand_tour.DIFFICULTY[grand_tour.SHIPPING_DIFFICULTY]
inst = grand_tour.make_instance(seed=42, **params)
question = grand_tour.render(inst)
candidate = grand_tour.parse_answer(model_output)
ok, reason = grand_tour.verify(inst, candidate)
```

From the repository root:

```bash
python3 results/2508.11570/gen_2508_11570.py
bash scripts/emit.sh 2508.11570 20 standard
```

## Caveats

- The paper proves worst-case ASP-completeness, not average hardness of this planted distribution. Plants are boundaries of uniformly sampled coarse-grid spanning trees. The explicit construction attack failed at the shipping size, but a specialized algorithm may find a subtler signature.
- G4 is stricter than random vertex permutations: it samples randomized augmenting-path perfect matchings, so local edge, degree, uniqueness, and forced-edge constraints already hold in the underlying 2-factor. The sampler is not uniform, and 0/200,000 on one shipping instance is empirical—not proof that every seed or prior has probability below `1e-6`.
- The panel did not try a full SAT/ILP solver, transfer-matrix dynamic programming, exhaustive `n=11` backtracking, or a learned attack. External evidence is three medium-effort deciding calls; one emitted nothing because its reasoning hit the token cap. Grok’s timeout supplied no hardness evidence.
- Full-grid instances become easy with no forced edges or when two forced incidences determine every vertex. Reducing below `n=11` is unsafe: the cycle-merging attack broke `n=8`.
- Coordinates are semantic and fixed by the statement. `canonical_key` exactly removes forced-edge order/orientation and all eight square rotations/reflections; it does not solve abstract graph isomorphism under coordinate-destroying permutations, which are not symmetries of this coordinate-defined family.
