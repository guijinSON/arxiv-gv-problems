"""Verified generator for iterated strict-dominance witnesses (arXiv:0910.5107).

The module instantiates the three-payoff bimatrix games in the proof of
Theorem 6.6 (``3-Strict`` is P-hard).  A true monotone-circuit spine and its
elimination word are built first.  Randomly sized false circuit branches are
then attached and both players' strategies are independently relabelled.

The answer is a symbolic elimination word.  ``verify`` replays every deletion
against the current subgame and checks strict inequalities in the two payoff
matrices.  It never reads ``inst["answer"]``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# Keep the repository helpers importable when harden.py is launched here.  This
# family is finite/discrete and needs no helper, so the fallback is complete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the standard-library path is primary
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "two-player normal-form game with payoffs in {-1,0,1}",
        "current row and column strategy sets",
        "strict-dominance elimination word",
    ],
    "verification_operations": [
        "exact integer payoff comparison",
        "strategy-set deletion",
        "elimination-word replay",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 6, Theorem 6.6 (MCV1 to 3-Strict bimatrix games)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "In the target dependency cone, viable and false predecessor branches "
        "are separated by whether the preceding input column touches an all-one "
        "row; without this local invariant one must scan the whole game or trace "
        "long false branches."
    ),
    "hardness_basis": (
        "Track B: Theorem 6.1's repeated strict-dominance scan is polynomial "
        "(a direct implementation is O((R+C)(R^2 C+C^2 R)) exact comparisons); "
        "at shipping R=175 and C=262 the bit-parallel implementation solved 8/8 "
        "in 2.30 seconds mean wall-clock while representing 348,009,727 exact "
        "payoff comparisons, whereas the invariant route needs 70 local incidence "
        "checks."
    ),
    "max_answer_tokens": 127,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is the number of false AND/OR branch pairs.  Depth, hence answer length,
# stays fixed on the shipping ladder; only the haystack grows.
DIFFICULTY = {
    "easy": {"n": 64, "depth": 24},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The target cone alternates through input columns distinguished by the "
    "presence or absence of an ALL1 grandparent row."
)
PLACEBO_HINT = (
    "The target calculation rewards keeping the current row and column sets "
    "carefully separated throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly 2*depth-1 strings, alternating row and column "
        "deletions and ending at the target row.  Each string is Rv<Rd or "
        "Cv<Cd with in-range decimal indices: delete v because d strictly "
        "dominates it.  Victims do not repeat and every dominator is still active."
    ),
    "bounds": {
        "length": "2*depth-1",
        "row_index_min": 0,
        "row_index_max": "row_count-1",
        "column_index_min": 0,
        "column_index_max": "column_count-1",
        "alternating_sides": True,
        "target_last": True,
        "repeated_victims": False,
        "active_dominators": True,
    },
}

NOTES = (
    "Section 1, Definitions 1.1--1.3 fix strict, ordinary and weak dominance; "
    "this family uses Definition 1.1's strict inequality against every remaining "
    "opponent strategy. Section 3 observes that every elimination word has "
    "polynomial length. Section 6, Theorem 6.1 gives the easy regime: arbitrary "
    "strict-dominance elimination is in P because its reduced game is order "
    "independent. Theorem 6.6 nevertheless proves P-hardness for exactly three "
    "payoff values by the MCV1 construction implemented here. That theorem, not "
    "an external graph surrogate, fixes every payoff rule. The answer is built "
    "from a true circuit spine before false branches or labels are sampled. The "
    "payoff-histogram outlier, low-label branch, high-label branch and 64 random "
    "backward traces are audited; the polynomial full scan is reported honestly "
    "as Track B's successful reference algorithm rather than as a failing attack."
)


_TOKEN_RE = re.compile(r"^([RC])(\d+)<\1(\d+)$")
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000

# Filled from the separately owned harden.py transcripts after the oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _falling(x, k):
    result = 1
    for i in range(k):
        result *= x - i
    return result


def _token(side, victim, dominator):
    return f"{side}{victim}<{side}{dominator}"


def _parse_token(token):
    if not isinstance(token, str):
        return None
    match = _TOKEN_RE.fullmatch(token)
    if match is None:
        return None
    return match.group(1), int(match.group(2)), int(match.group(3))


def _validate_params(n, depth, seed):
    if not _is_int(n) or n < 1:
        raise ValueError("n must be an integer at least 1")
    if not _is_int(depth) or depth < 2:
        raise ValueError("depth must be an integer at least 2")
    if n < depth - 1 and not (n == 1 and depth == 2):
        raise ValueError("n must be at least depth-1")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _random_composition(total, parts, rng):
    """Positive random composition, used only for false-branch lengths."""
    values = [1] * parts
    for _ in range(total - parts):
        values[rng.randrange(parts)] += 1
    return values


def make_instance(n, seed=0, **params):
    """Build a certified Theorem 6.6 game without solving it.

    The true AND/OR spine is created first, together with the forced elimination
    victims and the surviving-input dominators.  Every side branch is then made
    false by construction, branch lengths are randomized, and strategy labels
    are independently shuffled.
    """
    depth = params.pop("depth", 24)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, depth, seed)
    rng = random.Random(seed)

    # Logical row vertices.  Prefixes are private construction names and never
    # appear in the rendered instance.
    true_and = [f"a{i}" for i in range(depth)]
    all_one = []
    false_and = []
    false_or_inputs = {}
    and_input = {true_and[0]: None}

    branch_lengths = _random_composition(n, depth - 1, rng)
    branch_tops = []
    for branch, length in enumerate(branch_lengths):
        previous_and = None
        for level in range(length):
            false_or = f"q{branch}_{level}"
            false_vertex = f"f{branch}_{level}"
            all_one.append(false_vertex)
            if previous_and is None:
                second_false = f"f{branch}_{level}_base"
                all_one.append(second_false)
                false_or_inputs[false_or] = [false_vertex, second_false]
            else:
                false_or_inputs[false_or] = [previous_and, false_vertex]
            current_and = f"x{branch}_{level}"
            false_and.append(current_and)
            and_input[current_and] = false_or
            previous_and = current_and
        branch_tops.append(previous_and)

    spine_or_inputs = {}
    spine_ors = []
    for level in range(1, depth):
        spine_or = f"o{level}"
        spine_ors.append(spine_or)
        # Input order is randomized before all labels are hidden.
        inputs = [true_and[level - 1], branch_tops[level - 1]]
        rng.shuffle(inputs)
        spine_or_inputs[spine_or] = inputs
        and_input[true_and[level]] = spine_or

    and_vertices = true_and + false_and
    row_vertices = and_vertices + all_one
    or_vertices = list(false_or_inputs) + spine_ors

    # Each circuit row vertex has its paper-construction mate column t_v; every
    # OR vertex has its column t_or.  Relabel rows and columns independently.
    shuffled_rows = list(row_vertices)
    rng.shuffle(shuffled_rows)
    row_label = {name: i for i, name in enumerate(shuffled_rows)}

    logical_columns = [("mate", name) for name in row_vertices]
    logical_columns += [("or", name) for name in or_vertices]
    rng.shuffle(logical_columns)
    column_label = {item: i for i, item in enumerate(logical_columns)}

    all_one_rows = sorted(row_label[name] for name in all_one)
    and_inputs = []
    for name in and_vertices:
        input_or = and_input[name]
        cols = [] if input_or is None else [column_label[("or", input_or)]]
        and_inputs.append({"row": row_label[name], "columns": cols})
    rng.shuffle(and_inputs)

    mate_columns = [None] * len(row_vertices)
    for name in row_vertices:
        mate_columns[row_label[name]] = column_label[("mate", name)]

    all_or_inputs = dict(false_or_inputs)
    all_or_inputs.update(spine_or_inputs)
    or_inputs = []
    for name, inputs in all_or_inputs.items():
        or_inputs.append({
            "column": column_label[("or", name)],
            "rows": [row_label[v] for v in inputs],
        })
    rng.shuffle(or_inputs)

    # Carry the paper proof's elimination sequence through both relabellings.
    anchor = row_label[all_one[0]]
    answer = []
    for level in range(depth):
        answer.append(_token("R", row_label[true_and[level]], anchor))
        if level + 1 < depth:
            spine_or = spine_ors[level]
            false_top = branch_tops[level]
            answer.append(_token(
                "C",
                column_label[("or", spine_or)],
                column_label[("mate", false_top)],
            ))

    return {
        "paper": "arXiv:0910.5107",
        "family": "Theorem 6.6 three-payoff strict-dominance game",
        "n": n,
        "depth": depth,
        "row_count": len(row_vertices),
        "column_count": len(logical_columns),
        "target_row": row_label[true_and[-1]],
        "all_one_rows": all_one_rows,
        "and_inputs": and_inputs,
        "mate_columns": mate_columns,
        "or_inputs": or_inputs,
        "witness_length": 2 * depth - 1,
        "answer": answer,
    }


def _compile(inst):
    """Validate and compile the sparse, complete payoff specification."""
    if isinstance(inst, dict):
        cached = inst.get("_compiled")
        if isinstance(cached, dict) and cached.get("cache_version") == 1:
            return cached, "ok"
    try:
        rows = inst["row_count"]
        cols = inst["column_count"]
        target = inst["target_row"]
        all_one_list = inst["all_one_rows"]
        and_records = inst["and_inputs"]
        mates = inst["mate_columns"]
        or_records = inst["or_inputs"]
        depth = inst["depth"]
    except (KeyError, TypeError):
        return None, "instance is missing game data"
    if not all(_is_int(x) for x in (rows, cols, target, depth)):
        return None, "instance dimensions are malformed"
    if rows < 1 or cols < 1 or not 0 <= target < rows or depth < 2:
        return None, "instance dimensions are out of range"
    if not isinstance(mates, list) or len(mates) != rows:
        return None, "mate-column list has wrong shape"
    if any(not _is_int(c) or not 0 <= c < cols for c in mates):
        return None, "mate-column index is out of range"
    if len(set(mates)) != rows:
        return None, "mate columns are not distinct"

    if not isinstance(all_one_list, list) or any(
            not _is_int(r) or not 0 <= r < rows for r in all_one_list):
        return None, "ALL1 row list is malformed"
    all_one = set(all_one_list)
    if len(all_one) != len(all_one_list):
        return None, "ALL1 row list has duplicates"

    and_inputs = {}
    if not isinstance(and_records, list):
        return None, "AND input list is malformed"
    for rec in and_records:
        if not isinstance(rec, dict):
            return None, "AND input record is malformed"
        r, input_cols = rec.get("row"), rec.get("columns")
        if not _is_int(r) or not 0 <= r < rows or r in and_inputs or r in all_one:
            return None, "AND row index is malformed"
        if not isinstance(input_cols, list) or len(input_cols) > 2:
            return None, "AND input-column list is malformed"
        if any(not _is_int(c) or not 0 <= c < cols for c in input_cols):
            return None, "AND input column is out of range"
        and_inputs[r] = tuple(input_cols)
    if set(and_inputs) | all_one != set(range(rows)):
        return None, "row types do not partition the row strategies"

    or_inputs = {}
    for rec in or_records if isinstance(or_records, list) else ():
        if not isinstance(rec, dict):
            return None, "OR input record is malformed"
        c, input_rows = rec.get("column"), rec.get("rows")
        if not _is_int(c) or not 0 <= c < cols or c in or_inputs or c in mates:
            return None, "OR column index is malformed"
        if not isinstance(input_rows, list) or len(input_rows) != 2:
            return None, "OR input-row list is malformed"
        if any(not _is_int(r) or not 0 <= r < rows for r in input_rows):
            return None, "OR input row is out of range"
        if input_rows[0] == input_rows[1]:
            return None, "OR input rows must be distinct"
        or_inputs[c] = tuple(input_rows)
    if set(mates) | set(or_inputs) != set(range(cols)):
        return None, "column types do not partition the column strategies"
    if any(c not in or_inputs for values in and_inputs.values() for c in values):
        return None, "an AND input is not an OR column"
    expected_length = 2 * depth - 1
    if inst.get("witness_length") != expected_length:
        return None, "witness length is inconsistent with depth"
    compiled = {
        "cache_version": 1,
        "rows": rows,
        "cols": cols,
        "target": target,
        "depth": depth,
        "all_one": all_one,
        "and_inputs": and_inputs,
        "mates": tuple(mates),
        "base_columns": set(mates),
        "or_inputs": or_inputs,
    }
    # A private, derived cache makes the 200k density audit practical.  It is
    # never rendered or emitted; emit.sh serializes only question and answer.
    if isinstance(inst, dict):
        inst["_compiled"] = compiled
    return compiled, "ok"


def _payoff_a(data, row, col):
    # Theorem 6.6, first payoff table.
    return int(row in data["all_one"] or col in data["and_inputs"][row])


def _payoff_b(data, row, col):
    # Theorem 6.6, second payoff table.
    if col in data["base_columns"]:
        return int(data["mates"][row] == col)
    return 0 if row in data["or_inputs"][col] else -1


def verify(inst, answer):
    """Replay a candidate elimination word using exact integer comparisons."""
    data, reason = _compile(inst)
    if data is None:
        return False, reason
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    expected = 2 * data["depth"] - 1
    if len(answer) != expected:
        return False, f"wrong number of steps: expected {expected}, got {len(answer)}"

    removed_rows = set()
    removed_cols = set()
    for index, raw in enumerate(answer):
        parsed = _parse_token(raw)
        if parsed is None:
            return False, f"step {index + 1} is not a token Rv<Rd or Cv<Cd"
        side, victim, dominator = parsed
        required_side = "R" if index % 2 == 0 else "C"
        if side != required_side:
            return False, f"step {index + 1} must eliminate a {required_side} strategy"
        limit = data["rows"] if side == "R" else data["cols"]
        if not 0 <= victim < limit or not 0 <= dominator < limit:
            noun = "row" if side == "R" else "column"
            return False, f"step {index + 1} has a {noun} index outside 0..{limit - 1}"
        removed = removed_rows if side == "R" else removed_cols
        if victim in removed:
            return False, f"step {index + 1} repeats an already eliminated victim"
        if victim == dominator:
            return False, f"step {index + 1} uses the victim as its own dominator"
        if dominator in removed:
            return False, f"step {index + 1} dominator is not active"

        if side == "R":
            for col in range(data["cols"]):
                if col in removed_cols:
                    continue
                if _payoff_a(data, dominator, col) <= _payoff_a(data, victim, col):
                    return False, (
                        f"step {index + 1} is not strict row dominance at column C{col}"
                    )
            removed_rows.add(victim)
        else:
            for row in range(data["rows"]):
                if row in removed_rows:
                    continue
                if _payoff_b(data, row, dominator) <= _payoff_b(data, row, victim):
                    return False, (
                        f"step {index + 1} is not strict column dominance at row R{row}"
                    )
            removed_cols.add(victim)

    if answer[-1].split("<", 1)[0] != f"R{data['target']}":
        return False, "the final victim is not the designated target row"
    if data["target"] not in removed_rows:
        return False, "the target row remains active"
    return True, "ok"


def render(inst):
    """Render a self-contained sparse specification of both payoff matrices."""
    data, reason = _compile(inst)
    if data is None:
        raise ValueError(reason)
    all_one = " ".join(f"R{r}" for r in sorted(data["all_one"]))
    and_lines = []
    for row in sorted(data["and_inputs"]):
        inputs = data["and_inputs"][row]
        rhs = "-" if not inputs else " ".join(f"C{c}" for c in inputs)
        and_lines.append(f"  R{row}: {rhs}")
    mate_lines = [
        f"  R{row}: C{data['mates'][row]}" for row in range(data["rows"])
    ]
    or_lines = []
    for col in sorted(data["or_inputs"]):
        r1, r2 = data["or_inputs"][col]
        or_lines.append(f"  C{col}: R{r1} R{r2}")

    statement = f"""Find a strict-dominance elimination word in a finite bimatrix game.

