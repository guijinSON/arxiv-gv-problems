# Laurent phenomenon algebra mutation fingerprints

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | polynomial (one exact monomial) |
| Native objects | rank-two LP seeds, irreducible cubic/linear exchange polynomials, compressed mutation words, coefficient monomials |
| Intended intuition | symmetry: cubic coefficient mutation is an order-eight dihedral action |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

This generator is based on Lam and Pylyavskyy, [*Laurent phenomenon algebras* (arXiv:1206.2611)](https://arxiv.org/abs/1206.2611). It hands the solver independent copies of the paper's normalized cubic rank-two LP seed, exact monomial coefficients over a polynomial UFD, and two run-length encoded mutation blocks per copy. The requested witness is a coefficient-1 monomial: a weighted fingerprint of the final cubic and linear exchange-polynomial coefficients. Verification applies the exact coefficient mutations, expands the six fingerprint factors as exponent vectors, and compares integers; it never reads `inst["answer"]`.

Generation is inverse. For every component, `make_instance` samples the final element of the eight-element coefficient group first, factors it into two random group elements, samples mutation words conditioned to represent those factors, and gives every block a repetition count congruent to 1 modulo 4. The answer is carried from the sampled endpoint. It is never recovered by solving the displayed word. The initial cubic is Eisenstein at its private atom `p`, the linear polynomial is primitive, and Proposition 2.15 guarantees mutation preserves valid LP seeds.

## Why this is Track B

Section 2.1 supplies (LP1–LP2), Section 2.2 defines exact mutation, Proposition 2.16 proves involutivity, and Theorem 5.1 proves Laurentness. The decisive result is Theorem 6.4 and its cubic `(b,c)=(1,3)` proof: the two coefficient mutations are `(DG)(EF)(KL)` and `(AD)(BC)(FK)(GH)`, and they generate a group of order eight. The same theorem identifies all easy finite rank-two regimes: `b=0`, `(1,1)`, `(1,2)`, and `(1,3)`. This family deliberately uses the cubic finite regime, so a Track A claim would be false.

The reference algorithm successively applies every mutation digit. At the shipping preset its eight-seed median was 358,108 mutation symbols, 1,255,394 exact role swaps, and 0.0154 seconds, with 8/8 correct. Its complexity is `O(L)` for expanded word length `L`. Recognizing the dihedral action allows block exponentiation and fingerprint assembly in 258 exact operations on the measured shipping instance (264 worst-case). That gap—not computational intractability—is the Track B claim.

The four failing attacks target construction leakage. Final states are uniform, so a lexicographically distinguished state is not an outlier; using only the last block discards a randomized factor; 256 structure-aware restarts are too few for `8^8` endpoints; and the by-hand commuting-parity ansatz loses the noncommuting order information. Each scored 0/8.

## Worked demo

This is `make_instance(seed=7, **DIFFICULTY["demo"])` rendered in full. A person can solve it on paper: after deriving the two coefficient involutions, only one component and two short base words remain.

```text
Compute an exact exchange-polynomial fingerprint in a product of cubic rank-two Laurent phenomenon algebras.

Definitions (everything needed for the problem).
A rank-two LP seed is an ordered pair (X,P(Y)); (Y,Q(X)), where P and Q are irreducible polynomials over a unique-factorization coefficient ring and neither uses its own paired variable.
Mutation 1 replaces X by X'=P(Y)/X.  If Q uses X, substitute X=P(0)/X', remove from the whole resulting Laurent polynomial every common coefficient factor it shares with P(0), and multiply by the unique power of X' that makes an ordinary polynomial not divisible by X'.  P remains attached to X'.
Mutation 2 is the same rule with the two slots interchanged.  The sign is normalized so every displayed leading coefficient is positive.
A block [w]^r means execute the mutation digits of w from left to right and repeat that whole word exactly r times.  Concatenate the two displayed blocks in their displayed order.  Digits are slot numbers, not exponents.

Each independent component starts with
  P(T) = A*T^3 + B*K*L*T^2 + C*H*K^2*L^2*T + D*G*H^2*K^3*L^3
  Q(T) = E*T + F*G*H*K*L^2.
Its coefficient ring is Z[p,a,b,c,d,e,f,g,h,k,l], using private atoms carrying that component's number.
The roles are A=a^rA, B=p*b^rB, C=p*c^rC, D=p*d^rD, E=e^rE, F=f^rF, G=g^rG, H=h^rH, K=k^rK, L=l^rL.
Thus P is Eisenstein at p and Q is primitive linear, so these really are LP seeds.

After all mutations in a component, write its two exchange polynomials in the same ordered slots as P_f(T)=p3*T^3+p2*T^2+p1*T+p0 and Q_f(T)=q1*T+q0.
Define its fingerprint Phi = p3^1*p2^2*p1^4*p0^8*q1^16*q0^32.  All six coefficients are monomials, so Phi is one monomial in the component's 11 atoms.
Your answer is the product of Phi over all components, hence one coefficient-1 monomial.

There are 1 components.  Each exponent row is rA,rB,rC,rD,rE,rF,rG,rH,rK,rL.
component 0: r=(2,1,2,3,1,1,3,1,2,3); blocks [1112]^5 [2122]^5

Output uses the following global exponent order:
  p0,a0,b0,c0,d0,e0,f0,g0,h0,k0,l0
A rational coefficient is [numerator,denominator], and a monomial is its full exponent list in that exact order.  Exponents are nonnegative integers.
Give your final answer inside <answer></answer> tags as a JSON polynomial containing exactly one [coefficient, exponent-list] term.
Example for one component only: <answer>[[[1,1],[8,1,2,4,8,16,32,40,52,66,98]]]</answer>
Output nothing else inside the tags.
```

The planted answer is `[[[1,1],[14,2,2,8,24,16,32,120,52,132,294]]]`. `verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the final exponent returns `(False, "wrong exponent length: expected 11, got 10")`.

## Difficulty presets

The counts below use seed 12345. Only the demo grows the witness; from easy onward the 90-atom answer and `8^8` endpoint space stay fixed while the expanded mutation haystack grows.

| Preset | Parameters `(n, components, base_len)` | Expanded symbols | Compact ops | Answer atoms | Endpoint space | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | `(1,1,3)` | 35 | 24 | 13 | 8 | hand example; not hardened |
| easy | `(100,8,5)` | 53,129 | 225 | 90 | 16,777,216 | bare held, but G9(b) failed: hinted oracle solved 1/1 |
| medium | `(500,8,7)` | 350,490 | 258 | 90 | 16,777,216 | **ships**; bare and hinted held |
| hard | `(2000,8,8)` | 1,767,483 | 275 | 90 | 16,777,216 | available, not needed |

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verify and JSON round-trip |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced JSON inside prose parses and verifies |
| G4 | pass | 0/200,000 structured guesses; exact probability `1/16,777,216 = 5.96046e-8` |
| G5 | pass | shipping density 0/200,000; exact one valid endpoint; strongest failing restart median 256 iterations and 0.0317 s; reference median 1,255,394 swaps |
| G6 | pass | four attacks each 0/8; reference algorithm 8/8 as expected on Track B |
| G7 | pass | doubled `n=1000` builds and verifies; answer atom count unchanged |
| G8 | pass | 80/80 key-invariance and 80/80 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | hinted verdict hardened; 272 chars, 68 estimated tokens, 90 atoms, 258 intended operations |

## Oracle loop

The shipping bare transcript is script-generated and contains three distinct vendors.

| Preset | Model | Seed | Solved | Verification result |
|---|---|---:|---|---|
| medium | `openai/gpt-5.6-terra` | 983558592 | no | exponent out of bounds |
| medium | `google/gemini-3.1-pro-preview` | 180314648 | no | fingerprint mismatch in component 0 |
| medium | `x-ai/grok-4.6` | 162763149 | no | fingerprint mismatch in component 0 |

## G9 arms

| Arm | Solved / attempts | Verdict or interpretation |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; polarity-flipped gate passes |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is `0.0`. The structural sentence bought the oracle pool no measured improvement, so these runs do not show that naming the dihedral symmetry alone unlocks the intended route; they show only that the family remains difficult after that information is supplied. The shipping answer is 272 characters (68 estimated tokens), contains 90 atomic values, and the intended route uses 258 exact operations.

## Use

```python
import gen_1206_2611 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
prompt = g.render(inst)
candidate = g.parse_answer(model_reply)
ok, reason = g.verify(inst, candidate)
```

From the repository root, emit twenty fresh shipping instances with:

```bash
bash scripts/emit.sh 1206.2611 20 medium
```

## Caveats

This is not a claim of structural or complexity-theoretic hardness. Theorem 6.4 supplies a tiny finite group, and software solves every instance quickly; exposing the two permutations makes the route substantially easier. The density is exact only under the declared prior—uniform independent choice among the eight reachable coefficient states per component—and says nothing about a solver using the word structure. The panel did not run a general CAS factorization engine or test every symbolic automorphism of the coefficient ring. The canonical key exactly handles component reordering, alternative mutation words with the same group value, inserted involution pairs, four extra block repetitions, and their compositions; it does not attempt general LP-seed isomorphism. Finally, two G9 failures were empty length-limited model responses, so the 0/3 rates include both wrong witnesses and reasoning-budget exhaustion, as the harness specifies.
