# Rejected: arXiv 1903.00471

Paper: Assaf Goldberger, [*Cohomology-Developed Matrices — constructing
families of weighing matrices and automorphism actions*](https://arxiv.org/abs/1903.00471),
version 3 (2023).

## Decision

No family in the paper clears **H** under either track while retaining the
paper's native matrix objects and the required no-tool limits.  **G** and **V**
are not the problem: the paper constructs generalized weighing matrices by
theorem, and a submitted matrix can be checked exactly by testing its alphabet,
support, and `W W* = w I`.  The failure is hardness.

- **Track A fails.**  The paper proves existence and gives constructions, not
  average-case hardness for a generated distribution.  In its easiest and most
  explicit infinite family, Section 4.1 gives every Paley kernel entry directly
  as the power-residue symbol of `t-s`; Corollary 4.2 only appends the all-one
  border.  Algorithm 3.11 is also an exhaustive constructive algorithm for all
  `H^1`-developed matrices from the group action and stabilizer characters.
- **Track B also fails.**  The specialized certificate-producing algorithm for
  the proposed Paley distribution is already the shortest route: make the
  quadratic-residue table and cyclically shift its sign row.  The compact route
  is no shorter in substance than this mechanical algorithm, and both are tiny
  at every writable full-matrix size.  Enlarging the matrix until the routine
  arithmetic might become burdensome crosses the 256-atom output cap first.

This is therefore not a rejection based merely on “an algorithm exists.”  The
mechanical cost and compact route are quantified below; they are comparable and
there is no million-operation-versus-dozen-operation compression gap to test.

## What the paper actually establishes

Section 1 defines a `GW(N,w;n)` as an `N x N` matrix over zero and the `n`th
roots of unity satisfying `W W* = w I_N`.  Sections 2–3 formulate the
Automorphism Lifting Problem in terms of monomial covers.  Theorem 3.4
classifies split monomial covers by pairs of stabilizer homomorphisms, Proposition
3.7 gives the executable orientability condition, and Algorithm 3.11 constructs
the corresponding matrices orbit by orbit.  The complexity remark following
the algorithm explicitly gives a general exhaustive bound and then notes the
usual reductions from using orbit-spreading generators and a small number of
orbits.

Theorem 5.2(c) is the theorem-backed orthogonality route: if the `(P,P)` action
has one orientable orbit, every invariant matrix satisfies `A A* = c I`.
Theorem 6.1 applies it to projective spaces, Theorem 6.9 to Grassmannians, and
Theorem 6.13 to flag varieties.  These are strong generatability results, but
none states computational hardness or identifies a hard distribution.

Most decisively, Section 4.1 has already specialized all of that machinery for
the Paley family.  For finite-field indices `s != t`, equation (4.1) is

```text
A[s,t] = chi(t-s),       A[s,s] = 0,
```

where `chi` is the chosen power-residue character.  Corollary 4.2 adds one row
and column of ones to obtain `GW(q+1,q;n)`.  Thus the certificate is produced by
direct evaluation, not by solving a search instance.

## Mechanical cost versus compact route

I benchmarked the real (`n=2`) Paley construction in CPython using exact integer
arithmetic.  For prime `q`, the mechanical implementation first computes the
`(q-1)/2` nonzero squares and then evaluates all `q(q-1)` off-diagonal
differences.  The compact route computes that same residue row once and obtains
the other finite rows by cyclic shifts.  There is no different invariant or
change of variables left to discover.

| candidate | answer atoms | JSON chars | mechanical exact operations | compact route | measured build | measured exact `WW^T` check |
|---|---:|---:|---:|---:|---:|---:|
| full `W(14,13)` (`q=13`) | 196 | 499 | 162 (6 modular squares + 156 differences) | 6 modular squares, then cyclic shifts | 0.0000148 s | 0.000184 s |
| cyclic first row only (`q=251`) | 251 | 628 | 125 modular squares/table inserts | the same 125 operations | 0.0000261 s | not needed to produce the row |

The timing figures are averages over 20,000 construction runs and 5,000 Gram
checks for `q=13`, and 5,000 first-row runs for `q=251`, on this builder.  They
are included only to fix scale; the exact operation counts are the important
numbers.

The largest full matrix allowed by G9(c) in this family has order 14: it uses
196 atomic entries.  The next relevant prime, `q=17`, produces an 18 by 18
matrix with **324 atoms**, already beyond the 256-atom cap.  At the largest
compressed-first-row setting, the mechanical method and the purported compact
route are literally the same 125-square computation.  A model failure there
would measure modular table production and transcription, not recognition of a
hidden structure.  This is exactly the Track B rejection case where the compact
route is no shorter than the mechanical route.

## Other native candidates checked

| candidate | result |
|---|---|
| Output the Paley conference matrix | G and V pass; H(A) fails because Section 4.1 is a direct formula, and H(B) fails by the cost comparison above. |
| Output only a group-developed first row | It postpones the atom cap to `q <= 251`, but certificate production is still exactly residue-table enumeration; no compression gap appears. |
| Output a symbolic quadratic-character formula | Euler's criterion gives the one-monomial polynomial `x^((q-1)/2)` directly from the public `q`.  This removes the transcription, but also removes the search: mechanical and compact costs are both constant-size formula evaluation, with no seed-dependent hidden information. |
| Output the monomial-cover characters | Section 4.1 writes them explicitly as `psi_X(a)=chi(a)` and `psi_Y=1`; for `n=2` the bounded answer space is tiny, and for larger `n` direct character evaluation remains the whole task. |
| Projective-space matrix (Theorem 6.1) | The only non-Paley case comfortably near the full-matrix cap is `q=3,d=2`, of order 13 (169 atoms); the next parameter moves outside the cap, while Algorithm 3.11 and the determinant/residue characters still construct it directly. |
| Grassmannian matrix (Theorem 6.9) | The first genuinely non-projective case, `q=3,d=4,k=2`, has order 130, hence 16,900 matrix entries. |
| Flag-variety matrix (Theorem 6.13) | The order is a Gaussian multinomial and exceeds the writable range at the first nontrivial parameters satisfying the theorem's `n >= r` condition. |
| Quasiproduct (Theorem 5.9) | It composes already-known matrices and increases the output order; it supplies G by composition but worsens G9 without creating a shorter recovery witness. |
| Hide row/column permutations or signs | These are precisely Hadamard equivalences from Section 1.  They are structure-preserving transformations, but at fixed parameters they are the same problem under G8 and cannot provide distinct-instance evidence; adding arbitrary side constraints would make the benchmark about an external completion/parity problem rather than this paper's construction. |

## Gate outcome

| requirement | result |
|---|---|
| G — generatable | Pass for the paper's matrices by Corollary 4.2 and Theorems 5.2, 6.1, 6.9, and 6.13. |
| V — exact witness | Pass: exact root-of-unity encoding and matrix multiplication decide `W W* = w I`; for `n=2` this is integer arithmetic only. |
| H — Track A | **Fail:** no distributional hardness theorem or regime, and the shipping candidate has a direct construction. |
| H — Track B | **Fail:** mechanical and compact certificate production are the same residue-table/cyclic-shift computation (125 exact operations even at the largest compressed writable case). |
| G9(c) escalation | Full matrices exceed 256 atoms immediately after `q=13`; compressed rows remain writable but are pure arithmetic/transcription with no shorter structural route. |
| Overall | **Rejected before code, as STEP 0 requires.** |

No generator or hand-written hardening evidence was created.  Building one
would only wrap the displayed construction in a task whose certificate is
produced by the same tiny algorithm, or would replace the paper's mathematics
with an unrelated hidden-permutation/completion puzzle.
