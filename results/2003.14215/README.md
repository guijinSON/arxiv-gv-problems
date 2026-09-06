# arXiv:2003.14215 — key recovery in a difference block cipher

**Paper.** Roberto La Scala, Sharwan K. Tiwari, *Stream/block ciphers,
difference equations and algebraic attacks*, [arXiv:2003.14215](https://arxiv.org/abs/2003.14215)
(cs.CR, cs.SC, math.AC, math.RA).

| field | value |
|---|---|
| `TRACK` | **B** — no-tool compression |
| native domain | algebra |
| object regime | finite_field (GF(2)) |
| computational core | other (key recovery in an explicit difference system) |
| certificate form | integer_tuple (a vector in GF(2)^K — the key) |
| intended intuition | **symmetry**: the round count is a multiple of the key subsystem's period, so the cipher is a power of one fixed permutation |
| `domain_essentiality` | **native** (`reduction_kind = none`) |
| shipping preset | `hard`: K = L = 48, m = 6 (R = 288 rounds), 3 pairs |

The solver is handed the paper's own objects — an explicit difference system
over GF(2) and t-states of its solutions — and `verify` operates on exactly
those objects by re-running the system. Nothing is compiled away.

## What the family is

A *difference block cipher* (Definition 5.6) is a reducible invertible explicit
difference system together with a final clock T; the key is the initial state of
the key subsystem, the plaintext is v(0) and the ciphertext is v(T). Section 7
instantiates this with KeeLoq, equation (7.1):

```
k(t+64) = k(t)
x(t+32) = x(t) + x(t+16) + NL( x(t+1), x(t+9), x(t+20), x(t+26), x(t+31) ) + k(t)
```

This module ships that system shape at reduced size. The solver sees

```
k(t+K) = k(t)
x(t+L) = x(t) + x(t+a1) + x(t+a2) + NL( x(t+p1), ..., x(t+p5) ) + k(t)
```

over GF(2) with L = K, the taps drawn per instance, and NL fixed to KeeLoq's own
truth table `0x3A5C742E` — the module asserts on every run that this table and
the ANF printed in (7.1) agree on all 32 inputs. `x(0)` occurs linearly and
every other term sits at clock >= 1, so Corollary 3.4 makes the system
invertible, which is what Definition 5.6 requires. The key subsystem is a cyclic
permutation of period K (Definition 4.1, Proposition 4.5).

Published: R = m·K, the taps, the truth table, and a handful of
plaintext/ciphertext pairs under one key. Asked for: the K-bit key.
**Checking is cheap and exact** — re-run the difference equation R times per
pair and compare bit strings. No floats appear anywhere.

**Generation is forward-only and the key is sampled first.** `make_instance`
draws the key uniformly from GF(2)^K, draws one plaintext P uniformly, and
computes its *slid partner* `P* = F(P)` — one K-round encryption with the key
already in hand — then encrypts everything for R rounds and shuffles the pair
list. Nothing is ever searched for.

## Why it is hard — Track B

**The algorithm that exists** is the paper's own key-period reduction, Section 5,
final subsection: *"A better strategy is possible when the period of the key
subsystem, say d, is sufficiently small ... we are reduced to compute
V_K(I' + J') for T = 64."* Because R = m·K and the key subsystem has period K,
the encryption is `E = F^m` for the single-period map F, so `E∘F = F∘E`. If two
published plaintexts satisfy `P_j = F(P_i)`, then `(P_i, P_j)` is itself a
*K-round* plaintext/ciphertext pair — and since the block length equals K,
`P_i || P_j` is the **entire internal bit-sequence** of those K rounds. Every
round equation then *defines* one key bit rather than constraining it. The
identical relation holds on the ciphertext side (`C_j = F(C_i)`), which is what
discriminates the true slid pair from the other `s(s-1)-1` ordered hypotheses.
Complexity O(s²·K) GF(2) operations; **measured 384–576 primitive operations**
at the shipping preset over 25 seeds (a wrong hypothesis dies after about two
bits, so only the true one is read to full length).

**The mechanical route** is the algebraic attack this paper is about —
Definition 5.9, an algebraic attack by multiple plaintext/ciphertext pairs,
solved by Gröbner bases or SAT (Sections 6 and 7 run exactly this against Bivium
and KeeLoq). On an *explicit* difference system (Definition 2.1) every round
equation is affine in each single variable, so this attack is unit propagation
plus branching. With R = m·K and m ≥ 2 the first round equation whose left-hand
side is a published ciphertext bit is t = R−L = (m−1)K ≥ K: **every key bit is
already assigned before the first consistency check exists**, so the search tree
cannot be pruned above the leaves. Measured, it spends **1.35 · 2^K search
nodes** (0.5·2^12, 1.5·2^14, 1.35·2^16 at K = 12, 14, 16 with m ≥ 3) and the
count is flat in m past m = 3. Two supporting measurements:

* *Linearisation at degree ≤ 3* of the same system at the shipping preset: 768
  unknowns, 7.55e7 monomials, 864 equations — a rank deficit of 7.55e7. It
  cannot work.
* *Theorem 5.4's elimination* (f'_t = T̄^t(f), which removes the intermediate
  variables and leaves equations in the key alone) blows past 1500 monomials at
  rounds 14–15 of 24 at the `demo` preset (K = 12) and at round 23 of 128 at
  `medium` (K = 32). The degrees explode exactly as Section 5 warns.

