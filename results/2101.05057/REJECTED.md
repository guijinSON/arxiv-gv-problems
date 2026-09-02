# Rejected: planted reset words in strongly connected partial DFAs

Paper: Mikhail V. Berlinkov, Robert Ferens, Andrew Ryzhikov, and Marek
Szykuła, *Synchronization of strongly connected partial DFAs and prefix
codes*, [arXiv:2101.05057](https://arxiv.org/abs/2101.05057) (v4, 3 June
2026).

## Decision

The proposed family fails **H (hardness)**. I therefore stopped at Step 0 and
did not create a generator, self-test report, README, or oracle-loop
transcript. Those artifacts would misrepresent a polynomial-time constructive
problem as hard witness search.

## Exact definition

Section 2 defines a partial DFA as a finite state set `Q`, an alphabet `Sigma`,
and a possibly undefined transition for each state/letter pair. Applying a
word discards every state whose run encounters an undefined transition. The
word's rank is the number of distinct surviving destination states. A **reset
word** is exactly a word of rank 1: at least one run must survive, and all
surviving runs must finish in one state. It need not be defined on every state.

This distinction matters. Section 1.5 calls a word defined on every state and
mapping all states to one state *carefully synchronizing*, and explicitly says
that this is not the paper's reset-word definition.

The proposed inverse generator could sample a word first, arrange transitions
so that its image has size one, and verify it by replaying the transitions.
Thus G and V are possible. They do not imply H.

## Why H fails

Section 3.5, Proposition 3.12 gives constructive polynomial-time algorithms
for the exact regime in the title:

- synchronizability of a strongly connected partial DFA is decided in
  `O(|Sigma| n^2)` time;
- a word of **minimum nonzero rank** is found in `O(|Sigma| n^3)` time (apart
  from storage for the output word).

The construction marks compressible unordered state pairs by reverse BFS and
then repeatedly applies a shortest pair-compressing word to the current image.
Lemma 3.6 (the paper's `lem:strcon_minimal_rank`) is the strong-connectivity
fact that makes this iteration reach the global minimum nonzero rank.

On every instance produced by the proposed planter, a reset word exists, so
the minimum nonzero rank is 1. Proposition 3.12 therefore returns a valid
reset-word witness directly. The solver need not guess the planted word or
recover any hidden construction. Increasing `n`, adding decoys, hiding state
labels, or making the naive word space exponential merely enlarges a
polynomial-time pair-compression computation.

The same obstruction covers the paper's finite-prefix-code/literal-automaton
special case. Theorem 3.18 even constructs a linear-length, logarithmic-rank
word in polynomial time, and Corollary 3.19 supplies a polynomial reset-length
upper bound for synchronizing literal automata. None of these results creates
a hard positive-witness search regime.

## Why nearby variants were not substituted

- **Ask whether a reset word exists.** This is a yes/no answer, not a witness,
  and Proposition 3.12 decides it in polynomial time anyway.
- **Ask for a shortest reset word or the reset threshold.** Making optimality
  the claim violates the witness contract. Adding an externally chosen length
  bound would define a different constrained problem; this paper gives no
  hardness theorem or answer-first hard-instance construction for such a
  planted distribution.
- **Drop strong connectivity.** Section 1.5 notes PSPACE-completeness for
  general partial DFAs, but that is explicitly the regime the paper excludes
  to obtain its algorithms. Replacing the title regime with arbitrary partial
  automata would abandon the proposed paper family, and the paper supplies no
  inverse generator whose planted distribution inherits the cited worst-case
  hardness.
- **Use careful synchronization.** Section 1.5 cites PSPACE-completeness and
  exponential shortest witnesses for this different notion, expressly to
  contrast it with the notion studied in the paper. The paper neither develops
  that problem nor provides a bounded, answer-first hard construction; merely
  planting a careful word would not establish hardness of the generated
  instances.
- **Use the lower-bound automata in Section 4.** Proposition 4.2 is an explicit
  construction with a known quadratic reset threshold. It is useful for an
  extremal bound, not for hiding a witness from a solver.

## Gate outcome

| requirement | result |
|---|---|
| G -- sample the answer first | Pass in principle: plant a word and its rank-1 action |
| H -- no known polynomial-time or closed-form method | **Fail: Proposition 3.12 constructs a minimum-rank word in `O(|Sigma| n^3)`** |
| V -- cheap exact verification | Pass: replay the word from every state and require a singleton nonempty image |

Because H fails analytically in the shipped parameter regime, running 200,000
random guesses or the LLM hardening harness would not be meaningful evidence
and would contradict the instruction to stop after a Step-0 rejection.
