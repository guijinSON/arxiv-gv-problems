# Rejected at Step 0: arXiv 2411.17780

Paper: Shaofei Du, Wenjuan Luo, and Hao Yu,
[*On Hamilton paths in vertex-transitive graphs of order \(10p\)*](https://arxiv.org/abs/2411.17780)
(2024).

## Decision

No problem family supported by this paper clears **G, H, and V** together.  The
prior-triage proposal--generate an arbitrary graph with a planted Hamilton
cycle--would be generatable and exactly verifiable, but it discards the paper's
defining promise: the graph is a very specific orbital graph for a
`PSL(2,s^m)` action.  An arbitrary planted graph need not even be
vertex-transitive.  Its difficulty distribution is not licensed or analysed by
this paper, so it cannot support Track A; using it would be a convenience
analogue of generic Hamilton cycle rather than coverage of this result.

The paper's native family also cannot be rescued as Track B under the output
contract:

- A literal Hamilton-cycle witness has at least **310 vertex atoms** in the
  smallest admissible case, already above the 256-atom cap.
- A compact semiregular-lift witness is possible in principle, but after the
  ten-orbit quotient data are made available, the paper's own proof produces
  it by the same roughly twenty operations as the compact route.  There is no
  no-tool compression gap.
- If only the expanded native graph is supplied, extracting those quotient
  incidences requires thousands of inspections even at the smallest case; the
  solver who sees the lifting insight must do that work too.  This exceeds the
  300-operation intended-route cap and measures data processing rather than
  discovery of structure.

This is chiefly an **H failure on both tracks**, with an independent G9(c)
failure for the literal native witness.  V is not the issue: either a full
cycle or an executable lift certificate can be checked exactly.  Per the
Step-0 stop rule, no generator, self-test report, README, or oracle transcripts
were created.

## What the paper actually proves

Section 2 defines orbital graphs, semiregular automorphisms, their quotient
(multi)graphs, and lifts.  Lemma 2.1 says that the lift of a quotient `k`-cycle
under a prime-order semiregular automorphism is either one `kp`-cycle or `p`
disjoint `k`-cycles; in the latter case every quotient edge used by the cycle
has multiplicity one.

Section 3 fixes the special action.  With `k=s^m`, `k+1=2p`, and
`10 | (k-1)`, it takes

```text
G = PSL(2,k),
H = Z_s^m semidirect Z_((k-1)/10),
Omega = G/H,  |Omega| = 5(k+1) = 10p.
```

Lemma 3.1 supplies a cyclic semiregular subgroup `S` of prime order `p` with
exactly ten orbits.  Lemma 3.2 proves that, for each basic orbital graph
`Y(i)`, the quotient on those ten orbits is `K_10` and every pair of quotient
orbits has at least two connecting edge matchings.  The proof obtains the
multiplicity bound from finite-field equations such as

```text
a^2 + c*y^10 = 1
```

and Proposition 2.2's solution-count estimate.  Theorem 1.1 then observes that
every connected graph in the promised action contains one of the `Y(i)` and
therefore contains a Hamilton cycle.

This is also the answer to the certificate-producing-algorithm question.  It
is not a hidden hard search regime: form the ten semiregular orbits, use the
fixed Hamilton cycle of the complete quotient, choose connecting matchings,
and change one matching if the first lift splits.  Lemma 2.1 certifies that the
changed lift is Hamiltonian.  The paper contains no NP-hardness theorem,
average-case hardness result, or hard distribution for finding these cycles.

## Exact lower bound and output-cap failure

The hypotheses require an odd prime power `k` with `10 | (k-1)` and
`p=(k+1)/2` prime.  Direct enumeration of the admissible prime powers begins

| `k` | `p=(k+1)/2` | graph order `10p` |
|---:|---:|---:|
| 61 | 31 | **310** |
| 81 | 41 | 410 |
| 121 | 61 | 610 |
| 361 | 181 | 1810 |

This agrees with Lemma 3.2's proof, which says the only case below 72 is
`k=61` and handles it by Magma.  Consequently, even the smallest full
Hamilton-cycle answer contains 310 vertex identifiers.  It exceeds the
256-atomic-element cap before any hardness scaling begins.  Increasing the
paper's parameter only lengthens the answer, so this route is `cap_bound`, not
a shippable ladder.

## Mechanical cost versus compact route

There are two honest representations, and neither gives Track B.

### Expanded native graph

For `Y(i)` at `k=61`, Lemma 3.1 gives degree 61 on 310 vertices, hence

```text
|E(Y(i))| = 310 * 61 / 2 = 9,455.
```

The paper-backed algorithm first assigns the 310 vertices to the ten
`S`-orbits and scans connecting edges to obtain their matchings.  Thus even a
straight adjacency-list implementation needs up to **9,455 edge inspections
plus 310 orbit placements** before performing the lift.  That is polynomial
and tiny for software, but the compact route available after recognizing the
semiregular action still needs the same extraction from this representation.
It is far above the 300-operation no-tool cap.  The gap is not between a
mechanical method and an insight; it is between a machine scan and asking a
person to scan the same data.

### Quotient/voltage representation

If the instance supplies the extracted quotient matchings, take the fixed
quotient cycle `0,1,...,9,0`, select one shift on each of its ten edges, and
add the ten shifts modulo `p`.  If the sum is zero, replace one selected shift
by the second, distinct shift on that quotient edge.  The total changes by a
nonzero amount; because `p` is prime, the lift is a single Hamilton cycle.

Counting ten table reads, ten modular additions, one zero test, and at most one
replacement gives **at most 22 primitive exact operations**.  The compact
route is the identical at-most-22 operations: recognizing the lifting lemma
does not remove any remaining work.  A standard-library Python microbenchmark
of this ten-edge procedure at `p=31` ran 1,000,000 repetitions in **0.420
seconds**, or about **0.420 microseconds per certificate** on this machine.
The wall-clock number is machine-dependent; the portable evidence is the
22-versus-22 operation count and ratio 1.

So the two numbers required for Track-B triage are:

| representation | mechanical certificate algorithm | compact route after insight |
|---|---:|---:|
| expanded native graph, minimum case | at most 9,455 edge inspections + 310 orbit placements | the same extraction, then <=22 lift operations |
| supplied ten-orbit quotient data | <=22 exact operations | <=22 exact operations |

The first violates G9(c); the second has no meaningful compression gap.

## Other candidate witnesses audited

| candidate task | G | H | V / other gate | outcome |
|---|---:|---:|---:|---|
| Return all `10p` vertices of a Hamilton cycle in the promised orbital graph | Theorem guarantees existence, but its counting proof does not print the concrete connecting edges; extracting them is the solver | Track A unsupported; proof gives a polynomial structural method | Exact edge and uniqueness checks pass; 310 atoms minimum | Reject / cap-bound route |
| Return a ten-edge semiregular-lift certificate | Can be inverse-built for a cyclic cover or extracted from a promised graph | **Fails A and B:** the exposed quotient is `K_10`, and the lift is obtained in <=22 operations | Exact expansion and edge checks pass | Reject |
| Output solutions of the Section 3 diagonal equations | Inverse generation would change the coefficient distribution; theorem-backed generation supplies existence, not concrete roots | Trying `y` and applying finite-field square-root algorithms is polynomial and is the certificate-producing search; no shorter paper-given route exists | Exact substitution passes | Reject |
| Plant a Hamilton cycle in an arbitrary random graph (prior triage) | Passes by inverse generation | No theorem in this paper supports distributional hardness; common planted distributions may be easy | Exact checking passes | Reject as a convenience analogue |
| Plant the natural cycle in a circulant/Cayley graph of order `10p` | Passes and is vertex-transitive | The connection generator directly exposes a cycle; mechanical and compact routes coincide | Exact checking passes | Reject |

The diagonal-equation option is not rejected merely because an algorithm
exists.  Its mechanical work (trial values plus modular square roots) is also
the work a solver must perform after seeing the equation's structure.  Making
the modulus large increases arithmetic labor on both sides; it does not create
the required compact route and eventually becomes a calculator test.

## Gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G -- certificate known by construction | Possible only for generic planted covers/cycles, not for a diverse native `PSL(2,k)` family without extracting the cycle | Lemma 3.2 proves multiplicities by counting solutions; it does not list the required field solutions or Hamilton cycle |
| V -- exact witness checking | **Passes in isolation** | Check a full cycle directly, or expand a ten-edge lift certificate and check all incidences modulo `p` |
| H -- Track A | **Fails** | No distributional hardness theorem; the paper's semiregular quotient proof is a polynomial certificate-producing method on the promised family |
| H -- Track B | **Fails** | With quotient data, mechanical and compact routes are 22 versus 22 operations; without it, both must process the expanded graph |
| G9(c) -- writable native answer | **Fails** | Minimum full cycle has 310 atoms, above 256; the compact alternative fails H |
| Overall | **Rejected at STEP 0** | No paper-supported representation makes G, H, V, and the no-tool caps hold simultaneously |

No oracle run can repair the absence of a qualifying hardness regime, and no
generic planted-cycle implementation was written merely to manufacture passing
local gates.
