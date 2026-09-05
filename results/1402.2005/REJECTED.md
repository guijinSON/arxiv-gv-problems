# Rejection: [arXiv:1402.2005](https://arxiv.org/abs/1402.2005) — *Extremal families of cubic Thue equations*

## Decision

No generator is shipped. The native single-witness problem clears G and V but fails
H on both tracks. The natural completeness version (find all solutions, or certify
that no further solution exists) additionally fails V under the witness rule.

The decisive source is Theorem 1.2 in Section 1. For every integer parameter `t`, it
does not merely assert existence for

```text
F_3,t(x,y) = x^3 - (t^4-t)x^2 y + (t^5-2t^2)x y^2 + y^3 = 1.
```

It explicitly lists the five integer solutions

```text
(1,0), (0,1), (t,1), (t^4-2t,1),
(1-t^3, t^8-3t^5+3t^2),
```

with only the stated extra solution `(6,-5)` when `t=-1`. Section 2 reiterates that
these displayed pairs already give `N_{F_3,t} >= 5`. Thus the prior triage proposal
“choose an integer pair and construct a cubic form evaluating to one” is generatable
and exactly checkable, but it is not hard for this paper's distribution.

## Step 0 cost comparison

The algorithm producing the certificate is direct evaluation of Theorem 1.2's
displayed polynomial formula. If any solution is accepted, `(1,0)` or `(0,1)` costs
zero arithmetic operations. Even after excluding all solutions with `|y| <= 1`, the
remaining displayed witness can be evaluated with nine exact integer operations:

```text
t2=t*t; t3=t2*t; t5=t3*t2; t8=t5*t3;
x=1-t3; y=t8-3*t5+3*t2.
```

For the measured 150-decimal-digit value `t = 10^149 + 123456789`, chosen so that the
JSON answer is still below the project's 2,000-character cap, the answer occupied
1,646 characters. In seven batches of 20,000 runs under CPython 3.12.3, median
mechanical formula evaluation was `7.21e-6` seconds and median exact substitution was
`1.63e-4` seconds. Exact symbolic expansion reduces the substituted form identically
to `1`; direct integer substitution was also checked for every `t` from -100 through
100.

The compact route is the very same nine-operation formula; it is not shorter than
the mechanical certificate-producing algorithm. The mechanical/compact gap is
therefore `9 operations / 9 operations` (and `0 / 0` if the two universal trivial
solutions are allowed). Increasing `|t|` only increases digit arithmetic and answer
transcription; it does not create a structural search problem. This is calculator
cost, not no-tool compression.

Section 5 says that general cubic Thue equations can also be solved by established
Tzanakis–de Weger/Baker routines in PARI or Magma. Those general routines are not a
basis for Track B here: on this promised parametric family, Theorem 1.2's direct
formula is already a strictly simpler mechanical algorithm. The paper's own proof
likewise reduces remaining `10 <= t <= 576241` cases using continued fractions with
`Q=10^60`, but that work proves completeness; it is unnecessary for producing any of
the displayed witnesses.

The broader prior-triage idea of choosing an arbitrary pair and then fitting an
arbitrary cubic form around it does not rescue the proposal. Such forms are no longer
the parametric family solved by Theorem 1.2, and the paper supplies no distributional
hardness theorem for them with which to support Track A. For Track B, concealing a
random planted pair supplies no compact route at all: the solver's route is just the
general Thue-equation algorithm. That is hidden-instance search, not no-tool
compression of a structural identity from this paper.

## Gate analysis

| Formulation | G | H | V | Result |
|---|---:|---:|---:|---|
| Find any integer solution | pass | fail | pass | Two constant answers are visible from the equation. |
| Find a solution with `|y| > 1` | pass | fail | pass | Theorem 1.2 gives it in nine operations. |
| Find all solutions / prove there are no others | pass | fail | fail | Substitution checks the listed pairs but cannot certify completeness. |

For Track A, H fails because a deterministic constant-length formula solves every
generated instance in the distribution. Worst-case hardness of arbitrary Thue
equations is irrelevant to this promised family.

For Track B, H also fails: the mechanical certificate algorithm and the by-hand
shortcut are identical, with the measured costs above. There is no million-operation
route compressed by an invariant into a short route; there is only direct evaluation
of an already displayed identity.

For the completeness formulation, the paper's argument is not an executable finite
witness supplied by a candidate answer. Sections 2–4 use units in cubic fields,
Matveev bounds, and a Baker–Davenport/Mignotte continued-fraction computation; Section
4 says full details of that computation are available from the authors on request.
A checker that merely substitutes the five pairs has not verified that there is no
sixth pair. Shipping “all solutions” would therefore violate the witness rule.

## Considered transformations

Section 2 notes the paper-licensed equivalence
`F_3,-t(x-t*y,y) = F_4,t(x,y)`. Carrying a listed witness through this disclosed
unimodular change of variables adds only a constant number of integer operations, so
the mechanical and compact routes remain the same length. H still fails.

Hiding an arbitrary `GL_2(Z)` transformation would not repair this honestly. If the
map is supplied, applying its inverse is another short explicit formula. If it is not
supplied, the intended solver has no compact route shorter than recovering an
artificial encoding or running a general form-equivalence/Thue routine. The resulting
difficulty comes from the builder's hidden wrapper, not from the paper's extremal
family, and it does not establish Track A distributional hardness or Track B
compression.

Accordingly this is a Step 0 rejection, before module construction or oracle
hardening. The failed gate is **H on Track A and Track B**; the “find all” fallback
also fails **V**.
