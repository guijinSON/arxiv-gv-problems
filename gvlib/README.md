# gvlib — exact math for generator/verifier modules

Standard library only. Deterministic. No import-time IO, no printing, no `random`.
59 tests: `python3 gvlib/test_gvlib.py`.

## Why this exists

The corpus collapsed into combinatorics, and the audit found that it did **not**
collapse because non-discrete papers fail the gates. Acceptance is roughly equal
across strata (discrete 56%, geometry 60%, symbolic/algebraic 44%, number theory
43%); of 45 rejections, 24 fail on **H** and *none* cite tooling cost. Papers with
continuous or algebraic content are not rejected — they are never picked up.

One thing that plausibly steers a builder away from them: a graph family needs
`dict` and `set`, and a Gram-matrix or SOS family needs exact linear algebra over
Q that the builder must write, debug and justify inside its own single file
before it can even test whether the family is hard. A shipped module already
hand-rolls Gaussian elimination over `Fraction` (`results/2601.19161/`). This
package is the attempt to delete that tax: the certificate machinery is written
once, audited once, and tested once, so choosing a polynomial certificate costs
about what choosing a subset of vertices costs.

It does not make any family hard, and it is not evidence of diversity. It only
removes a cost.

## What is in it

| module | for |
|---|---|
| `gvlib.rationals` | coercion, validation, JSON encoding of `Fraction` scalars |
| `gvlib.sparse_poly` | multivariate polynomials over Q: `dict[exponent tuple] -> Fraction` |
| `gvlib.exact_matrices` | rational matrices: `det` (Bareiss), `rank`, `solve`, `nullspace`, `gram`, `ldl`, `is_psd` |
| `gvlib.roots` | Sturm chains, exact root counting, isolating intervals, `refine` |

Every public function has a docstring that states what it *guarantees* — read it
before trusting it in a `verify()`. A test asserts that none of them is missing.

## What is deliberately **not** in it

- **No CAS / expression layer.** No expression trees, no simplification, no
  pattern matching, no `Symbol`. An answer that needs a general expression is an
  answer with no bounded `CERTIFICATE_LANGUAGE`, and a verifier that has to
  *simplify* before comparing is a verifier whose correctness nobody can audit.
  Ship a polynomial in a fixed monomial basis instead, and compare exactly.
- **No interval arithmetic.** Zero papers in the 12,167-paper pool carry any
  interval-arithmetic language, so this would be machinery with no customer.
  `roots.refine` returns certified *rational* endpoints from exact sign
  comparisons, which is what a real-number-flavoured certificate actually needs.
- **No polynomial factorisation, Gröbner bases, resultants, or rational-function
  arithmetic.** Cited certificate language in pool metadata: 41 SOS, 16 Gram
  matrix, 7 Nullstellensatz, 3 Positivstellensatz, 1 Farkas, 0 Lyapunov, 0
  symbolic integration, 0 Gosper/Zeilberger, 0 telescoping. The SOS/Gram/Farkas
  end is served by `sparse_poly` + `exact_matrices`; the rest is not, and adding
  a Gröbner engine to serve seven papers would be more unaudited code than the
  whole package.
- **No algebraic-number arithmetic.** `roots` lets you *name* a real algebraic
  number exactly (squarefree polynomial + isolating interval) and check a claim
  about it. It will not add two of them.

If a family needs one of these, write it in the module and say so in the README
caveats — do not quietly widen this package.

## Importing it from a generated module

Modules are loaded by file path from three different working directories
(`scripts/harden.py` runs from `results/<id>/`, `submit.sh` and `emit.sh` from
the repo root), so `import gvlib` alone is not enough. Put this at the top of
`results/<id>/gen_<id>.py`:

```python
import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gvlib import exact_matrices as em, rationals as rat, roots as rt, sparse_poly as sp
```

This is verified to work when the module is loaded from `results/<id>/`, from the
repo root, and when run directly.

**Know what you are trading.** A module that imports `gvlib` is still standard
library only, but it is no longer a single self-contained file: it runs inside
this repo, not next to it. The emitted `artifacts/<id>.jsonl` rows are unaffected
— they are data. If a family must stay standalone, vendor the twenty lines it
needs and say so; do not half-import.

## JSON-native answer conventions

