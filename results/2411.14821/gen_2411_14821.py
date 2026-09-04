"""Generator for a supported weakly-stable matching witness.

The generated instances are the regular Exact-3-Cover kernels used by the
complete, dichotomous matching construction in Section 3 of arXiv:2411.14821.
A returned list of set-gadget indices is a compact encoding of a full stable
matching; :func:`verify` expands that encoding and checks the matching.

Only the Python standard library is used.  Importing this module has no side
effects.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    "demo": {"n": 8, "degree": 6},
    "easy": {"n": 16, "degree": 6},
    "medium": {"n": 32, "degree": 6},
    "hard": {"n": 64, "degree": 6},
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Paper basis.  Section 2 (Definitions 2.1 and 2.2 in the typeset paper) fixes
weak stability and ex-post stability.  Section 3.1, especially Theorems 3.1
and 3.2, proves NP-completeness for complete preferences when at least one side
has dichotomous ties.  The theorem immediately following Theorem 3.2 observes
that even finding one weakly stable deterministic matching consistent with the
support of the supplied random matching is NP-complete.  Its proof fixes the
two special edges and extracts an Exact-3-Cover from every supported stable
matching.  This module uses that search problem and returns the cover selector,
which compactly determines the full matching checked by verify().

Easy regimes avoided.  Proposition 2.1 makes ex-post stability linear-time
when both sides are strict.  Section 4.2 gives an integer-programming method,
not a polynomial-time algorithm, for weak ex-post stability.  Theorems 4.2 and
4.3 make robust ex-post stability and ex-post strong stability polynomial-time;
neither stronger notion is generated here.  The paper gives no FPT algorithm
for the weak supported-matching search problem and lists parameterized
algorithms as future work, so n is allowed to grow.

Inverse generation and attacks.  The planted exact cover is sampled first as a
uniform random partition of the elements.  Every decoy layer is sampled by the
same partition procedure; layers and set indices are then hidden by a uniform
shuffle.  Thus planted and decoy triples have the same marginal distribution,
all triples have size three, and every element has the same frequency.  The
outlier attack uses local overlap/frequency signatures, the greedy attack uses
the most-constrained uncovered element, and the random-restart attack repeats
that greedy rule with random tie breaking.  The shipped scale is chosen only
after these attacks and the mandated multi-vendor hardening loop.
""".strip()


def _random_partition(element_count: int, rng: random.Random) -> list[tuple[int, int, int]]:
    order = list(range(element_count))
    rng.shuffle(order)
    return [tuple(sorted(order[i : i + 3])) for i in range(0, element_count, 3)]


def _connected(element_count: int, triples: list[tuple[int, int, int]]) -> bool:
    """Connectivity of the element co-occurrence graph."""
    adj = [[] for _ in range(element_count)]
    for a, b, c in triples:
        adj[a].extend((b, c))
        adj[b].extend((a, c))
        adj[c].extend((a, b))
    seen = {0}
    stack = [0]
    while stack:
        v = stack.pop()
        for u in adj[v]:
            if u not in seen:
                seen.add(u)
                stack.append(u)
    return len(seen) == element_count


def make_instance(n: int, seed: int = 0, degree: int = 6, **params: Any) -> dict:
    """Sample a cover first, then conceal it among identically drawn layers.

    ``n`` is the number of triples in an answer, so there are ``3*n`` ground
    elements.  ``degree`` is both the number of independent partition layers
    and the number of triples containing each element.  Larger ``n`` enlarges
    the exact-cover search; degree is held in the sparse-but-crowded regime.
    """
    if params:
        raise TypeError(f"unknown parameters: {', '.join(sorted(params))}")
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 3:
        raise ValueError("degree must be an integer at least 3")

    rng = random.Random(seed)
    element_count = 3 * n

    # Reject the whole exchangeable draw, rather than only a later layer, so
    # the planted layer and all decoy layers remain identically distributed.
    for _ in range(10_000):
        layers = [_random_partition(element_count, rng) for _ in range(degree)]
        flat = [triple for layer in layers for triple in layer]
        if len(set(flat)) != len(flat):
            continue
        if not _connected(element_count, flat):
            continue
        break
    else:
        raise RuntimeError("could not draw distinct connected partition layers")

    labelled = [(triple, layer) for layer, part in enumerate(layers) for triple in part]
    rng.shuffle(labelled)
    triples = [triple for triple, _ in labelled]
    planted = sorted(i for i, (_, layer) in enumerate(labelled) if layer == 0)

    return {
        "n": n,
        "degree": degree,
        "element_count": element_count,
        "sets": [list(t) for t in triples],
        "answer": planted,
    }


