# Rejection: the planted `(3,4)` zero-sum-flow distribution is easy

The proposed family passes **G** and **V** but fails **H on Track A**. It inverse-generates a zero-sum 3-flow on an all-negative `(3,4)`-semiregular signed graph, and the checker validates any candidate by exact incident-edge sums. The failure is distributional hardness, not generation or verification.

The source is Section 2.7 of arXiv:1608.06944. Its exact definition identifies a zero-sum `k`-flow with a nowhere-zero `k`-flow on the all-negative signed graph. Theorem 27(ii) reports NP-completeness for zero-sum 3-flow on `(3,4)`-semiregular graphs, while Theorem 27(i) gives a polynomial algorithm for `(2,4)`-graphs with only `O(log n)` degree-4 vertices. The draft is inside the hard theorem's ambient regime, but that worst-case theorem does not cover its planted distribution.

## Decisive attack

Every degree-3 vertex has one of two sign types: a permutation of `(1,1,-2)` or of `(-1,-1,2)`. The draft's exact-2-in-4 propagation finds a consistent type assignment quickly on these planted instances. For fixed types, the remaining problem is **bipartite perfect matching**. Put the two types on opposite sides and join two degree-3 vertices when they share a degree-4 neighbour. Matching them chooses one magnitude-two edge at every degree-3 vertex and balances selected counts of the two types at each degree-4 vertex. Hopcroft–Karp completes the flow and the ordinary checker verifies it.

This type-then-matching attack solved 8/8 seeds at `n=18`, 8/8 at `n=20`, and 8/8 at the largest writable `n=21` (252 edge values against the 256-atom cap). At `n=21` it averaged **0.0249 seconds**, never exceeded **0.0666 seconds**, used two Hopcroft–Karp phases, and scanned roughly **482–500 matching edges**. The sign-type search is exponential in the worst case, so this does not refute Theorem 27; it refutes the Track A claim for the generated distribution.

## Why Track B also does not apply

The **mechanical cost** at the largest writable size is already below 0.07 seconds for the exact construction-aware attack. The **compact route** is not shorter: it is the same exact-2-in-4 propagation followed by the same perfect-matching completion, with hundreds of matching-edge scans and no additional invariant, symmetry, or change of variables. Thus there is no large mechanical-versus-compact gap for a Track B no-tool-compression benchmark.

Increasing `n` cannot rescue the draft within the output contract: `n=21` already has 252 answer atoms, and `n=22` would have 264. This is not a `cap_bound` hard family—the attack has already solved every writable rung—so the correct outcome is rejection of this generator. A different gadget distribution derived from the Monotone NAE-3-SAT reduction may remain possible; this rejection does not claim otherwise.
