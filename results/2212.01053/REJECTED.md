# Rejected: arXiv 2212.01053

Paper: Dragan Mašulović, [*Deducibility in Sudoku*](https://arxiv.org/abs/2212.01053) (v3, 17 April 2026).

## Decision

This paper does not contain a problem family satisfying **G, H, and V** simultaneously. A completed classic Sudoku grid is an easy-to-check witness and can be planted before clues are removed, but the paper defines only the fixed classic `9 x 9` game. It gives no scalable order parameter and no computational-hardness theorem or hard planted distribution. Consequently the proposed family fails **H**, and it cannot pass the mandatory **G7 scaling** gate. I stopped at Step 0 rather than manufacture a generalized problem not studied in the paper, claim unmeasured gates, or run the oracle loop on a family already ruled out analytically.

## What the full paper actually defines

Section 3 fixes Sudoku propositions to `r_i c_j not-approximately d` with all three indices in `{1,...,9}`. Its three domain axioms enforce distinct uniquely determined values in each of the nine rows, nine columns, and nine `3 x 3` boxes.

Section 4 is more precise than the ordinary clue-grid description in the introduction:

- a grid is a `9 x 9` matrix whose entries are nonempty subsets of `{1,...,9}`;
- a full grid has a singleton set in every cell;
- a Sudoku grid satisfies the row, column, and box axioms;
- a grid `B` is compatible with `A` when every cell-set of `B` is a subset of the corresponding cell-set of `A`;
- a solution is a compatible full grid (subsequent semantic statements and the main theorems quantify over full Sudoku grids).

Thus the paper formalizes candidate elimination for one fixed board. It does not define generalized `b^2 x b^2` Sudoku, Latin-square completion of growing order, or another input family whose dimension can tend to infinity.

Section 5 proves soundness and completeness of the proposed logic. Its central corollary is:

```text
a Sudoku grid has a unique solution if and only if it has a logically deducible solution.
```

This is a semantic/logical equivalence, not a complexity result. The paper neither claims NP-hardness nor analyzes a parameter regime in which finding a solution is computationally hard. In fact, the appendix notes that there are exactly `9^3 = 729` Sudoku propositions, another explicit indication that the formal universe is fixed.

Sections 6 and 7 define when two boards are essentially the same. The allowed transformations include the eight geometric symmetries, row and column shuffles that preserve the three bands/stacks, and arbitrary digit relabellings. Section 8 uses those transformations to prove Gurth's Symmetrical Placement Theorem. These results are important for canonicalization but do not create a growing search problem.

## Why the proposed planted generator fails

### Fixed classic Sudoku is not a hard asymptotic family

Sampling a completed grid first and deleting entries would satisfy inverse generation for the search task “return any completion.” Verification is exact and cheap: check all 81 entries, the clues, and every row, column, and box. However, every instance has the same fixed 81 cells and nine symbols. There are finitely many possible instances and finitely many answers; the introduction quotes `6,670,903,752,021,072,936,960` completed grids. Formally, any problem on this fixed domain has a constant-time lookup algorithm. More practically, `n` cannot control board order, so doubling `n` cannot produce a size-doubled instance as G7 requires.

Using `n` as “number of blank cells” does not repair this. It is bounded by 81, and hardness is not monotone: zero blanks exposes the witness, while 81 blanks admits any completed grid and is easier to satisfy than a carefully constrained puzzle. The paper supplies no theorem identifying an intermediate clue count as a hard regime.

### Removing clues does not establish uniqueness or deducibility

Deleting clues preserves the planted completion, but it does not prove that the completion is unique. If the requested witness were merely any completion, uniqueness is irrelevant but the fixed-size H/G7 failure remains. If the requested object were specifically a *deducible* solution, Section 5 equates that claim with uniqueness. Checking the submitted grid alone would not verify uniqueness; a checker would need to rule out every other completion. The paper gives a logical equivalence, not a cheap uniqueness certificate or an inverse construction guaranteed to retain uniqueness after random clue deletion.

### A deduction is not a suitable replacement witness

Section 5 defines a proof as a finite but unbounded sequence of formulas, each an axiom, a premise, or a modus-ponens consequence. The Sudoku-axiom set is itself defined semantically as all formulas true in every full Sudoku grid. A purported proof therefore has unbounded witness length, and recognizing arbitrary axiom lines is not the requested cheap substitute-and-compare verification. The completeness proof establishes existence; it does not provide a bounded proof format or efficient proof-search algorithm.

### Generalized Sudoku would be a different paper regime

One could replace 9 by a growing order and appeal to known hardness results for generalized Sudoku. That would produce a plausible scalable CSP, but neither the generalized definition nor those hardness results occur in this paper. The requested family must come from the given paper, and the README would have no honest paper section or theorem supporting such a regime. Importing an external NP-completeness theorem would therefore not cure this Step-0 failure.

### Random transformations do not create genuine diversity

A common generator starts with one patterned solution and applies digit permutations, band/stack permutations, within-band/within-stack row/column permutations, and rotations/reflections. Section 7 explicitly classifies these as Sudoku transformations and defines transformed grids as not essentially different. Under the required G8 key, all such outputs must collapse to the same problem. A one-template generator would therefore also fail canonical distinctness even though its raw encodings and seeds differ.

## Gate outcome

| requirement | result |
|---|---|
| G — sample a witness first | Possible for a fixed classic puzzle: plant a full grid, then retain compatible clues/candidate sets |
| H — no known polynomial-time or closed-form method, with a large scalable answer space | **Fail: the paper's universe is the one fixed 9 x 9 board; it provides no growing hard regime or complexity theorem** |
| V — cheap exact witness checking | Pass for a completed grid; not established for uniqueness/deducibility or arbitrary formal proofs |
| G7 — difficulty grows with `n` and size doubling still works | **Fail: board size and alphabet are fixed at 9, and clue count is bounded and non-monotone** |
| G8 — structural diversity under relabelling | A canonicalizer must quotient Section 7's transformations; template-plus-transform generation collapses to one key |

No `gen_2212_01053.py`, `selftest_report.json`, `README.md`, or `llm_loop_transcript.jsonl` was created. Those files would falsely imply that a compliant generator reached Steps 1–5. Running `scripts/harden.py` would likewise contradict the instruction to stop immediately once G, H, or V fails.
