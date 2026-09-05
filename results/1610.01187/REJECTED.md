# Rejected at STEP 0: arXiv 1610.01187

Paper: Gorjan Alagic and Alexander Russell,
[*Quantum-Secure Symmetric-Key Cryptography Based on Hidden Shifts*](https://arxiv.org/abs/1610.01187)
(EUROCRYPT 2017, arXiv v2).

## Decision

No self-contained family from this paper clears **G + H + V** under either
hardness track. The prior-triage proposal—choose a secret shift, sample a random
function, and publish it together with its translate—does pass **G** by inverse
generation and can pass **V** if both complete function tables are published.
It fails **H on Track A**, because an explicit table changes the paper's
black-box-oracle problem into a linear-time lookup problem. It also fails **H on
Track B**: for random function labels, the lookup is both the mechanical method
and the shortest possible route; there is no compact invariant to notice.

Implementation therefore stopped before STEP 1, as the task requires. No
generator, self-test report, README, or oracle transcripts were created. This is
not a `cap_bound` result and it is not a rejection merely because an algorithm
exists: the measured mechanical and compact costs are given below and are the
same.

## What the paper actually defines

Section 3.1 defines Hidden Shift over a finite group `G`: the algorithm receives
**black-box oracle access** to functions `f,g : G -> {0,1}^ell` promised to obey
`g(x)=f(s*x)`, and must return `s`. The paragraph opening Section 3 says that
query and running-time complexity are measured as `poly(log |G|)`. Its randomized
hardness assumption samples `f` uniformly; the separate injective assumption is
worst-case in the choice of `f`. Random Hidden Shift also samples `s` uniformly.

This representation is load-bearing. A finite prompt cannot provide quantum
oracle access. It must instead do one of the following, and none preserves all
three gates:

1. Publish complete tables. Then the serialized input already contains every
   oracle value and admits the lookup attack below in time linear in its own
   length.
2. Publish succinct circuits. A circuit made by visibly inserting `s` leaks the
   answer; a reversible circuit gives efficient inverse access; and a generic
   obfuscated circuit is neither constructed nor covered by any theorem in the
   paper. Exact equivalence of arbitrary circuits would also cease to be the
   cheap checker required by V.
3. Publish only sampled evaluations or a hash commitment. That turns the task
   into finite-transcript hash preimage search, not the paper's Hidden Shift
   oracle problem, and the paper supplies no distributional theorem for it.
4. Keep an oracle seed or cipher key only inside `inst` for the checker. Then the
   solver has not been given all instance data and validity depends on a hidden
   oracle, contrary to the witness rule and the self-contained output contract.

The hardness discussion in Section 3.2 does not repair this mismatch. Section
3.2.1 lists efficient cases, including Simon's algorithm for `(Z/2)^n` and the
constant-exponent solvable groups covered by FIMSS. Section 3.2.2 cites
Kuperberg's Theorem 7.1, giving time and query complexity
`2^O(sqrt(log |G|))` for abelian Hidden Shift, and singles out `Z/2^n` as the
paper's main conjecturally hard cyclic family. Those bounds concern succinct
group elements plus oracle access, not a `Theta(|G|)`-entry serialization of the
oracles.

Most decisively, Section 4.2.2 explicitly warns that Random Hidden Shift and its
variants become trivial with even partial inverse access: one evaluation of
`f^{-1} o g` yields the shift. A complete injective table supplies `f^{-1}` by a
scan or by a dictionary built in one pass. Theorem 4 in that section (the
Even–Mansour key-recovery reduction) is therefore careful about how inverse
oracles are simulated; it does not assert hardness for publicly serialized
tables.

## Certificate-producing method and checker

For the direct cyclic candidate, choose `N=2^b`, sample `s` uniformly in
`Z/N`, sample an injective table `f`, and set `g[x]=f[(x+s) mod N]`. The planted
answer is the integer `s`; the generator never solves its output. An exact
checker can verify any candidate `t` by testing
`g[x] == f[(x+t) mod N]` for every `x`. Thus G and V are not the problem.

The certificate-producing attack on the rendered instance is immediate. Since
`g[0]=f[s]`, read `g[0]` and locate that value in the displayed `f` table. For an
injective `f`, its index is exactly `s`. This takes `Theta(N)` equality tests
without an inverse index, `Theta(N)` preprocessing and one lookup with an index,
or one lookup if the inverse table is also displayed. It succeeds on every
instance.

## Mechanical cost versus compact route

### Direct Hidden Shift table

The bounded answer language contains only `N` shifts, so strict G4 guess
resistance requires `N > 10^6`; the first power-of-two choice is `N=2^20` and
has exact random-guess probability `1/2^20 = 9.5367431640625e-7`.

I measured the direct `g[0]` lookup on one deterministic random permutation and
20 independently sampled shifts at this smallest G4-clearing size:

| quantity | measurement |
|---|---:|
| group size | 1,048,576 |
| mean / maximum equality tests | 517,398.85 / 995,247 |
| mean / maximum wall time (`list.index`) | 0.05705 s / 0.15435 s |
| JSON characters, one compact table | 7,277,499 |
| JSON characters, both tables (estimate) | 14,554,998 |
| successful recoveries | 20/20 |

The **compact route is the same scan**: read `g[0]`, then compare it with random,
semantically meaningless labels until the match is found. Under the same
operation convention its mean and maximum lengths are therefore 517,398.85 and
995,247 operations, respectively. The mechanical-to-compact ratio is 1, and
both are far above G9(c)'s 300-operation intended-route cap. Randomly relabelling
the range—exactly the distribution used by the paper—rules out a shorter
value-based invariant.

### Best table-economical alternative: Even–Mansour key recovery

Section 4.1 defines `E(x)=P(x*k1)*k2`. Over the additive cyclic group this is
`E[x]=P[(x+k1) mod N]+k2 mod N`. Asking for the pair `(k1,k2)` enlarges the
nominal language to `N^2`, so `N=1024` is the smallest power of two whose pair
space clears G4 (`1/N^2 = 9.5367431640625e-7`) while keeping the tables small.

On 20 deterministic random permutations and key pairs, the exact early-abort
alignment scan recovered 20/20 keys. It tries each `k1`, derives `k2` from
`E[0]`, and compares table entries until mismatch or full agreement:

| quantity | measurement |
|---|---:|
| group size / nominal pair space | 1,024 / 1,048,576 |
| mean / maximum counted modular operations and comparisons | 3,751.95 / 5,013 |
| mean / maximum wall time | 0.000706 s / 0.003474 s |
| successful recoveries | 20/20 |

The usual adjacent-difference/KMP formulation is also linear: the output shift
`k2` cancels from `E[x+1]-E[x]`, leaving a cyclic shift of the corresponding
difference word of `P`. But computing and aligning that random word is the
compact route as well as the standard route, again `Theta(N)` and above 300
operations. Lowering `N` enough to fit 300 operations makes the `N^2` answer
space far smaller than `10^6`; raising it lengthens both routes together. Giving
an inverse oracle only invokes the paper's own one-query trivialization.

These are the two numbers required by the Track B test: at the best compact
table candidate, the measured mechanical route is about **3,752 operations**
and the compact route is the **same linear alignment scan** (about 3,752 under
the same accounting). There is no million-operation mechanical route compressed
to a dozen insightful steps.

## Why the other paper-native tasks do not rescue a family

| paper object | candidate witness | failing gate |
|---|---|---|
| Random/Decisional Hidden Shift, Section 3.1 | a shift for the positive case | **H** with tables; a negative decision has no finite refutation certificate supplied by the paper |
| Even–Mansour distinguishability, Section 4.2.1 and Theorem 3 | the two group keys proving the positive case | **H**: explicit tables admit the linear translation-alignment attack measured above |
| Even–Mansour full key recovery, Section 4.2.2 and Theorem 4 | `(k1,k2)` | **H**: inverse access is explicitly identified as trivializing the underlying shift; forward tables still give a linear scan |
| Hidden-Shift CBC-MAC, Section 5 and Theorem 5 | two colliding messages | **V/H conflict**: public evaluation tables make collision search an ordinary finite-table task, while hiding the MAC key leaves the checker dependent on data unavailable to the solver |
| Feistel and slide constructions, Section 6 and Appendix B | a distinguisher or recovered key | **H/V conflict**: the results only replace Simon's subroutine by an oracle Hidden Shift subroutine; they do not give a self-contained exact instance representation |
| qCPA security itself | proof that no efficient adversary exists | **V**: this is an asymptotic security assumption/reduction, not a bounded witness an exact checker can inspect |

Using SHA as a compact “random oracle,” adding a secret-key verifier, or
encoding circuit equivalence as SAT could manufacture a different hard task.
None is a paper-licensed reduction, and each compiles away the very oracle model
on which this paper's claims depend. Such a family would at best be a convenience
analogue and would not answer the requested native problem.

## Gate diagnosis

| requirement | result |
|---|---|
| G — generatable | **passes** for positive Hidden Shift and Even–Mansour instances by sampling the shift/keys first |
| V — verifiable | **passes only with complete public tables or public evaluation circuits**, by exact substitution over all inputs |
| H — Track A | **fails** for every self-contained table distribution: lookup/alignment is linear in serialized input size and succeeds universally |
| H — Track B | **fails**: mechanical and compact routes are the same random-label scan; measured ratios are 1, and G4-clearing sizes exceed the 300-operation route cap |
| overall | **rejected at STEP 0** |

The paper supports a meaningful oracle-complexity assumption and cryptographic
reductions. It does not support turning those oracles into a static, exact,
self-contained no-tool witness problem without either revealing a linear-time
solution or changing the problem.