def render(inst: dict) -> str:
    n = int(inst["n"])
    degree = int(inst["degree"])
    element_count = int(inst["element_count"])
    triples = inst["sets"]
    lines = "\n".join(
        f"  {j}: {triple[0]} {triple[1]} {triple[2]}" for j, triple in enumerate(triples)
    )
    example = ", ".join(str(i) for i in range(n))
    return f"""SUPPORTED WEAKLY-STABLE MATCHING — COMPACT SELECTOR WITNESS

There are {element_count} ground elements, numbered 0 through {element_count - 1},
and {len(triples)} set gadgets, numbered 0 through {len(triples) - 1}.  Each set
gadget contains exactly three distinct ground elements; every ground element
occurs in exactly {degree} gadgets.  The gadget data are:

{lines}

This is a compact presentation of the following two-sided matching instance.
For each gadget j and port l in {{0,1,2}}, with T[j,l] the l-th displayed
element, there are agents c(j,l), d(j,l) and items x(j,l), y(j,l).  There is an
item a(e) and collector agent z(e) for every ground element e, plus agents s1,
s2 and items o1,o2.  Port arithmetic is modulo 3.

The positive entries of the supplied random matching p are exactly these
supported pairs (unlisted pairs have probability zero):

  p(c(j,l),a(T[j,l])) = 1/{degree}
  p(c(j,l),x(j,l))    = 1/{degree}
  p(c(j,l),y(j,l))    = {degree - 2}/{degree}
  p(d(j,l),x(j,l))    = {degree - 2}/{degree}
  p(d(j,l),y(j,l))    = 2/{degree}
  p(z(e),x(j,l))      = 1/{degree * element_count}  for every e,j,l
  p(s1,o1) = p(s2,o2) = 1.

These entries are nonnegative and every row and column sums to 1.  Preferences
and priorities are complete and dichotomous: every brace below is one tied top
tier, all unlisted partners form one tied bottom tier, and top is strictly
preferred to bottom.

  c(j,l) top: {{a(T[j,l]), y(j,l), x(j,l-1)}}
  s1 top: {{o2}} together with every y(j,l)
  d(j,l), z(e), and s2: indifferent among all items
  a(e) top: every c(j,l) whose T[j,l]=e
  x(j,l) top: {{c(j,l), c(j,l+1)}}
  y(j,l) top: {{d(j,l), s1}}
  o1 and o2: indifferent among all agents.

A deterministic matching is supported when every one of its pairs has positive
probability above.  It is weakly stable when there is no unmatched agent-item
pair for which BOTH sides strictly prefer each other to their assigned partners.

Your witness is the compact selector for a supported weakly stable matching.
Select exactly {n} distinct gadget indices whose triples cover every ground
element exactly once.  The checker expands them canonically: selected c ports
take their a-items; unselected c ports take their same-port x-items; every d
takes its y-item; z(e) takes the selected port's remaining x-item containing e;
and s1-o1, s2-o2 are paired.  The checker then recomputes bijectivity, support,
and weak stability.  Order of the {n} output indices does not matter; indices
are 0-based and repeats are forbidden.

Give your final answer inside <answer></answer> tags, as exactly {n}
comma-separated base-10 gadget indices with no brackets.
Example (format only): <answer>{example}</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL)


def parse_answer(text: str) -> object | None:
    """Parse the last tagged comma-separated integer list in solver output."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```"):
        rows = body.splitlines()
        if rows and rows[0].strip().startswith("```"):
            rows = rows[1:]
        if rows and rows[-1].strip() == "```":
            rows = rows[:-1]
        body = "\n".join(rows).strip()
    if len(body) >= 2 and body[0] == "[" and body[-1] == "]":
        body = body[1:-1].strip()
    if not body or re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body) is None:
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError, OverflowError):
        return None


