# Rejected: arXiv 2602.19989

## Decision

No generator is shipped. The natural witness family from this paper fails **H
(hardness)**, and the proposed inverse generator also fails **G4 (guess
resistance)**. Running the LLM hardening loop after either failure would not make
the family acceptable.

Paper: Simone Costa and Stefano Della Fiore, [*New bounds for (weak)
sequenceability in `Z_k`*](https://arxiv.org/abs/2602.19989), especially Sections
1--3.

## Exact problem read from the paper

Section 1 defines a valid ordering of a finite set `A` in an abelian group as a
permutation `a_1,...,a_m` whose partial sums
`p_i = a_1 + ... + a_i` are pairwise distinct. A sequencing is a valid ordering
with `p_i != 0` for every `1 <= i < m`. Thus a proposed permutation is a compact
witness and can be checked exactly in linear time using modular addition and a
set of previously seen partial sums. G and V would therefore be straightforward.

The relevant regimes are existence regimes, not hardness regimes:

- Theorem 1.3 proves sequenceability when
  `|A| <= exp(c (log p)^(1/3))`, where `p` is the least prime divisor of the
  modulus.
- Theorem 1.4 proves `t`-weak sequenceability when
  `t <= exp(c (log p)^(1/4))`.
- Sections 2 and 3 prove these statements by probabilistic splitting and
  ordering, anti-concentration, the Lovasz Local Lemma, and a union bound. The
  paper states no NP-hardness or other computational lower bound for finding the
  ordering.

## Why H is not supportable

The paper itself says in Section 1 that the prime case was recently settled by
Pham and Sauermann. Their cited paper, [*On Graham's rearrangement
conjecture*](https://arxiv.org/abs/2602.15797), is not merely a lookup
classification: Section 5 starts from a uniformly random permutation and repairs
its zero-sum intervals with bounded-distance transpositions. Lemmas 5.1--5.3
bound the total probability of the bad starting events by `2/25`; the proof of
Theorem 1.2 then explicitly chooses each repair from a constant-size window.

For every fixed `alpha`, this proof yields a Las Vegas randomized polynomial-time
search procedure in the regime
`C_alpha <= |A| <= p^(1-alpha)`: sample a permutation, compute all zero-sum
intervals, try the bounded set of repairs described in Section 5, verify, and
restart on failure. A good start occurs with probability at least `23/25`, and
all tests and repairs are polynomial in `|A|` (with `alpha` fixed). The prime
specialization of Theorem 1.3's much sparser asymptotic regime lies inside this
range for any suitable fixed `alpha`. It therefore cannot satisfy the task's
requirement that there be no known polynomial-time method.

Restricting a generator to composite moduli would avoid that particular theorem,
but it would not supply positive hardness evidence: arXiv 2602.19989 proves only
existence there and gives no hard search regime. Designing an unrelated encoded
CSP in the residues would go beyond what the paper establishes and would still
need an independent hardness argument. The paper's `t`-weak relaxation likewise
comes with existence machinery rather than a hardness result.

## Direct failure of the proposed planted generator

I also tested the triage proposal exactly as a solver would: sample a valid
ordering first, discard its order to obtain `A`, then guess by uniformly shuffling
the supplied elements. This sampler already enforces every obvious structural
constraint (the answer is a permutation of `A`), so it is the required
structure-aware prior rather than a sample from `Z_k^n`.

Parameters and result:

| quantity | value |
|---|---:|
| modulus | `2^61 - 1 = 2305843009213693951` (prime) |
| `|A|` | 32 |
| independent planted instances | 8 |
| random permutations per instance | 25,000 |
| valid guesses | **200,000 / 200,000** |
| measured `P(random guess)` | **1.0** |
| required by G4 | `< 1e-6` |

This is the expected failure mode in the sparse regime: the modulus is enormous
relative to the `O(|A|^2)` intervals that could create a partial-sum collision,
so generic plants make almost every ordering valid. Making `A` highly structured
to force many zero-sum relations would abandon the same-distribution generic
plant and, absent a theorem, provides no basis for claiming H.

## Gate disposition

| gate/property | result |
|---|---|
| G (inverse generation) | feasible |
| V (exact verification) | feasible in linear time |
| H (no known efficient method) | **failed** in the prime theorem regime |
| G4 structure-aware guessing | **failed: 200,000/200,000 hits** |
| Remaining gates | not run after mandatory rejection |
| LLM hardening loop | not run; its prerequisites failed |

Accordingly, `gen_2602_19989.py`, `selftest_report.json`, and an oracle transcript
were intentionally not created.