So at the shipping preset the mechanical route is **2^48.4 search nodes and
2^60.3 ≈ 1.4e18 primitive operations** against a compact route of **492
operations** — a ratio of **2^51.4**. Measured, not guessed, at the point where
it was capped: 5,755 nodes and 2.19e7 primitive operations in 40.0 s, i.e. 143.9
nodes/s and 3,802 operations per node; extrapolating to 2^48.4 nodes gives
**83,697 years** in this implementation. Plain brute force over the key space
runs at a measured 2,084 keys/s at R = 288 rounds, so 2^48 keys is 1.35e11 s =
**4,279 years**. The compact route, by contrast, is a dozen lines of bookkeeping
plus 48 table lookups, which a model *can* execute in context. That gap is the
Track B claim.

**The easy regime I had to avoid** is documented with numbers in
[`window_analysis.md`](window_analysis.md). Briefly: the obvious family — reduced
rounds R against block length L, with no relation to the key period — is dead.
There the compact route and the standard algebraic attack are *literally the same
algorithm*, and they never separate by more than about one order of magnitude at
any u = R−L. At u = 0 the standard attack costs 1.12e3 primitive operations
against a 1.6e2 compact route (7:1); by u = 22, where the standard attack first
reaches 1e6 operations, the compact route needs more than 2^7 branch decisions,
i.e. ≥1.5e5 operations — 150× over G9's route cap. Tying R to the key period is
what decouples them.

## Worked example (`demo`, seed 3)

`K = L = 12`, `m = 2` (R = 24 rounds), 2 pairs. The full rendered statement is
reproduced in `demo_example.txt`; the data is

```
x(t+12) = x(t) + x(t+1) + x(t+4) + NL(x(t+5),x(t+6),x(t+8),x(t+10),x(t+11)) + k(t)
NL = 0x3A5C742E        R = 24

P1 = 100000011110      C1 = 000101010010
P2 = 001010110110      C2 = 101100001000
```

The answer is `111111011100`. `verify` returns `(True, 'ok')` on it; flipping
bit 5 gives `(False, 'ciphertext mismatch on pair 1 (3 of 12 bits differ)')` and
dropping the last bit gives `(False, 'key length 11, expected 12')`.
`enumerate_all` confirms **1 valid key out of 4096**.

**A person can solve this one by hand.** The slid ordered pair here is `(1, 0)`:
P1 = F(P2), verified above. So `P2 || P1` is exactly x(0..23) and the
twelve round equations read the key off directly: about 60 XORs and 12 table
lookups. Trying the wrong orientation first costs one extra read-off. The
compact route as implemented spends 156 primitive operations here (144–240
across 24 demo seeds).

## Difficulty presets

| preset | K = L | m | R = m·K | pairs | key space | compact route ops |
|---|---|---|---|---|---|---|
| demo | 12 | 2 | 24 | 2 | 2^12 | 144–240 |
| easy | 24 | 3 | 72 | 3 | 2^24 | 240–360 |
| medium | 32 | 4 | 128 | 3 | 2^32 | 288–468 |
| **hard (ships)** | **48** | **6** | **288** | **3** | **2^48** | **384–576** |

