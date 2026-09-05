# Rejected at Step 0: arXiv 1601.03780

Paper: Joseph Antonides, Claire Kiers, and Nicole Yamzon,
[*On the Long-Repetition-Free 2-Colorability of Trees*](https://arxiv.org/abs/1601.03780)
(v2, 27 January 2022).

## Decision

No generator is shipped. The prior-triage family—generate a tree of radius at
most seven and ask for a long-repetition-free binary coloring—passes **G** and
**V**, but it fails **H on both tracks**.

- **Track A is false.** Proposition 2.2 does not merely establish existence. Its
  proof gives the coloring directly: find a center, assign each vertex its
  distance from that center, and read its color from the fixed depth word
  `00010111`. This is an `O(|V|+|E|)=O(|V|)` algorithm on a tree and succeeds on
  every instance in the proposed radius-seven distribution.
- **Track B has no compression gap.** The compact route is the same center/depth
  traversal as the mechanical route. With an explicit coloring as the answer,
  it also has to emit one bit per vertex. At the 256-atom answer limit, the
  reference computation takes only about 0.00040 seconds and 3,319 elementary
  traversal/output events, while any route must already write 256 atoms. If the
  center is supplied, both routes reduce to the same one-BFS lookup procedure.
  There is no invariant that replaces a large mechanical calculation by a
  short calculation; recognizing the theorem *is* the whole algorithm.

The negative Tyler-tree result does not rescue the paper. A bare claim that a
Tyler tree has no valid 2-coloring is not an executable witness, while giving a
coloring and asking for a violating path requires an explicitly colored
229,768,889,091-vertex tree at height eight. A succinct coloring circuit plus a
private decoding trick would make the added encoding, rather than this paper's
tree-coloring mathematics, carry the difficulty.

I therefore stopped before Step 1, as required. No module, self-test report, or
oracle transcripts were fabricated.

## Exact paper objects and regimes

Definition 1.2 calls `uu` a *long square* when `|u| >= 3`; a word is
long-square-free when it contains no such contiguous factor. Definition 1.3
calls a vertex coloring long-repetition-free when the color word on **every
simple path** is long-square-free.

The paper proves two complementary statements:

1. **Proposition 2.2:** every tree of radius at most seven has a
   long-repetition-free 2-coloring. The proof colors by generation from a center
   using `00010111`.
2. **Lemma 3.2 and Proposition 3.4:** the Tyler tree `T_n`, whose level-`j`
   vertices have `2^(n-j)+1` children, is claimed not to admit such a coloring
   for `n >= 8`. The proof recursively extracts a binary subtree monochromatic
   on each level and turns a long palindrome in the level word into a repeated
   path word.

No hardness theorem, average-case statement, FPT boundary, approximation
result, or computational search problem appears in the paper. The positive
regime is constructive in the strongest possible sense, and the negative
regime is a fixed extremal obstruction rather than a hard family of search
instances.

## Step-0 certificate-producing algorithm

For the proposed positive family, the certificate algorithm is immediate from
the proof of Proposition 2.2:

1. Find a diameter by two breadth-first traversals and take its midpoint as a
   center (or use the already designated center if the instance supplies it).
2. Run breadth-first search from the center to obtain every vertex depth.
3. For depth `d in {0,...,7}`, output bit `00010111[d]`.

The complexity is linear because a tree has `|E|=|V|-1`. Randomly relabeling
the vertices does not hide this construction: breadth-first search is invariant
under relabeling and recovers the same generations.

The paper has several indexing slips in this proof: it writes
`a_1 ... a_7 = 00010111` even though the displayed word has eight symbols, and
later uses `a_0`. I used the only consistent interpretation, namely depths
`0,...,7`. I then independently checked the certificate instead of relying on
the prose proof. Every tree path has a depth sequence

```text
s, s-1, ..., l, l+1, ..., t
```

for endpoint depths `s,t <= 7` and lowest depth `l`. Exhaustively scanning all
such triples and every possible half-length at least three finds no square for
`00010111`; the only valid binary depth palettes of length eight are that word
and its bitwise complement `11101000`. Thus the positive construction is
correct under the repaired indexing, but a compressed palette answer would
have only two possibilities and would fail guess resistance.

## Mechanical cost versus compact route

I measured the strongest faithful version at the largest possible explicit
coloring under the output cap. The test tree had 256 vertices, two depth-seven
arms ensuring radius seven, and all remaining vertices attached with a local
seeded RNG without exceeding depth seven. The solver used three BFS traversals
(two to find a diameter/center and one for depths) followed by the palette
lookup.

The operation counter charged one event for each queue pop, directed-edge
examination, newly discovered vertex, and emitted color. On a tree this is

```text
3 * (n + 2(n-1) + (n-1)) + n = 13n - 9.
```

At `n=256` the measured figures were:

| quantity | result |
|---|---:|
| reference algorithm | diameter-center BFS + depth BFS + palette lookup |
| asymptotic complexity | `O(n)` time, `O(n)` space |
| counted events | **3,319** |
| mean CPython wall time over 10,000 runs | **0.000396 s** |
| answer atoms | **256** |
| unavoidable answer writes | **256** |

If a center is supplied, one BFS plus output costs `5n-3 = 1,277` counted
events at `n=256` and measured about `0.000091 s`. If the input is weakened
further to a parent-before-child array, both the standard and purported compact
routes use roughly `2n` depth/lookup operations. Reducing `n` enough to fit the
300-operation intended-route cap only makes this already identical algorithm
smaller; it does not uncover a shortcut.

So the comparison required for Track B is not “millions of mechanical steps
versus a dozen insightful steps.” It is the **same linear pass versus the same
linear pass**, with a 256-symbol output lower bound at the largest writable
setting. The large nominal space of all `2^256` color tables is irrelevant
because the theorem directly computes a valid member.

## Why the negative result does not yield another family

The height-eight Tyler tree is extraordinarily large. From Definition 1.6 its
level sizes are

```text
1,
257,
33,153,
2,154,945,
71,113,185,
1,208,924,145,
10,880,317,305,
54,401,586,525,
163,204,759,575,
```

for a total of **229,768,889,091 vertices**. This leaves the following options,
none of which clears all three gates:

| candidate task | disposition |
|---|---|
| Output a long-repetition-free coloring of a radius-seven tree | **H fails on Track A:** Proposition 2.2 gives the linear algorithm. **H fails on Track B:** the compact and mechanical routes coincide. |
| Output only the center and eight-bit depth palette as a compressed coloring | **H/G4 fail:** tree centers are found in linear time, and the exact palette scan leaves only the displayed word and its complement. At ordinary explicit sizes the candidate language is small; at huge succinct sizes the encoding, not the coloring theorem, creates the puzzle. |
| Certify that `T_8` has no valid 2-coloring | **V fails:** the word “no” is not a witness. The paper gives a prose universal argument, not a bounded refutation object with an executable local checker. Reusing the same fixed proof template would in any event be a lookup, not a large answer space. |
| Given an arbitrary coloring of explicit `T_8`, output a bad path | The path would pass **V**, but the instance needs over 229 billion explicit color bits. The paper gives no succinct coloring language or compact-route theorem. |
| Inverse-plant one bad path in a moderate colored tree | **G and V can pass, H is unsupported:** the paper proves no hardness for that planted distribution. Any public checksum, affine mask, or circuit used to reveal the planted path would be a benchmark-convenience wrapper absent from the paper. |
| Ask for a 3-coloring of `T_8` | The certificate itself has over 229 billion atoms; it violates the output contract before hardness is considered. |

There are also source-level off-by-one errors in the negative proof: Lemma 3.1
requires a binary word of length at least nine, but Proposition 3.4 selects only
`b_0,...,b_7` before invoking it, while the base case and the definition of
height indicate that level eight was intended. The source also defines binary
complement using `mod 1`, evidently instead of `mod 2`. These are repairable
typographical errors, but a benchmark checker cannot use the published prose as
an opaque negative certificate. Even under the natural repairs, the size and
hardness conclusions above are unchanged.

## Gate diagnosis

| requirement | result | evidence |
|---|:---:|---|
| G — certificate known without solving | Passes for the positive radius-seven construction | Proposition 2.2 supplies the depth palette; exact enumeration independently validates it. |
| V — exact witness checking | Passes for an explicit positive coloring or a supplied bad path | Enumerate tree paths and compare adjacent blocks exactly. |
| H — Track A | **Fails** | The certificate-producing algorithm is `O(n)` on every tree in the proposed regime. |
| H — Track B | **Fails** | At `n=256`, 3,319 mechanical events and 256 mandatory outputs; the compact route is the identical traversal, not a shorter structural computation. |
| Native negative alternative | **Fails V or the size contract** | Non-colorability has no finite executable certificate in the paper; an explicitly colored `T_8` has 229,768,889,091 vertices. |
| Overall | **Rejected at Step 0** | No paper-supported family satisfies G, H, and V simultaneously under either declared track. |

This rejection is not based merely on the existence of an efficient algorithm.
It identifies that algorithm, measures it at the writable limit, gives the
compact-route lower bound, and shows that the two routes are the same
calculation. The only ways found to create a large gap introduce a succinct
encoding or hidden decoding problem not present in the paper.
