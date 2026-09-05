# Planar-function equivalence certificates (arXiv:2605.26263)

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | polynomial identity |
| certificate form | exact symbolic |
| intuition | change of variables |
| domain essentiality | native |
| reduction | none |

This is a native finite-field problem based on [Guardieiro–Marques–Quoos–Tizziotti,
*On planar functions over* $\mathbb F_{q^3}$](https://arxiv.org/abs/2605.26263).
The solver receives quadratic Dembowski–Ostrom polynomials on an explicitly
represented field $\mathbb F_{p^3}$.  It must identify the one polynomial that is
an invertible multiplicative change of variables of the paper's Theorem 3.3
family and return the change-of-variable certificate `(index, v, r)`.  The checker
performs exact field arithmetic, checks all five coefficient identities, checks
$3r^2-3r+1\ne0$, and executes the Dickson-determinant factor identity.  It never
reads the planted answer.

## Why the construction and certificate are trustworthy

For an admissible base-field value $r$, Theorem 3.3 gives

\[
g_r(X)=X^2+2(1-r)X^{p+1}+2rX^{p^2+1}+(1-r)X^{2p}+rX^{2p^2}.
\]

The generator samples nonzero $u,v$ first and plants $u g_r(vX)$, carrying
`(v,r)` into the answer.  Every other row starts from an independent draw of the
same transformed family; it then samples nonzero $a,h$ and changes one
coefficient by the unique exact field value that forces
$f(X+a)-f(X)-f(a)$ to send $h$ to zero.  Thus both sides are known by
construction: the chosen row has a planarity certificate, and each decoy has a
derivative-collision certificate.  No instance is solved during generation.

There is a harmless normalization error in the paper's displayed proof.  Direct
substitution of Theorem 3.3 into Proposition 2.1 gives
$16\omega(z+y)(z+x)(y+x)$, whereas the proof displays scalar 4.  Corollary 2.6's
system supplies one factor 4 and Proposition 2.1 supplies the other.  Since the
characteristic is odd, the omitted scalar is nonzero and the planarity conclusion
is unchanged.  The module checks the corrected identity; a separate direct
enumeration over small fields also matched it.

## Why this is Track B

The generated distribution has an $O(m\log p)$ invariant-and-Hilbert-90
recovery algorithm, so Track A would be false.  The domain-standard mechanical
route from Proposition 2.1 instead tests $p^2+p+1$ projective directions per
surviving candidate and a $3\times3$ Dickson determinant at each one:
$O(mp^2)$ for $m$ rows.  At the
provisional shipping setting $p=307,m=6$, the measured run tested 96,008
directions and used at least 5,664,472 scalar additions/multiplications (0.30
seconds on the original run and 0.51 seconds on the final audit).  This is easy
for code and out of reach by hand.

The compressed route is to notice

\[
c_1^2c_4+c_2^2c_3=4c_0c_3c_4.
\]

It scans the six rows, recovers $r=c_2^2/(4c_0c_4)$ and
$t=2c_3/c_1=v^{p-1}$, then applies the three-term cyclic Hilbert-90 projector.
Counting the binary powering used for inversions and Frobenius maps, the measured
bound is 180 exact field multiplications/additions; the norm-one identity removes
two generic inversions from the Hilbert--90 projector.  This is the
structure the task tests; a CAS or the bundled reference algorithm is expected
to solve every instance.

## Worked demo (`n=5, candidates=4, seed=7`)

Here $F=\mathbb F_5[T]/(T^3+T+1)$ and `[a0,a1,a2]` means
$a_0+a_1T+a_2T^2$.  Each row lists `(c0,c1,c2,c3,c4)` for
$c_0X^2+c_1X^6+c_2X^{26}+c_3X^{10}+c_4X^{50}$:

```text
0: [3,1,4] [0,4,2] [3,1,3] [3,3,3] [0,4,3]
1: [4,1,3] [2,3,3] [1,3,2] [2,0,2] [2,3,0]
2: [0,4,0] [3,0,2] [1,0,1] [4,1,2] [1,2,3]
3: [1,0,4] [1,4,0] [1,4,3] [0,4,4] [1,0,0]
```

The required conditions are the four displayed coefficient identities in
`render()`, with $t=v^4$, $s=t^6$, and nonzero
$\omega=3r^2-3r+1$.  A valid output is:

```json
{"index":2,"v":[1,3,0],"r":3}
```

`verify(inst, answer)` returns `(True, "ok")`.  Changing `r` to 0 returns
`(False, "r must be distinct from 0 and 1")`.  A person can solve this demo on
paper by checking the four row invariants and doing arithmetic in the 125-element
field; it is intentionally illustrative rather than hard.

## Difficulty presets

| preset | lower bound for prime `p` | rows | witness atoms | status |
|---|---:|---:|---:|---|
| demo | 5 | 4 | 5 | hand-scale example |
| easy | 149 | 6 | 5 | hardening starts here |
| medium | 211 | 6 | 5 | available escalation |
| hard | 307 | 6 | 5 | provisional local shipping rung |

`make_instance` uses the first odd prime at least `n`.  Further escalation raises
the field size while keeping six rows and the five-atom answer fixed; it returns
`cap_bound` before binary-power arithmetic would exceed G9(c)'s 300-operation cap.

## Gate measurements

The machine-readable values are in `selftest_report.json`; these are the executed
local checks at the provisional `hard` rung.

| gate | result | measurement |
|---|---|---|
| G1 planted verifies | pass | 12/12 preset/seed checks |
| G2 corruptions | pass | 5/5 rejected with 5 distinct reasons |
| G3 round trip | pass | tagged JSON amid prose; garbage returns `None` |
| G4 guessing | pass | 0/200,000; exact density $5.8172\times10^{-9}$ |
| G5 density/baseline | pass | 306 / 52,602,815,556; 96,008 directions |
| G6 adversaries | pass | four attacks × 8 seeds, 0 successes; reference solves |
| G7 scaling | pass | $p:307\to617$, space $5.26\times10^{10}\to8.67\times10^{11}$ |
| G8 canonical key | pass | 100 invariance/carried-witness checks; 20/20 distinct |
| G9(c) caps | pass | 36 chars, 9 tokens, 5 atoms; 180 operations |

## Oracle loop and G9 diagnostic

The required `scripts/harden.py` calls are currently pending because OpenRouter
returned HTTP 403 `Key limit exceeded (total limit)` for every vendor redraw.
Those API errors are not counted as model failures.  No hardness result has been
invented from the outage.

| bare preset | seed | model | scored | reason |
|---|---:|---|---|---|
| easy | 600703194 | Gemini 3.1 Pro Preview | no | HTTP 403 key limit |
| easy | 377133067 | Claude Sonnet 5 | no | HTTP 403 key limit |
| easy | 1185498182 | Gemini 3.1 Pro Preview | no | HTTP 403 key limit |
| easy | 1330560325 | Claude Sonnet 5 | no | HTTP 403 key limit |

The script-owned bare transcript and both G9 scratch transcripts are retained;
each has four error records and zero scored attempts.  They must be overwritten
by successful harness runs once quota is restored.

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 0 | API quota blocked before a scored call |
| structural hint | 0 / 0 | not run |
| placebo hint | 0 / 0 | not run |

The structural hint names only the existence and shape of the homogeneous
coefficient invariant; it does not give the formula or chain a solution method.
Hinted-minus-placebo is undefined until both script-owned arms run.  The serialized
answer is under 50 characters, 5 atomic elements, and at most 10 tokens; the compact
route is bounded by 180 exact field operations.

## Use

```python
from gen_2605_26263 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
answer = parse_answer('<answer>{"index":2,"v":[1,3,0],"r":3}</answer>')
assert verify(inst, answer) == (True, "ok")
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 2605.26263 20
```

## Caveats

- This benchmarks no-tool recognition, not cryptographic or asymptotic hardness.
  A finite-field package makes it easy, as Track B explicitly records.
- The guess density is for the declared prior: a uniform row, a uniform nonzero
  `v`, and a uniform admissible `r`.  It does not model a solver that has found
  part of the coefficient invariant.
- Tested attacks are coordinate-energy outlier selection, first-row greedy,
  256 well-formed random certificates, and the base-field-twist ansatz.  No
  Gröbner-basis package was available; exact Dickson enumeration is the measured
  domain reference instead.
- `canonical_key` quotients row order, Frobenius, and independent nonzero
  input/output scalings of each row using three exact row invariants.  It does not solve arbitrary
  $\mathrm{GL}_3(\mathbb F_p)$ basis equivalence; that stronger isomorphism problem
  is deliberately listed here rather than hidden behind a hash of the rendering.
- The module is standard-library-only in its finite-field implementation; `gvlib`
  is imported when present but is not required.
