# Rejection: arXiv:1111.3517

## Decision

This paper does not yield a family that passes all of G, H, and V under the
tested construction. The retained construction passes **G** and **V**, but it
fails **H on Track B**. It cannot be claimed on Track A either.

The source is Yero and Rodríguez-Velázquez, [*Roman domination in Cartesian
product graphs and strong product graphs*](https://arxiv.org/abs/1111.3517).
Section 1 fixes the exact Roman-domination and graph-product definitions.
Section 2 defines the class \(\mathfrak F\) by efficient dominating sets (perfect
codes), and the proof of Theorem 26 uses their closed-neighborhood partition
inside a strong product. Those facts license the retained generator and its
checker. Theorems 10, 17, and 23 are explicit upper-bound constructions, while
Theorem 27 derives Romanity directly for the stated product class. The paper
contains no average-case or generated-distribution hardness theorem.

## The attempted Track B family

The generator first samples two finite-field hyperplanes and then constructs
two polynomially presented Cayley graphs for which those hyperplanes are
perfect codes. Their product is a perfect code in the strong product, so twice
its indicator is a Roman dominating function. The certificate is two
projectively normalized hyperplane normals. It is known by inverse generation,
and `verify` checks the two transversal identities exactly without reading the
planted answer.

For the tested \(p=29,d=5\) preset, the mechanical normalized-projective scan
has complexity \(O(d p^d)\). It averaged **25,019,321 exact field operations and
0.832 seconds** to find certificates across eight seeds; a full count on the
measured instance used **108,961,350 operations and 3.533 seconds**. The compact
route takes the annihilator of the common nonlinear-coefficient span and used
at most **192 exact field operations** for both factors.

That arithmetic gap initially made the construction a plausible Track B
family. In practice, however, the common-nullspace invariant is exposed by the
polynomial presentation and is readily executable without tools. The
script-owned bare hardening run produced these scored results:

| parameters | valid solves / attempts |
|---|---:|
| \(p=29,d=5\) (`easy`) | 3 / 3 |
| \(p=37,d=5\) (`medium`) | 2 / 3 |
| \(p=47,d=5\) (`hard`) | 3 / 3 |
| \(p=97,d=5\) (escalated) | 3 / 3 |

Thus **11/12** unhinted attempts returned certificates accepted by the exact
checker. Increasing the modulus and coefficient crowding did not hide the same
five-dimensional nullspace calculation. A subsequent \(p=191\) level was not
scored because the OpenRouter quota expired; its four HTTP 403 records are
infrastructure errors, not failed solves, and are not used as evidence.

Track A is unavailable because neither the paper nor these measurements support
hardness for the generated Cayley distribution. Track B fails because the
compact 192-operation route is precisely what the evaluated solvers repeatedly
recognized and executed. This is not a rejection merely because an efficient
algorithm exists: the mechanical/compact costs are reported above, and the
deciding evidence is successful no-tool execution across every tested size.

## Retained evidence

- `rejected_gen_1111_3517.py`: complete generator and local gates.
- `selftest_report.json`: passing G1–G9(c) measurements for the attempted family.
- `llm_loop_transcript.jsonl`: script-owned scored bare attempts and later quota
  errors.
- `g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl`: script-owned
  quota-error diagnostics; neither contains a scored attempt.

The module is retained for audit as required. It must not be emitted as a
shipping generator.