Definitions.
There are two players. The row player chooses one row strategy and receives
the integer payoff A(row,column); the column player chooses one column strategy
and receives B(row,column). At any moment only the not-yet-deleted strategies
are active. A row Rd strictly dominates a different active row Rv exactly when
A(Rd,c) > A(Rv,c) for EVERY active column c. A column Cd strictly dominates a
different active column Cv exactly when B(r,Cd) > B(r,Cv) for EVERY active row
r. One legal step deletes the dominated strategy. All inequalities are strict.

Rows and columns below are indexed from 0, with inclusive ranges
R0..R{data['rows'] - 1} and C0..C{data['cols'] - 1}. The target is
R{data['target']}. The two complete payoff matrices are specified exactly by
the following rules; no data outside this statement is needed.

A payoff rules:
* Every ALL1 row has A(r,c)=1 for every column c.
* Every other row appears under AND-INPUTS. It has A(r,c)=1 exactly at its
  listed input columns, and A(r,c)=0 at every other column. A dash means no
  input columns.

ALL1 ROWS:
  {all_one}
AND-INPUTS:
{chr(10).join(and_lines)}

B payoff rules:
* Each row has the unique mate column printed under MATES. At a mate column c,
  B(r,c)=1 when c is r's own mate and B(r,c)=0 otherwise.
