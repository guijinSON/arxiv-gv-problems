# Parked papers — rejected, but the rejection is suspect

These are NOT free papers and NOT accepted problems. Each was rejected under a
harness or prompt defect that has since been fixed, so the rejection does not
mean what it says. They are recorded here rather than silently re-queued,
because re-running them competes with new papers for build lanes.

To re-open one: delete `results/<id>/REJECTED.md`, set `claims/<id>.json` status
back to `in_progress`, and launch it.

## Rejected under the pre-fix `harden.py` (no cap_bound detection)

`scripts/harden.py` only learned to DETECT cap_bound on 2026-09-05. Before that
it took `escalate() -> None` at face value, so a ladder stopped by the 256-atom
answer cap was recorded as `too_easy` and the paper was given up.

| paper | evidence | signal |
|---|---|---|
| 2601.05272 | ladder climbed n=64,72,80,84 and stopped at 249 atoms against a 256-atom cap; `.meta.json` records the bare pre-fix `too_easy` | answer_cap + single_axis |
| 2210.14608 | 240 atoms / 1092 chars; ladder moves `['n']` only | answer_cap + single_axis |
| 2410.07666 | 240 atoms / 1210 chars; ladder moves `['degree','n']` | answer_cap |
| 1011.6021  | 12 atoms; ladder moves `['n']` only | single_axis |
| 2201.13153 | 6 atoms; ladder moves `['n']` only | single_axis |
| 2605.11545 | 1 atom; ladder moves `['n']` only | single_axis |

The last three are the weaker signal: the answers are tiny, so the cap was never
the binding constraint. What they show is that the family was never explored —
one dial was turned and the paper was dropped. They need a second axis, not a
shorter witness.

Found by replaying the new detector over every rejection that still had a module
on disk: 5 of 10 would now be parked instead of rejected. `2601.05272` had its
module deleted by the builder, so it is listed from the audit record instead.

### Second batch, found the same way (2026-09-05, post-fix rerun)

These were rejected minutes before the fixed `harden.py` was deployed, so they ran
under the old detector too.

| paper | evidence | signal |
|---|---|---|
| 2411.12911 | *On large Sidon sets*. `.meta.json` records the bare pre-fix `too_easy` from `escalate() -> None` after 3 escalations. The rejection note states the builder implemented and measured BOTH the mechanical and compact costs and found "the large gap made this a plausible Track B candidate" — it died on the escalation ceiling, not on the analysis | unmeasurable: module deleted |

`2411.12911` and `2601.05272` both deleted their modules, so neither can be
replayed. They are parked on the strength of the recorded verdict and the note.
`prompts/codex_task.md` now tells builders to keep a rejected module as
`rejected_gen_<id>.py` precisely so this stops happening.

Checked and NOT parked from the same batch: `1608.00931` replays as genuinely not
cap-bound (ladder moves `['n','payload_bits']`, `escalate()` returns a dict, and its
harden verdict was `hardened`) — it was rejected on the G9(b) polarity-flipped gate,
which is a validity failure and stands. `1602.08620` (the paper's hard distribution
is UNSATISFIABLE formulas, so there is no assignment to plant), `2306.09948` (the
paper's construction IS the compact route — one pass over the output array, no gap)
and `2211.12582` are correct rejections.

## Rejected on reviewer-disputed grounds

| paper | rejection | why it is disputed |
|---|---|---|
| 2602.19989 | fails G9(b) hinted-oracle on Track B | a reviewer supplied a concrete family sketch for it; the note also argues Track A is unavailable because "an efficient exact recovery algorithm" exists, which is not by itself a reason (that is what Track B is for) |

## Checked and left rejected

| paper | rejection | verdict on the rejection |
|---|---|---|
| 1301.4723 | Step 0, G fails | CORRECT. The paper's Section 5 replaces duplicate S-box images "in such a way" that DU and NL are not compromised, and gives no algorithm and no theorem making an arbitrary replacement work. There is no answer-first construction to generate from. |