Follow these everywhere an answer, an instance field, or a `canonical_key` input
crosses a JSON boundary. They exist so that two families do not invent two
different encodings of the same rational.

| object | JSON form | example |
|---|---|---|
| rational | `[num, den]`, lowest terms, `den > 0` | `-3/4` → `[-3, 4]` |
| vector of rationals | list of pairs — **never** a flat list | `[[1,2],[0,1]]` |
| matrix | list of rows of pairs | `[[[1,1],[0,1]],[[0,1],[1,1]]]` |
| monomial | exponent list, one entry per variable, 0-indexed | `x0^2*x1` → `[2,1]` |
| polynomial | `{"nvars": n, "terms": [[exponents, [num, den]], ...]}` | see below |

```python
>>> sp.to_json(sp.power(sp.add(sp.var(0, 2), sp.var(1, 2)), 2))
{'nvars': 2, 'terms': [[[0, 2], [1, 1]], [[1, 1], [2, 1]], [[2, 0], [1, 1]]]}
```

Encoders are canonical (terms sorted by graded lex, rationals in lowest terms),
so the same polynomial always serialises the same way — safe inside a
`canonical_key`. Decoders are strict and total: `from_json` raises on anything
malformed and never returns an approximation, `rationals.parse_rational` returns
`None` on garbage instead of raising. `sparse_poly.from_json` also accepts a bare
list of terms, so a solver that omits the `nvars` wrapper is still gradeable —
tolerant in, canonical out. Pass the expected shape (`nvars=`, `rows=`, `cols=`)
when reading solver output so a wrong-shape answer becomes a clean rejection
instead of an exception three calls later.

`to_string` renders a polynomial for `render()`; there is no parser for that
format on purpose. If a solver must *return* a polynomial, ask for the JSON form
so the output contract has exactly one shape to grade.

## `verify()` must never depend on floating point

Not "should avoid". **Never.** A grader that compares `abs(a - b) < 1e-9` is not
exact verification — it is a tolerance nobody chose, applied to numbers nobody
bounded, and it silently converts a hardness claim into a rounding claim. It
fails in both directions: a correct witness with large intermediate values is
rejected, and a wrong witness that lands inside the tolerance is accepted. It is
also non-reproducible across platforms, which makes a shipped artifact
unauditable.

So, in a generated module:

- never call `float()`, never write a float literal, never use `math.sqrt`,
  `math.isclose`, `numpy`, or `**0.5`;
- compare with `==` on `Fraction`, or with `sparse_poly.is_zero(sub(a, b))`;
- if a quantity is genuinely irrational, do not return it — return a certificate
  *about* it (an isolating interval, a Gram matrix, a minimal polynomial);
- bound the coefficients your `CERTIFICATE_LANGUAGE` declares and enforce the
  bound with `rationals.within_bits`, or `search_space` is fiction.

gvlib enforces this on itself: `Q()` raises `TypeError` on a `float` rather than
accepting `0.1` as `3602879701896397/36028797018963968`, and a test parses the
library's own AST and fails on any float literal, any `float()`/`complex()`/
`round()` call, and any import outside `{fractions, math, re}`. Consider copying
that AST test into a module's `selftest()`.

## Recipe 1 — an SOS / Gram certificate

Both recipes below are executed by `test_gvlib.py` (`TestWorkedRecipes`), so they
cannot drift from working code.

The generator plants a PSD Gram matrix over a fixed monomial basis and publishes
only the expanded polynomial. The solver must produce **some** PSD Gram matrix
that expands to it.

```python
basis = [(0,), (1,), (2,)]                       # the monomials 1, x, x^2
planted = em.matrix([[1, 1, 1], [1, 1, 1], [1, 1, 1]])
target = sp.gram_form(planted, basis)            # x^4 + 2x^3 + 3x^2 + 2x + 1

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
```

That is the entire verifier, and it satisfies the interface rule that `verify`
accepts any valid witness rather than only `inst["answer"]`: the Gram matrix is
**not** unique. `free = [[0,0,1],[0,-2,0],[1,0,0]]` expands to the zero
polynomial, so `planted + λ·free` has the same expansion for every λ; at
λ = -1/4 it is a different rank-3 PSD matrix that `verify` accepts, and at
λ = +1/4 it is indefinite and `verify` rejects it *for the PSD reason while the
expansion still matches*. That second case is the one worth having a test for.