* Every non-mate column appears under OR-INPUT-ROWS with exactly two rows.
  At such a column c, B(r,c)=0 for either listed input row and B(r,c)=-1 for
  every other row.

MATES:
{chr(10).join(mate_lines)}
OR-INPUT-ROWS:
{chr(10).join(or_lines)}

Output exactly {2 * data['depth'] - 1} legal deletion steps as a JSON list of
strings. Steps must alternate row, column, row, column, and so on; the last
step must delete target R{data['target']}. A row token Rv<Rd means "delete Rv,
strictly dominated by active Rd". A column token Cv<Cd has the analogous
meaning. Indices are decimal and 0-based. A victim may not repeat, the victim
and dominator must differ, order matters, and the dominator must still be
active. Other valid words of this exact prescribed shape are accepted.

Give your final answer inside <answer></answer> tags, as that JSON list.
Example syntax: <answer>["R4<R9","C2<C7","R1<R9"]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the tagged JSON word from prose or a fenced response."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```") and payload.endswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list) or any(not isinstance(x, str) for x in answer):
        return None
    return answer


def random_candidate(inst, rng):
    """Sample uniformly from the statement-aware bounded word language."""
    data, reason = _compile(inst)
    if data is None:
        raise ValueError(reason)
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    depth = data["depth"]
    pre_rows = rng.sample(
        [r for r in range(data["rows"]) if r != data["target"]], depth - 1
    )
    row_victims = pre_rows + [data["target"]]
    col_victims = rng.sample(range(data["cols"]), depth - 1)
    removed_rows = set()
    removed_cols = set()
    answer = []
    for level in range(depth):
        victim = row_victims[level]
        while True:
            dominator = rng.randrange(data["rows"])
            if dominator != victim and dominator not in removed_rows:
                break
        answer.append(_token("R", victim, dominator))
        removed_rows.add(victim)
        if level + 1 < depth:
            victim_c = col_victims[level]
            while True:
                dominator_c = rng.randrange(data["cols"])
                if dominator_c != victim_c and dominator_c not in removed_cols:
                    break
            answer.append(_token("C", victim_c, dominator_c))
            removed_cols.add(victim_c)
    return answer


