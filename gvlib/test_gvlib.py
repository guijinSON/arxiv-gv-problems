#!/usr/bin/env python3
"""Tests for gvlib.  Run: ``python3 gvlib/test_gvlib.py``

Deterministic: every random case uses a fixed seed, so a failure here is
reproducible from the line number alone.

Three kinds of test live here, and the second and third are the point:

  * unit tests of each guarantee stated in a docstring;
  * cross-checks against an *independent* implementation written in this file
    (cofactor determinant, brute-force root counting, direct expansion), so a
    shared bug in the fast path shows up as a disagreement;
  * mechanical audits of the library source: no float literal, no ``float()``
    call, no import outside {fractions, math, re}, and a docstring on every
    public name.
"""

import ast
import os
import random
import sys
import unittest
from fractions import Fraction as F
from itertools import permutations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gvlib
from gvlib import exact_matrices as em
from gvlib import rationals as rat
from gvlib import roots as rt
from gvlib import sparse_poly as sp

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_FILES = ["__init__.py", "rationals.py", "sparse_poly.py",
             "exact_matrices.py", "roots.py"]


# --------------------------------------------------------------------------
# independent reference implementations, used only to cross-check the library
# --------------------------------------------------------------------------

def cofactor_det(A):
    """Determinant by Leibniz/permutation expansion.  Deliberately naive."""
    n = len(A)
    total = F(0)
    for perm in permutations(range(n)):
        sign = 1
        seen = list(perm)
        for i in range(n):
            for j in range(i + 1, n):
                if seen[i] > seen[j]:
                    sign = -sign
        term = F(1)
        for i in range(n):
            term *= A[i][perm[i]]
        total += sign * term
    return total


