# arXiv 1607.08453 problem generator

This is a native graph-product, **Track B** generator based on Ana Silva’s
[Fall-colorings and b-colorings of graph products](https://arxiv.org/abs/1607.08453).
It ships at `medium`: all local gates pass and the script-owned bare oracle
loop returned `hardened`, with an evidence-quality caveat recorded below.

| Profile field | Value |
|---|---|
| Track | B — an efficient exact scan exists and is reported |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: two ordered triples of factor vertices |
| Intuition | change of variables: undo affine labels to expose phase boundaries |
| Domain essentiality | native; no reduction |

## The problem

The solver receives two implicitly but exactly specified vertex-coloured cycle
graphs and their strong product. Each factor has three odd alternating colour
blocks, affinely relabelled by a displayed chain of modular bijections. It must
give one b-vertex of each factor colour. The six labels certify all nine product
colours: every Cartesian pair of supplied factor witnesses is a b-vertex of the
displayed strong-product colouring. Verification decodes only the six labels,
checks their two cycle neighbours, and forms the nine exact product-neighbour
colour sets.

This is the paper’s native mathematics. Section 1 fixes the definition of a
b-vertex. Section 2.1 defines b-homomorphisms, and Lemma 2 proves that an
adjacency product preserves them. Section 3 defines the strong product;
Proposition 3 says `K3 strong-product K3` is `K9`, and Corollary 6 gives the
composed b-colouring used here.

## Why Track B

Track A would be false. The product certificate is produced explicitly from
factor certificates, and the general mechanical method simply scans every
factor vertex and its closed neighbourhood. For decoder length `L` this costs
`O((|V(A)|+|V(B)|)L)` exact operations. On eight shipping instances the
reference implementation solved 8/8, averaging **99,603,306 operations and
8.67 seconds** (maximum 114,519,979 operations and 9.57 seconds in the final
self-test).

The compact route is much shorter. In decoded coordinates the colour word is
three odd blocks `0101...`, `1212...`, `2020...`; the phase changes identify
the three factor b-vertices. Composing each inverse affine chain and evaluating
it at those boundaries takes **158 exact operations** at shipping size. That
route must first be recognized; performing a roughly 100-million-operation
scan without tools is not viable in context.

The paper’s easy regimes matter here. Section 3 explicitly classifies products
of complete graphs (Proposition 3, Proposition 4, and Theorem 3.2), so using
complete factors would reduce the task to a displayed row/column formula. This
family instead uses non-complete cycles and asks for concrete b-vertices, while
remaining honest that its compact affine construction is efficiently solvable.
The Introduction’s NP-completeness statements are worst-case results and are
not used as distributional-hardness evidence.

## Worked demo

For `make_instance(n=3, spread=0, chain_len=2, seed=7)`, the complete rendered
problem is:

```text
Find b-vertices for a strong-product b-colouring

A proper k-colouring assigns one colour in {0,...,k-1} to every vertex and
gives adjacent vertices different colours.  A vertex of colour c is a
b-vertex if it has at least one neighbour of every colour other than c.  A
proper colouring is a b-colouring if every colour has a b-vertex.

Factor A: s=3 (odd), order m=3s=9.
Its encoded vertex labels are the integers 0 through 8.
To decode a label x, start z=x and apply these rows in order;
a row (a,b,a_inv) means z <- (a*z+b) mod m, and a_inv is
the displayed multiplicative inverse of a modulo m:
  (5, 0, 2)
  (2, 8, 5)
Two encoded labels are adjacent exactly when their decoded coordinates
differ by +1 or -1 modulo m, so this factor is a cycle.
For decoded coordinate t, write t=q*s+r with q in {0,1,2} and
0<=r<s. Its colour is (q + (r mod 2)) mod 3.

Factor B: s=3 (odd), order m=3s=9.
Its encoded vertex labels are the integers 0 through 8.
To decode a label x, start z=x and apply these rows in order;
a row (a,b,a_inv) means z <- (a*z+b) mod m, and a_inv is
the displayed multiplicative inverse of a modulo m:
  (2, 5, 5)
  (2, 8, 5)
Two encoded labels are adjacent exactly when their decoded coordinates
differ by +1 or -1 modulo m, so this factor is a cycle.
For decoded coordinate t, write t=q*s+r with q in {0,1,2} and
0<=r<s. Its colour is (q + (r mod 2)) mod 3.

The strong product P of A and B has ordered-pair vertices (x,y).  Distinct
(x,y) and (x',y') are adjacent exactly when one of the following holds:
  * x=x' and y is adjacent to y' in B;
  * y=y' and x is adjacent to x' in A;
  * x is adjacent to x' in A and y is adjacent to y' in B.
The displayed product colouring is
  C(x,y) = 3*colour_A(x) + colour_B(y),
so its colours are the integers 0 through 8.

Your certificate must be [[a0,a1,a2],[b0,b1,b2]].  For c=0,1,2, ac must be
an encoded label of a b-vertex of colour c in A, and bc must be an encoded
label of a b-vertex of colour c in B.  Equivalently, every one of the nine
ordered pairs (ai,bj) must be a b-vertex of product colour 3i+j.  The order of
the two rows and the colour order 0,1,2 within each row are fixed.  Labels are
decimal integers, all bounds above are inclusive, and repeats are forbidden
within either row.

Give your final answer inside <answer></answer> tags as one JSON 2-by-3 matrix of decimal integers.
Example: <answer>[[3,17,42],[8,29,11]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[1,4,7],[0,3,6]]</answer>`.
`verify(inst, [[1,4,7],[0,3,6]])` returns `(True, "ok")`; swapping the first
two entries returns `(False, "factor A entry 0 has colour 1, not 0")`. A person
can solve this smallest instance by listing each nine-vertex factor cycle.

## Difficulty presets

| Preset | Odd block `s` per factor | Decoder stages | Compact operations | Status |
|---|---:|---:|---:|---|
| demo | 3 | 2 | 38 | hand-scale illustration |
| easy | 100,001–120,001 | 10 | 118 | oracle solved 1/3 |
| medium | 1,000,001–1,200,001 | 14 | 158 | **ships; oracle 0/3** |
| hard | 10,000,001–12,000,001 | 18 | 198 | available escalation |

Each factor has `3s` vertices. Escalation increases factor orders and decoder
crowding while the certificate remains six integers.

## Gate results

| Gate | Final measured result |
|---|---|
| G1 | 16/16 planted witnesses verified; 16/16 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged prose/fences round-tripped; malformed output returned `None` |
| G4 | 0/200,000 structure-aware guesses; space 1,434,459,202,219,035,049,130,646,999,414,694,875 |
| G5 | shipping density 0/200,000; demo exact count 1/729; 4,096 restarts failed in 0.032 s; seed-7 reference scan 80,344,233 ops in 6.23 s |
| G6 | five attacks each 0/8; reference scan 8/8 as expected, mean 99,603,306 ops / 8.67 s |
| G7 | doubled factor orders 6,151,287 and 6,216,081; answer stayed six atoms |
| G8 | 80/80 key invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 51 characters, 27 conservative tokens (29 worst-case), 6 atoms, 158 route operations |

## Oracle loop

| Preset | Seed | Model | Result | Verification reason |
|---|---:|---|---|---|
| easy | 109082055 | Gemini 3.8 Flash | solved | `ok` |
| easy | 1612409835 | GPT-5.6 Terra | failed | factor-B colour mismatch |
| easy | 144858797 | Gemini 3.8 Flash | failed | factor-A colour mismatch |
| medium | 1205276760 | GPT-5.6 Terra | failed | factor-A colour mismatch |
| medium | 587647952 | Gemini 3.8 Flash | failed | empty HTTP-200 response marked `content_filter` |
| medium | 1266896402 | Gemini 3.8 Flash | failed | HTTP-200 body was a provider error message; no answer parsed |

The script verdict is `hardened` at medium. Only the first medium row is a clean
mathematical miss; the other two are provider-side failures that escaped the
harness’s API-error redraw because they arrived as HTTP 200 responses. This
weakens the oracle evidence and should not be mistaken for three independent
mathematical failures. The transcript is preserved verbatim.

## G9 arms

| Arm | Solved / attempts | Diagnostic |
|---|---:|---|
| bare shipping rows | 0/3 | one invalid answer; two provider artifacts as above |
| structural hint | 0/3 | one invalid answer, one wrong impossibility argument, one truncated calculation |
| placebo hint | 0/3 | two invalid answers, one truncated calculation |

`hinted − placebo = 0.0`. The structural hint bought no observed solved-rate
improvement, so this run does not show that naming the phase-boundary invariant
alone is sufficient. It also does not gate shipment. Answer size and route
effort are within all G9(c) caps.

## Use

```python
from gen_1607_08453 import make_instance, render, parse_answer, verify

inst = make_instance(n=1_000_001, spread=100_000, chain_len=14, seed=123)
print(render(inst))
candidate = parse_answer("<answer>[[1,2,3],[4,5,6]]</answer>")
print(verify(inst, candidate))
```

From the repository root:

```bash
bash scripts/emit.sh 1607.08453 20
```

## Caveats

This family is easy with a short program, a symbolic affine simplifier, or the
compact coordinate insight; that is the Track B premise. The 0/200,000 guess
rate uses the exact advertised prior—one uniformly sampled label from each
known colour class—so it rules out blind legal guessing, not correlated or
algebraic attacks. The panel did not test SAT/ILP encodings, graph-isomorphism
software, a purpose-built symbolic simplifier, side channels, or models with a
calculator. All factor vertices have degree two, defeating degree outliers but
also making the underlying graph class transparent.

The graph is supplied by exact formulas rather than a multi-million-row edge
list; the mechanical baseline scans that representation. Canonicalization is
complete for the represented affine relabellings and factor swap, while the
self-test samples affine relabellings rather than materializing arbitrary
million-vertex permutations. Finally, the formal bare verdict relies on two
provider artifacts, so a future rerun with three clean medium responses would
materially strengthen confidence even though the local G/H/V evidence is
complete.