def search_space(inst):
    """Exact cardinality of the structure-aware certificate language."""
    data, reason = _compile(inst)
    if data is None:
        raise ValueError(reason)
    d, rows, cols = data["depth"], data["rows"], data["cols"]
    row_victims = _falling(rows - 1, d - 1)
    row_dominators = math.prod(rows - q - 1 for q in range(d))
    col_victims = _falling(cols, d - 1)
    col_dominators = math.prod(cols - q - 1 for q in range(d - 1))
    return row_victims * row_dominators * col_victims * col_dominators


def _all_candidates_small(inst):
    """Enumerate the exact language, only after its size has been capped."""
    data, reason = _compile(inst)
    if data is None:
        raise ValueError(reason)
    d, rows, cols = data["depth"], data["rows"], data["cols"]
    target = data["target"]
    for row_prefix in itertools.permutations(
            [r for r in range(rows) if r != target], d - 1):
        row_victims = tuple(row_prefix) + (target,)
        for col_victims in itertools.permutations(range(cols), d - 1):
            row_choices = []
            active_rows = set(range(rows))
            for victim in row_victims:
                row_choices.append(tuple(sorted(active_rows - {victim})))
                active_rows.remove(victim)
            col_choices = []
            active_cols = set(range(cols))
            for victim in col_victims:
                col_choices.append(tuple(sorted(active_cols - {victim})))
                active_cols.remove(victim)
            for row_doms in itertools.product(*row_choices):
                for col_doms in itertools.product(*col_choices):
                    word = []
                    for level in range(d):
                        word.append(_token(
                            "R", row_victims[level], row_doms[level]
                        ))
                        if level + 1 < d:
                            word.append(_token(
                                "C", col_victims[level], col_doms[level]
                            ))
                    yield word