def dense_mul(a, b):
    """Dense univariate polynomial product, written out directly."""
    if not a or not b:
        return []
    out = [F(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def dense_add(a, b):
    """Dense univariate polynomial sum, written out directly."""
    n = max(len(a), len(b))
    out = []
    for i in range(n):
        out.append((a[i] if i < len(a) else F(0)) + (b[i] if i < len(b) else F(0)))
    return rt.normalize(out)


def from_roots(rs):
    """The monic polynomial with exactly the given roots, dense ascending."""
    p = [F(1)]
    for r in rs:
        p = dense_mul(p, [-F(r), F(1)])
    return p


class TestRationals(unittest.TestCase):

    def test_Q_accepts_exact_forms(self):
        self.assertEqual(rat.Q(3), F(3))
        self.assertEqual(rat.Q(F(3, 4)), F(3, 4))
        self.assertEqual(rat.Q("7"), F(7))
        self.assertEqual(rat.Q("-3 / 4"), F(-3, 4))
        self.assertEqual(rat.Q("1.25"), F(5, 4))
        self.assertEqual(rat.Q([3, -6]), F(-1, 2))
        self.assertEqual(rat.Q((0, 5)), F(0))

    def test_Q_rejects_inexact_input(self):
        for bad in [0.1, 1.0, True, False, None, {}, object()]:
            with self.assertRaises(TypeError):
                rat.Q(bad)
        for bad in ["1e5", "abc", "", "1/0", "0x10", "3/4/5"]:
            with self.assertRaises(ValueError):
                rat.Q(bad)
        with self.assertRaises(ValueError):
            rat.Q([1, 0])
        with self.assertRaises(ValueError):
            rat.Q([1, 2, 3])
        with self.assertRaises(TypeError):
            rat.Q([1, True])

    def test_json_roundtrip_and_canonical_form(self):
        self.assertEqual(rat.to_json(F(6, -8)), [-3, 4])
        self.assertEqual(rat.to_json(0), [0, 1])
        self.assertEqual(rat.from_json([1, -2]), F(-1, 2))
        for q in [F(0), F(7), F(-22, 7), F(1, 3)]:
            self.assertEqual(rat.from_json(rat.to_json(q)), q)
            num, den = rat.to_json(q)
            self.assertIsInstance(num, int)
            self.assertIsInstance(den, int)
            self.assertGreater(den, 0)

    def test_from_json_is_strict(self):
        for bad in [3, "3/4", [1], [1, 2, 3], [[1, 2], [3, 4]]]:
            with self.assertRaises((TypeError, ValueError)):
                rat.from_json(bad)
        with self.assertRaises(TypeError):
            rat.from_json([1, 2.0])

    def test_parse_rational_is_total(self):
        self.assertEqual(rat.parse_rational("  -7  "), F(-7))
        self.assertEqual(rat.parse_rational("22/7"), F(22, 7))
        self.assertEqual(rat.parse_rational("-.5"), F(-1, 2))
        self.assertEqual(rat.parse_rational("3."), F(3))
        self.assertEqual(rat.parse_rational("0.1"), F(1, 10))
        self.assertNotEqual(rat.parse_rational("0.1"), F(3602879701896397,
                                                         36028797018963968))
        for bad in ["", "x", "1e5", "1/0", "--3", "1 2", ".", None, 5]:
            self.assertIsNone(rat.parse_rational(bad))

    def test_vector_json(self):
        v = [F(1, 2), F(-3), F(0)]
        self.assertEqual(rat.vector_to_json(v), [[1, 2], [-3, 1], [0, 1]])
        self.assertEqual(rat.vector_from_json(rat.vector_to_json(v)), v)
        with self.assertRaises(TypeError):
            rat.vector_from_json("12")

    def test_bit_size_and_bounds(self):
        self.assertEqual(rat.bit_size(0), 1)
        self.assertEqual(rat.bit_size(F(255, 2)), 8)
        self.assertEqual(rat.bit_size(F(1, 256)), 9)
        self.assertEqual(rat.bit_size(F(3, 4)), 3)   # denominator 4 needs 3 bits
        self.assertTrue(rat.within_bits(F(3, 4), 3))
        self.assertFalse(rat.within_bits(F(3, 4), 2))
        self.assertFalse(rat.within_bits(F(1, 2 ** 40), 32))
        with self.assertRaises(ValueError):
            rat.within_bits(1, 0)


class TestSparsePoly(unittest.TestCase):

    def test_normalize_validates_and_drops_zeros(self):
        p = sp.normalize({(1, 0): 2, (0, 1): 0, (0, 0): "1/2"})
        self.assertEqual(p, {(1, 0): F(2), (0, 0): F(1, 2)})
        self.assertEqual(sp.normalize({(1, 0): 1}), {(1, 0): F(1)})
        self.assertEqual(sp.normalize({}, nvars=3), {})
        with self.assertRaises(ValueError):
            sp.normalize({(1, 0): 1, (0,): 1})
        with self.assertRaises(ValueError):
            sp.normalize({(-1,): 1})
        with self.assertRaises(TypeError):
            sp.normalize({(1.0,): 1})
        with self.assertRaises(TypeError):
            sp.normalize([((1,), 1)])
        src = {(1,): F(1)}
        sp.normalize(src)
        self.assertEqual(src, {(1,): F(1)})

    def test_arity_and_builders(self):
        self.assertIsNone(sp.arity({}))
        self.assertEqual(sp.arity(sp.var(1, 3)), 3)
        self.assertEqual(sp.const(0, 2), {})
        self.assertEqual(sp.const(F(-1, 2), 2), {(0, 0): F(-1, 2)})
        with self.assertRaises(ValueError):
            sp.var(3, 3)

    def test_add_sub_cancel(self):
        x, y = sp.var(0, 2), sp.var(1, 2)
        self.assertEqual(sp.add(x, sp.scale(x, -1)), {})
        self.assertTrue(sp.is_zero(sp.sub(sp.add(x, y), sp.add(y, x))))
        with self.assertRaises(ValueError):
            sp.add(sp.var(0, 2), sp.var(0, 3))

    def test_binomial_expansion(self):
        x, y = sp.var(0, 2), sp.var(1, 2)
        p = sp.power(sp.add(x, y), 4)
        self.assertEqual(p, {(4, 0): F(1), (3, 1): F(4), (2, 2): F(6),
                             (1, 3): F(4), (0, 4): F(1)})
        self.assertEqual(sp.power(x, 0), sp.const(1, 2))
        with self.assertRaises(ValueError):
            sp.power({}, 0)
        with self.assertRaises(ValueError):
            sp.power(x, -1)

    def test_power_matches_repeated_mul(self):
        rng = random.Random(11)
        checked = 0
        for _ in range(20):
            p = random_poly(rng, nvars=2, terms=3)
            if not p:
                continue
            acc = sp.const(1, 2)
            for k in range(5):
                self.assertEqual(sp.power(p, k), acc)
                acc = sp.mul(acc, p)
                checked += 1
        self.assertGreater(checked, 50)

    def test_evaluate_is_a_homomorphism(self):
        rng = random.Random(7)
        for _ in range(60):
            p = random_poly(rng, nvars=3, terms=4)
            q = random_poly(rng, nvars=3, terms=4)
            pt = [F(rng.randint(-4, 4), rng.randint(1, 3)) for _ in range(3)]
            self.assertEqual(sp.evaluate(sp.add(p, q), pt),
                             sp.evaluate(p, pt) + sp.evaluate(q, pt))
            self.assertEqual(sp.evaluate(sp.mul(p, q), pt),
                             sp.evaluate(p, pt) * sp.evaluate(q, pt))
        self.assertEqual(sp.evaluate({}, [1, 2, 3]), F(0))
        with self.assertRaises(TypeError):
            sp.evaluate(sp.var(0, 1), [0.5])
        with self.assertRaises(ValueError):
            sp.evaluate(sp.var(0, 2), [1])

    def test_compose_agrees_with_evaluation(self):
        rng = random.Random(3)
        for _ in range(30):
            p = random_poly(rng, nvars=2, terms=3)
            subs = [random_poly(rng, nvars=2, terms=2) or sp.const(1, 2)
                    for _ in range(2)]
            pt = [F(rng.randint(-3, 3)) for _ in range(2)]
            inner = [sp.evaluate(s, pt) for s in subs]
            self.assertEqual(sp.evaluate(sp.compose(p, subs), pt),
                             sp.evaluate(p, inner))
        self.assertEqual(sp.compose({}, []), {})

    def test_degree(self):
        p = sp.normalize({(2, 3): 1, (4, 0): 1})
        self.assertEqual(sp.degree(p), 5)
        self.assertEqual(sp.degree(p, 0), 4)
        self.assertEqual(sp.degree(p, 1), 3)
        self.assertEqual(sp.degree({}), -1)
        with self.assertRaises(ValueError):
            sp.degree(p, 2)

    def test_equal_across_shapes(self):
        self.assertTrue(sp.equal({(0,): 0}, {}))
        self.assertFalse(sp.equal(sp.var(0, 1), sp.var(0, 2)))
        self.assertTrue(sp.equal({(1, 1): F(2)}, {(1, 1): "2"}))

    def test_terms_order_is_stable(self):
        p = {(0, 2): F(1), (2, 0): F(1), (0, 0): F(1), (1, 0): F(1)}
        self.assertEqual([e for e, _ in sp.terms(p)],
                         [(0, 0), (1, 0), (0, 2), (2, 0)])
        shuffled = dict(reversed(list(p.items())))
        self.assertEqual(sp.terms(p), sp.terms(shuffled))

    def test_to_string(self):
        x, y = sp.var(0, 2), sp.var(1, 2)
        p = sp.add(sp.scale(sp.mul(sp.power(x, 2), y), F(3, 4)), sp.const(-2, 2))
        self.assertEqual(sp.to_string(p), "3/4*x0^2*x1 - 2")
        self.assertEqual(sp.to_string({}), "0")
        self.assertEqual(sp.to_string(sp.scale(x, -1), names=["u", "v"]), "-u")

    def test_json_roundtrip_and_tolerance(self):
        rng = random.Random(5)
        for _ in range(30):
            p = random_poly(rng, nvars=3, terms=4)
            self.assertTrue(sp.equal(sp.from_json(sp.to_json(p)), p))
        self.assertEqual(sp.to_json({}), {"nvars": 0, "terms": []})
        bare = [[[1, 0], [1, 2]], [[1, 0], [1, 2]]]
        self.assertEqual(sp.from_json(bare), {(1, 0): F(1)})
        with self.assertRaises(ValueError):
            sp.from_json([[[1, 0], [1, 1]]], nvars=3)
        with self.assertRaises(ValueError):
            sp.from_json({"nvars": 2, "terms": [[[1], [1, 1]]]})
        with self.assertRaises(ValueError):
            sp.from_json({"terms": [[[1, 0]]]})
        with self.assertRaises(TypeError):
            sp.from_json({"terms": "x"})

    def test_univariate_bridge(self):
        p = sp.normalize({(2,): 3, (0,): -1})
        self.assertEqual(sp.to_univariate(p), [F(-1), F(0), F(3)])
        self.assertEqual(sp.from_univariate([-1, 0, 3]), p)
        self.assertEqual(sp.to_univariate({}), [])
        with self.assertRaises(ValueError):
            sp.to_univariate(sp.var(0, 2))

    def test_gram_form_expands_quadratic_form(self):
        G = [[F(2), F(1)], [F(1), F(3)]]
        basis = [(1, 0), (0, 1)]
        p = sp.gram_form(G, basis)
        self.assertEqual(p, {(2, 0): F(2), (1, 1): F(2), (0, 2): F(3)})
        rng = random.Random(9)
        for _ in range(20):
            pt = [F(rng.randint(-5, 5)) for _ in range(2)]
            expect = sum(G[i][j] * pt[i] * pt[j] for i in range(2)
                         for j in range(2))
            self.assertEqual(sp.evaluate(p, pt), expect)
        with self.assertRaises(ValueError):
            sp.gram_form(G, [(1, 0)])


def random_poly(rng, nvars, terms):
    """A random normalised polynomial; may be zero."""
    p = {}
    for _ in range(terms):
        e = tuple(rng.randint(0, 2) for _ in range(nvars))
        p[e] = F(rng.randint(-4, 4), rng.randint(1, 3))
    return sp.normalize(p)


def random_matrix(rng, m, n):
    return [[F(rng.randint(-5, 5), rng.randint(1, 4)) for _ in range(n)]
            for _ in range(m)]


class TestExactMatrices(unittest.TestCase):

    def test_matrix_validation(self):
        A = em.matrix([[1, "1/2"], [0, 3]])
        self.assertEqual(A, [[F(1), F(1, 2)], [F(0), F(3)]])
        self.assertEqual(em.shape(A), (2, 2))
        for bad in [[], [[]], [[1, 2], [3]], "12", [1, 2]]:
            with self.assertRaises((TypeError, ValueError)):
                em.matrix(bad)
        with self.assertRaises(TypeError):
            em.matrix([[0.5]])

    def test_matmul_transpose_laws(self):
        rng = random.Random(21)
        for _ in range(20):
            A = random_matrix(rng, 3, 4)
            B = random_matrix(rng, 4, 2)
            C = random_matrix(rng, 2, 3)
            self.assertEqual(em.matmul(em.matmul(A, B), C),
                             em.matmul(A, em.matmul(B, C)))
            self.assertEqual(em.transpose(em.matmul(A, B)),
                             em.matmul(em.transpose(B), em.transpose(A)))
            self.assertEqual(em.matmul(A, em.identity(4)), A)
            v = [F(rng.randint(-3, 3)) for _ in range(4)]
            self.assertEqual(em.matvec(A, v),
                             [r[0] for r in em.matmul(A, [[x] for x in v])])
        with self.assertRaises(ValueError):
            em.matmul(em.identity(2), em.identity(3))
        with self.assertRaises(ValueError):
            em.matvec(em.identity(2), [1])

    def test_det_matches_independent_expansion(self):
        rng = random.Random(2)
        for n in range(1, 6):
            for _ in range(15):
                A = random_matrix(rng, n, n)
                self.assertEqual(em.det(A), cofactor_det(A))

    def test_det_handles_zero_pivots_and_singularity(self):
        A = em.matrix([[0, 1], [1, 0]])
        self.assertEqual(em.det(A), F(-1))
        B = em.matrix([[0, 0, 2], [0, 3, 0], [5, 0, 0]])
        self.assertEqual(em.det(B), cofactor_det(B))
        S = em.matrix([[1, 2, 3], [2, 4, 6], [1, 0, 1]])
        self.assertEqual(em.det(S), F(0))
        self.assertEqual(em.det([[F(3, 7)]]), F(3, 7))

    def test_det_is_multiplicative(self):
        rng = random.Random(4)
        for _ in range(20):
            A = random_matrix(rng, 4, 4)
            B = random_matrix(rng, 4, 4)
            self.assertEqual(em.det(em.matmul(A, B)), em.det(A) * em.det(B))
        with self.assertRaises(ValueError):
            em.det(random_matrix(random.Random(0), 2, 3))

    def test_rank(self):
        rng = random.Random(6)
        self.assertEqual(em.rank(em.identity(5)), 5)
        self.assertEqual(em.rank([[F(0), F(0)], [F(0), F(0)]]), 0)
        self.assertEqual(em.rank(em.matrix([[1, 2, 3], [2, 4, 6]])), 1)
        for _ in range(20):
            A = random_matrix(rng, 4, 3)
            B = random_matrix(rng, 3, 5)
            r = em.rank(em.matmul(A, B))
            self.assertLessEqual(r, min(em.rank(A), em.rank(B)))
            self.assertEqual(em.rank(A), em.rank(em.transpose(A)))
        for _ in range(15):
            A = random_matrix(rng, 4, 4)
            self.assertEqual(em.rank(A) == 4, em.det(A) != 0)

    def test_solve_exact(self):
        rng = random.Random(8)
        for _ in range(30):
            A = random_matrix(rng, 4, 4)
            if em.det(A) == 0:
                continue
            x = [F(rng.randint(-6, 6), rng.randint(1, 3)) for _ in range(4)]
            b = em.matvec(A, x)
            got = em.solve(A, b)
            self.assertEqual(got, x)
        A = em.matrix([[1, 1, 0], [0, 0, 1]])
        got = em.solve(A, [F(2), F(5)])
        self.assertEqual(em.matvec(A, got), [F(2), F(5)])
        with self.assertRaises(ValueError):
            em.solve(A, [1])

    def test_solve_reports_inconsistency(self):
        A = em.matrix([[1, 1], [2, 2]])
        self.assertIsNone(em.solve(A, [F(1), F(3)]))
        self.assertIsNotNone(em.solve(A, [F(1), F(2)]))

    def test_nullspace(self):
        rng = random.Random(10)
        for _ in range(20):
            A = random_matrix(rng, 3, 5)
            basis = em.nullspace(A)
            self.assertEqual(len(basis), 5 - em.rank(A))
            for v in basis:
                self.assertEqual(em.matvec(A, v), [F(0)] * 3)
                self.assertNotEqual(v, [F(0)] * 5)
            if basis:
                self.assertEqual(em.rank([list(v) for v in basis]), len(basis))
        self.assertEqual(em.nullspace(em.identity(3)), [])

    def test_gram_is_symmetric_and_psd(self):
        rng = random.Random(12)
        for _ in range(20):
            V = random_matrix(rng, 4, 3)
            G = em.gram(V)
            self.assertTrue(em.is_symmetric(G))
            self.assertTrue(em.is_psd(G))
            self.assertEqual(em.rank(G), em.rank(V))
            for i in range(4):
                for j in range(4):
                    self.assertEqual(G[i][j],
                                     sum(V[i][k] * V[j][k] for k in range(3)))

    def test_ldl_reconstructs_the_matrix(self):
        rng = random.Random(14)
        for _ in range(25):
            V = random_matrix(rng, 4, rng.randint(1, 4))
            A = em.gram(V)
            L, D = em.ldl(A)
            diag = [[D[i] if i == j else F(0) for j in range(4)]
                    for i in range(4)]
            self.assertEqual(em.matmul(em.matmul(L, diag), em.transpose(L)), A)
            for i in range(4):
                self.assertEqual(L[i][i], F(1))
                for j in range(i + 1, 4):
                    self.assertEqual(L[i][j], F(0))
        with self.assertRaises(ValueError):
            em.ldl(em.matrix([[1, 2], [3, 4]]))
        with self.assertRaises(ValueError):
            em.ldl(em.matrix([[1, 2, 3], [1, 2, 3]]))

    def test_psd_edge_cases(self):
        psd_rank_deficient = em.matrix([[1, 1], [1, 1]])
        self.assertTrue(em.is_psd(psd_rank_deficient))
        self.assertFalse(em.is_positive_definite(psd_rank_deficient))
        indefinite = em.matrix([[1, 2], [2, 1]])
        self.assertFalse(em.is_psd(indefinite))
        antidiag = em.matrix([[0, 1], [1, 0]])
        self.assertFalse(em.is_psd(antidiag))
        self.assertIsNone(em.ldl(antidiag))
        self.assertFalse(em.is_psd(em.matrix([[1, 2], [3, 4]])))
        self.assertFalse(em.is_psd(em.matrix([[1, 0, 0], [0, 1, 0]])))
        self.assertTrue(em.is_positive_definite(em.matrix([[2, 1], [1, 2]])))
        self.assertTrue(em.is_psd([[F(0)]]))
        self.assertFalse(em.is_positive_definite([[F(0)]]))

    def test_leading_minors_do_not_decide_psd(self):
        # The documented trap: every leading principal minor is >= 0 and the
        # matrix is still not positive semidefinite.
        A = em.matrix([[0, 0], [0, -1]])
        self.assertEqual(em.leading_principal_minors(A), [F(0), F(0)])
        self.assertFalse(em.is_psd(A))
        B = em.matrix([[2, 1], [1, 2]])
        self.assertEqual(em.leading_principal_minors(B), [F(2), F(3)])
        self.assertTrue(em.is_positive_definite(B))
        with self.assertRaises(ValueError):
            em.leading_principal_minors(em.matrix([[1, 2, 3], [4, 5, 6]]))

    def test_ldl_to_squares_is_an_exact_identity(self):
        # x^T A x == sum_k w_k * (l_k . x)^2, checked as polynomials.
        rng = random.Random(16)
        n = 3
        basis = [tuple(1 if i == j else 0 for i in range(n)) for j in range(n)]
        for _ in range(20):
            V = random_matrix(rng, n, rng.randint(1, 3))
            A = em.gram(V)
            L, D = em.ldl(A)
            squares = em.ldl_to_squares(L, D)
            self.assertTrue(all(w > 0 for w, _ in squares))
            self.assertEqual(len(squares), em.rank(A))
            total = {}
            for w, c in squares:
                form = {}
                for i, ci in enumerate(c):
                    if ci:
                        form = sp.add(form, sp.scale(sp.var(i, n), ci))
                total = sp.add(total, sp.scale(sp.power(form, 2), w))
            self.assertTrue(sp.equal(total, sp.gram_form(A, basis)))

    def test_json_roundtrip(self):
        A = em.matrix([[1, "-1/2"], [0, 3]])
        self.assertEqual(em.to_json(A), [[[1, 1], [-1, 2]], [[0, 1], [3, 1]]])
        self.assertEqual(em.from_json(em.to_json(A)), A)
        self.assertEqual(em.from_json(em.to_json(A), rows=2, cols=2), A)
        with self.assertRaises(ValueError):
            em.from_json(em.to_json(A), rows=3)
        with self.assertRaises(ValueError):
            em.from_json(em.to_json(A), cols=5)
        with self.assertRaises(ValueError):
            em.from_json([])
        with self.assertRaises(ValueError):
            em.from_json([[[1, 1]], [[1, 1], [2, 1]]])
        with self.assertRaises(TypeError):
            em.from_json([[1, 1]])


class TestRoots(unittest.TestCase):

    def test_normalize_and_degree(self):
        self.assertEqual(rt.normalize([1, 2, 0, 0]), [F(1), F(2)])
        self.assertEqual(rt.normalize([0, 0]), [])
        self.assertEqual(rt.degree([]), -1)
        self.assertEqual(rt.degree(rt.normalize([1, 0, 3])), 2)
        with self.assertRaises(TypeError):
            rt.normalize([0.5])
        with self.assertRaises(TypeError):
            rt.normalize("12")

    def test_evaluate_and_derivative(self):
        p = rt.normalize([-1, 0, 3])          # 3x^2 - 1
        self.assertEqual(rt.evaluate(p, 2), F(11))
        self.assertEqual(rt.evaluate(p, F(1, 3)), F(-2, 3))
        self.assertEqual(rt.derivative(p), [F(0), F(6)])
        self.assertEqual(rt.derivative([F(5)]), [])
        with self.assertRaises(TypeError):
            rt.evaluate(p, 0.5)

    def test_divmod_and_gcd(self):
        rng = random.Random(18)
        checked = 0
        for _ in range(40):
            a = rt.normalize([F(rng.randint(-4, 4)) for _ in range(5)])
            b = rt.normalize([F(rng.randint(-4, 4)) for _ in range(3)])
            if not b:
                continue
            q, r = rt.divmod_poly(a, b)
            self.assertLess(rt.degree(r), rt.degree(b))
            self.assertEqual(dense_add(dense_mul(q, b), r), rt.normalize(a))
            checked += 1
        self.assertGreater(checked, 20)
        with self.assertRaises(ZeroDivisionError):
            rt.divmod_poly([F(1)], [])
        self.assertEqual(rt.divmod_poly([F(1)], [F(1), F(1)]), ([], [F(1)]))
        g = rt.gcd_poly(from_roots([1, 2, 3]), from_roots([2, 3, 5]))
        self.assertEqual(g, from_roots([2, 3]))
        self.assertEqual(rt.gcd_poly([], []), [])

    def test_squarefree(self):
        p = dense_mul(from_roots([1, 1, 2]), [F(1)])
        self.assertFalse(rt.is_squarefree(p))
        self.assertEqual(rt.squarefree_part(p), from_roots([1, 2]))
        self.assertTrue(rt.is_squarefree(from_roots([1, 2])))
        self.assertFalse(rt.is_squarefree([F(3)]))
        self.assertFalse(rt.is_squarefree([]))
        self.assertEqual(rt.squarefree_part([]), [])
        self.assertEqual(rt.squarefree_part([F(4), F(2)]), [F(2), F(1)])

    def test_sturm_counts_match_brute_force(self):
        rng = random.Random(20)
        for _ in range(30):
            k = rng.randint(1, 4)
            rs = rng.sample(range(-6, 7), k)
            p = from_roots(rs)
            lo, hi = F(-13, 2), F(13, 2)
            expected = sum(1 for r in rs if lo < r < hi)
            self.assertEqual(rt.count_roots(p, lo, hi), expected)
            a, b = F(-1, 2), F(7, 2)
            self.assertEqual(rt.count_roots(p, a, b),
                             sum(1 for r in rs if a < r < b))

    def test_count_roots_refuses_bad_preconditions(self):
        p = from_roots([1, 2])
        with self.assertRaises(ValueError):
            rt.count_roots(p, 1, 3)           # endpoint is a root
        with self.assertRaises(ValueError):
            rt.count_roots(p, 3, 0)           # a >= b
        with self.assertRaises(ValueError):
            rt.count_roots(from_roots([1, 1]), F(1, 2), 5)   # not squarefree

    def test_sign_changes_skips_zeros(self):
        seq = rt.sturm_sequence(from_roots([-1, 1]))
        self.assertGreaterEqual(rt.sign_changes(seq, 0), 0)
        self.assertEqual(rt.sign_changes(seq, -5) - rt.sign_changes(seq, 5), 2)
        with self.assertRaises(ValueError):
            rt.sturm_sequence([F(3)])

    def test_root_bound_contains_every_root(self):
        rng = random.Random(22)
        for _ in range(20):
            rs = rng.sample(range(-9, 10), rng.randint(1, 4))
            p = from_roots(rs)
            B = rt.root_bound(p)
            self.assertTrue(all(-B < r < B for r in rs))
            self.assertNotEqual(rt.evaluate(p, B), 0)
            self.assertNotEqual(rt.evaluate(p, -B), 0)
        with self.assertRaises(ValueError):
            rt.root_bound([F(2)])

    def test_isolate_known_cubic(self):
        p = from_roots([1, 2, 3])
        iv = rt.isolate_roots(p)
        self.assertEqual(len(iv), 3)
        for r, (a, b) in zip([1, 2, 3], iv):
            self.assertLess(a, r)
            self.assertLess(r, b)
        for (a, b) in iv:
            self.assertNotEqual(rt.evaluate(p, a), 0)
            self.assertNotEqual(rt.evaluate(p, b), 0)
        for i in range(len(iv) - 1):
            self.assertLessEqual(iv[i][1], iv[i + 1][0])

    def test_isolate_no_real_roots(self):
        self.assertEqual(rt.isolate_roots([F(1), F(0), F(1)]), [])
        self.assertEqual(rt.isolate_roots([F(1), F(0), F(1)], -10, 10), [])

    def test_isolate_planted_rational_roots(self):
        rng = random.Random(24)
        for _ in range(25):
            k = rng.randint(1, 5)
            rs = sorted(F(rng.randint(-20, 20), rng.choice([1, 2, 3]))
                        for _ in range(k))
            rs = sorted(set(rs))
            p = from_roots(rs)
            iv = rt.isolate_roots(p)
            self.assertEqual(len(iv), len(rs))
            for r, (a, b) in zip(rs, iv):
                self.assertTrue(a < r < b)
            for r in rs:
                hits = [1 for (a, b) in iv if a < r < b]
                self.assertEqual(len(hits), 1)

    def test_isolate_separates_very_close_roots(self):
        # A Mignotte-style polynomial: x^10 - 2*(5x-1)^2 has two real roots
        # about 1e-7 apart near 1/5.  Bisection must still separate them.
        p = [F(0)] * 11
        p[10] = F(1)
        p[0] += F(-2)
        p[1] += F(20)
        p[2] += F(-50)
        self.assertTrue(rt.is_squarefree(p))
        iv = rt.isolate_roots(p)
        near = [(a, b) for a, b in iv if F(1, 6) < a < F(1, 4)]
        self.assertEqual(len(near), 2)
        for a, b in near:
            self.assertEqual(rt.count_roots(p, a, b), 1)
        self.assertLessEqual(near[0][1], near[1][0])
        # planted roots at distance 1/1000 and 2/10**6
        for rs in ([F(0), F(1, 1000), F(1)], [F(1, 10 ** 6), F(-1, 10 ** 6), F(5)]):
            q = from_roots(rs)
            self.assertEqual(len(rt.isolate_roots(q)), len(rs))

    def test_isolate_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            rt.isolate_roots(from_roots([1, 1]))
        with self.assertRaises(ValueError):
            rt.isolate_roots(from_roots([1, 2]), 1, 5)
        with self.assertRaises(ValueError):
            rt.isolate_roots(from_roots([1, 2]), 5, 0)

    def test_refine_sqrt2(self):
        p = [F(-2), F(0), F(1)]
        intervals = rt.isolate_roots(p)
        self.assertEqual(len(intervals), 2)
        iv = intervals[1]                     # the positive root
        self.assertGreaterEqual(iv[0], 0)
        a, b = rt.refine(p, iv, F(1, 10 ** 6))
        self.assertLessEqual(b - a, F(1, 10 ** 6))
        self.assertLess(a * a, 2)
        self.assertGreater(b * b, 2)

    def test_refine_lands_on_exact_rational_root(self):
        p = from_roots([F(1, 2), 3])
        iv = rt.isolate_roots(p)[0]
        a, b = rt.refine(p, iv, F(1, 1000))
        self.assertTrue(a <= F(1, 2) <= b)
        self.assertEqual(rt.refine(p, (F(1, 2), F(1, 2)), F(1, 10)),
                         (F(1, 2), F(1, 2)))
        with self.assertRaises(ValueError):
            rt.refine(p, (F(0), F(0)), F(1, 10))
        with self.assertRaises(ValueError):
            rt.refine(p, (F(0), F(1, 4)), F(1, 10))   # no sign change
        with self.assertRaises(ValueError):
            rt.refine(p, (F(0), F(1)), 0)

    def test_isolation_is_deterministic(self):
        p = from_roots([F(-7, 3), F(1, 5), 4])
        self.assertEqual(rt.isolate_roots(p), rt.isolate_roots(p))
        iv = rt.isolate_roots(p)[0]
        self.assertEqual(rt.refine(p, iv, F(1, 10 ** 4)),
                         rt.refine(p, iv, F(1, 10 ** 4)))

    def test_bridge_to_sparse_poly(self):
        p = sp.mul(sp.from_univariate([-2, 1]), sp.from_univariate([-3, 1]))
        dense = sp.to_univariate(p)
        self.assertEqual(dense, [F(6), F(-5), F(1)])
        self.assertEqual(len(rt.isolate_roots(dense)), 2)


class TestWorkedRecipes(unittest.TestCase):
    """The two recipes printed in gvlib/README.md, executed.

    They are here so the README cannot drift away from working code: if a
    recipe stops verifying, this test fails and the README is wrong.
    """

    def test_sos_certificate_recipe(self):
        # A generator plants a PSD Gram matrix over the monomial basis
        # [1, x, x^2] and publishes only the expanded polynomial.
        basis = [(0,), (1,), (2,)]
        planted = em.matrix([[1, 1, 1], [1, 1, 1], [1, 1, 1]])
        target = sp.gram_form(planted, basis)
        self.assertEqual(sp.to_string(target),
                         "x0^4 + 2*x0^3 + 3*x0^2 + 2*x0 + 1")

        # The whole verifier: symmetric PSD, and it expands to the target.
        def verify(answer_json):
            try:
                G = em.from_json(answer_json, rows=3, cols=3)
            except (TypeError, ValueError) as exc:
                return False, "malformed Gram matrix: %s" % (exc,)
            if not em.is_psd(G):
                return False, "Gram matrix is not positive semidefinite"
            if not sp.equal(sp.gram_form(G, basis), target):
                return False, "Gram form does not expand to the target"
            return True, "ok"

        self.assertEqual(verify(em.to_json(planted)), (True, "ok"))

        # The Gram matrix is not unique: this direction expands to zero, so it
        # slides along the SOS cone.  A verifier must accept the other witness.
        free = em.matrix([[0, 0, 1], [0, -2, 0], [1, 0, 0]])
        self.assertTrue(sp.is_zero(sp.gram_form(free, basis)))
        other = em.add(planted, em.scale(free, F(-1, 4)))
        self.assertEqual(verify(em.to_json(other)), (True, "ok"))
        self.assertNotEqual(other, planted)
        self.assertEqual(em.rank(other), 3)          # genuinely different

        # Same expansion, but off the cone -- rejected for the right reason.
        indefinite = em.add(planted, em.scale(free, F(1, 4)))
        ok, why = verify(em.to_json(indefinite))
        self.assertFalse(ok)
        self.assertIn("semidefinite", why)

        # Wrong expansion -- rejected for the other reason.
        wrong = [row[:] for row in planted]
        wrong[0][0] += F(1)
        ok, why = verify(em.to_json(wrong))
        self.assertFalse(ok)
        self.assertIn("expand", why)
        self.assertFalse(verify("not a matrix")[0])

        # And the certificate really is a weighted sum of squares.
        L, D = em.ldl(planted)
        squares = em.ldl_to_squares(L, D)
        total = {}
        for w, c in squares:
            form = {}
            for i, ci in enumerate(c):
                if ci:
                    form = sp.add(form, sp.scale(sp.from_univariate(
                        [0] * i + [1]), ci))
            total = sp.add(total, sp.scale(sp.power(form, 2), w))
        self.assertTrue(sp.equal(total, target))

    def test_real_root_certificate_recipe(self):
        # x^3 - 4x + 1 has three irrational real roots; the answer is an
        # isolating interval for the LARGEST one, to width 2^-20.
        p = [F(1), F(-4), F(0), F(1)]
        width = F(1, 2 ** 20)
        self.assertTrue(rt.is_squarefree(p))
        bound = rt.root_bound(p)
        intervals = rt.isolate_roots(p)
        self.assertEqual(len(intervals), 3)
        planted = rt.refine(p, intervals[-1], width)

        def verify(a, b):
            if not a < b:
                return False, "endpoints out of order"
            if b - a > width:
                return False, "interval wider than 2^-20"
            if rt.evaluate(p, a) == 0 or rt.evaluate(p, b) == 0:
                return False, "an endpoint is itself a root"
            if rt.count_roots(p, a, b) != 1:
                return False, "not exactly one root in the interval"
            if rt.count_roots(p, b, bound) != 0:
                return False, "a larger root lies above the interval"
            return True, "ok"

        self.assertEqual(verify(*planted), (True, "ok"))
        self.assertEqual(verify(F(-5), F(5)),
                         (False, "interval wider than 2^-20"))
        middle = rt.refine(p, intervals[1], width)
        self.assertEqual(verify(*middle)[0], False)
        self.assertIn("larger root", verify(*middle)[1])
        a, b = planted
        self.assertEqual(verify(b, a)[0], False)
        # the certificate pins a real number no float could name exactly
        self.assertLess(rt.evaluate(p, a) * rt.evaluate(p, b), 0)


class TestSourceAudit(unittest.TestCase):
    """Mechanical checks on the library source itself."""

    def _trees(self):
        for name in LIB_FILES:
            path = os.path.join(HERE, name)
            with open(path, "r") as fh:
                yield name, ast.parse(fh.read(), filename=path)

    def test_no_floating_point_anywhere(self):
        for name, tree in self._trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(
                        node.value, (float, complex)):
                    self.fail("%s:%d has a float literal %r"
                              % (name, node.lineno, node.value))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                        and node.func.id in ("float", "complex", "round"):
                    self.fail("%s:%d calls %s()"
                              % (name, node.lineno, node.func.id))
                if isinstance(node, ast.Attribute) and node.attr in (
                        "sqrt", "isclose", "fsum", "hypot"):
                    self.fail("%s:%d uses %s" % (name, node.lineno, node.attr))

    def test_imports_are_stdlib_and_minimal(self):
        allowed = {"fractions", "math", "re"}
        for name, tree in self._trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertIn(top, allowed,
                                      "%s imports %s" % (name, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue          # relative, inside gvlib
                    top = (node.module or "").split(".")[0]
                    self.assertIn(top, allowed,
                                  "%s imports from %s" % (name, node.module))

    def test_every_public_name_is_documented(self):
        for module in (rat, sp, em, rt):
            self.assertTrue(module.__doc__)
            for name in module.__all__:
                obj = getattr(module, name)
                doc = getattr(obj, "__doc__", None)
                self.assertTrue(doc and doc.strip(),
                                "%s.%s has no docstring" % (module.__name__, name))
        self.assertTrue(gvlib.__doc__)

    def test_package_exports_are_stable(self):
        self.assertEqual(sorted(gvlib.__all__),
                         ["exact_matrices", "rationals", "roots", "sparse_poly"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