(min–max over 24 seeds each.)

`m ≥ 3` for every non-demo preset: at m = 2 the interior window is small enough
that the algebraic attack costs only 0.04·2^K instead of 1.35·2^K, which is a
measured 30× discount and not worth taking.

`escalate()` moves **two parameters per call at fixed answer length** — K never
moves, so the answer stays exactly K bits and K atoms:

| call | params | answer atoms |
|---|---|---|
| 0 (ships) | K=48, m=6, npairs=3, nl_taps=5 | 48 |
| 1 | K=48, **m=8**, npairs=3, **nl_taps=6** | 48 |
| 2 | K=48, **m=10**, **npairs=4**, nl_taps=6 | 48 |
| 3 | K=48, **m=14**, npairs=4, **nl_taps=7** | 48 |
| 4 | `"cap_bound"` — a fifth pair pushes the compact route to a measured 1092 operations, past G9's cap, and only K raises difficulty beyond that; K *is* the answer length |

Measured compact-route maxima along the ladder: 624, 588, 624 operations on
rungs 1–3 (8 seeds each) — the answer stays 48 atoms throughout.

`m` lengthens the interior window the algebraic attack must propagate through;
`nl_taps` raises NL's arity and algebraic degree, which raises the linearisation
monomial count; `npairs` grows the number of ordered hypotheses as s(s−1). None
of the three lengthens the answer, and the first two leave the compact route's
operation count untouched.

## Gate results

Every number below is from `selftest_report.json` in this directory, produced by
`python3 gen_2003_14215.py`. All gates are measured at the shipping preset
unless the row says otherwise.

| gate | result |
|---|---|
| **G1** planted verifies | PASS — 24/24 (4 presets × 6 seeds) |
| **G2** rejects corruption | PASS — 0 corruptions accepted over 4 presets × 3 seeds × 7 corruption kinds; distinct reasons for length, range, type and ciphertext mismatch |
| **G3** round-trip | PASS — prose, comma-separated, fenced and labelled forms all recover the key; garbage returns `None`; the empty `<answer></answer>` in the prompt text does not confuse the parser |
| **G4** guess resistance | PASS — 0 hits in 200,000 structure-aware samples; the space is 2^48 = 2.8e14, P(guess) = 3.6e-15. The statement pins exactly one property of the answer (it is K bits), so the naive and structure-aware spaces coincide |
| **G5** density + baseline cost | PASS — see below |
| **G6** adversary panel | PASS — **9** attacks, 0 successes each over 8 seeds; `reference_algorithm` solves 8/8 in 0.004 s / 456 operations, as Track B expects |
| **G7** scales | PASS — ladder monotone in K (12 → 24 → 32 → 48); `escalate()` output builds and verifies with 48 answer atoms and a 444-operation route; the round-doubled instance (m = 12, R = 576) builds and verifies |
| **G8** canonical_key | PASS — invariant under all 5 relabellings on 20 seeds (100/100), the relabelled instance still verifies against the original answer (100/100), 20/20 distinct keys on unrelated seeds |
| **G9** no-tool suitability | PASS on the gated part (caps): 48 answer chars, 48 atoms, 504 route operations against caps of 2000 / 256 / 1000. The three-arm diagnostic was not run — no `OPENROUTER_API_KEY` here |

### G5 in full

| quantity | value |
|---|---|
| exact solution count, `demo` | 1 valid key out of 4096, on 20/20 seeds (exhaustive) |
| expected spurious keys, shipping | 2^(K − s·L) = 2^(48 − 144) = **2^-96** |
| sampled density, shipping | 0 / 200,000 |
| baseline attack | the algebraic attack of Definition 5.9 (Gröbner-style elimination / unit propagation with branching) |
| baseline result | did **not** solve, on every seed |
| baseline measured | 5,755 nodes / 2.19e7 primitive ops / 40.0 s before the cap; 143.9 nodes/s; 3,802 ops per node |
| baseline projected to completion | 2^48.4 nodes, 2^60.3 primitive ops, **83,697 years** |
| brute force measured | 2,084 keys/s at R = 288 → 2^48 keys = 1.35e11 s = **4,279 years** |
| compact route | **492** primitive operations at seed 11; 384–504 over the report's 12 seeds, 384–576 over 25 |
| mechanical : compact | **2^51.4** |