def _layout(inst: dict) -> tuple[int, int, int, int]:
    element_count = int(inst["element_count"])
    set_count = len(inst["sets"])
    port_count = 3 * set_count
    side_count = 2 * port_count + element_count + 2
    return element_count, set_count, port_count, side_count


def _expanded_matching(inst: dict, selected: set[int]) -> list[int]:
    """Return item_of_agent using the integer layout documented in verify."""
    element_count, set_count, port_count, side_count = _layout(inst)
    triples = inst["sets"]

    # Agent IDs: c ports, d ports, z elements, s1, s2.
    # Item IDs:  a elements, x ports, y ports, o1, o2.
    item_of_agent = [-1] * side_count
    selected_port_for_element = [-1] * element_count
    for j, triple in enumerate(triples):
        for l, element in enumerate(triple):
            port = 3 * j + l
            if j in selected:
                item_of_agent[port] = element  # c(j,l)-a(element)
                selected_port_for_element[element] = port
            else:
                item_of_agent[port] = element_count + port  # c(j,l)-x(j,l)
            item_of_agent[port_count + port] = element_count + port_count + port

    for element, port in enumerate(selected_port_for_element):
        item_of_agent[2 * port_count + element] = element_count + port

    item_of_agent[-2] = element_count + 2 * port_count
    item_of_agent[-1] = element_count + 2 * port_count + 1
    return item_of_agent


def _supported(inst: dict, agent: int, item: int) -> bool:
    element_count, set_count, port_count, side_count = _layout(inst)
    if not (0 <= agent < side_count and 0 <= item < side_count):
        return False
    triples = inst["sets"]
    if agent < port_count:  # c(j,l)
        port = agent
        j, l = divmod(port, 3)
        return item in (
            triples[j][l],
            element_count + port,
            element_count + port_count + port,
        )
    if agent < 2 * port_count:  # d(j,l)
        port = agent - port_count
        return item in (
            element_count + port,
            element_count + port_count + port,
        )
    if agent < 2 * port_count + element_count:  # collector z(e)
        return element_count <= item < element_count + port_count
    if agent == side_count - 2:
        return item == side_count - 2
    return item == side_count - 1


def _agent_top(inst: dict, agent: int, item: int) -> bool:
    element_count, set_count, port_count, side_count = _layout(inst)
    triples = inst["sets"]
    if agent < port_count:
        port = agent
        j, l = divmod(port, 3)
        previous_port = 3 * j + (l - 1) % 3
        return item in (
            triples[j][l],
            element_count + port_count + port,
            element_count + previous_port,
        )
    if agent < 2 * port_count + element_count or agent == side_count - 1:
        return True  # d, z, and s2 have one indifference tier
    # s1
    return item == side_count - 1 or (
        element_count + port_count <= item < element_count + 2 * port_count
    )


def _item_top_agents(inst: dict, item: int) -> tuple[int, ...]:
    element_count, set_count, port_count, side_count = _layout(inst)
    triples = inst["sets"]
    if item < element_count:
        element = item
        return tuple(
            3 * j + l
            for j, triple in enumerate(triples)
            for l, value in enumerate(triple)
            if value == element
        )
    if item < element_count + port_count:
        port = item - element_count
        j, l = divmod(port, 3)
        return (port, 3 * j + (l + 1) % 3)
    if item < element_count + 2 * port_count:
        port = item - element_count - port_count
        return (port_count + port, side_count - 2)
    return tuple(range(side_count))  # o1 and o2: one indifference tier


