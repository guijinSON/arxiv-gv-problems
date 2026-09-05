# Rejection: arXiv:2006.10650

Paper: Grigorii Horosh, Victor Shcherbacov, Alexandru Tcachenco, and
Tatiana Yatsko, [“On groupoids with Bol-Moufang type identities”](https://arxiv.org/abs/2006.10650).

## Decision

No module is shipped. The proposed family—construct a finite operation table
satisfying selected Bol–Moufang identities—clears **G** and **V**, but fails
**H on both Track A and Track B**. The failure is not that certificates are
hard to verify. It is that the native construction question has an immediate,
identity-independent answer.

The exact STEP-0 question is decisive here: the certificate is an `n x n`
Cayley table. A constant table `T[x,y] = 0` produces it in `O(n^2)` time and
satisfies every identity in the paper, because both sides of every identity
evaluate to `0` under every substitution. Thus no search or paper-specific
insight is needed. This attack succeeds for every `n`, seed, and selected
identity set.

## What the paper actually establishes

- Section 1 defines a groupoid and the classical and generalized
  Bol–Moufang identity formats.
- Section 2.1 states that there are `n^(n^2)` labelled groupoid tables of
  order `n`, then completely lists isomorphism and anti-isomorphism classes
  only at order 2 (Propositions 1–3 and Corollary 1).
- Section 2.2, Proposition 4 proves that transposing a table (the
  `(12)`-parastrophe) preserves the number of models of the paired identity.
  Theorem 1 explicitly lists the classical parastrophe map (28 two-cycles and
  four fixed identities). This is a direct table transpose plus a fixed
  lookup, not a hard certificate search.
- Section 2.2, Proposition 5 explicitly gives six order-2 groupoids that
  satisfy all `F1`–`F60`, with direct calculation as the proof.
- Section 2.3 says that a program was written to generate groupoids of orders
  2, 3, and 4 and reports the resulting counts in Tables 1 and 2. It gives no
  asymptotic hardness theorem, hard parameter regime, FPT boundary, or
  scalable distribution.

The paper therefore supports exact substitution and finite classification,
but not a Track-A distributional hardness claim.

## Gate analysis

| gate | result |
|---|---|
| G — generatable | Passes trivially: choose the constant table first; that table is the witness by inverse construction. |
| V — verifiable | Passes: evaluate the two four-leaf terms for every `(x,y,z)`. For `k` identities this costs `O(k n^3)` exact table lookups and comparisons. |
| H — Track A | Fails: `T[x,y]=0` is a known `O(n^2)` construction for every generated request, so the generated distribution has a deterministic polynomial-time solver. |
| H — Track B | Fails the required in-context attack: “output one repeated symbol in every cell” succeeds on 8/8 seeds (indeed on all seeds). The compact route is one observation followed only by writing the answer, so there is no hidden invariant to discover. |
| G4/G6 consequence | Regardless of the cardinality `n^(n^2)` of the table language, the all-constant construction has success probability 1 as a deterministic attack. A large random-candidate space cannot repair this. |

Even natural extra conditions do not rescue the proposed family. If a
nonconstant table is demanded, the left-zero or right-zero operation satisfies
all 60 *classical* identities because their variable order is unchanged. If a
Latin square, quasigroup, loop, or both-sided cancellation is demanded, the
abelian group operation `T[x,y]=(x+y) mod n` satisfies every classical and
generalized identity listed in the paper: each side has the same variable
multiset and hence the same sum. Those are also direct `O(n^2)` constructions.

## Mechanical cost versus compact route

The comparison was made at `n=16`, the largest full-table answer allowed by
the 256-atomic-element G9(c) cap, and with all 60 classical identities.

| route | measured or exact cost |
|---|---:|
| Uncached exhaustive substitution | `60 * 16^3 * (6 lookups + 1 comparison) = 1,720,320` primitive operations |
| Cached Python substitution benchmark | median `0.03385 s` over 9 runs (`998,400` table lookups and `245,760` comparisons) |
| Compact construction | 1 observation, then 256 identical output entries; no arithmetic or search |

At the paper's largest classified order, `n=4`, naive enumeration begins with
`4^16 = 4,294,967,296` tables, while checking all 60 identities on one table
uses only `26,880` uncached primitive substitution operations. The mechanical
enumeration can therefore be very large, but this does not create a Track-B
problem: the compact route is the first trivial ansatz a solver can try and it
always works. The gap measures avoidable enumeration, not structural insight.

## Other native formulations considered

1. **Find an isomorphism or anti-isomorphism.** The paper classifies only order
   2, where testing both permutations is constant work. Scaling this to a hard
   distribution would require a new groupoid-isomorphism construction and
   hardness argument absent from the paper. Encoding graph isomorphism into a
   table would be a convenience reduction, not native coverage licensed by
   this source.
2. **Return the parastrophic identity or table.** Proposition 4 and Theorem 1
   give the answer by transposition and a fixed 60-item lookup. Mechanical and
   compact routes are both `O(n^2)` (or constant for the identity name), so
   Track B has nothing to test.
3. **Return the number of satisfying groupoids.** Tables 1 and 2 are a lookup
   for orders 2–4. For unbounded `n`, a bare integer is not a self-contained
   witness of the count, and an exhaustive classification certificate violates
   the bounded-answer requirement.
4. **Require an exact nonassociative identity signature, a partial-table
   completion, or a rare local substitution.** These restrictions could remove
   the constant and abelian-group answers, but they are not the problem studied
   or a reduction licensed by the paper. The source supplies neither an
   unlimited certificate-preserving construction nor a hardness regime for
   them. Adding one would manufacture a new CSP benchmark rather than turn this
   paper into a verified native generator.

Accordingly, writing a generator would either ship a family defeated by the
all-constant attack or replace the paper's problem with an unsupported CSP.
The honest outcome is rejection rather than a misleading Track-A claim or an
obvious Track-B puzzle.
