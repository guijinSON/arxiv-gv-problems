# Rejected at Step 0: the paper makes primitive witnesses dense, not hard to guess

Paper: Abhishek Bhowmick and Thái Hoàng Lê, [*On primitive elements in
finite fields of low characteristic*](https://arxiv.org/abs/1412.7373),
arXiv:1412.7373v1 (2014).

## Decision

No generator is shipped. The prior-triage proposal—present
`F_q[x]/(Q)` and ask for a low-degree polynomial representing a primitive
element—has a cheap exact verifier, but it cannot simultaneously satisfy **G**
and **H**.

- **G fails for the paper's theorem-backed family.** Theorems 5 and 6 prove
  that a low-degree set contains many primitive elements by character-sum and
  sieve estimates; neither proof identifies one. A generator that samples
  those polynomials and performs primitivity tests until one passes has solved
  the instance it is supposed to manufacture.
- **Track A fails independently.** Section 1.2 explicitly interprets Theorem 5
  as a probabilistic algorithm: sample a monic low-degree polynomial, with
  success probability close to `phi(q^n-1)/(q^n-1)`. The point of the theorem
  is that primitive witnesses retain their expected density. This is the
  opposite of the required structure-aware guess probability below `1e-6`.
- **Track B does not rescue the task.** A guaranteed answer still requires the
  same primitivity tests used by the mechanical algorithm; the paper exposes
  no shorter invariant that selects a passing polynomial. If those tests are
  omitted, a bare random choice already succeeds with conspicuously high
  probability. Thus there is neither a large mechanical-to-compact compression
  gap nor a failing in-context random-choice attack.

This is not a witness-rule rejection. Given the distinct prime divisors of
`q^n-1`, a submitted nonzero field element `a` is primitive exactly when

```text
a^((q^n-1)/ell) != 1
```

for every such prime `ell`. Polynomial modular exponentiation checks this
exactly without consulting a planted answer, so **V passes**.

Implementation stopped before Step 1, as required after a Step-0 failure. No
generator, self-test report, README, or oracle transcripts were fabricated.

## What the paper actually proves

The paper fixes a monic modulus polynomial `Q` of degree `n` over `F_q` and
identifies an irreducible such `Q` with the field `F_q[x]/(Q)`. Section 1 says
that `A_d` is the set of monic polynomials of degree exactly `d`, and that an
`r`-smooth polynomial has no irreducible factor of degree greater than `r`.

The exact regimes matter:

- Theorem 3 compares the character sum over `A_d` with the sum over its
  `r`-smooth members when `2 log_q(n) <= r <= d <= n`.
- Corollary 4 makes the normalized nonprincipal character sums small in the
  same regime.
- Theorem 5 uses the multiplicative-character indicator for primitive
  elements and concludes that their density among monic degree-`d`
  polynomials is close to the ambient density
  `phi(q^n-1)/(q^n-1)`, with an error multiplied by
  `2^omega(q^n-1)`.
- Section 1.2 immediately calls this a probabilistic primitive-element
  algorithm, using nearly logarithmic randomness and logarithmic time in the
  paper's model rather than the linear randomness/time of sampling a general
  field element.
- When `q^n-1` has too many distinct prime divisors for Theorem 5's two-sided
  error to be useful, Theorem 6 uses the shifted sieve of Theorem 10 to give a
  positive density lower bound. Its proof still counts witnesses; it does not
  output a distinguished one.

The exact certificate-producing question therefore has an unfavorable answer:
the paper produces a *dense candidate set*, and the executable producer of an
individual certificate is randomized sampling followed by the standard order
test. That is a solver for the proposed instance, not inverse generation.

## Structure-aware density: analytic and measured checks

The candidate language a solver would actually use is precisely the set of
monic degree-`d` polynomials. It would be invalid to claim the much larger set
of arbitrary coefficient strings as the guess space, because monicity and
degree are stated constraints.

Two low-characteristic checks show why this language cannot support G4:

1. Take `q=2`, extension degree `n=127`, and `r=d=14`. This is inside
   Theorem 3's native regime because `2 log_2(127) < 14`. The multiplicative
   group has order `2^127-1`, a prime. Every monic degree-14 representative is
   nonzero and is not `1`, so every candidate is primitive. The exact
   structure-aware probability is therefore **1**.
2. As a composite-order diagnostic, take `q=2`, `n=128`, `d=16`, and the
   irreducible modulus `x^128+x^7+x^2+x+1`. Here

   ```text
   2^128-1 =
     3 * 5 * 17 * 257 * 641 * 65537 * 274177 * 6700417
       * 67280421310721,
   phi(2^128-1)/(2^128-1) = 0.4992180736149612...
   ```

   A deterministic `random.Random(14127373)` diagnostic sampled 200 monic
   degree-16 polynomials and checked every candidate by exact polynomial-basis
   exponentiation. It found **107/200 = 0.535** primitive candidates. This is
   only a Step-0 diagnostic, not a fabricated 200,000-sample G4 report, but it
   agrees with the density mechanism Theorem 5 is designed to establish and
   is more than five orders of magnitude above the gate threshold.

Choosing the prime-order example as a shipping distribution would be absurdly
easy. Avoiding it does not solve the general problem: in the paper's intended
Theorem 5 regime, low-degree sampling deliberately preserves the ambient
primitive density. Making the accepted set rarer by asking for the
lexicographically first primitive element would abandon cheap witness
verification, since the checker would also have to certify that all earlier
candidates fail.

## Mechanical cost versus compact route

For the representative `F_(2^128)` diagnostic above, the domain-standard
algorithm is random sampling plus the order test. Square-and-multiply for all
nine prime divisors uses at most **1,585 field squarings/multiplications per
candidate** (counting the exact binary exponentiation schedule). A
standard-library Python implementation processed all 200 candidates in
**3.218840 seconds**, or **0.016094 seconds per candidate**. At the measured
success rate it needs about `1/0.535 = 1.87` candidates. A separate run of 100
complete sample-until-success searches used a mean of **1.86 candidates** and
**0.047689 seconds** per recovered witness (median one candidate and 0.044280
seconds).

There are only two purported compact routes:

| regime | mechanical cost | compact route | result |
|---|---:|---:|---|
| `q=2, n=127, d=14` | choose and emit one monic polynomial; no order exponentiation is needed once the prime group order is known | the identical one-choice route | Cost ratio 1; every candidate is valid, so G4 and the random-choice attack fail maximally. |
| `q=2, n=128, d=16` | at most 1,585 field operations per tested candidate; measured mean wall time 0.047689 s to success | for a guaranteed witness, the same prime-divisor exponent tests; without testing, one random choice succeeded 107/200 times | No separate insight is exposed. The guaranteed-route ratio is 1, while the unverified shortcut is already far too guessable. |
| general Theorem 5 parameters | sample from `A_d` and apply the same order test until success; the paper advertises nearly logarithmic randomness and logarithmic running time | no shorter selector is proved; a random candidate has approximately the ambient primitive density | Track A is false, and Track B has nothing to compress. |

At larger extension degrees, polynomial exponentiation can certainly become
impossible by hand. That alone is not Track B: hiding an executable algorithm
is useful only when the solver can replace it by a short visible invariant.
Here the generator's private knowledge of which sampled candidate passed is
not such an invariant. Conversely, choosing a primitive defining polynomial
so that the residue class of `x` is known to be primitive exposes a one-symbol
answer and makes the compact and mechanical constructions the same.

## Audit of the prior-triage construction

The suggestion “choose a primitive polynomial so its root is a known primitive
element” does not provide an unlimited valid family:

- If the generator searches irreducible degree-`n` polynomials and tests their
  roots until it finds a primitive one, it obtained the answer by solving the
  very primitive-element search being benchmarked, contrary to G.
- If an external explicit primitive-polynomial constructor is used, that
  theorem—not this paper—produces the root, and the resulting answer is simply
  the displayed residue class `x`. The public construction is the compact
  solution, so H fails on Track B as well as Track A.
- Hard-coding a table of primitive polynomials gives only a finite catalogue.
  Randomly relabelling its field presentations is a transformation of the same
  known instances, and a correct canonical key cannot count those relabellings
  as unlimited diversity.

The paper's density theorem cannot repair the first bullet: it proves that a
search will terminate with good probability but does not carry an individual
witness out of its character-sum proof.

## Other native formulations considered

| candidate problem | G | H | V | outcome |
|---|---:|---:|---:|---|
| Return one primitive member of the low-degree set | **Fail** without a separate primitive-polynomial constructor | **Fail** on A because of the paper's sampling algorithm; fail on B because random choice is already effective and no distinct shortcut exists | Pass by prime-divisor exponent tests | Rejected |
| Return the exact number/density of primitive members of `A_d` | No exact count is constructed by Theorem 5 or 6 | Not reached | **Fail** cheaply: the theorems give asymptotic bounds, while exact checking enumerates `q^d` candidates or needs the very character sums being claimed | Rejected |
| Return an exact character sum from Theorem 3 | The theorem supplies an estimate, not the exact algebraic sum | No paper-backed hard distribution with a planted exact value | **Fail** at hard size unless the checker enumerates `A_d`; the big-`O` statement is not an executable exact certificate | Rejected |
| Return an `r`-smooth polynomial | Pass by multiplying low-degree irreducibles | **Fail**: a product of permitted linear factors is an immediate answer | Pass by exact factor multiplication/division | Rejected |
| Return the lexicographically first primitive member | Generator must perform the search | Unsupported | **Fail** cheaply unless a certificate excludes every earlier polynomial | Rejected |
| Return many independent primitive elements to suppress guess probability | Generator must first find every listed primitive element; repeating the search does not become inverse generation | The paper's same randomized algorithm finds them one at a time | Pass for each element, but the answer grows | Rejected |

The proof of Theorem 3 is itself an analytic Cauchy-integral and Euler-product
argument with asymptotic error terms. Treating that proof as the submitted
certificate would violate the witness rule: it is not a bounded object the
checker can decide by exact substitution.

## Final gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G — certificate known by construction | **Fail for the native hard-looking task** | Theorems 5 and 6 count/guarantee primitive elements but do not identify one; sampling until a primitivity test passes is solving the instance. |
| H — Track A structural hardness | **Fail** | Section 1.2 explicitly gives the probabilistic algorithm, and its high success probability is the theorem's central conclusion. |
| H — Track B no-tool compression | **Fail** | The guaranteed compact route is the same order test as the mechanical route; omitting it leaves a random guess with measured probability 0.535 (and exact probability 1 in the `n=127` regime). |
| V — exact witness verification | **Passable** | Check one modular power for each distinct prime divisor of `q^n-1`. |
| Overall | **Rejected at Step 0** | No paper-native family found that satisfies G, H, and V simultaneously. |

No LLM hardening run can fix these failures. An oracle failing to carry out
1,585 finite-field operations in its head would not make a one-in-two random
guess resistant, and it would not turn search-produced generator knowledge
into an inverse-generated certificate.
