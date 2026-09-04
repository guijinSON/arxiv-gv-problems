#!/usr/bin/env python3
"""Domain-standard SAT/CSP attacks on the `sat-csp` audit group.

Three shipped families whose G6 panel ran only generic probes (outlier, greedy,
random-restart).  Each is attacked here with the algorithm a specialist reaches
for first, and graded ONLY by the module's own ``verify``.

  2404.18447  finite-field PRODSAT core over F_p
              -> one-hot CNF encoding of the ternary CSP + DPLL
                 (unit propagation, pure literal elimination, 2-watched literals)

  2401.06027  bounded Kempe sequence == Hamiltonian cycle in a cubic graph
              -> exact edge-status branch & propagate ("exactly one OUT edge per
                 vertex" + union-find premature-cycle rejection), the standard
                 cubic-HC solver

  2302.11250  semi-positive debt-swap reachability == exact 3-partition
              -> Algorithm X / DLX exact cover with MRV, then the forced
                 canonical swap schedule read off the public target creditors

Usage:
    python3 audit/attack_sat_csp.py [prodsat|kempe|debtswap|all] [budget_seconds]
"""

import importlib.util
import os
import statistics
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]


def load(relpath):
    path = os.path.join(REPO, relpath)
    spec = importlib.util.spec_from_file_location(
        "gen_" + os.path.basename(path).replace(".py", ""), path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# A generic DPLL SAT solver: unit propagation, pure literals, 2-watched
# literals, MOM-style branching.  ~150 lines, no external dependency.
# ===========================================================================

class DPLL:
    """Literals are nonzero ints; variable v in 1..nv, negation -v."""

    def __init__(self, nv, clauses, deadline):
        self.nv = nv
        self.deadline = deadline
        self.clauses = []
        self.assign = [0] * (nv + 1)          # 0 unknown, 1 true, -1 false
        self.watch = {}                        # literal -> [clause indices]
        for lit in range(-nv, nv + 1):
            if lit:
                self.watch[lit] = []
        self.units = []
        self.conflict = False
        for cl in clauses:
            cl = list(dict.fromkeys(cl))
            if any(-l in cl for l in cl):
                continue                       # tautology
            if not cl:
                self.conflict = True
                continue
            idx = len(self.clauses)
            self.clauses.append(cl)
            if len(cl) == 1:
                self.units.append(cl[0])
            else:
                self.watch[cl[0]].append(idx)
                self.watch[cl[1]].append(idx)
        self.trail = []

    # -- core propagation -------------------------------------------------
    def _enqueue(self, lit, queue):
        v, val = abs(lit), (1 if lit > 0 else -1)
        cur = self.assign[v]
        if cur == val:
            return True
        if cur == -val:
            return False
        self.assign[v] = val
        self.trail.append(v)
        queue.append(lit)
        return True

    def _propagate(self, queue):
        while queue:
            lit = queue.pop()
            false_lit = -lit
            watchers = self.watch[false_lit]
            keep = []
            ok = True
            for i, ci in enumerate(watchers):
                cl = self.clauses[ci]
                # find a new literal to watch
                other = None
                sat = False
                newwatch = None
                for l in cl:
                    a = self.assign[abs(l)]
                    val = a if l > 0 else -a
                    if val == 1:
                        sat = True
                        break
                    if val == 0 and l != false_lit:
                        if newwatch is None:
                            newwatch = l
                        else:
                            other = l
                if sat:
                    keep.append(ci)
                    continue
                if newwatch is None:
                    keep.extend(watchers[i:])
                    ok = False
                    break
                if other is not None:
                    self.watch[newwatch].append(ci)
                    continue
                # unit
                keep.append(ci)
                if not self._enqueue(newwatch, queue):
                    keep.extend(watchers[i + 1:])
                    ok = False
                    break
            self.watch[false_lit] = keep
            if not ok:
                return False
        return True

    # -- branching --------------------------------------------------------
    def _pick(self):
        score = {}
        for cl in self.clauses:
            unknown = []
            sat = False
            for l in cl:
                a = self.assign[abs(l)]
                val = a if l > 0 else -a
                if val == 1:
                    sat = True
                    break
                if val == 0:
                    unknown.append(l)
            if sat or len(unknown) > 3:
                continue
            w = 2 ** (4 - len(unknown))
            for l in unknown:
                score[l] = score.get(l, 0) + w
        if not score:
            for v in range(1, self.nv + 1):
                if self.assign[v] == 0:
                    return v
            return None
        return max(score, key=score.get)

    def solve(self):
        if self.conflict:
            return None
        queue = []
        for u in self.units:
            if not self._enqueue(u, queue):
                return None
        if not self._propagate(queue):
            return None
        # root-level pure literal elimination
        pos = set()
        neg = set()
        for cl in self.clauses:
            for l in cl:
                (pos if l > 0 else neg).add(abs(l))
        pure = [(v if v in pos else -v) for v in (pos ^ neg)]
        queue = []
        for p in pure:
            if self.assign[abs(p)] == 0 and not self._enqueue(p, queue):
                return None
        if not self._propagate(queue):
            return None
        sys.setrecursionlimit(100000)
        return self._dpll()

    def _dpll(self):
        if time.time() > self.deadline:
            raise TimeoutError
        lit = self._pick()
        if lit is None or (isinstance(lit, int) and self.assign[abs(lit)] != 0):
            if all(self.assign[v] != 0 for v in range(1, self.nv + 1)):
                return [v if self.assign[v] == 1 else -v for v in range(1, self.nv + 1)]
        if lit is None:
            return [v if self.assign[v] == 1 else -v for v in range(1, self.nv + 1)]
        for cand in (lit, -lit):
            mark = len(self.trail)
            queue = []
            if self._enqueue(cand, queue) and self._propagate(queue):
                if all(self.assign[v] != 0 for v in range(1, self.nv + 1)):
                    return [v if self.assign[v] == 1 else -v
                            for v in range(1, self.nv + 1)]
                r = self._dpll()
                if r is not None:
                    return r
            while len(self.trail) > mark:
                self.assign[self.trail.pop()] = 0
        return None


# ===========================================================================
# 2404.18447 -- finite-field PRODSAT core: one-hot CNF + DPLL
# ===========================================================================

def _point(q, p):
    return (0, 1) if q == p else (1, q)


def _evalc(coeff, vals, p):
    a, b, c = (_point(q, p) for q in vals)
    tot = 0
    for idx in range(8):
        tot += coeff[idx] * a[(idx >> 2) & 1] * b[(idx >> 1) & 1] * c[idx & 1]
    return tot % p


def build_tables(inst):
    """Ternary table constraints: the allowed (a,b,c) tuples per equation."""
    p, dom = inst["p"], inst["p"] + 1
    cons = []
    for cl in inst["clauses"]:
        co = cl["coeff"]
        tuples = [(x, y, z)
                  for x in range(dom) for y in range(dom) for z in range(dom)
                  if _evalc(co, (x, y, z), p) == 0]
        cons.append((tuple(cl["vars"]), tuples))
    return cons


def solve_csp_gac(inst, deadline):
    """Backtracking search maintaining generalized arc consistency (MAC/GAC-3)
    on the ternary table constraints -- the textbook CSP solver."""
    n, dom = inst["n"], inst["p"] + 1
    cons = build_tables(inst)
    incid = [[] for _ in range(n)]
    for ci, (sc, _) in enumerate(cons):
        for v in sc:
            incid[v].append(ci)
    nodes = [0]

    def gac(D, live):
        queue = list(range(len(cons)))
        while queue:
            ci = queue.pop()
            sc = cons[ci][0]
            new = [t for t in live[ci] if all(t[k] in D[sc[k]] for k in range(3))]
            if not new:
                return False
            live[ci] = new
            for k in range(3):
                sup = {t[k] for t in new}
                v = sc[k]
                if len(sup) < len(D[v]):
                    D[v] = D[v] & sup
                    if not D[v]:
                        return False
                    for cj in incid[v]:
                        if cj != ci and cj not in queue:
                            queue.append(cj)
        return True

    def rec(D, live):
        if time.time() > deadline:
            raise TimeoutError
        nodes[0] += 1
        un = [v for v in range(n) if len(D[v]) > 1]
        if not un:
            return [next(iter(D[v])) for v in range(n)]
        v = min(un, key=lambda x: len(D[x]))
        for val in sorted(D[v]):
            D2 = [set(s) for s in D]
            D2[v] = {val}
            L2 = [list(x) for x in live]
            if gac(D2, L2):
                r = rec(D2, L2)
                if r is not None:
                    return r
        return None

    D = [set(range(dom)) for _ in range(n)]
    live = [list(t) for _, t in cons]
    if not gac(D, live):
        return None, nodes[0]
    return rec(D, live), nodes[0]


def cnf_of(inst):
    """Direct one-hot CNF: at-least-one, at-most-one, plus one nogood clause
    per falsifying (a,b,c) tuple of every equation."""
    n, p = inst["n"], inst["p"]
    dom = p + 1

    def X(v, a):
        return v * dom + a + 1

    clauses = []
    for v in range(n):
        clauses.append([X(v, a) for a in range(dom)])
        for a in range(dom):
            for b in range(a + 1, dom):
                clauses.append([-X(v, a), -X(v, b)])
    for cl in inst["clauses"]:
        A, B, C = cl["vars"]
        co = cl["coeff"]
        for a in range(dom):
            for b in range(dom):
                for c in range(dom):
                    if _evalc(co, (a, b, c), p):
                        clauses.append([-X(A, a), -X(B, b), -X(C, c)])
    return n * dom, clauses, X


def attack_prodsat(budget):
    mod = load("results/2404.18447/gen_2404_18447.py")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print(f"[2404.18447] preset={mod.SHIPPING_DIFFICULTY} params={params}")
    wins, times = 0, []
    for sd in SEEDS:
        inst = mod.make_instance(seed=sd, **params)
        t0 = time.time()
        try:
            sol, nodes = solve_csp_gac(inst, time.time() + budget)
        except TimeoutError:
            sol, nodes = None, -1
        el = time.time() - t0
        ok, why = False, "no model / timeout"
        if sol is not None:
            ok, why = mod.verify(inst, sol)
        times.append(el)
        print(f"  seed {sd}: n={inst['n']} p={inst['p']} search_nodes={nodes} "
              f"{el:7.3f}s -> {'SOLVED' if ok else 'FAILED (' + str(why) + ')'}")
        wins += bool(ok)
    return "2404.18447", "ternary table CSP + MAC/GAC-3 backtracking", wins, times


def attack_prodsat_cnf(budget):
    """Secondary data point: the same instances as raw one-hot nogood CNF, run
    through the hand-written DPLL above.  Reported honestly, timeouts included."""
    mod = load("results/2404.18447/gen_2404_18447.py")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print(f"[2404.18447-cnf] preset={mod.SHIPPING_DIFFICULTY} params={params}")
    wins, times = 0, []
    for sd in SEEDS:
        inst = mod.make_instance(seed=sd, **params)
        t0 = time.time()
        nv, clauses, X = cnf_of(inst)
        try:
            model = DPLL(nv, clauses, time.time() + budget).solve()
        except TimeoutError:
            model = None
        el = time.time() - t0
        ok, why = False, "no model / timeout"
        if model is not None:
            truth = set(l for l in model if l > 0)
            dom = inst["p"] + 1
            cand = []
            for v in range(inst["n"]):
                hit = [a for a in range(dom) if X(v, a) in truth]
                cand.append(hit[0] if hit else 0)
            ok, why = mod.verify(inst, cand)
        times.append(el)
        print(f"  seed {sd}: cnf_vars={nv} clauses={len(clauses)} {el:7.3f}s -> "
              f"{'SOLVED' if ok else 'FAILED (' + str(why) + ')'}")
        wins += bool(ok)
    return "2404.18447", "one-hot nogood CNF + hand-written DPLL", wins, times


# ===========================================================================
# 2401.06027 -- bounded Kempe == Hamiltonian cycle in a cubic graph.
# Exact edge branch&propagate: every vertex of a cubic graph has EXACTLY one
# incident edge outside the Hamiltonian cycle.
# ===========================================================================

class CubicHC:
    def __init__(self, n, edges, deadline):
        self.n = n
        self.edges = [tuple(e) for e in edges]
        self.m = len(self.edges)
        self.deadline = deadline
        self.inc = [[] for _ in range(n)]
        for i, (u, v) in enumerate(self.edges):
            self.inc[u].append(i)
            self.inc[v].append(i)
        self.state = [0] * self.m          # 0 undecided, 1 IN, -1 OUT
        self.cin = [0] * n
        self.cout = [0] * n
        self.parent = list(range(n))
        self.size = [1] * n
        self.in_count = 0
        self.trail = []                     # ('e', idx) or ('u', child, root)
        self.solution = None
        self.nodes = 0

    def find(self, x):
        while self.parent[x] != x:
            x = self.parent[x]
        return x

    def _undo(self, mark):
        while len(self.trail) > mark:
            kind, a, b = self.trail.pop()
            if kind == 'e':
                i = a
                u, v = self.edges[i]
                if self.state[i] == 1:
                    self.cin[u] -= 1
                    self.cin[v] -= 1
                    self.in_count -= 1
                else:
                    self.cout[u] -= 1
                    self.cout[v] -= 1
                self.state[i] = 0
            else:
                self.parent[a] = a
                self.size[b] -= self.size[a]

    def _set(self, i, val, queue):
        if self.state[i] == val:
            return True
        if self.state[i] != 0:
            return False
        u, v = self.edges[i]
        self.state[i] = val
        self.trail.append(('e', i, 0))
        if val == 1:
            self.cin[u] += 1
            self.cin[v] += 1
            self.in_count += 1
            if self.cin[u] > 2 or self.cin[v] > 2:
                return False
            ru, rv = self.find(u), self.find(v)
            if ru == rv:
                # premature cycle unless it closes the whole tour
                if self.in_count == self.n:
                    self.solution = True
                    return True
                return False
            if self.size[ru] < self.size[rv]:
                ru, rv = rv, ru
            self.parent[rv] = ru
            self.size[ru] += self.size[rv]
            self.trail.append(('u', rv, ru))
        else:
            self.cout[u] += 1
            self.cout[v] += 1
            if self.cout[u] > 1 or self.cout[v] > 1:
                return False
        queue.append(u)
        queue.append(v)
        return True

    def _propagate(self, queue):
        while queue:
            if self.solution:
                return True
            x = queue.pop()
            und = [i for i in self.inc[x] if self.state[i] == 0]
            if self.cin[x] == 2:
                for i in und:
                    if not self._set(i, -1, queue):
                        return False
            elif self.cout[x] == 1:
                for i in und:
                    if not self._set(i, 1, queue):
                        return False
            if self.cin[x] + len(und) < 2:
                return False
        return True

    def _pick(self):
        best, bestscore = None, -1
        for x in range(self.n):
            und = [i for i in self.inc[x] if self.state[i] == 0]
            if not und:
                continue
            score = 3 - len(und)
            if score > bestscore:
                bestscore, best = score, und[0]
                if bestscore == 2:
                    break
        return best

    def _search(self):
        if self.solution:
            return True
        if time.time() > self.deadline:
            raise TimeoutError
        self.nodes += 1
        i = self._pick()
        if i is None:
            return self.in_count == self.n
        for val in (1, -1):
            mark = len(self.trail)
            q = []
            if self._set(i, val, q) and self._propagate(q):
                if self.solution:
                    return True
                if self._search():
                    return True
            self._undo(mark)
        return False

    def solve(self):
        q = list(range(self.n))
        if not self._propagate(q):
            return None
        if self.solution or self._search():
            return self._extract()
        return None

    def _extract(self):
        adj = [[] for _ in range(self.n)]
        for i, (u, v) in enumerate(self.edges):
            if self.state[i] == 1:
                adj[u].append(v)
                adj[v].append(u)
        if any(len(a) != 2 for a in adj):
            return None
        order = [0]
        prev, cur = -1, 0
        while True:
            nxt = adj[cur][0] if adj[cur][0] != prev else adj[cur][1]
            if nxt == 0:
                break
            order.append(nxt)
            prev, cur = cur, nxt
        return order if len(order) == self.n else None


def attack_kempe(budget):
    mod = load("results/2401.06027/gen_2401_06027.py")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print(f"[2401.06027] preset={mod.SHIPPING_DIFFICULTY} params={params}")
    wins, times = 0, []
    for sd in SEEDS:
        inst = mod.make_instance(seed=sd, **params)
        n = inst["n"]
        t0 = time.time()
        solver = CubicHC(n, inst["edges"], time.time() + budget)
        try:
            cyc = solver.solve()
        except TimeoutError:
            cyc = None
        el = time.time() - t0
        ok, why = False, "no cycle / timeout"
        if cyc is not None:
            ok, why = mod.verify(inst, cyc)
        times.append(el)
        print(f"  seed {sd}: n={n} cubic_edges={len(inst['edges'])} "
              f"nodes={solver.nodes} {el:7.4f}s -> "
              f"{'SOLVED' if ok else 'FAILED (' + str(why) + ')'}")
        wins += bool(ok)
    return "2401.06027", "cubic-HC edge branch&propagate + union-find", wins, times


# ===========================================================================
# 2302.11250 -- semi-positive debt swaps == exact 3-partition.
# Algorithm X (DLX) exact cover with MRV column selection.
# ===========================================================================

def exact_cover_triples(values, target, deadline):
    m = len(values)
    triples = []
    idx_by_val = {}
    for i, v in enumerate(values):
        idx_by_val.setdefault(v, []).append(i)
    for i in range(m):
        for j in range(i + 1, m):
            want = target - values[i] - values[j]
            for k in idx_by_val.get(want, ()):
                if k > j:
                    triples.append((i, j, k))
    rows_by_item = [[] for _ in range(m)]
    for t in triples:
        for x in t:
            rows_by_item[x].append(t)

    remaining = set(range(m))
    chosen = []
    live = {t: True for t in triples}

    def rec():
        if time.time() > deadline:
            raise TimeoutError
        if not remaining:
            return True
        # MRV: item with fewest live triples
        best, bestrows = None, None
        for x in remaining:
            rows = [t for t in rows_by_item[x] if live[t]]
            if best is None or len(rows) < len(bestrows):
                best, bestrows = x, rows
                if not rows:
                    return False
        for t in bestrows:
            killed = []
            for x in t:
                remaining.discard(x)
                for u in rows_by_item[x]:
                    if live[u]:
                        live[u] = False
                        killed.append(u)
            chosen.append(t)
            if rec():
                return True
            chosen.pop()
            for u in killed:
                live[u] = True
            for x in t:
                remaining.add(x)
        return False

    if rec():
        return [list(t) for t in chosen], len(triples)
    return None, len(triples)


def build_schedule(inst, groups):
    """Canonical swap schedule from a 3-partition, using only public fields."""
    n = inst["n"]
    d_for_stage = {}
    for d in range(n - 1):
        creditor = inst["target_creditors"][f"d{d}"]      # e.g. "U3"
        d_for_stage[(int(creditor[1:]) - 1) // 2] = f"d{d}"
    out, filler = [], 0
    for stage, group in enumerate(groups):
        for item in group:
            out.append(sorted((f"i{item}", f"c{filler}")))
            filler += 1
        if stage < n - 1:
            out.append(sorted((f"p{stage}", d_for_stage[stage])))
    return out


def attack_debtswap(budget):
    mod = load("results/2302.11250/gen_2302_11250.py")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print(f"[2302.11250] preset={mod.SHIPPING_DIFFICULTY} params={params}")
    wins, times = 0, []
    for sd in SEEDS:
        inst = mod.make_instance(seed=sd, **params)
        t0 = time.time()
        try:
            groups, ntri = exact_cover_triples(
                inst["item_values"], inst["target_sum"], time.time() + budget)
        except TimeoutError:
            groups, ntri = None, -1
        cand = build_schedule(inst, groups) if groups else None
        el = time.time() - t0
        ok, why = False, "no cover / timeout"
        if cand is not None:
            ok, why = mod.verify(inst, cand)
        times.append(el)
        print(f"  seed {sd}: bins={inst['n']} items={len(inst['item_values'])} "
              f"cand_triples={ntri} swaps={len(cand) if cand else 0} "
              f"{el:7.3f}s -> {'SOLVED' if ok else 'FAILED (' + str(why) + ')'}")
        wins += bool(ok)
    return "2302.11250", "Algorithm X exact 3-cover + forced schedule", wins, times


# ===========================================================================

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    jobs = {"prodsat": attack_prodsat, "prodsat-cnf": attack_prodsat_cnf,
            "kempe": attack_kempe, "debtswap": attack_debtswap}
    todo = ["prodsat", "kempe", "debtswap"] if which == "all" else [which]
    rows = []
    for name in todo:
        print("=" * 74)
        rows.append(jobs[name](budget))
        print()
    print("=" * 74)
    print(f"SUMMARY  (budget {budget:.0f}s/seed, {len(SEEDS)} seeds each, "
          f"graded by each module's own verify)")
    for pid, attack, wins, times in rows:
        med = statistics.median(times)
        verdict = "BROKEN" if wins else "SURVIVED"
        print(f"  {pid} | {attack} | solved {wins}/{len(SEEDS)} | "
              f"median {med:.4f}s | {verdict}")


if __name__ == "__main__":
    main()
