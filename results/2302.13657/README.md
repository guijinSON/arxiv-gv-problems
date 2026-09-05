# Affine isomorphisms of arc structures (arXiv:2302.13657)

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | exact symbolic six-coefficient affine map on arc coordinates |
| Intended intuition | invariant: the finite-field sum of a step set scales with the hidden multiplier |
| Domain essentiality | native; no reduction |

## Problem and trust model

[Dalmau, Krokhin, and Opršal, *Functors on relational structures which admit both left and right adjoints*](https://arxiv.org/abs/2302.13657) defines relation-preserving maps in Definition 2.2 and the three-relation arc structure in Section 6.2. Its vertices are directed arcs; `D`, `I`, and `O` record consecutive arcs, a common head, and a common tail. Section 6 also states that a digraph homomorphism induces a homomorphism between the corresponding functor images.

An instance gives two cyclic Cayley digraphs over the same prime field by exact step sets `S` and `T`. The answer is a six-coefficient ambient affine map `(x,s) -> (a*x+c*s+b,d*x+e*s+f)` on arc coordinates. The checker uses arc-set membership to force `d=0`, then `O` and `D` to force `c=f=0` and `e=a`; it also checks invertibility and the exact identity `a*S=T (mod p)`. Relation `I` then follows from equality of transformed heads. Generation is inverse: sample `a,b`, form `T=a*S`, and retain `[a,0,b,0,a,0]`. No instance is solved during generation.

This is honestly Track B. The paper gives no distributional hardness theorem for planted homomorphisms—in fact its conclusion says no specific promise-CSP hardness application is known beyond the arc-graph use it cites—so Track A would be unsupported. The exact reference method first propagates the four relation-forced coefficient equalities, then enumerates the image of one source step and checks each possible multiplier: `O(m^2)`, with an eight-seed hard-preset median of 5,389 counted operations and 0.00045 seconds in the recorded self-test. The compact route notices covariance of the set sum. The source set is constructed with sum one, so after summing both displayed sets the target sum is `a`; including the four coefficient implications, this is 242 operations at hard. The paper-side easy mechanism is functoriality itself (Section 6, before Definition 6.1), not a hardness theorem.

## Worked demo

Here is `render(make_instance(n=11, step_count=5, seed=0))` in full:

```text
Affine isomorphism of arc structures over a prime field

All arithmetic below is modulo the prime p = 11, using canonical residues
0,1,...,p-1.  The displayed lists are unordered sets: they contain distinct,
nonzero residues, and their written order has no meaning.

For a step set S, define the cyclic Cayley digraph G(S).  Its vertices are the
residues x in F_p.  For every x and every s in S it has the directed arc
x -> x+s.  Write that arc as the pair (x,s).

The arc structure A(S) is a relational structure whose vertices are all arcs
(x,s) of G(S), with three binary relations:

  D((x,s),(y,t)) holds exactly when x+s = y       (consecutive arcs);
  I((x,s),(y,t)) holds exactly when x+s = y+t     (the same head);
  O((x,s),(y,t)) holds exactly when x = y         (the same tail).

Source step set S = [1, 3, 4, 6, 9]
Target step set T = [6, 7, 8, 9, 10]

Find six canonical residues a,c,b,d,e,f in {0,...,p-1} such that the affine rule

  Phi(x,s) = (a*x+c*s+b mod p, d*x+e*s+f mod p)

is a bijective homomorphism from A(S) to A(T): it must send every source arc to
a target arc and preserve all three relations D, I, and O.  Its 2-by-2 linear
part must be invertible modulo p.  The six coefficients are the complete finite
description of Phi; do not list its p*|S| values.  Coefficients are ordered
exactly as a,c,b,d,e,f; order matters and no coefficient may be omitted.

Give your final answer inside <answer></answer> tags, as six base-10 integers
a, c, b, d, e, f separated by commas.  Example: <answer>3, 0, 7, 0, 3, 0</answer>
Output nothing else inside the tags.
```

The answer is `<answer>7, 0, 4, 0, 7, 0</answer>`. `verify(inst, [7,0,4,0,7,0])` returns `(True, "ok")`; `verify(inst, [1,0,4,0,1,0])` returns `(False, "the affine map sends steps to the wrong set (3 missing, 3 extra)")`. A person can solve the demo by propagating the relation constraints and testing ten multipliers, or by observing that the source sum is 1 and the target sum is 7 modulo 11.

## Difficulty and measured gates

| preset | requested `n` | actual prime for seed 0 | steps `m` | compact operations | status |
|---|---:|---:|---:|---:|---|
| demo | 11 | 11 | 5 | 12 | hand-solvable illustration |
| easy | 2,000,000 | 2,000,221 | 60 | 122 | oracle run blocked |
| medium | 3,000,000 | 3,000,061 | 90 | 182 | not reached |
| hard | 5,000,000 | 5,000,161 | 120 | 242 | provisional shipping preset |

Difficulty raises both the prime-field haystack and the near-symmetric step crowd while the certificate stays six integers. `escalate()` continues both axes until 149 steps; the answer length remains fixed.

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verify; 12/12 JSON round-trips |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | tagged answer recovered from prose/Markdown; garbage rejected |
| G4 | 0/200,000 structure-aware guesses; exact hard probability `1/(p-1) = 1.999936e-7` |
| G5 | exactly `p=5,000,161` valid affine maps in the bounded language; reference median 5,389 operations / 0.00045 s |
| G6 | five attacks, each 0/8; reference and compact algorithms each solve 8/8 as expected |
| G7 | doubled request builds at a larger prime, verifies, enlarges the search space, and keeps six answer atoms |
| G8 | 100/100 affine/order/reversal invariance checks, 100/100 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass: 31 chars, about 8 tokens, 6 atoms, 242 intended operations |

## Oracle loop and G9 diagnostics

The mandatory harness was run after the final construction change, but the shared OpenRouter key returned HTTP 403 `Key limit exceeded` on every retry. Errors are not model failures. Consequently `.meta.json` has no hardening verdict, `SHIPPING_DIFFICULTY="hard"` is provisional, and this directory is **not submit-ready** until the three runs are repeated with a funded key.

| run | preset | solved/scoreable attempts | infrastructure errors | conclusion |
|---|---|---:|---:|---|
| bare | easy | 0/0 | 4 | no hardness verdict |
| structural hint | hard only | 0/0 | 4 | diagnostic unavailable |
| placebo hint | hard only | 0/0 | 4 | diagnostic unavailable |

Hinted minus placebo is therefore not measurable. The hint’s effect on the claimed invariant cannot yet be assessed.

## Use

```python
import gen_2302_13657 as g

inst = g.make_instance(seed=0, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
candidate = g.parse_answer("<answer>4288884, 0, 4076256, 0, 4288884, 0</answer>")
print(g.verify(inst, candidate))
```

After rerunning the oracle evidence successfully, emit from the repository root with `bash scripts/emit.sh 2302.13657 20`.

## Caveats

This benchmark asks for an affine induced map, not an arbitrary homomorphism, and makes no NP-hardness claim. With tools, even the reference algorithm finishes in milliseconds; that is why this is Track B. The G4 prior is uniform over the relation-forced maps `[u,0,b,0,u,0]`, already enforcing the constraints a reader can derive cheaply, but it says nothing about a solver that discovers the sum invariant. The panel tests minimum-residue alignment, sorted greedy alignment, an additive ansatz, small multipliers, and 4,096 random restarts. It does not test general graph-isomorphism software, Weisfeiler–Leman refinement on the fully expanded structures, or multiplicative-energy attacks. The canonical key quotients input order, independent affine vertex relabellings, and reversal; it does not solve arbitrary Cayley-graph isomorphism, so a non-affine isomorphism could remain as two keys. The Cayley presentation is succinct, but it defines the paper’s native finite digraph and arc-structure relations exactly rather than replacing them with a surrogate. Most importantly, the required cross-vendor oracle evidence is currently missing because of external quota exhaustion.
