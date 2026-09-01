# Rejected: planar door-gadget reachability

Paper: MIT Gadgets Group, Jeffrey Bosboom, Erik D. Demaine, Jenny
Diomidova, Della Hendrickson, Hayashi Layers, and Jayson Lynch,
[*Walking through Doors is Hard, even without Staircases: Universality and
PSPACE-hardness of Planar Door Gadgets*](https://arxiv.org/abs/2006.01256),
arXiv:2006.01256v2.

## Decision

This paper does not supply a family meeting the task's witness contract. The
natural proposed witness, a route through a planar system of doors, has no
polynomial length bound and is therefore an unbounded-length object, one of the
task's explicit disqualifiers. If route length is capped to make the witness
polynomially bounded, the paper's PSPACE-hardness theorem no longer applies,
so **H (hardness) becomes unsupported**. Per Step 0, I did not manufacture a
generator, self-test report, or oracle-loop transcript after establishing this
failure.

## Exact problem checked

Section 1.1 defines a gadget by finite sets of states and locations and a set
of transitions `(state, entrance) -> (new_state, exit)`. A system contains
multiple gadgets, an initial state for each, and a connection graph joining
gadget locations. The agent may move freely within a connected component of
that graph and may traverse a gadget only when its current local state permits
the transition. A system traversal is a finite sequence of such local
traversals whose consecutive endpoints are connected. Planarity additionally
requires the wheel-graph expansion of the gadgets and connections to be
planar, respecting each gadget's cyclic order up to rotation and reflection.

Sections 1.2, 2.1, and 3 define the relevant two-state doors:

- A self-closing door has an opening tunnel/button and a tunnel that is usable
  only while open and closes itself when traversed.
- A symmetric self-closing door has two tunnels, exactly one open at a time;
  traversing either swaps which one is open.
- An open--close door has opening, closing, and traverse tunnels (the opening
  action may instead be a button). Opening and closing set the state, while the
  traverse tunnel is usable exactly when open. Tunnels may be directed or
  undirected, with the variations specified in the paper.

For all these types, the search task suggested by prior triage would hand the
solver a planar system, start location, target location, and initial door
states, and ask for the traversal sequence reaching the target.

## Hard regime and the witness-length obstruction

Theorem 2.7 proves every self-closing and symmetric self-closing door variant
planarly universal; Corollary 2.8 concludes that planar reachability with any
such door is PSPACE-complete. Theorem 3.7 and Corollary 3.8 prove the analogous
statements for every open--close door variation. This is the correct hard
regime: one player, unbounded reachability, planar wiring, and arbitrarily many
two-state doors.

A proposed route is easy to replay exactly: maintain the agent's component and
one bit per door, reject a traversal whose entrance is unreachable or whose
door state forbids it, apply the state change, and finally compare the location
with the target. But replay time and witness size are linear in the route
length, and neither definition nor theorem bounds that length polynomially in
the system description.

With `d` two-state doors, the global configuration graph already has up to an
exponential number of state assignments (`2^d`, multiplied by the agent's
location component). PSPACE membership in Corollary 2.8 is invoked as general
1-player reachability, not by exhibiting a polynomial certificate. Indeed, a
polynomial bound on a route for every reachable instance would put this
PSPACE-complete language in NP and imply `NP = PSPACE`. Thus the source of the
paper's hardness is precisely the potentially exponentially long stateful
walk, not a polynomially sized witness of the kind required here.

Inverse generation does not fix the mismatch. Sampling a short route first
and building a maze around it would satisfy generation and replay, but it
restricts the distribution to instances with short certificates. The paper
does not prove that this bounded-route subproblem is hard, and a planted route
can leave exactly the positional, degree, or greedy signatures targeted by G6.
Conversely, retaining the unbounded PSPACE-complete problem violates the
bounded-witness requirement.

## Why other paper-native choices do not rescue the family

| Candidate witness task | Failure |
|---|---|
| Find a route in a door system | The route is not polynomially bounded; this is an explicitly disallowed unbounded-length witness. |
| Find a route of at most a stated polynomial bound | Verification and inverse planting become possible, but Corollaries 2.8/3.8 do not establish hardness for this changed problem. |
| Construct a door simulation of a supplied finite gadget | Theorem 2.4 gives a direct general construction for self-closing doors, and Theorems 2.7/3.7 finish the planar construction via explicit fixed simulations, so this is not a hard search family. Checking full behavioral equivalence would also require quantified reachability, not cheap sequence replay. |
| Rediscover the Case-8 `OTtocC` simulation | Section 3.4.9 gives one fixed 10-door solution and a 29-step traversal, not an unlimited scalable family; testing that no unintended behavior exists requires configuration-space search. |
| Use Sokobond or the Mario applications in Section 4 | These are reductions of the same unbounded reachability problem and retain the route-length issue. Several game models also rely on informal continuous mechanics, so exact standard-library verification would not be faithful to the paper. |
| Answer whether no route exists | This is an absence claim, expressly forbidden by the task. |

## Easy-regime audit

The full v2 text contains no FPT result, approximation scheme, or
polynomial-time algorithm for a nontrivial restricted reachability regime that
could be used to tune parameters. Its constructive results instead concern
universality: Theorem 2.4 directly simulates an arbitrary finite gadget, and
Sections 2.4 and 3 build fixed planar crossover/self-closing simulations. Those
constructions make simulation search easy; they do not provide polynomially
bounded routes for hard reachability instances.

## Gate outcome

| Requirement | Result |
|---|---|
| G -- inverse generation | Possible only by planting a chosen finite route, but no hard planted distribution is justified by the paper. |
| H -- no known polynomial/closed-form solution | Passes for the paper's **unbounded** reachability problem; unsupported after imposing the witness bound required by the task. |
| V -- cheap exact witness | A finite route can be replayed, but its length is unbounded/exponential in the instance size, so it fails the task's witness contract. |

The rejection occurs before Steps 1--4. Running the LLM hardening loop cannot
repair a mismatch between the theorem's unbounded problem and the required
bounded witness family.