def _check_expanded(inst: dict, selected: set[int]) -> tuple[bool, str]:
    item_of_agent = _expanded_matching(inst, selected)
    side_count = len(item_of_agent)
    if any(item < 0 for item in item_of_agent):
        return False, "expanded matching leaves an agent unmatched"
    if len(set(item_of_agent)) != side_count or set(item_of_agent) != set(range(side_count)):
        return False, "expanded matching is not bijective"
    for agent, item in enumerate(item_of_agent):
        if not _supported(inst, agent, item):
            return False, f"expanded pair ({agent},{item}) is outside the random-matching support"

    owner = [-1] * side_count
    for agent, item in enumerate(item_of_agent):
        owner[item] = agent

    # An item can strictly prefer only one of its top-tier agents while assigned
    # to its bottom tier, so testing these small lists is the exact blocking-pair
    # test for dichotomous preferences.
    for item in range(side_count):
        top_agents = _item_top_agents(inst, item)
        if owner[item] in top_agents:
            continue
        for agent in top_agents:
            current = item_of_agent[agent]
            if _agent_top(inst, agent, item) and not _agent_top(inst, agent, current):
                return False, f"expanded matching is blocked by agent {agent} and item {item}"
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid selector; the planted answer is never consulted."""
    if not isinstance(answer, list):
        return False, "answer must be a list of integer gadget indices"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every gadget index must be an integer"

    n = int(inst["n"])
    triples = inst["sets"]
    if len(answer) != n:
        return False, f"expected exactly {n} gadget indices"
    if len(set(answer)) != len(answer):
        return False, "gadget indices must be distinct"
    if any(x < 0 or x >= len(triples) for x in answer):
        return False, f"gadget index outside inclusive range 0..{len(triples) - 1}"

    counts = [0] * int(inst["element_count"])
    for j in answer:
        for element in triples[j]:
            counts[element] += 1
    overlaps = [e for e, count in enumerate(counts) if count > 1]
    if overlaps:
        return False, f"selected triples overlap at element {overlaps[0]}"
    missing = [e for e, count in enumerate(counts) if count == 0]
    if missing:
        return False, f"selected triples do not cover element {missing[0]}"

    return _check_expanded(inst, set(answer))


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample the solver-visible shape: n distinct, in-range set indices."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return sorted(rng.sample(range(len(inst["sets"])), int(inst["n"])))


def search_space(inst: dict) -> int | None:
    return math.comb(len(inst["sets"]), int(inst["n"]))


def enumerate_all(inst: dict) -> int | None:
    """Count exact covers by bounded exhaustive branching, or return None."""
    n = int(inst["n"])
    if n > 10:
        return None
    element_count = int(inst["element_count"])
    masks = [sum(1 << e for e in triple) for triple in inst["sets"]]
    incident = [[] for _ in range(element_count)]
    for j, triple in enumerate(inst["sets"]):
        for e in triple:
            incident[e].append(j)

    node_cap = 1_000_000
    nodes = 0

    def visit(remaining: int) -> int:
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            raise OverflowError
        if remaining == 0:
            return 1
        best: list[int] | None = None
        pending = remaining
        while pending:
            bit = pending & -pending
            e = bit.bit_length() - 1
            candidates = [j for j in incident[e] if masks[j] & remaining == masks[j]]
            if not candidates:
                return 0
            if best is None or len(candidates) < len(best):
                best = candidates
                if len(best) == 1:
                    break
            pending ^= bit
        assert best is not None
        return sum(visit(remaining ^ masks[j]) for j in best)

    try:
        return visit((1 << element_count) - 1)
    except OverflowError:
        return None


def _incidence_graph(inst: dict) -> tuple[list[list[int]], int, int]:
    element_count = int(inst["element_count"])
    set_count = len(inst["sets"])
    adj = [[] for _ in range(element_count + set_count)]
    for j, triple in enumerate(inst["sets"]):
        node = element_count + j
        for e in triple:
            adj[e].append(node)
            adj[node].append(e)
    return adj, element_count, set_count


def _root_walk_signature(adj: list[list[int]], root: int, length: int = 12) -> tuple:
    """Relabelling-invariant local cycle and distance data for one root."""
    total = len(adj)
    current = [0] * total
    current[root] = 1
    returns = []
    for step in range(1, length + 1):
        following = [0] * total
        for v, count in enumerate(current):
            if count:
                for u in adj[v]:
                    following[u] += count
        current = following
        if step % 2 == 0:
            returns.append(current[root])

    distances = [-1] * total
    distances[root] = 0
    frontier = [root]
    while frontier:
        following_frontier = []
        for v in frontier:
            for u in adj[v]:
                if distances[u] < 0:
                    distances[u] = distances[v] + 1
                    following_frontier.append(u)
        frontier = following_frontier
    histogram = tuple(sorted(Counter(distances).items()))
    return tuple(returns), histogram


def canonical_key(inst: dict) -> str:
    """A strong cheap invariant of the bipartite incidence structure.

    Exact hypergraph canonical labelling is a graph-isomorphism problem.  The
    key therefore uses all rooted closed-walk and distance histograms (an
    inexpensive isomorphism invariant), not labels, seed, input order, or
    rendered text.
    """
    adj, element_count, set_count = _incidence_graph(inst)
    left_roots = sorted(
        _root_walk_signature(adj, root)
        for root in range(element_count)
    )
    right_roots = sorted(
        _root_walk_signature(adj, root)
        for root in range(element_count, element_count + set_count)
    )
    payload = repr((element_count, set_count, left_roots, right_roots)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the exact-cover dimension while retaining constraint density."""
    if "n" not in params:
        return None
    harder = dict(params)
    current = int(harder["n"])
    harder["n"] = max(current + 8, (3 * current + 1) // 2)
    return harder


def _transform_instance(
    inst: dict, element_permutation: list[int], set_order: list[int]
) -> dict:
    """Relabel elements and reorder sets, carrying the witness along."""
    element_count = int(inst["element_count"])
    set_count = len(inst["sets"])
    if sorted(element_permutation) != list(range(element_count)):
        raise ValueError("not an element permutation")
    if sorted(set_order) != list(range(set_count)):
        raise ValueError("not a set permutation")
    inverse_set_order = [0] * set_count
    for new, old in enumerate(set_order):
        inverse_set_order[old] = new
    triples = [
        sorted(element_permutation[e] for e in inst["sets"][old]) for old in set_order
    ]
    return {
        "n": inst["n"],
        "degree": inst["degree"],
        "element_count": element_count,
        "sets": triples,
        "answer": sorted(inverse_set_order[j] for j in inst["answer"]),
    }


def _attack_outlier(inst: dict) -> list[int]:
    """Choose extremes of per-set frequency/overlap statistics."""
    triples = [set(t) for t in inst["sets"]]
    frequencies = Counter(e for triple in triples for e in triple)
    scored = []
    for j, triple in enumerate(triples):
        intersections = [len(triple & other) for k, other in enumerate(triples) if k != j]
        score = (
            tuple(sorted(frequencies[e] for e in triple)),
            sum(value > 0 for value in intersections),
            sum(value * value for value in intersections),
        )
        scored.append((score, j))
    low = sorted(scored)[: int(inst["n"])]
    return sorted(j for _, j in low)


def _greedy_candidate(inst: dict, rng: random.Random | None = None) -> list[int] | None:
    element_count = int(inst["element_count"])
    masks = [sum(1 << e for e in triple) for triple in inst["sets"]]
    incident = [[] for _ in range(element_count)]
    for j, triple in enumerate(inst["sets"]):
        for e in triple:
            incident[e].append(j)
    remaining = (1 << element_count) - 1
    chosen: list[int] = []
    while remaining:
        choices = []
        pending = remaining
        while pending:
            bit = pending & -pending
            e = bit.bit_length() - 1
            feasible = [j for j in incident[e] if masks[j] & remaining == masks[j]]
            if not feasible:
                return None
            choices.append((len(feasible), e, feasible))
            pending ^= bit
        width = min(row[0] for row in choices)
        tied = [row for row in choices if row[0] == width]
        _, _, feasible = rng.choice(tied) if rng is not None else min(tied, key=lambda x: x[1])
        j = rng.choice(feasible) if rng is not None else min(feasible)
        chosen.append(j)
        remaining ^= masks[j]
    return sorted(chosen)


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 64) -> list[int] | None:
    for _ in range(restarts):
        answer = _greedy_candidate(inst, rng)
        if answer is not None and verify(inst, answer)[0]:
            return answer
    return None