To exhibit the actual sum of squares, `em.ldl_to_squares(*em.ldl(G))` returns
`(weight, linear form)` pairs with

    x^T G x  ==  sum(w * (c · x)^2)

and every weight a positive rational. The weights stay outside the squares
because a rational PSD matrix need not have rational square roots; a weighted
rational SOS is the honest exact certificate.

## Recipe 2 — a real-root certificate

A continuous-flavoured answer with a finite exact certificate: name a real
algebraic number by an isolating interval with rational endpoints.

```python
p = [F(1), F(-4), F(0), F(1)]                    # x^3 - 4x + 1, ascending
width = F(1, 2 ** 20)
bound = rt.root_bound(p)                         # all real roots inside (-5, 5)

def verify(a, b):
    if not a < b:                       return False, "endpoints out of order"
    if b - a > width:                   return False, "interval wider than 2^-20"
    if rt.evaluate(p, a) == 0 or rt.evaluate(p, b) == 0:
        return False, "an endpoint is itself a root"
    if rt.count_roots(p, a, b) != 1:    return False, "not exactly one root in the interval"
    if rt.count_roots(p, b, bound) != 0:
        return False, "a larger root lies above the interval"
    return True, "ok"
```

`rt.isolate_roots(p)` then `rt.refine(p, interval, width)` produces the planted
answer. Every comparison is a comparison of rationals; the endpoints are
certified bounds, not estimates. Note the last check — without it, an interval
around the *middle* root passes everything else.

## Guarantees and traps

- **All leading principal minors ≥ 0 does NOT mean positive semidefinite.**
  `[[0,0],[0,-1]]` has leading principal minors 0 and 0 and is not PSD. Sylvester's
  criterion (all *> 0*) is correct for positive *definiteness* only. Deciding PSD
  from minors needs *every* principal minor, which is exponential. Use
  `em.is_psd`, which is LDL^T with the zero-pivot rule: exact, complete, and
  linear-algebra cheap. `em.leading_principal_minors` exists but carries this
  warning in its own docstring.
- **`is_psd` treats symmetry as part of the definition** and returns `False`
  (never raises) for a non-symmetric or non-square argument, so `verify()` can
  call it on whatever a solver produced without a guard. `em.ldl` *does* raise on
  a non-symmetric input — that one is a programming error, not a solver error.
- **Sturm needs a squarefree polynomial.** `count_roots` and `isolate_roots`
  check it and raise rather than silently miscounting; `rt.squarefree_part`
  gives you one with the same distinct real roots. They also refuse an interval
  endpoint that is itself a root.
- **`count_roots(p, a, b)` counts the *open* interval** `(a, b)`. Isolating
  intervals may share an endpoint (`(-3,0)` and `(0,3)` for `x^2-2`); the roots
  are strictly inside.
- **`refine` may return a degenerate `(r, r)`** when the root is exactly the
  rational `r`. Handle it, or state in `render()` that the answer's interval must
  have positive width.
- **`solve` returns a particular solution** with free variables set to 0, and
  `None` for an inconsistent system. Use `nullspace` for the rest of the affine
  space; do not read a unique-solution claim into it.
- **`degree` returns -1 for the zero polynomial**, in both `sparse_poly` and
  `roots`, so `degree(p) < d` reads correctly for every d ≥ 0.
- **`sparse_poly.power` and `sparse_poly.evaluate`**, not `pow` and `eval`:
  shadowing builtins — one of them `eval` — inside a verifier is not worth the
  two saved characters.
- **Cost is schoolbook.** `mul` is O(|p|·|q|), `matmul` is O(mnp), `det` is
  Bareiss. Certificates here are small and the arithmetic must stay auditable; if
  a family needs asymptotically better, it probably needs a different certificate.

## Testing

```
$ python3 gvlib/test_gvlib.py
Ran 59 tests in 0.071s
OK
```

The suite is deterministic (fixed seeds) and includes cross-checks against
independent implementations written inside the test file — a permutation-expansion
determinant against Bareiss, brute-force root counting against Sturm, direct
expansion against `gram_form` — so a shared bug shows up as a disagreement rather
than as two functions agreeing on the same mistake. Add to it before adding to
the library.
