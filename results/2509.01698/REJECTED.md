# Rejected at Step 0: arXiv 2509.01698

Paper: Nadzieja Hodur, Monika Pilśniak, Magdalena Prorok, and Ingo
Schiermeyer, [*On k-colorability of (bull, H)-free
graphs*](https://arxiv.org/abs/2509.01698) (2025).

## Decision

No problem generator is shipped. The natural paper-native witness tasks are
generatable and exactly verifiable, but they fail **H on both tracks**.

- **Track A fails.** The paper's main scalable objects are clique expansions of
  odd cycles. Theorem 4 gives necessary-and-sufficient arithmetic conditions for
  their `k`-colorability, and Section 4 constructs a coloring with the circular
  `k`-coloring algorithm plus a short deterministic adjustment. Theorems 6--8
  are structural classifications of the remaining advertised 4- and
  5-colorability regimes. The paper gives no average-case hardness theorem for
  any generated distribution in these classes.
- **Track B also fails.** The Section 4 construction is already the compact
  route: scan the clique sizes and write consecutive color names. At the largest
  symmetric full-coloring instance that stays within the 256-atom answer cap,
  the mechanical route uses 256 modular assignments (278 elementary exact
  operations including the theorem's condition checks), while the compact route
  uses those same 256 assignments. The operation ratio is 1 if the promised
  conditions are trusted and 1.09 if they are rechecked. There is no costly
  mechanical computation for an invariant to compress.

This is an H rejection, not a witness-rule rejection. A coloring is checked by
examining every edge. A non-colorability witness can expose the expanded-cycle
blocks and the violated inequality. Both are finite exact certificates; they
are simply easy to produce in the paper's regime.

Implementation stops before Step 1, as required. No generator, self-test report,
or oracle transcripts were fabricated.

## What the paper actually studies

Section 1 defines a clique expansion
`C_p[k_1,...,k_p]`: replace the `i`th vertex of a chordless cycle by a clique of
size `k_i`, retain every edge inside each clique, and add every edge between
consecutive cliques. It also defines the circular `k`-coloring (`k`-CC)
algorithm: when vertices are numbered consecutively through the blocks, vertex
`m` receives color `((m-1) mod k)+1`.

Theorem 4 states that the odd expansion
`C_(2r+1)[k_1,...,k_(2r+1)]` is `k`-colorable exactly when

1. `k_i + k_(i+1) <= k` for every consecutive pair, and
2. `sum_i k_i <= r*k`.

Section 4 is constructive. It starts with `k`-CC, scans for the first even block
where enough colors can be repeated, and assigns consecutive increasing or
decreasing color intervals to the remaining blocks. Thus the theorem does not
merely decide existence; its proof produces the positive witness.

The paper explicitly identifies further easy structure:

- immediately before Theorem 4, vertices of degree below 4 are removed and
  reinserted because their coloring is called trivial;
- Theorem 10 says a connected `(bull, claw)`-free graph with independence number
  at least 3 is perfect or an odd-cycle clique expansion;
- Theorem 11 says that, in the same class, the presence of an induced cycle of
  length at least 6 forces the graph itself to be a clique expansion of that
  cycle;
- Theorems 6--8 list the exceptional structures that obstruct 4- or
  5-colorability; and
- Fact 22 reduces coloring a graph with independence number 2 to maximum
  matching in its complement via `chi(G)=|V(G)|-nu(complement(G))`.

These are the exact regimes in which a paper-specific family would have to
live. They are classification and direct-construction regimes, not a hard
generated distribution.

## Step-0 mechanical cost versus compact route

I measured the certificate-producing rule on the cap-sized native example

`G = C_7[37,37,37,37,36,36,36]`, `k = 86`.

It has 256 vertices, so its natural coloring witness has exactly 256 atomic
elements. Theorem 4 applies because every adjacent sum is at most 74 and the
total is `256 <= 3*86 = 258`. In this example the unadjusted circular rule
already gives a proper coloring: emit `((m-1) mod 86)+1` for
`m=1,...,256`.

The cost accounting is:

| quantity | measured value |
|---|---:|
| modular color assignments | 256 |
| additions/comparisons/multiplication to recheck both Theorem 4 conditions | 22 |
| total exact operations with recheck | 278 |
| compact-route modular assignments | 256 |
| serialized JSON coloring length | 997 characters |
| coloring atoms | 256 |
| graph edges checked by an exact verifier | 13,917 |

A standard-library Python microbenchmark of
`[(m % 86)+1 for m in range(256)]`, using nine batches of 200,000 evaluations,
had a median time of **0.000003927 seconds per coloring** on this runner.

The compact route is no shorter. Seeing the cyclic structure tells the solver
to use the displayed circular coloring rule, which is exactly the mechanical
algorithm. Every natural explicit coloring must still emit 256 color entries.
Encoding the answer as the formula instead would remove that work, but it would
also make the task an immediate readout of the definition rather than a witness
search. Raising the size only lengthens the identical modular sequence until the
answer cap is hit; it never opens a Track B gap.

## Why the prior planted-coloring proposal does not supply Track A

The introduction says 3-colorability is NP-complete for bull-free graphs. Its
justification is that 3-colorability is NP-complete for `K_3`-free graphs and a
`K_3`-free graph is automatically bull-free. This is a worst-case statement
about the broad bull-free class, cited from prior work; this paper does not give
the reduction or an instance distribution.

Sampling a coloring first and adding random cross-color edges would satisfy G,
but it would not satisfy H on the evidence in this paper:

- worst-case NP-completeness says nothing about that planted distribution;
- arbitrary planted instances need not be claw-free and therefore do not lie in
  the paper's main `(bull, claw)` regime;
- forcing triangle-freeness would be an additional generator design, not a
  reduction central to this paper; and
- no theorem here shows that the planted partition is hidden from spectral,
  greedy, or color-refinement attacks.

Calling this Track A would therefore substitute worst-case hardness for the
required distributional claim. Calling it Track B would require a short
solver-visible recovery invariant distinct from the standard coloring search;
the paper supplies none for such planted graphs.

## Other native witness tasks considered

| candidate family | G and V | why H still fails |
|---|---|---|
| Given clique sizes satisfying Theorem 4, output a proper `k`-coloring | The proof constructs it; edge inequalities verify it exactly | The `k`-CC/Section 4 procedure is linear in the output and is already the compact route |
| Return the chromatic number of an odd-cycle clique expansion | Theorem 4 gives `max(max_i(k_i+k_(i+1)), ceil(sum(k_i)/r))` | The value is obtained by one linear scan; a scalar answer is also guessable unless accompanied by a coloring/lower-bound certificate |
| Certify failure of the adjacent-pair condition | Output vertices of a `(k+1)`-clique | With the blocks exposed, take any `k+1` vertices from the offending consecutive pair; with them hidden, block recovery is the same neighborhood-comparison work for both mechanical and purported compact routes |
| Certify failure of the total-sum condition | Give the cyclic clique partition, or representatives whose closed neighborhoods determine it | With the partition exposed, the certificate is a direct sum; with it hidden, the paper provides no shortcut distinct from computing the true-twin classes and quotient cycle |
| Find one of the exceptional graphs in Theorems 6--8 | A listed induced vertex set is exactly checkable | Planting and hiding a fixed obstruction creates an unanalysed subgraph-search distribution; the classifications do not prove that distribution hard or provide a separate compact decoder |
| Use general bull-free 3-colorability | A planted coloring is easy to generate and verify | Only worst-case NP-completeness is cited; no hard generated distribution or paper-central reduction is supplied |

The hidden-block variants do not rescue Track B. From an adjacency list, the
standard route forms closed neighborhoods, groups true twins, and reads the
cycle quotient. The solver-visible route is the same grouping. If block labels
or fingerprints are exposed to make selection a dozen-step shortcut, then the
statement gives away the block constraint: `random_candidate` must sample one
representative per exposed block, and essentially every such candidate is
valid. That fails the structure-aware guessing test instead of creating
hardness.

## Gate diagnosis

| requirement | result |
|---|---|
| G -- certificate known by construction | **Passes in isolation:** Theorem 4 and its proof construct colorings; violated inequalities construct exact lower-bound witnesses |
| V -- exact witness verification | **Passes in isolation:** compare colors on every edge, or verify the clique partition and integer inequality |
| H -- Track A structural hardness | **Fails:** the main regime has a necessary-and-sufficient test and constructive linear procedure; the only NP-completeness statement is worst-case and does not cover a planted distribution |
| H -- Track B no-tool compression | **Fails:** 256 mechanical modular assignments versus the same 256-step compact route (278 with theorem-condition checks), measured at 3.927 microseconds |
| G4 for scalar reformulations | **Fails:** colorability is binary and the chromatic number has at most 256 possibilities in the cap-sized example |
| Overall | **Rejected at Step 0** |

This rejection is not the bare observation that an efficient algorithm exists.
The paper's certificate algorithm was evaluated at the largest writable natural
example, and its mechanical cost and compact route are essentially identical.
The alternative with genuine worst-case hardness lacks the distributional
theorem that Track A requires and lacks a paper-backed compression insight for
Track B.