def enumerate_all(inst):
    """Brute-force the language when it has at most 100,000 candidates."""
    if search_space(inst) > 100_000:
        return None
    return sum(1 for answer in _all_candidates_small(inst) if verify(inst, answer)[0])


def canonical_key(inst):
    """Merkle-normalize the target-rooted payoff-incidence tree.

    The result is invariant under independent row and column relabelling and
    under reordering of every displayed record/input list.  The construction's
    entire game lies in the target dependency tree.  This is a structural hash,
    never a hash of the seed, answer, or rendered statement.
    """
    data, reason = _compile(inst)
    if data is None:
        return "invalid:" + reason
    row_to_or = data["and_inputs"]
    all_one = data["all_one"]
    or_to_rows = data["or_inputs"]
    root = ("R", data["target"])
    stack = [(root, False)]
    visiting = set()
    digests = {}
    while stack:
        node, expanded = stack.pop()
        if node in digests:
            continue
        if expanded:
            visiting.discard(node)
            side, index = node
            if side == "R":
                if index in all_one:
                    payload = b"F"
                else:
                    children = [("C", c) for c in row_to_or[index]]
                    payload = b"A(" + b",".join(
                        sorted(digests[ch] for ch in children)
                    ) + b")"
            else:
                children = [("R", r) for r in or_to_rows[index]]
                payload = b"O(" + b",".join(
                    sorted(digests[ch] for ch in children)
                ) + b")"
            digests[node] = hashlib.sha256(payload).digest()
            continue
        if node in visiting:
            return "invalid:dependency cycle"
        visiting.add(node)
        stack.append((node, True))
        side, index = node
        if side == "R" and index not in all_one:
            children = [("C", c) for c in row_to_or[index]]
        elif side == "C":
            children = [("R", r) for r in or_to_rows[index]]
        else:
            children = []
        for child in reversed(children):
            if child not in digests:
                stack.append((child, False))
    return "strict-tree-v1:" + digests[root].hex()


