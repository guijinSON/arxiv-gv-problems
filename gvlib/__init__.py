"""gvlib -- exact, standard-library-only math for generator/verifier modules.

Four small modules, all exact, all deterministic, no third-party dependency:

    rationals        coercion, validation and JSON encoding of Fraction scalars
    sparse_poly      multivariate polynomials over Q as dict[exponents] -> Fraction
    exact_matrices   rational matrices: det (Bareiss), rank, solve, Gram, LDL/PSD
    roots            Sturm sequences and real-root isolation over Q

It exists so that a family whose certificate is a polynomial identity, a Gram
matrix or an isolating interval costs a builder about as much as a family whose
certificate is a subset of vertices.  See gvlib/README.md for the JSON answer
conventions and for the standing rule that ``verify()`` must never touch a float.

Nothing here reads a file, prints, or uses ``random``; importing gvlib has no
side effects.
"""

from . import rationals
from . import sparse_poly
from . import exact_matrices
from . import roots

__all__ = ["rationals", "sparse_poly", "exact_matrices", "roots"]
__version__ = "0.1.0"
