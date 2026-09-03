# Rejected: arXiv 2410.07666

Paper: David Eppstein, [“Computational Complexities of Folding”](https://arxiv.org/abs/2410.07666).

## Decision

No generator from this attempt should ship. The final candidate fails mandatory
gate G6: a cheap random-restart WalkSAT/min-conflicts attack finds a verified
witness on **8/8** shipping instances. This overrides the LLM harness's
`hardened` verdict. The retained module, self-test report, and script-owned
transcript are diagnostic evidence only.

## Why the triaged reconfiguration family was not used

Sections 5.1–5.2 define “flaps and flips”: a state places every hinged square on
one side of its hinge, and a move changes one flap while preserving all overlap
and above/below constraints. Theorem 4 proves pairwise reachability
PSPACE-complete, through NCL (Lemma 11).

That does not yield an admissible generator under this task's witness contract.
An unrestricted reachability witness may contain exponentially many flips, so
it is an unbounded-length object. Sampling a short legal path first and adding a
polynomial move bound makes verification easy, but the paper gives no hardness
result for that planted, bounded problem. Theorem 4 cannot be cited for the
restricted distribution. Therefore the prior-triage “hidden move sequence” idea
fails H (and the unrestricted version fails the bounded-witness requirement).

## Alternative tested: the finite NAE folding-signal core

Section 3.3 defines NAE3SAT and describes the flat-folding reduction in which a
variable signal has two folding states and a clause gadget accepts exactly when
its three possibly negated signals are not all equal. Theorem 2 transfers the
ETH lower bound to bounded-ply crease patterns when cell-adjacency treewidth is
allowed to grow. Theorem 1 identifies the easy regime that must be avoided:
flat folding takes `(p!)^O(w) n^2` time for ply `p` and treewidth `w`, so both
parameters cannot remain small.

The experimental module samples a Boolean witness first, constructs a regular
degree-7 factor graph, and independently chooses every clause polarity from the
six patterns satisfied by that witness. Every variable has the same occurrence
degree, and clause polarities do not use a visibly different distribution for
planted and decoy signals. A candidate is one signed token per signal; checking
all NAE gadgets is exact and linear.

This is only the combinatorial signal layer of the paper's geometric reduction,
not a coordinate-level crease-pattern generator. Even if that abstraction were
accepted as the family, its planted distribution is easy.

## Measured evidence

| Check | Result |
|---|---:|
| Planted witnesses | 15/15 verified |
| Corruptions | 5/5 rejected with distinct reasons |
| Parser round-trip | passed |
| Structure-aware uniform guesses | 0/200,000 |
| Exact small probe (`n=18`) | 4 / 262,144 solutions (`1.5259e-5`) |
| Literal-imbalance attack | 0/8 |
| Deterministic greedy attack | 0/8 |
| 5,000-node DPLL + unit propagation | 0/8 at `n=192` |
| Signed spectral rounding | 0/8 |
| WalkSAT, 32 restarts × `200n` moves | **8/8 solved** |
| Canonical-key composed relabellings | 20/20 invariant and witnesses carried |
| Unrelated canonical keys | 20/20 distinct |

An earlier `n=96, degree=7` preset was also rejected because the 5,000-node
DPLL attack solved 3/8 seeds. Increasing to `n=192` defeated that capped DPLL,
but did not defeat proper randomized local search. A diagnostic `n=384` sweep
still let the same WalkSAT attack solve 7/8 seeds. Per the task instructions I
did not continue hand-tuning after this failure.

## Oracle transcript

The required harness first solved all three `n=12` instances. At `n=192`, Grok
and GPT-5.6-terra returned parsed assignments rejected respectively at clauses
C012 and C001. Claude used its entire 32,000-token completion budget and emitted
no answer; the harness records that as a length-limited failure. It therefore
wrote `verdict: hardened` for `n=192, degree=7`.

That transcript is useful evidence that LLM failure alone is insufficient here:
a small, conventional randomized CSP heuristic solves every panel seed. G6 is
false in `selftest_report.json`, `all_passed` is false, and this result is
intentionally rejected.