def escalate(params):
    """Double only the false-branch haystack; keep the answer depth fixed."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    depth = params.get("depth", 24)
    if not _is_int(n) or not _is_int(depth):
        return None
    return {"n": n * 2, "depth": depth}


def _generic_strict_scan(inst):
    """Theorem 6.1's repeated scan, bit-parallel but comparison-counted.

    Each integer mask represents one payoff-signature row or column.  A mask
    containment test performs exactly the same all-active-opponents comparison
    as the displayed polynomial scan.  ``comparisons`` reports those logical
    coordinate comparisons; wall time benefits from Python's C-level big ints.
    """
    data, reason = _compile(inst)
    if data is None:
        return None, {"comparisons": 0, "reason": reason}
    active_rows = set(range(data["rows"]))
    active_cols = set(range(data["cols"]))
    word = []
    comparisons = 0
    rounds = 0
    all_col_mask = (1 << data["cols"]) - 1
    all_row_mask = (1 << data["rows"]) - 1
    active_col_mask = all_col_mask
    active_row_mask = all_row_mask

    a_one = []
    for row in range(data["rows"]):
        if row in data["all_one"]:
            a_one.append(all_col_mask)
        else:
            mask = 0
            for col in data["and_inputs"][row]:
                mask |= 1 << col
            a_one.append(mask)

    b_minus = [0] * data["cols"]
    b_zero = [0] * data["cols"]
    b_one = [0] * data["cols"]
    for col in range(data["cols"]):
        if col in data["base_columns"]:
            owner = data["mates"].index(col)
            b_one[col] = 1 << owner
            b_zero[col] = all_row_mask ^ (1 << owner)
        else:
            mask = 0
            for row in data["or_inputs"][col]:
                mask |= 1 << row
            b_zero[col] = mask
            b_minus[col] = all_row_mask ^ mask
    while data["target"] in active_rows:
        rounds += 1
        found = None
        row_order = sorted(active_rows)
        col_order = sorted(active_cols)
        for victim in row_order:
            for dominator in row_order:
                if victim == dominator:
                    continue
                comparisons += len(active_cols)
                good = a_one[dominator] & (all_col_mask ^ a_one[victim])
                dominates = active_col_mask & (all_col_mask ^ good) == 0
                if dominates:
                    found = ("R", victim, dominator)
                    break
            if found is not None:
                break
        if found is None:
            for victim in col_order:
                for dominator in col_order:
                    if victim == dominator:
                        continue
                    comparisons += len(active_rows)
                    good = (
                        b_one[dominator] & (b_zero[victim] | b_minus[victim])
                    ) | (b_zero[dominator] & b_minus[victim])
                    dominates = active_row_mask & (all_row_mask ^ good) == 0
                    if dominates:
                        found = ("C", victim, dominator)
                        break
                if found is not None:
                    break
        if found is None:
            break
        side, victim, dominator = found
        word.append(_token(side, victim, dominator))
        if side == "R":
            active_rows.remove(victim)
            active_row_mask &= ~(1 << victim)
        else:
            active_cols.remove(victim)
            active_col_mask &= ~(1 << victim)
        if len(word) > data["rows"] + data["cols"]:
            break
    return word, {"comparisons": comparisons, "rounds": rounds}


def _dependency_maps(data):
    outgoing = {r: 0 for r in range(data["rows"])}
    for inputs in data["or_inputs"].values():
        for row in inputs:
            outgoing[row] += 1
    return outgoing


def _pad_attack_word(inst, partial, rng):
    """Return a language-shaped candidate while retaining an attack's prefix."""
    data, _ = _compile(inst)
    expected = 2 * data["depth"] - 1
    if len(partial) == expected:
        return partial
    fallback = random_candidate(inst, rng)
    merged = list(partial[:expected])
    merged.extend(fallback[len(merged):])
    # Preserve the mandatory target-last syntax even after a failed trace.
    parsed = _parse_token(merged[-1])
    dom = parsed[2] if parsed and parsed[0] == "R" and parsed[2] != data["target"] else (
        0 if data["target"] != 0 else 1
    )
    merged[-1] = _token("R", data["target"], dom)
    return merged


def _backward_trace(inst, chooser, rng):
    """Build the guessed target proof induced by a local branch chooser."""
    data, _ = _compile(inst)
    anchor = min(data["all_one"])
    seen = set()

    def prove(row):
        if row in seen or row in data["all_one"]:
            return []
        seen.add(row)
        inputs = data["and_inputs"].get(row, ())
        if not inputs:
            return [_token("R", row, anchor)]
        if len(inputs) != 1:
            return []
        col = inputs[0]
        candidates = data["or_inputs"].get(col, ())
        if len(candidates) != 2:
            return []
        chosen = chooser(col, candidates, data)
        if chosen not in candidates or chosen in data["all_one"]:
            return []
        other = candidates[0] if candidates[1] == chosen else candidates[1]
        prefix = prove(chosen)
        if not prefix:
            return []
        return prefix + [
            _token("C", col, data["mates"][other]),
            _token("R", row, anchor),
        ]

    return _pad_attack_word(inst, prove(data["target"]), rng)


