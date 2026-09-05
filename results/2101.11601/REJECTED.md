# Rejected at Step 0: no hard generated distribution in arXiv:2101.11601

Paper: Oliver Janzer, Benny Sudakov, and István Tomon,
[*Long directed paths in Eulerian digraphs*](https://arxiv.org/abs/2101.11601)
(2021).

## Decision

No generator is shipped. A directed path is an excellent finite witness, and
the prior-triage proposal can satisfy **G** by planting a path and **V** by
checking distinct vertices and consecutive arcs. It does not satisfy **H on
either track**.

- **Track A fails.** The paper proves an extremal existence theorem, not a
  computational or distributional hardness result. It gives no hard planted
  distribution or parameter regime. Moreover, the natural construction in
  which the planted path is statistically indistinguishable from decoy cycles
  was solved on 20/20 maximum-answer-size instances by the domain-standard
  cycle-cover relaxation and repair attack described below.
- **Track B fails.** The retained planted cycle is private generator state, not
  a solver-visible invariant. The shortest public route found is the same
  matching-and-repair computation as the mechanical route. If cycle-layer
  labels are exposed to make the planted route public, following one labeled
  layer is itself the obvious by-hand attack; mechanical and compact routes
  both become the same 255 successor steps.

This is an H failure, not a witness-rule failure and not `cap_bound`. Step 0
therefore stops the build before a module, self-test report, README, or oracle
transcripts are created.

## What the paper actually proves

Section 1 fixes the native objects precisely. A digraph is simple and loopless,
although both opposite arcs `uv` and `vu` may occur. It is Eulerian when every
vertex has equal indegree and outdegree. “Connected” means that the underlying
undirected graph is connected; for an Eulerian digraph this is equivalent to
strong connectivity.

Theorem 1.2 says that there is an absolute constant `c > 0` such that every
connected Eulerian digraph of average degree at least `d` has, from every
specified start vertex, a simple directed path of length at least

```text
c * d^(1/2 + 1/40) = c * d^(21/40).
```

The result is asymptotic: Section 3 assumes that `c` is sufficiently small, and
several proofs assume that `d` is sufficiently large. No numerical value of
`c` or finite threshold for `d` is extracted. Thus Theorem 1.2 alone cannot be
turned into an exact finite benchmark threshold by substituting displayed
constants.

The paper also identifies regimes in which the existence argument simplifies:

- Lemma 3.3 turns any sufficiently long directed cycle into a long path from
  the specified vertex by first taking a path into the cycle.
- Lemma 3.6 says that when `Delta(G) <= d^20`, an Eulerian digraph has a cycle
  of length at least `d^(2/3)/(400 log d)` for sufficiently large `d`.
- The proof of Theorem 1.2 reduces to a minimal `d`-full Eulerian subgraph,
  repeatedly uses cycle decompositions and connected components, and inducts
  on `floor(d)`.

These are existence and extremal statements. The paper contains no NP-hardness
theorem, average-case theorem, planted-distribution analysis, FPT lower bound,
or algorithmic running-time claim for finding the promised path.

## Step-0 certificate question

For an arbitrary graph satisfying Theorem 1.2, the paper does not hand the
generator a path certificate at construction time. The proof of Lemma 3.1
chooses a random path and proves that a required property holds with positive
probability by a union bound. Lemma 3.6 similarly invokes the Lovász Local
Lemma for a random vertex partition. The main proof then uses contradiction and
induction, with the constant `c` left implicit. Repeatedly sampling choices or
running a longest-path search until a suitable certificate appears would be
solving the generated instance, which G forbids.

Inverse generation repairs G: choose a Hamilton cycle first, retain its order,
and add balanced decoy arcs. It does not repair H. The certificate-producing
algorithm in that route is simply the private cycle sampler, requiring 256 arc
insertions and 255 path transitions at the tested size. Those private random
choices are absent from the public instance.

## Audit of the prior-triage planted family

I tested a strong, native version of the proposed construction:

1. Independently sample four uniformly shuffled Hamilton cycles on 256
   vertices, rejecting a new cycle if it shares an arc with an earlier one.
2. Take the uncolored union of their arcs and designate the first cycle only in
   private generator state.
3. Specify the first vertex of that cycle as the required start and ask for a
   directed Hamilton path, i.e. a path of length 255.

The union is a simple connected Eulerian digraph with exactly 1,024 arcs and
indegree = outdegree = 4 at every vertex. All four layers come from the same
distribution, so degree, position, magnitude, and per-vertex statistics do not
distinguish the retained layer. A 256-vertex answer is the largest explicit
path allowed by the task's atomic-answer cap.

The attack uses the standard cycle-cover relaxation. Split every vertex into a
tail copy and a head copy and find a perfect matching in this bipartite graph.
Each perfect matching is a directed cycle cover. Randomize the augmenting-path
matching choices, and retry until the cover has one cycle; traversing that cycle
from the specified start is then a verifier-accepted Hamilton path.

At `n = 256`, degree 4, over seeds 10000 through 10019, the attack produced a
valid witness on **20/20** instances:

| measurement | result |
|---|---:|
| successful instances | 20 / 20 |
| median / maximum matching trials | 78 / 285 |
| median / maximum arc probes | 111,401 / 402,388 |
| total wall clock | 11.255804 s |
| median / maximum wall clock | 0.310618 s / 2.891997 s |

The implementation used randomized Kuhn augmenting paths, `O(VE)` per matching
trial; a Hopcroft–Karp implementation would improve the per-trial worst-case
bound to `O(E sqrt(V))`. Timings are machine-dependent, while the success count,
trial counts, and explicitly counted arc probes are the portable evidence. This
is exactly the “classical polynomial relaxation, then repair” attack required
for a path problem, and it breaks the generated distribution rather than merely
citing worst-case complexity.

## Mechanical cost versus compact route

At the would-be shipping point, the successful public mechanical route costs a
median **111,401 adjacency probes**, 78 matching trials, and 0.310618 seconds,
followed by emitting 256 vertices. The only 255-step route is to replay the
generator's retained cycle, but the public graph contains neither layer colors
nor the generator's random permutation history. Private state is not a
solver-visible structural insight, so it cannot establish Track B.

The shortest public “compact” route found is therefore the same cycle-cover
matching and repair algorithm: **111,401 probes versus 111,401 probes** at the
median measured instance, a 1:1 ratio. Exposing a cycle decomposition does not
create a compression problem: it changes both costs to the identical 255 edge
follows and makes the fourth in-context attack succeed immediately. The paper's
inductive proof supplies no separate invariant or change of variables that
recovers the particular retained cycle from the uncolored union.

Increasing `n` is unavailable for this explicit Hamilton-path formulation
because 256 vertices already saturate the answer-atom cap. Raising the degree
or adding further uncolored cycles is not a paper-backed hardness regime and
does not cure the absence of a public compact route. It would amount to tuning
a new planted distribution against this particular attack.

## Other native formulations considered

| candidate task | G | H | V | outcome |
|---|---:|---:|---:|---|
| Find the path promised by Theorem 1.2 in an arbitrary qualifying graph | **Fails as a generator route:** the proof gives existence with implicit constants and probabilistic choices, not a held path | No computational hardness regime is stated | A submitted path is exact | Reject |
| Plant a Hamilton cycle and add balanced decoy cycles | Pass by inverse generation and composition of cycles | **Track A fails:** 20/20 cycle-cover attack; **Track B fails:** retained layer is private | Pass | Reject |
| Include the cycle decomposition used by the proof | Pass | **Fails both tracks:** following a displayed cycle is the direct algorithm and obvious in-context attack | Pass | Reject |
| Ask for a longest path rather than one above a threshold | A planted path proves feasibility but not optimality | An optimum needs an upper-bound certificate absent from the paper | Path alone cannot certify optimality | Reject |
| Ask for a long cycle using Lemma 3.6 | Inverse planting is possible | The paper presents this as the simplifying bounded-maximum-degree regime; no hard distribution is given | Pass for a concrete cycle | Reject |

## Gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G — certificate known without solving | Passes only after inverse planting | Retain one sampled Hamilton cycle; arbitrary theorem-hypothesis sampling does not retain a witness |
| H — Track A structural hardness | **Fail** | No theorem for the generated distribution, and the natural same-distribution plant is solved 20/20 by cycle-cover matching and repair |
| H — Track B no-tool compression | **Fail** | Public mechanical and public compact routes are the same 111,401-probe median computation; the 255-step planted route is secret |
| V — exact witness checking | Pass | Check start, exact length, range, distinctness, and every consecutive directed arc |
| Overall | **Rejected at Step 0** | No paper-supported native family makes G, H, and V hold simultaneously |

No oracle failure or large raw answer space can override the successful native
attack or turn the generator's hidden random choices into a solver-visible
insight.