The key is **uniquely determined** by the published data and this is established
two ways: (a) exhaustively, by `enumerate_all` at the `demo` preset over the full
2^12 key space, which returns exactly 1 on all 20 seeds tested; and (b) by the
counting bound — each of the s pairs imposes L = K bits of constraint on a K-bit
key, so the expected number of keys other than the planted one that reproduce
every pair is (2^K − 1)·2^(−s·L) = 2^-96 at the shipping preset. `verify`
accepts *any* key that reproduces all pairs, so it is a decision procedure, not
merely a soundness test.

### G6 in full — every attack and why it fails

| attack | what it is | result |
|---|---|---|
| `brute_force_key_search` | exhaustive search over GF(2)^K | 0/8 — 2^48 keys |
| `algebraic_attack_definition_5_9` | **the domain-standard attack**: keep the intermediate state variables, propagate every round equation with a single unknown, branch when propagation stalls | 0/8 — degenerates to exhaustive key search |
| `linearisation_degree_3` | linearise the same system at degree ≤ 3 | 0/8 — 7.55e7 monomials against 864 equations |
| `key_equation_elimination_theorem_5_4` | the paper's own elimination f'_t = T̄^t(f), which removes the intermediate variables | 0/8 — monomial count explodes by rounds 14–15 of 24 even at `demo` |
| `guess_and_determine_interior_bits` | Section 5's guess-and-determine over the R−L interior bits | 0/8 — 2^240 interior bits at shipping |
| `correlation_hill_climb` | greedy descent on the Hamming distance between E_k(P) and C | 0/8 |
| `outlier_pair_statistics` | is the planted plaintext a positional/weight/run-length outlier? rank the pairs and search from the most anomalous one | 0/8 |
| `naive_readoff_plaintext_ciphertext` | **the in-context attack**: the obvious ansatz, that P‖C is the internal sequence — true only when R ≤ L | 0/8 |
| `fixed_point_scan_section_5` | Section 5's *other* key-period device: look for a published pair with C = P | 0/8 — no fixed point is ever published |
| `reference_algorithm` (Track B, reported separately) | the key-period / slid-pair attack | **8/8, as expected** |

**The plant leaves no statistical signature, and this is provable rather than
hoped for.** For *any* two K-bit strings A and B there is a key k with
F_k(A) = B — the K round equations determine k uniquely from the sequence A‖B.
(Verified 400/400 at K = 32.) So the slid pair puts *no constraint at all* on
the published plaintexts, and no statistic over them can find it. What
discriminates it is that the read-off from (P_i, P_j) agrees with the read-off
from (C_i, C_j) — a K-bit coincidence available only to a solver who has the
insight. The report records a `plant_detectability` diagnostic: the rank the
generic distance statistics assign to the true slid ordered pair, against the
chance mean rank of (s(s−1)+1)/2 = 3.5. Measured over 8 seeds: ranks
[6, 1, 6, 1, 3, 5, 3, 5], **mean 3.75** against a chance mean of 3.5. The
statistics see nothing.

## The oracle loop

**Not run in this environment — there is no `OPENROUTER_API_KEY` here.** All
nine gates pass without it (`all_gates_pass: true`, 372.9 s).
`llm_loop_transcript.jsonl` and `.meta.json` are therefore absent and must be
produced by `python3 ../../scripts/harden.py gen_2003_14215.py` before this
result is submitted. `SHIPPING_DIFFICULTY` is set to `hard` on the strength of
the measured attack costs above, and should be re-pointed if the harness
escalates.

## The G9 arms

| arm | solved / attempts |
|---|---|
| bare | not run (no API key) |
| hinted | not run (no API key) |
| placebo | not run (no API key) |
| hinted − placebo | not measured |

Gated part (G9c), measured:

| cap | limit | measured |
|---|---|---|
| serialised answer | ≤ 2000 chars | **48 chars** (`"0110...."`), 100 chars as JSON |
| answer atoms | ≤ 256 | **48** |
| intended route | ≤ 1000 exact operations | **504** (max over the report's 12 seeds; 384–576 over a wider 25-seed sweep) |

The intended route is: for each of the s(s−1) = 6 ordered plaintext hypotheses,
read key bits off (P_i, P_j) and off (C_i, C_j) one at a time and stop at the
first disagreement — a wrong hypothesis dies after about two bits — then finish
the surviving one from the P side alone. Counted primitives are one NL table
lookup and five XORs per key bit. The rendered statement is 2,388 characters.

`STRUCTURAL_HINT` names the invariant and stops — *"The number of rounds is an
exact multiple of the key subsystem's period, so the encryption map is a power
of one fixed permutation of the state space."* It does not say to look for a
slid pair, does not say to read anything off, and chains no second step.

## How to use it

```python
import gen_2003_14215 as g

inst = g.make_instance(seed=0, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))                       # the statement; leaks nothing
ok, why = g.verify(inst, inst["answer"])    # (True, 'ok')

# the compact route, independently of the planted answer
key, ops = g.slide_attack(inst)
assert g.verify(inst, key)[0]
```

```bash
python3 gen_2003_14215.py                   # runs selftest, writes the report
bash scripts/emit.sh 2003.14215             # from the repository root
```

## Caveats — read these

1. **The whole difficulty is one observation.** Once a solver sees that R is a
   multiple of the key period and that a single-period pair reads the key off,
   the rest is 48 table lookups. That is deliberate — it is what makes the
   failure informative rather than a patience test — but it means this family
   measures one insight, not a chain of them, and a model that has seen slide
   attacks on KeeLoq may well have the insight pre-loaded. **The oracle loop is
   the only thing that can settle whether it does.** It has not been run here.
2. **`P(guess)` means 2^-48 and nothing more.** `random_candidate` samples
   uniformly from GF(2)^48 because that is genuinely all the statement pins
   down. It does *not* measure the chance of guessing the right ordered
   hypothesis *given* the insight, which is 1/6 at the shipping preset — an
   adversary who has the read-off simply tries all six, which is why the compact
   route contains that loop. Nothing about the 2^-48 figure should be read as
   protection against a solver that has the insight.
3. **The Gröbner/SAT attack is my own implementation, not Singular or
   CryptoMiniSat.** No external library may be imported, so the domain-standard
   attack is modelled by unit propagation over the ANF with branching — which is
   exactly what CryptoMiniSat's XOR propagation and Buchberger with linear
   leading terms do on an explicit difference system, and the structural
   argument in "Why it is hard" shows why no implementation can prune above the
   leaves. I could not run the real tools, and say so rather than claiming their
   numbers.
4. **The projected 2^48 figure is an extrapolation** from measured node counts
   at K = 12, 14, 16 (0.5·2^12, 1.5·2^14, 1.35·2^16), supported by the pruning
   argument. It is not a measurement at K = 48; nothing is.
5. **`nl_taps > 5` leaves KeeLoq.** The shipping preset uses KeeLoq's own NL
   function 0x3A5C742E. Escalation rungs 1 and 3 replace it with a random
   balanced function of 6 or 7 arguments to raise the algebraic degree. Those
   rungs are still difference ciphers in the paper's sense but are no longer
   KeeLoq's NL.
6. **`canonical_key`'s invariance group is small** — permutations of the
   published pair list and the swap of the two linear taps. There is a further
   symmetry the key does *not* collapse: shifting time by δ and cyclically
   shifting the key by δ maps an instance to a genuinely equivalent one, but it
   changes the answer, so I treat those as distinct instances. Computing it
   requires the key, which `canonical_key` does not have.
7. **`m = 2` is a trap and is excluded.** At m = 2 the algebraic attack costs
   0.04·2^K instead of 1.35·2^K. Only `demo` uses it, and `demo` is not gated.
8. **Attacks I did not try**: cube attacks / higher-order differentials, a real
   SAT solver with conflict-driven clause learning, correlation attacks using
   many more pairs, and Courtois-style low-degree annihilators of NL. The last
   is the one I would look at first: KeeLoq's NL has algebraic immunity 2, so an
   annihilator-based attack would lower the degree of the round equations —
   though it does not touch the fact that every key bit is assigned before the
   first consistency check exists.
