# Rejected at Step 0: arXiv 2312.02799

Paper: Nico Brown et al., [*Conway's Game of Life is
Omniperiodic*](https://arxiv.org/abs/2312.02799) (2023).

## Decision

No self-contained family from this paper clears **G + H + V** under either
hardness track. The native witness—a finite Life oscillator—is generatable and
exactly verifiable, but the paper's scalable distribution fails **H on Track A**
and **H on Track B**. This is not a rejection merely because an algorithm exists:
the mechanical and compact costs are measured below and are essentially the same.

Implementation stopped before Step 1, as required after a Step-0 failure. No
generator, self-test report, README, or oracle transcripts were fabricated.

## What the paper actually says

Section 1 defines Conway's Life on the infinite square grid with the B3/S23 rule.
An oscillator is a finite pattern that returns to its starting configuration; its
period is its least positive return time. The paper is a constructive history and
catalogue, not a reconfiguration or automata-decision paper. The prior-triage label
"reconfiguration / automata decision" is therefore not supported by the full text.

The relevant easy regimes are unusually explicit:

- At the start of Section 2, infinite oscillators are excluded because evenly
  spaced glider streams give every period at least 14, while all smaller periods
  were already known.
- Section 2.3 says direct cell-by-cell depth-first search is effective mainly for
  low periods; `lifesrc` and `dr` enforce the Life rule forward and backward and
  prune inconsistent branches.
- Section 2.4 gives the composition identity needed for trivial oscillators:
  placing noninteracting period-`n` and period-`m` oscillators together produces
  period `lcm(n,m)`.
- Section 2.5.2 proves the scalable finite construction. Four Snarks form a
  diagonal rectangular glider track. If its side lengths are `n,m > 13`, one
  circuit takes `8(n+m+1)` generations; eight evenly spaced gliders therefore
  produce period `p=n+m+1`. The proof chooses
  `n=floor((p-1)/2)` and `m=ceil((p-1)/2)`, constructing every `p >= 43`.
- The Appendix supplies RLE patterns for the remaining individual periods. In
  particular, the final period-19 and period-41 examples are catalogue entries,
  not outputs of a parameterized hard search problem.
- Sections 2.2, 2.3, and 2.6 describe how discoveries were made: soup censuses,
  constrained depth-first cell search, brute-force catalyst placement, and
  just-in-time catalyst search. Section 2.6 explicitly says a catalyst-search hit
  is a roll of the dice and cannot request a period in advance. Section 2.7 notes
  that bounded oscillator existence can be encoded for a SAT solver and that this
  is currently effective only at fairly low periods. None of these sections proves
  distributional hardness for instances manufactured by the proposed generator.

Thus the answer to the Step-0 certificate question is: for `p >= 43`, the
certificate is produced by the displayed Snark-loop formula; below 43, it is read
from the finite RLE gallery. Verification by exact Life evolution is valid, but it
does not make certificate production hard.

## Candidate families and their failure

| native proposed task | certificate producer | outcome |
|---|---|---|
| Given `p >= 43`, return a finite oscillator of least period `p` | Section 2.5.2's four-Snark/eight-glider placement | G and V pass; Track A fails because this exact distribution has an explicit constructor. |
| Given a gallery period below 43, return an oscillator | Appendix RLE lookup | Finite classification-table lookup, not an unlimited hard family. |
| Place known noninteracting oscillators and return the combined pattern/period | Section 2.4's LCM identity | The certificate and period are obtained by the same short composition used to build the instance. |
| Given a generated Snark loop, recover its period | Read the four gadget placements and apply `p=n+m+1` | The strongest algorithm for this generated distribution is the same short template recognizer; generic cycle simulation is not an honest baseline. |
| Hide a phase or initial pattern of a known oscillator | Evolve or invert the already held catalogue pattern | The hiding/recovery puzzle is not studied or reduced to in the paper, and translations, rotations, reflections, or phase shifts of one oscillator are canonically the same object. |
| Plant a pattern inside decoys or partial-cell clues | The generator's hidden planted pattern | This creates a new completion/CSP distribution. The paper gives no average-case theorem for it, and the masking reduction is benchmark convenience rather than paper-licensed mathematics. |

Any claimed negative or optimal answer would be worse: the paper supplies neither a
bounded refutation system for nonexistence nor an optimum certificate. Its theorem
is existence by explicit construction.

## Mechanical cost versus compact route

I benchmarked the scalable construction rather than inferring its cost from the
size of the Life state space. The probe used the paper's published Snark RLE and
period-43 loop RLE. Decomposing the latter into four oriented copies of the former
shows the fixed gadget structure directly. For the infinite subfamily
`p = 43 (mod 4)`, increasing the spacing of the three glider phases around each
Snark gives the paper's loop at arbitrary scale; exact Life simulation confirmed
the resulting periods 43, 47, 51, 55, 59, 63, 67, 71, and 75.

At a hypothetical shipping value `p=1,000,003`, the construction has:

| measurement | value |
|---|---:|
| live cells in the certificate | 236 |
| fixed-template coordinate transforms | 256 (`4 * 64`) |
| bounding box | `1,000,025` by `1,000,025` |
| properly gap-compressed RLE length | 935 characters |
| median Python construction time | 0.000100136 seconds |
| maximum measured construction time | 0.000127731 seconds |

Timing is the per-construction result from twenty batches of 1,000 constructions.
The large empty distances cost only a few decimal digits in RLE; they do not make
the constructor expensive.

For the **full oscillator witness**, the compact route is not shorter than this
mechanical route. Both compute the two side lengths, place the same four fixed
reflector templates and eight glider phases, and serialize the same 236 live cells.
The operation ratio is effectively 1:1, and the mechanical route is only about 256
coordinate transforms—not the million-operation computation that Track B is meant
to compress. The output happens to fit G9(c), but enlarging `p` grows only empty
spacing and decimal coordinates; it never grows the work being compressed.

For the **period-recognition variant**, naive exact cycle detection would indeed
cost `Theta(p * C)` local updates for `C` active cells. That is not the strongest
algorithm on the generated distribution. Matching the four fixed Snark templates
and reading their displacement takes `Theta(C)` exact comparisons, after which the
same displayed equation `p=n+m+1` gives the answer. A self-contained statement that
exposes the gadget representation makes this a few arithmetic operations and an
obvious by-hand attack. A raw-RLE statement merely replaces the short insight with
decoding and fixed-catalogue template matching; its compact route and its
distribution-specific mechanical algorithm again perform the same work. Reporting
generic Life simulation as the Track-B `reference_algorithm` would conceal this
stronger algorithm and manufacture a false compression gap.

## Why neither hardness track applies

### Track A — structural hardness

Track A fails. The Section 2.5.2 theorem supplies an explicit certificate-producing
algorithm for every scalable instance in the natural `p >= 43` regime. Section 2.4
does the same for composed instances, and the Appendix handles the finite remainder.
The very large historical soup and catalyst searches concern discovery of smaller or
novel mechanisms; they are not required to solve an instance sampled from the
explicit Snark-loop distribution. No theorem in the paper establishes hardness for
a planted, masked, or phase-hidden distribution.

### Track B — no-tool compression

Track B also fails for the natural search task. The mechanical producer and the
compact route are the same 256-transform construction, with a measured wall time of
about 0.1 milliseconds even at period 1,000,003. There is no substantial calculation
being replaced by an invariant.

Changing the question to period recognition creates an apparent gap only if the
generic simulator is deliberately chosen over the stronger generated-distribution
recognizer. With the paper's gadget coordinates visible, the obvious geometric
ansatz succeeds. With those coordinates hidden behind raw RLE or decoys, the alleged
compact route must do the same template search as the recognizer, or rely on memorized
Snark data not derivable from the self-contained prompt. Neither version supplies
four honest failing in-context attacks while retaining a short executable insight.

## Gate diagnosis

| requirement | result |
|---|---|
| G — known certificate by construction | **Passable.** Use the Section 2.5.2 Snark-loop theorem, Section 2.4 composition, or an Appendix RLE. |
| V — exact witness verification | **Passable.** Parse the finite live-cell set, evolve B3/S23 exactly, require return at `p`, and reject returns at `p/q` for every prime divisor `q` of `p`. |
| H — Track A | **Fail.** The target distribution has the explicit constructor above; historical search cost is irrelevant to generated instances. |
| H — Track B | **Fail.** Mechanical and compact certificate production both use the same roughly 256 fixed-template transforms; period recognition has an equally short distribution-specific recognizer. |

The obstruction is not the answer cap and is therefore not `cap_bound`. It is the
absence of a defensible hardness claim for a generated distribution that remains the
paper's own problem. A future benchmark could use Life predecessor or partial-pattern
completion only with a source that proves a suitable reduction or hard parameter
regime for that task; this paper does not.
