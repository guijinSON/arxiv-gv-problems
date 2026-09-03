# Rejected: exposed equalizer witnesses in the explicit Stallings-graph family

Paper: Jialin Lei and Teng Zhang, [*Colored Stallings graphs and
counterexamples to the Stallings equalizer conjecture*](https://arxiv.org/abs/2604.24502),
arXiv:2604.24502v2 (9 May 2026).

## Decision

No problem generator is shipped. The natural witness task suggested by the
paper—given two free-group homomorphisms, return a nontrivial word on which
they agree—meets **G (inverse generation)** and **V (exact verification)** but
fails **H (hardness)** on the paper's actual counterexample family. The
construction exposes valid witnesses in closed form, including length-one
witnesses. Increasing the rank or the word lengths does not remove that
solver.

Per Step 0 of the task, I stopped before writing a module, self-test report, or
LLM-hardening transcript. Random-guess and oracle failures cannot override a
deterministic construction that succeeds on every generated instance.

## Exact definition and theorem regime

Section 1 defines, for homomorphisms

```text
g,h : F(Sigma) -> F(Delta),
```

the equalizer

```text
Eq(g,h) = { w in F(Sigma) : g(w) = h(w) }.
```

Equality is equality in the free group, so a candidate word is checked by
substituting the listed images of the domain generators into the word, freely
reducing both results, and comparing them. This is an exact, inexpensive
verifier and would satisfy V.

Theorem 1.2 is structural, not a computational-hardness theorem. For every
`n >= 2`, it constructs monomorphisms `g,h : F_n -> F_2` whose equalizer has
rank at least `2n-2`. Proposition 3.3 and Construction 4.1 fix the domain basis

```text
F_n = <t, x_1, ..., x_(n-1)>
```

and define, with `c_i = a^(-i)b^i`,

```text
g(t) = a,              h(t) = b,
g(x_i) = c_i^2,        h(x_i) = c_i^2.
```

Lemma 4.3 proves that the subgroup represented by the colored Stallings graph
`Gamma_n` is a rank-`2n-2` free factor of `Eq(g,h)`.

## Fatal closed-form solvers

### One equalizer word

For every `i` from `1` through `n-1`, the displayed definition gives

```text
g(x_i) = h(x_i).
```

Thus `x_1` is a valid nontrivial witness on every instance and can be found by
one comparison of two input rows. Its reduced length is one. Permuting the
input rows, renaming generators, or inverting generators does not help: compare
each generator image under `g` and `h` and return any equal pair (or its
inverse). This attack is linear in the displayed input size.

Length constraints do not repair the family. For any positive target length
`L`, the freely reduced word `x_1^L` is in the equalizer. Products and powers of
the other `x_i` give unlimited further explicit witnesses.

### A full rank-`2n-2` independent family

The paper's own graph also exposes the larger witness family. Use the chain of
`t`-edges as a maximal tree in `Gamma_n`. The two `x_i`-loops—one at the base
vertex and one at the vertex reached by `t^i`—give the graph-basis words

```text
x_i                    for 1 <= i < n,
t^i x_i t^(-i)         for 1 <= i < n.
```

There are exactly `2n-2` such words. Lemma 4.2 verifies their membership and
Lemma 4.3 verifies the rank/free-factor claim. Consequently, even a stronger
task asking for the whole independent family has the closed-form solution
printed by Construction 4.1. A solver does not need to search the nominal word
space or reconstruct a hidden planted answer.

### Stabilized variants

Propositions 5.1 and 5.2 only add dummy generators to the same maps. They
explicitly retain the subgroup `A_m` and its colored graph, so they retain all
of the witnesses above. Remark 5.3 is easier still: membership is exactly the
linear exponent-sum condition `e_x(w) = e_y(w)`. These non-injective variants
therefore do not supply a hard positive-witness family.

## Why nearby modifications do not qualify

- **Hide the construction with a random Nielsen automorphism.** Precomposing
  both maps by a long hidden change of free basis would conceal the displayed
  words, but recovering a planted basis is a new average-case problem. This
  paper gives no complexity reduction, hard planted distribution, or theorem
  transferring hardness to that distribution. Claiming H from the apparent
  obscurity of the transformed strings would be unsupported. It would also
  make canonicalization under changes of basis a substantive unresolved part
  of G8 rather than a harmless relabelling check.
- **Ask for the exact rank or a maximum-rank basis.** Section 6 only conjectures
  the upper bound `rank Eq(g,h) <= 2n-2`. An exact-rank or maximum claim makes
  optimality part of the answer, which the task forbids, and the paper does not
  prove that its lower bound is the complete equalizer rank.
- **Ask whether the equalizer is trivial or whether another word exists.** A
  yes/no answer or an absence is not an admissible witness. On the explicit
  family nontriviality is already witnessed by every `x_i`.
- **Use a general or bounded Post Correspondence Problem instance.** Section 1
  mentions algorithmic work connecting equalizers and PCP, but this paper does
  not prove a computational-hardness regime or provide an answer-first hard
  distribution for general PCP instances. Substituting that external problem
  would no longer be generating the explicit family established here.
- **Return a colored Stallings graph.** The paper constructs `Gamma_n`
  explicitly in Section 4. Returning it is a transcription task, while asking
  for a proof that it captures an entire equalizer would require more than the
  requested substitution-style witness verification.

The paper also identifies genuinely easy special settings in its introduction:
Ciobanu and Logan give algorithms for immersion pairs, and fixed-subgroup cases
have constructive theory for endomorphisms. More importantly for this task,
the paper never asserts computational hardness for its counterexamples; the
word "harder" in Section 1 concerns the mathematical rank problem, not the
complexity of finding one of the explicitly exhibited words.

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G — sample the witness first | Pass in principle | Construct any listed `x_i` or graph-basis word before emitting the maps. |
| H — no polynomial/closed-form solver | **Fail** | `x_1` solves every instance; the `2n-2` graph-basis words above solve the stronger batch task. |
| V — cheap exact verification | Pass | Substitute generator images, freely reduce both words, and compare. |
| G4/G6 | Not run | A deterministic 100% attack makes random-guess estimates irrelevant. |
| G7 | Does not rescue H | Larger `n` creates more immediately visible witnesses. |
| Oracle loop | Not run | Step 0 requires stopping once H fails. |

The prior triage was correct about substitution verification but not about
hardness: the colored Stallings graph plants witnesses by displaying the very
loops that produce them.