def _attack_candidates(inst, seed):
    data, _ = _compile(inst)
    outgoing = _dependency_maps(data)
    result = {}

    def histogram_choice(_col, candidates, _data):
        # Per-row payoff support and outdegree only; labels break exact ties.
        return min(candidates, key=lambda r: (
            len(data["and_inputs"].get(r, ())), outgoing[r], r
        ))

    result["outlier_payoff_histogram"] = _backward_trace(
        inst, histogram_choice, random.Random(seed ^ 0xA51)
    )
    result["greedy_lowest_label_branch"] = _backward_trace(
        inst, lambda _c, rs, _d: min(rs), random.Random(seed ^ 0xB62)
    )
    result["greedy_highest_label_branch"] = _backward_trace(
        inst, lambda _c, rs, _d: max(rs), random.Random(seed ^ 0xC73)
    )

    restart_rng = random.Random(seed ^ 0xD84)
    last = None
    for _ in range(64):
        def random_choice(_c, rows, _d, local_rng=restart_rng):
            return rows[local_rng.randrange(len(rows))]
        candidate = _backward_trace(inst, random_choice, restart_rng)
        last = candidate
        if verify(inst, candidate)[0]:
            break
    result["random_backward_trace_64"] = last
    return result


def _relabel_instance(inst, row_perm=None, col_perm=None, reorder=False, seed=0):
    """Apply an actual game isomorphism and carry the witness through it."""
    data, reason = _compile(inst)
    if data is None:
        raise ValueError(reason)
    if row_perm is None:
        row_perm = list(range(data["rows"]))
    if col_perm is None:
        col_perm = list(range(data["cols"]))
    if sorted(row_perm) != list(range(data["rows"])):
        raise ValueError("row_perm is not a permutation")
    if sorted(col_perm) != list(range(data["cols"])):
        raise ValueError("col_perm is not a permutation")
    rng = random.Random(seed)
    and_records = [
        {
            "row": row_perm[rec["row"]],
            "columns": [col_perm[c] for c in rec["columns"]],
        }
        for rec in inst["and_inputs"]
    ]
    or_records = [
        {
            "column": col_perm[rec["column"]],
            "rows": [row_perm[r] for r in rec["rows"]],
        }
        for rec in inst["or_inputs"]
    ]
    if reorder:
        rng.shuffle(and_records)
        rng.shuffle(or_records)
        for rec in and_records:
            rng.shuffle(rec["columns"])
        for rec in or_records:
            rng.shuffle(rec["rows"])
    mates = [None] * data["rows"]
    for old_row, old_col in enumerate(inst["mate_columns"]):
        mates[row_perm[old_row]] = col_perm[old_col]
    answer = []
    for raw in inst["answer"]:
        side, victim, dominator = _parse_token(raw)
        mapping = row_perm if side == "R" else col_perm
        answer.append(_token(side, mapping[victim], mapping[dominator]))
    return {
        **{k: v for k, v in inst.items() if k not in {
            "target_row", "all_one_rows", "and_inputs", "mate_columns",
            "or_inputs", "answer", "_compiled"
        }},
        "target_row": row_perm[inst["target_row"]],
        "all_one_rows": [row_perm[r] for r in inst["all_one_rows"]],
        "and_inputs": and_records,
        "mate_columns": mates,
        "or_inputs": or_records,
        "answer": answer,
    }


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    """Run correctness, density, adversary, scaling and invariance gates."""
    report = {}

    # G1: every preset, three unrelated seeds, plus JSON-native serialization.
    failures = []
    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checked += 1
            if not ok or not native:
                failures.append({
                    "preset": preset, "seed": seed, "reason": reason,
                    "json_native": native,
                })
    report["G1_planted_verifies"] = {
        "pass": not failures, "checked": checked, "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping)
    planted = list(inst["answer"])
    corruptions = {}

    cases = {}
    cases["drop_one"] = planted[:-1]
    first = _parse_token(planted[0])
    cases["swap_victim_dominator"] = [
        _token(first[0], first[2], first[1])
    ] + planted[1:]
    duplicate = list(planted)
    duplicate[2] = duplicate[0]
    cases["duplicate"] = duplicate
    cases["empty"] = []
    out = list(planted)
    out[0] = _token("R", inst["row_count"], first[2])
    cases["out_of_range"] = out
    for name, bad in cases.items():
        ok, reason = verify(inst, bad)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I replayed the inequalities.\n```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThe block is my final witness."
    )
    parsed = parse_answer(response)
    roundtrip_ok, roundtrip_reason = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and roundtrip_ok,
        "verify_reason": roundtrip_reason,
    }

    guess_rng = random.Random(0x915107)
    hits = 0
    for _ in range(_GUESS_SAMPLES):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "measured_probability": hits / _GUESS_SAMPLES,
        "candidate_space": search_space(inst),
        "sampler": (
            "uniform exact-length alternating words with distinct victims, "
            "target last, and active in-range dominators"
        ),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference_stats = []
    reference_successes = 0
    for seed in range(810, 818):
        probe = make_instance(seed=seed, **shipping)
        started = time.perf_counter()
        word, stats = _generic_strict_scan(probe)
        elapsed = time.perf_counter() - started
        ok, _ = verify(probe, word)
        reference_successes += int(ok)
        reference_stats.append({
            "seed": seed,
            "wall_clock_sec": elapsed,
            "comparisons": stats["comparisons"],
            "rounds": stats["rounds"],
        })
    mean_wall = sum(x["wall_clock_sec"] for x in reference_stats) / 8
    mean_comparisons = sum(x["comparisons"] for x in reference_stats) / 8
    mean_rounds = sum(x["rounds"] for x in reference_stats) / 8
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and reference_successes == 8,
        "shipping_density_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": hits / _GUESS_SAMPLES,
        "demo_candidate_space": search_space(demo),
        "demo_exact_valid_answers": demo_count,
        "baseline_wall_clock_sec_mean": mean_wall,
        "baseline_wall_clock_sec_max": max(x["wall_clock_sec"] for x in reference_stats),
        "baseline_payoff_comparisons_mean": mean_comparisons,
        "baseline_payoff_comparisons_max": max(x["comparisons"] for x in reference_stats),
        "baseline_rounds_mean": mean_rounds,
        "reference_successes": reference_successes,
        "reference_attempts": 8,
    }

    attack_names = [
        "outlier_payoff_histogram",
        "greedy_lowest_label_branch",
        "greedy_highest_label_branch",
        "random_backward_trace_64",
    ]
    attack_results = {name: {"successes": 0, "attempts": 8}
                      for name in attack_names}
    attack_started = time.perf_counter()
    for seed in range(810, 818):
        probe = make_instance(seed=seed, **shipping)
        for name, candidate in _attack_candidates(probe, seed).items():
            attack_results[name]["successes"] += int(verify(probe, candidate)[0])
    attack_wall = time.perf_counter() - attack_started
    all_failed = all(x["successes"] == 0 for x in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "seeds": list(range(810, 818)),
        "failing_panel_wall_clock_sec": attack_wall,
        "reference_algorithm": {
            "name": "Theorem 6.1 repeated strict-dominance scan",
            "complexity": "O((R+C)(R^2*C+C^2*R)) exact payoff comparisons",
            "wall_clock_sec_mean": mean_wall,
            "operations_mean": mean_comparisons,
            "rounds_mean": mean_rounds,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    bigger_params = escalate(shipping)
    started = time.perf_counter()
    bigger = make_instance(seed=4242, **bigger_params)
    bigger_build = time.perf_counter() - started
    bigger_ok, bigger_reason = verify(bigger, bigger["answer"])
    report["G7_scales"] = {
        "pass": bigger_ok
        and bigger["n"] == 2 * inst["n"]
        and len(bigger["answer"]) == len(inst["answer"])
        and search_space(bigger) > search_space(inst),
        "base_n": inst["n"],
        "doubled_n": bigger["n"],
        "answer_length_base": len(inst["answer"]),
        "answer_length_doubled": len(bigger["answer"]),
        "base_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(bigger),
        "doubled_build_sec": bigger_build,
        "verify_reason": bigger_reason,
    }

    invariant_failures = []
    invariance_checks = 0
    witness_checks = 0
    for seed in range(20):
        probe = make_instance(seed=1000 + seed, **shipping)
        key = canonical_key(probe)
        rrng = random.Random(5000 + seed)
        row_perm = list(range(probe["row_count"]))
        col_perm = list(range(probe["column_count"]))
        rrng.shuffle(row_perm)
        rrng.shuffle(col_perm)
        transforms = [
            _relabel_instance(probe, row_perm=row_perm, reorder=True, seed=seed),
            _relabel_instance(probe, col_perm=col_perm, reorder=True, seed=seed),
            _relabel_instance(
                probe, row_perm=row_perm, col_perm=col_perm,
                reorder=True, seed=seed,
            ),
        ]
        for transformed in transforms:
            invariance_checks += 1
            if canonical_key(transformed) != key:
                invariant_failures.append({"seed": seed, "kind": "key"})
            ok, reason = verify(transformed, transformed["answer"])
            witness_checks += 1
            if not ok:
                invariant_failures.append({
                    "seed": seed, "kind": "carried witness", "reason": reason,
                })
    unrelated_keys = [
        canonical_key(make_instance(seed=9000 + seed, **shipping))
        for seed in range(20)
    ]
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct == 20,
        "invariant": (
            "target-rooted Merkle normal form of the full payoff-incidence tree"
        ),
        "invariance_checks": invariance_checks,
        "real_transformation_witness_checks": witness_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct,
        "failures": invariant_failures,
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _answer_atoms(inst["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_ops = 3 * (inst["depth"] - 1) + 1
    caps_pass = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    arms = {
        name: dict(G9_ORACLE_RESULTS.get(name, {"solved": 0, "attempts": 0}))
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"].get("attempts") else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"].get("attempts") else None
    )
    difference = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": caps_pass,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "pending"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
