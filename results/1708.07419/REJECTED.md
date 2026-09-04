# Rejected: no supported hard certified distribution

Paper: Olga Kharlampovich and Alexei Myasnikov,
[*Undecidability of Equations in Free Lie Algebras*](https://arxiv.org/abs/1708.07419),
arXiv:1708.07419v1 (22 August 2017).

## Decision

No generator is shipped. The proposed family—sample elements of a free Lie
algebra, derive equations that they satisfy, and ask for a satisfying
assignment—has **G (inverse generation)** and **V (exact substitution)**, but
the paper gives no hardness result for that planted distribution. Its theorem
is worst-case undecidability of the unrestricted solvability problem, not
average-case hardness of satisfiable instances sampled together with solutions.
Consequently the proposal fails **H (hardness)** on Track A.

The paper's own theorem-backed positive instances do not provide a Track B
alternative. Their witnesses are produced by an explicit Jacobi-identity
recurrence, and an obvious alternating-chain ansatz recovers them in linear
time. There is no gap between an impractical mechanical solver and a compact
but difficult-to-discover route of the kind Track B requires.

This is therefore a Step-0 rejection. In accordance with the task instruction
to stop when G, H, or V fails, `gen_1708_07419.py`, `selftest_report.json`, the
README for a shipped module, and oracle-loop transcripts were not fabricated.

## What the paper actually defines

Section 1 defines an equation over a Lie algebra as an equality of two Lie
terms with variables and constants. A solution assigns an algebra element to
each variable so that the two evaluated terms are equal. The native decision
problem asks whether an arbitrary finite system has any solution in the
infinite-dimensional free Lie algebra.

The proof proceeds through Diophantine interpretations:

- Section 2, the reduction lemma, gives an effective procedure translating a
  finite system over an e-interpreted structure into an equivalent finite
  system over the interpreting structure.
- Section 3 explicitly interprets the coefficient field and its scalar action
  in a free Lie algebra of rank at least two. The defining equations force
  tuples of the form `(alpha*a_1, ..., alpha*a_n)`, and field addition,
  multiplication, and scalar multiplication are then represented by displayed
  equations.
- Section 4, Lemma 7 (label `l1` in the
  source), analyzes the system

  ```text
  [x,c] + [y,b] = [z,a]
  [x,b]           = [z1,a]
  [y,c]           = [z2,a].
  ```

  Its projection to `(x,y)` is exactly

  ```text
  ([b,f(a^2)] + alpha*a, [c,f(a^2)] + beta*a),
  ```

  where `f` is a univariate polynomial over the coefficient field.
- Section 4, Theorem 3 (source label `th3`), uses that set to e-interpret
  `K[t]` in every free Lie algebra of rank greater than two. Theorem 4
  interprets the integers in characteristic zero. Theorem 5 combines
  the `K[t]` interpretation with Denef's undecidability result to prove that the
  unrestricted Diophantine problem is undecidable for rank greater than two.

The exact hard regime is thus **arbitrary finite systems with unbounded term
degree, unbounded witness size, and no promise of satisfiability**. It is not a
bounded family of positive instances with certificates supplied by a sampler.

## Step-0 discriminator: what produces the certificate?

There are two materially different answers, and neither yields an admissible
family.

### Inverse-planted arbitrary equations

Choose finite Lie polynomials `u_1, ..., u_k` first and construct equations that
become identities after `x_i := u_i`. The generator itself produces the
certificate in linear time in the emitted syntax: it simply returns the sampled
tuple. Exact evaluation can be implemented by embedding the free Lie algebra
in the free associative algebra, recursively expanding `[p,q]` as `pq-qp`, and
comparing the resulting integer or rational word coefficients.

This clears G and V. It says nothing about H. The undecidability theorem does
not apply to the distribution conditioned on a sampled solution and does not
state that recovering *some* solution of such instances is hard. In particular,
the equations used to plant each assignment may expose it syntactically,
linearly, by degree, or through normal-form coefficients. Random relabelling and
decoys cannot turn a worst-case theorem into a distributional one.

The paper remarks that there is a parameterized infinite sequence of systems
whose solvability is undecidable. That sequence is not an answer-first
generator: selecting exactly its solvable members and supplying their witnesses
requires resolving the very solvability question used in the reduction. If one
instead starts from known solutions, the paper supplies no theorem about the
resulting subdistribution.

### The paper's theorem-backed Jacobi instances

Lemma 6 (source label `le:principal`) proves that for any `r` and nonnegative
`m,n` there is an `s` satisfying

```text
[[r,a^(m)],[b,a^(2n)]] = [[r,a^(m+2n)],b] + [s,a].
```

Write `D(u)=[u,a]`, `R_i=D^i(r)`, and `B_i=D^i(b)`. The executable Jacobi
identity

```text
[u,D(v)] = D([u,v]) - [D(u),v]
```

telescopes immediately to the explicit witness

```text
s = sum(j=0..2n-1) (-1)^j [R_(m+j), B_(2n-1-j)].
```

Thus the certificate is produced in `O(n)` symbolic terms by the same recurrence
as the proof. A solver's obvious alternating-coefficient ansatz succeeds on
every instance. The later proof that particular pairs satisfy the three-equation
system likewise invokes these displayed recurrences; it is not a hidden search
problem.

This rules out Track A because an explicit efficient construction exists. It
also rules out an honest Track B benchmark:

- If iterated adjoints and sums are allowed in the bounded certificate language,
  the compact answer above is directly writable and the required fourth
  in-context attack succeeds.
- If the answer must be fully expanded in a Hall or associative-word basis,
  scaling only increases normalization and transcription work. That measures a
  calculator/output bottleneck and eventually violates G9's answer and intended
  route caps.
- Concealing the alternating vector behind a random dense basis change makes
  recovery ordinary exact linear algebra. The Lie identity is then no longer
  load-bearing; this would be a benchmark-convenience transformation, not native
  coverage of the paper.

## Why the undecidability reduction cannot simply be planted

An undecidability reduction maps an arbitrary source instance to a target Lie
system while preserving whether a solution exists. It does not provide any of
the following ingredients required here:

1. a computable sampler supported on hard instances;
2. a certificate for every sampled instance without solving the source problem;
3. a bounded certificate language whose witnesses fit the output caps; or
4. a theorem that the answer-first image distribution remains hard.

Sampling a polynomial equation together with a polynomial solution before
applying the interpretation satisfies item 2, but discards the undecidability
premise: only a special satisfiable distribution remains. Conversely, sampling
the arbitrary source systems to which Denef's theorem applies loses the known
certificate and therefore fails G. The two properties cannot be combined using
anything proved in this paper.

There is also no useful certified-negative route here. The paper proves an
undecidable absence question but does not furnish bounded Nullstellensatz-style
or refutation certificates for nonsolvability in a free Lie algebra. Restricting
all variables and terms to a fixed finite language makes brute-force checking
decidable and again falls outside the theorem's unbounded regime.

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G — certificate known by construction | Pass for planted assignments and the explicit Jacobi family | The sampler returns its chosen assignment; Lemma 6 gives the telescoping `s` |
| H — Track A distributional hardness or Track B compression hardness | **Fail** | Worst-case undecidability does not cover the planted distribution; the theorem-backed positive family has an `O(n)` explicit recurrence and a successful by-hand ansatz |
| V — cheap exact witness checking | Pass in principle | Substitute and normalize exactly in the free associative algebra |
| G1–G9 | Not run | Step 0 already rules out H |
| LLM hardening loop | Not run | Oracle failures cannot supply a missing distributional-hardness theorem or override the explicit recurrence |

## What would be needed for a viable successor

A defensible generator would need an independently justified hard distribution
of satisfiable polynomial or Lie systems, an answer-first reduction that maps
its certificates into bounded Lie-polynomial witnesses, and attacks including
Hall/Lyndon normalization, linear coefficient solving, Gröbner-style elimination,
and construction-specific degree/support tests. Those ingredients are not in
arXiv:1708.07419. Importing them would create a benchmark based on a different
source rather than turn this paper's result into the requested verified family.
