# Rejected: no G–H–V family from arXiv:2510.00228

The paper was read in full. The natural certificate problems clear G and V, but
fail **H on Track A**, and the required Track B compression gap is absent. A
harder theorem-based generalization was also built and then broken by the
domain-standard attack. The attempted generator is retained as
`rejected_gen_2510_00228.py`.

## Step-0 findings

Definition 2.2 says that a radio-graceful labeling of an `N`-vertex graph is a
bijection to `1,...,N` satisfying

```text
|f(u)-f(v)| + d(u,v) >= diam(G)+1
```

for every distinct pair. Theorem 2.4 gives the decisive diameter-two
characterization: such a labeling is exactly an ordering whose consecutive
vertices form a Hamiltonian path in the antipodal graph, which is the graph
complement when the diameter is two.

The paper then exposes what makes its named infinite families easy:

- Theorems 2.5–2.6, Proposition 3.4, and Porism 3.22 use high minimum degree to
  certify Hamiltonian paths.
- Theorem 3.1 makes every even-diameter bipartite example an immediate negative;
  its antipodal graph is disconnected, so a component partition/BFS certifies
  the obstruction in linear time.
- Most decisively, Constructions 3.33 and 3.34 write down the graceful labeling
  of the Singer/polarity graphs by an alternating modular recurrence. Thus the
  paper itself supplies the certificate-producing algorithm.

## Why the explicit paper family fails both tracks

At the largest prime order whose full labeling fits the 256-atom answer cap,
`q=13` and `N=q^2+q+1=183`. Construction 3.34 starts at `v1=d1/2 (mod N)` and
alternates

```text
v_i = d0 - v_(i-1)  (i even)
v_i = d1 - v_(i-1)  (i odd).
```

The condition is `gcd(d0-d1,N)=1`. The measured mechanical cost is exactly 182
modular recurrence updates plus writing 183 vertices (805 JSON characters in
the audit); 200,000 complete runs took 2.822276 seconds, or 0.0000141 seconds
per labeling. This is an `O(N)` direct algorithm, so Track A is false.

Track B does not rescue it. After recognizing the recurrence, the compact route
still performs the same 182 updates and writes the same 183 entries. Mechanical
cost and compact-route length are therefore comparable (182 versus 182), not a
million-operation method compressed to a dozen insightful steps.

Compressing the answer to the recurrence constants also fails G4 rather than
fixing H. By the Singer difference-set definition in Section 3.3, the ordered
differences of distinct elements of `D` are every nonzero residue exactly once.
For `N=183=3*61`, 120 of the 182 ordered pairs have coprime difference, so a
structure-aware random pair succeeds with probability
`120/182 = 0.6593406593`, enormously above `1e-6`.

## Failed Track-A generalization

Theorem 3.26 says that the complement of any low-degree traceable graph is radio
graceful. To test whether that broad theorem could yield a harder native family,
the retained module inverse-generated a planar cubic antipodal graph around a
known Hamiltonian cycle, randomly divided its matching edges between two
noncrossing pages, and carried the labeling through a random vertex relabeling.
This clears G and V without solving the final graph.

An initial even/odd page assignment was rejected before the final audit because
the planted cycle parity was an exact `-1` adjacency eigenvector. Random page
membership removed that leak, and the cheap degree, greedy, random-restart,
spectral-seriation, bounded DFS, and perfect-matching-enumeration probes all
failed on the eight `n=240` audit seeds.

The required stronger attack nevertheless breaks the distribution. A binary
cycle-cover MILP (degree two at every vertex) with iterative subtour cuts,
solved by HiGHS, returned an exactly verified Hamiltonian cycle on 7 of 8 seeds:

| seed | solved | seconds | MILP rounds | subtour cuts |
|---:|:---:|---:|---:|---:|
| 9100 | yes | 11.108759 | 18 | 111 |
| 9101 | yes | 15.610094 | 23 | 112 |
| 9102 | yes | 1.264518 | 8 | 57 |
| 9103 | yes | 0.612444 | 9 | 53 |
| 9104 | no (20 s cap) | 20.002786 | 20 | 110 |
| 9105 | yes | 4.678584 | 14 | 76 |
| 9106 | yes | 1.361113 | 6 | 39 |
| 9107 | yes | 5.224006 | 15 | 90 |

Total: 59.862305 seconds, 113 MILP rounds, and 648 cuts. Track A requires every
reported attack to have zero successes; `7/8` is disqualifying. Worst-case
NP-completeness of planar cubic Hamiltonicity does not establish hardness for
this planted distribution. This construction also has no short instance-visible
route, so re-labelling the successful MILP as a Track B reference algorithm
would be dishonest.

## Decision

**H fails on Track A. Track B also fails because the explicit construction's
mechanical and compact routes are the same length, while the attempted harder
distribution has no compact route at all.** G and V were not the obstacle.
This is not `cap_bound`: the named construction remains directly linear-time at
every size, and the cap-compliant `q=13` instance already exposes the lack of a
compression gap.

Paper: [Radio gracefulness of Moore graphs and beyond](https://arxiv.org/abs/2510.00228),
especially Definition 2.2, Theorems 2.4, 3.1, and 3.26, and Constructions
3.33–3.34.
