# Rejection: arXiv 1507.08094

Paper: Sebastian E. Schmittner, [*A SAT-based Public Key Cryptography
Scheme*](https://arxiv.org/abs/1507.08094) (v3, 2015).

## Decision

No generator is shipped. The natural family passes **G** by inverse generation
and **V** by direct Boolean evaluation, but it fails **H on Track A** at every
writable parameter regime that was tested. It also has no distinct compact
route that could support **Track B**, and the paper's own security sizes exceed
the 256-atom answer cap.

This is a Step-0 rejection, so no `gen_1507_08094.py`, self-test report, or LLM
hardening transcript was produced.

## The paper's exact native problem

Section 2.1 defines a public key as a planted random `k`-SAT formula. Key
generation is:

1. choose a uniformly random private assignment in `{0,1}^n`;
2. choose `k` distinct variables and their literal signs uniformly;
3. retain the clause exactly when the private assignment satisfies it; and
4. repeat until `m` clauses have been retained.

Thus the proposed benchmark would hand the solver the resulting CNF and ask for
any satisfying assignment. The held private assignment is known without solving
the generated instance, so G is genuine inverse generation. A checker only
needs to test one literal per satisfied clause (at most `mk` literal tests), so V
is exact and cheap. The witness is the paper's native Boolean assignment, not a
surrogate.

Section 2.1 says that the intended hard region has `m` just above the critical
ratio and warns that other scalings are easier. Appendix E locates the empirical
maxima at approximately `m=5n` for planted 3-SAT and `m=10n` for planted 4-SAT.
There is no average-case hardness theorem for this generator. Appendix A gives
worst-case reductions for sets of functions related to the ciphertext decoding
problem, while Sections 3 and 6 explicitly say that decoding itself has not been
proved hard.

## Track A fails

Worst-case NP-completeness of SAT does not establish hardness for the paper's
conditioned-random distribution. I generated clauses exactly by Section 2.1 and
ran construction-aware and domain-standard attacks. Every returned assignment
was re-evaluated against the CNF before being counted as a success.

### Planted 3-SAT, `m=5n`

The exact MiniSat implementation benchmarked by Appendix E was run on 20 seeds
at each size:

| `n` | solved | median wall time | worst wall time | largest conflict count | largest propagation count |
|---:|---:|---:|---:|---:|---:|
| 128 | 20/20 | 0.0083 s | 0.0202 s | 687 | 18,094 |
| 192 | 20/20 | 0.0292 s | 0.0631 s | 9,048 | 301,393 |
| **256** | **20/20** | **0.3862 s** | **1.3797 s** | **79,502** | **3,352,147** |

At `n=256`, MiniSat used at most 96,312 decisions. This mandatory standard
attack would have `successes=20`, whereas a Track-A G6 panel requires zero.

The answer cap is load-bearing here. Appendix E estimates about `n=1000`--`1500`
for a 100-year single-thread MiniSat cost in the tested 3-SAT ratios. Section 6
recommends `n>2^10` against one PC, at least `n>2^11` under parallelism, and
preferably `n>2^14` in view of SAT Competition results. All of those private-key
vectors exceed the benchmark's limit of 256 atomic answer elements.

### Planted 4-SAT, `m=10n`

Appendix E reports a smaller 100-year estimate, about `n=350`, so this alternative
was tested separately. MiniSat solved 8/8 seeds at `n=96` in at most 3.16 seconds,
but hit a five-second diagnostic cap on 8/8 seeds at `n=128`. That does not rescue
Track A: a majority-initialized WalkSAT attack succeeds broadly throughout the
writable range.

| `n` | verified WalkSAT successes | flip budget per seed | observed successful flips | observed successful wall time |
|---:|---:|---:|---:|---:|
| 96 | 8/8 | 400,000 | 100--12,110 | 0.008--0.303 s |
| 128 | 8/8 | 400,000 | 679--133,048 | 0.012--1.974 s |
| 160 | 8/8 | 400,000 | 1,354--193,667 | 0.017--6.102 s |
| 192 | 7/8 | 400,000 | 6,092--141,841 | 0.365--4.917 s |
| 224 | 6/8 | 400,000 | 26,623--203,284 | 0.360--6.089 s |
| **256** | **6/8** | **400,000** | **4,694--283,822** | **0.056--3.325 s** |

The attack begins with the literal-sign majority for each variable, the direct
statistical footprint of accepting only clauses satisfied by the planted key,
and then applies ordinary noisy minimum-break local repair. Even one verified
success disqualifies a Track-A attack entry; the maximum writable instance gives
six successes in eight attempts. Moving away from `m/n=10` is not justified as
a hardening axis: Appendix E identifies that ratio as the 4-SAT critical/hard
setting, and Section 2.1 says moving away from the critical scaling makes SAT
instances easier.

The paper cites quiet planting in its discussion of how changing rejected
clauses can alter the distribution, but it does not use that construction for
its key generator. Replacing Section 2.1 with the cited paper's reweighted
ensemble would be a different generator, and it would not solve the no-tool
route problem below.

## Mechanical cost versus compact route (Track B audit)

Track B is not a fallback label for a generic hard SAT search. It requires a
short solver-visible invariant or change of variables whose execution is
substantially smaller than the mechanical algorithm.

For the maximum writable 3-SAT candidate, the mechanical route is MiniSat:
median 0.3862 seconds, at most 96,312 decisions and 3,352,147 propagations over
20 seeds. The paper supplies no separate compact route to a satisfying
assignment; its construction deliberately samples an unstructured random
private key. The only visible construction-specific clue is literal-sign bias.

For the strongest 4-SAT candidate, even computing that clue requires inspecting
all `km = 4 * 10 * 256 = 10,240` literal occurrences. It does not produce a
certificate: the measured local repair then required at least 4,694 flips on
the easiest successful shipping-size seed and as many as 283,822. Hence the
shortest construction-aware route actually tested costs at least 10,240
literal tallies plus thousands of repair steps, not at most 300 exact
operations. It is the mechanical attack itself, not a compressed alternative.

The compact-route length is therefore **not a hidden dozen-step method**: the
paper-provided route is the same full formula scan and SAT/local-search process,
with a measured lower endpoint of 14,934 primitive tally/flip steps on successful
`n=256` 4-SAT instances. Giving the private assignment, a PRNG seed, occurrence
totals, or a special algebraic rule for its bits would manufacture a shortcut
outside Section 2.1 and would make the corresponding outlier/majority attack
succeed by design.

Thus Track B fails independently of whether one calls MiniSat or WalkSAT
"efficient": there is no mechanical-versus-compact gap, and the only proposed
route exceeds G9(c)'s 300-operation limit by nearly two orders of magnitude even
at its measured minimum.

## Other native candidates do not repair H

| paper object | G | H | V | result |
|---|---|---|---|---|
| Recover a private assignment from the Section 2.1 public key | inverse generation | Track A attacks succeed; no Track-B compact route | evaluate the CNF | rejected |
| Decode one Section 2.2 ciphertext bit | encryption constructs it | only two possible answers, so it is guessable | evaluate at a supplied private key | fails H |
| Decode while also supplying a private-key certificate | encryption constructs both | collapses to the same planted-SAT search above | evaluate CNF and ANF | rejected |
| Produce a Section 5 identification response | prover constructs it | the response either reveals the planted SAT witness or the explicitly chosen relabelling; no new hard search family | exact literal/assignment checks | fails H |
| Use an Appendix A hard-to-decode collection | possible only after choosing a SAT witness | Appendix A proves worst-case reductions, not hardness for a generatable distribution; elementary-function labels are just the private bits | exact Boolean evaluation | no valid Track-A basis |

## Gate accounting

| gate | result | evidence |
|---|---|---|
| G | pass in principle | Section 2.1 samples the assignment before the clauses |
| V | pass in principle | exact CNF evaluation in `O(mk)` |
| H, Track A | **fail** | MiniSat solves 20/20 maximum-size 3-SAT instances; WalkSAT solves 6/8 maximum-size 4-SAT instances |
| H, Track B | **fail** | no distinct compact route; at least 14,934 measured tally/flip steps versus the 300-operation cap |

This is not `cap_bound`: increasing the private-key length past 256 would reach
the paper's more credible SAT-security sizes, but it would only enlarge a random
assignment witness and its uncompressed search. The family lacks the compact
no-tool route required by the benchmark before the output cap is reached.