def selftest() -> dict:
    """Run gates G1--G8 and return a JSON-serialisable measurement report."""
    report: dict[str, Any] = {}

    # G1: all named presets, several independent seeds.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=12345, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = list(shipping["answer"])
    nonselected = next(j for j in range(len(shipping["sets"])) if j not in set(planted))
    corruptions = {
        "drop_one": planted[:-1],
        "replace_one": planted[:-1] + [nonselected],
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [len(shipping["sets"])],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used exact-cover propagation.\n```text\n"
        + "<answer>\n```\n"
        + ", ".join(map(str, planted))
        + "\n```\n</answer>\n```\nThe indices are zero-based."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_count": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_rng = random.Random(0x241114821)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": total >= 200_000 and hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "hits_over_total": f"{hits}/{total}",
        "measured_probability": hits / total,
        "sampler": "uniform n-subset of in-range gadget indices",
        "naive_space": search_space(shipping),
    }

    small_params = DIFFICULTY["demo"]
    sparse_rows = []
    sparse_pass = True
    for seed in range(3):
        instance = make_instance(seed=700 + seed, **small_params)
        count = enumerate_all(instance)
        space = search_space(instance)
        fraction = None if count is None else count / space
        sparse_rows.append(
            {"seed": 700 + seed, "solutions": count, "space": space, "fraction": fraction}
        )
        if count is None or fraction is None or fraction >= 1e-5:
            sparse_pass = False
    report["G5_sparse_solutions"] = {"pass": sparse_pass, "instances": sparse_rows}

    attack_rows: dict[str, dict[str, Any]] = {
        "outlier": {"solved": 0, "seeds": 8},
        "greedy": {"solved": 0, "seeds": 8},
        "random_restart_64": {"solved": 0, "seeds": 8},
    }
    for offset in range(8):
        instance = make_instance(seed=9000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY])
        if verify(instance, _attack_outlier(instance))[0]:
            attack_rows["outlier"]["solved"] += 1
        greedy = _greedy_candidate(instance)
        if greedy is not None and verify(instance, greedy)[0]:
            attack_rows["greedy"]["solved"] += 1
        restarted = _attack_random_restart(instance, random.Random(50_000 + offset), 64)
        if restarted is not None:
            attack_rows["random_restart_64"]["solved"] += 1
    for row in attack_rows.values():
        row["failed_all"] = row["solved"] == 0
    report["G6_adversary_panel"] = {
        "pass": all(row["failed_all"] for row in attack_rows.values()),
        "attacks": attack_rows,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(shipping_params["n"])
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    base_space = search_space(shipping)
    doubled_space = search_space(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_space > base_space,
        "base_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "base_search_space": base_space,
        "doubled_search_space": doubled_space,
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    real_transform_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        instance = make_instance(n=8, degree=6, seed=80_000 + seed)
        base_key = canonical_key(instance)
        unrelated_keys.append(base_key)
        rng = random.Random(90_000 + seed)
        element_count = int(instance["element_count"])
        set_count = len(instance["sets"])
        identity_elements = list(range(element_count))
        identity_sets = list(range(set_count))
        permuted_elements = list(identity_elements)
        permuted_sets = list(identity_sets)
        rng.shuffle(permuted_elements)
        rng.shuffle(permuted_sets)
        transformations = [
            (permuted_elements, identity_sets),
            (identity_elements, permuted_sets),
            (permuted_elements, permuted_sets),
        ]
        for element_perm, set_perm in transformations:
            transformed = _transform_instance(instance, element_perm, set_perm)
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                g8_failures.append({"seed": seed, "kind": "key_changed"})
            ok, reason = verify(transformed, transformed["answer"])
            real_transform_checks += 1
            if not ok:
                g8_failures.append({"seed": seed, "kind": "not_real", "reason": reason})
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": real_transform_checks,
        "distinct_unrelated": distinct_count,
        "unrelated_total": 20,
        "failures": g8_failures,
        "invariant": "rooted closed-walk and distance histograms of the incidence graph",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
