# Step-0 rejection: arXiv:2510.20376

Paper: Masoumeh Koohestani, Doost Ali Mojdeh, and Mohsen Ghasemi,
[*Total perfect codes in Cayley sum graphs of cyclic groups*](https://arxiv.org/abs/2510.20376),
arXiv:2510.20376v1.

## Decision

No family justified by this paper clears **H**.  The natural planted family clears
G and V, but it clears neither Track A nor Track B.  This is a Step-0 rejection:
no generator module was written, so there is no built module to rename and retain.

The failure is not that the certificate is invalid.  A submitted vertex set can be
checked exactly and cheaply by counting its neighbours.  The failure is that the
paper's principal hypotheses expose the certificate by an explicit linear-time
rule, while a more general inverse-generated factorization also fell immediately
to the domain-standard exact-cover algorithm.

## Exact native problem and certificate

Section 1 defines `CS(G,S)` on the group elements: distinct `g,h` are adjacent
exactly when `g+h` belongs to `S`.  A total perfect code `C` is a vertex subset for
which every vertex, including vertices of `C`, has exactly one neighbour in `C`.
Thus the verifier for a proposed `C` only has to check, for every `x`, that exactly
one `c in C` satisfies `x+c in S` and `x != c`.

The decisive result is Section 2, Lemma 2.1 and Remark 2.2:

```text
C is a total perfect code of CS(G,S)  iff  G = (-C) ⊕ S.
```

Here `⊕` means that every group element has a unique representation as a sum of
one element from each factor.  This gives a valid inverse-generation route: choose
an exact factorization first and carry one factor as the certificate.  Lemma 3.5
states the same certificate as the executable polynomial identity

```text
f_(-C)(x) f_S(x) = 1 + x + ... + x^(n-1)  (mod x^n-1).
```

Consequently G and V are not the obstacles.

## What makes the paper's regimes easy

The paper is a characterization paper, not a hardness paper.  Its main cyclic
results repeatedly reduce existence and recovery to residues:

- Lemma 3.1 constructs the code `C = k Z_n` as soon as `k=|S|` divides `n`
  and the elements of `S` are pairwise distinct modulo `k`.
- Theorem 3.2 says this residue test is necessary and sufficient for subgroup total
  perfect codes.
- Theorems 3.6 and 3.7 make it necessary and sufficient for the stated prime and
  prime-power degree regimes.
- Theorem 3.13 does the same for square-free connection sets over all cyclic orders
  in the displayed class `N`, under the stated coprimality condition.
- Lemma 4.2 gives the direct-product code explicitly as
  `(m_1 Z_n1) x ... x (m_d Z_nd)`; Theorems 4.4 and 4.6 again recognize the
  applicable prime/prime-power cases by a coordinate residue test.
- Theorem 3.4 is even more explicit in its special regime: all codes have the
  displayed two-element form `{h_1+i, h_2+i+k}`.

The paper contains no worst-case or distributional complexity theorem, no
average-case claim, and no hard parameter regime for recovering a total perfect
code.  Its results instead recognize existence and write down a code.

## Why Track A fails

Track A would require evidence that the generated distribution resists the
domain-standard method.  None of Theorems 3.2, 3.4, 3.6--3.8, 3.13, 4.4, or 4.6
is a hardness theorem.  A generator that samples one representative of every
residue class modulo `k` lies exactly in Lemma 3.1's easy distribution: after
`k=|S|` is known, the answer is simply

```text
0, k, 2k, ..., (n/k-1)k.
```

Checking the residue premise costs `O(|S|)` bucket insertions and emitting the
answer costs `O(n/|S|)` additions.  Recovering the advertised witness does not
require graph search.  General-graph NP-hardness, even if imported from outside
the paper, would not establish hardness for this distribution.

## Why Track B also fails: measured mechanical and compact costs

I tested the strongest plausible Track-B escape from the explicit subgroup
formula.  It uses Remark 2.2 directly and constructs a non-subgroup cyclic
factorization from mixed-radix digit factors.  At the representative output-sized
setting

```text
n = 16,384,    |S| = 1,024,    |C| = 16,
```

four binary digit positions form `-C`, the other ten form `S`, and an even affine
shift preserves the factorization.  Plants and non-plants are not distinguished by
degree: `S` is square-free, and the resulting Cayley sum graph is regular and
connected.  The certificate has only sixteen vertices.

The natural domain-standard algorithm is Algorithm X on the exact-cover instance
whose candidate blocks are the cyclic translates `S-c`.  A bit-set implementation
was run on eight independently shuffled instances (seeds 0 through 7).  It solved
all 8/8:

| measurement | result |
|---|---:|
| recursive search nodes | 17 on every seed |
| translate compatibility tests | 16--1,356; median 75 |
| search wall clock | 0.000086--0.005733 s; median 0.001207 s |
| mandatory input insertions | 1,024 |
| total input-plus-search primitive steps | 1,040--2,380; median 1,099 |

The compact route observes that the minimum and maximum connection residues expose
the missing digit mask, enumerates its sixteen submasks, and undoes the shift.  It
uses about 35 integer/bit operations.  Excluding the unavoidable scan needed merely
to read the 1,024-element input, the measured mechanical search is only 75 steps at
the median versus about 35 for the compact route.  Including input parsing gives a
roughly 31-fold count difference, but both routes are tiny and the extra work is
input reading rather than mathematical search.  They are therefore comparable in
the sense relevant to Track B: the compact route is a constant-factor presentation
shortcut, not a compression of millions of mechanical operations into a dozen.

This behavior is structural, not an unlucky implementation detail.  Translating a
known code produces further codes (Section 3, Lemma 3.10), so the exact-cover model
has many symmetric solutions; on these inverse-generated digit factorizations its
first consistent branch extends without backtracking.  Making the input longer only
grows the prompt and its scan cost, not the substantive search.  It would test
transcription/navigation rather than the paper's mathematics.

The theorem-backed family is easier still: its mechanical method and compact route
are literally the same residue test followed by the displayed subgroup formula.
The polynomial restatement in Lemma 3.5 does not rescue it, because coefficient
matching merely verifies the already explicit factor and the classified regimes
still return that factor directly.

## Gate outcome

| requirement | outcome |
|---|---|
| G -- generatable | **Pass:** inverse generation by `Z_n=(-C)⊕S`, or the theorem-backed subgroup construction. |
| V -- verifiable | **Pass:** exact neighbour counts, unique-sum counts, or Lemma 3.5's polynomial identity. |
| H -- Track A | **Fail:** no distributional hardness theorem, and the paper's parameter regimes have explicit residue algorithms. |
| H -- Track B | **Fail:** 17-node exact cover (median 75 compatibility tests) versus an approximately 35-operation shortcut; no qualitative compression gap. |

Accordingly, building the prior-triage proposal would manufacture a large-looking
graph whose planted code is recoverable by the paper's own formula or by essentially
backtrack-free exact cover.  Stopping at Step 0 avoids reporting that as hardness.
