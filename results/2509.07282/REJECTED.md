# Rejected: arXiv 2509.07282

Paper: Jeff Shen and Lindsay M. Smith,
[*ALICE: An Interpretable Neural Architecture for Generalization in Substitution
Ciphers*](https://arxiv.org/abs/2509.07282) (2025).

## Decision

No family from this paper met **G, H, and V** simultaneously. The strongest
native candidate passed inverse generation and exact witness verification, and
it had a genuine Track B mechanical/compact cost gap. It nevertheless failed the
mandatory bare oracle loop: at the maximum permitted escalation, Grok 4.6
returned a complete inverse substitution key that `verify` accepted. The
script-owned verdict is `too_easy`, so the rules forbid further hand tuning or
shipping the family.

The experimental module and `llm_loop_transcript.jsonl` are retained as rejection
evidence. There is deliberately no shipping `README.md`, `selftest_report.json`,
or G9 hinted/placebo transcript: STEP 4 failed first and requires stopping.

## What the paper actually defines

Section 1.1 defines a one-to-one monoalphabetic substitution cipher. For a finite
alphabet `Sigma`, the key is a permutation `f` in the symmetric group; plaintext
characters `x_i` produce ciphertext characters `c_i=f(x_i)`. At inference the
solver receives ciphertext, not `f` or the plaintext, and must infer `f^-1` and
decrypt the text. This exact point invalidates the prior-triage suggestion to
show both plaintext and ciphertext: with a known plaintext, every used key entry
is recovered by one linear scan, so the mechanical cost and compact route are
both about `L` character comparisons. There is no Track B compression gap and no
Track A hardness claim.

The paper is empirical, not a complexity result. Its easy regimes are explicit:

- Section 3.2 says ciphertext length strongly controls difficulty. Below about
  30 characters, unicity is a problem; around 75 characters, over 90% of examples
  have at most one ALICE error; around 150 characters, about 95% are error-free.
- Appendix A surveys frequency/dictionary search, generalized Viterbi,
  compression, and beam search. Reported historical runtimes range from hours to
  seconds as those methods improve.
- Appendix H reports that the paper's own 85M-parameter ALICE-Base solver uses a
  single forward pass and processes 5,431 letters/s on one CPU core or 1.2 million
  letters/s on an H100. ALICE-Bijective additionally solves a linear assignment
  problem and directly exposes the inverse permutation (Sections 2.1 and 5).
- Appendix I is the reason Track B was worth testing rather than dismissing:
  the authors record then-current large language models failing short
  cryptograms even while their specialized model solves the task.

These results rule out an honest Track A claim for the generated distribution.
The paper supplies neither an average-case hardness theorem nor a parameter
regime in which its own inference methods cease to work.

## Witness and verifier problem

Ciphertext-only cryptogram solving is not directly an exact witness problem.
Given a candidate key, a checker can test bijectivity and decrypt, but deciding
whether the resulting text is the intended English plaintext requires a language
oracle or hidden ground truth. Reading `inst["answer"]` would violate the task.

The tested family retained the native ciphertext and inverse-permutation answer,
but added a SHA-256 commitment to the planted plaintext. Verification then used
only executable operations on the instance and candidate:

1. require a 26-character permutation of `A` through `Z`;
2. check every published ciphertext-to-plaintext crib;
3. substitute the key into the ciphertext exactly; and
4. compare the decrypted ASCII string's SHA-256 digest with the commitment.

Unused ciphertext letters remain harmless: the verifier accepts every bijective
completion that yields the committed plaintext, not only the planted completion.
The digest is validation metadata and gives the solver no plaintext characters.
This cleared V without replacing the cipher by a graph, SAT instance, or other
surrogate.

## Track B candidate that was tested

The generator sampled a grammatical plaintext and random encryption permutation
first, then derived the ciphertext, inverse key, cribs, and digest. Thus G held by
inverse construction; the generator never deciphered an instance to obtain its
certificate.

Difficulty used two fixed-witness axes:

| rung | hidden inverse entries | text variant | intended effect |
|---|---:|---:|---|
| demo | 5 | long | hand-checkable illustration |
| easy | 14 | long | 12 cribs remain |
| medium | 20 | long | 6 cribs remain |
| hard | 26 | medium | no cribs; less context |
| maximum escalation | 26 | short | no cribs; 44–45 characters |

For fixed text, hiding `n` entries grows the structure-aware certificate language
to exactly `n!`, while the answer remains 26 letters. After `n=26`, shortening the
text follows Section 3.2's measured hard direction. Two independent axes moved,
and neither lengthened the answer.

The intended compact route mirrors Section 5's interpretation: use repeated-word
and repeated-letter patterns, propagate one global bijection, then use ordinary
letter frequencies. At the final rung, scanning, propagating, and checking the
44–45-character text was conservatively counted as 114–116 exact character
operations, below the 300-operation cap. The serialized key is 28 JSON characters
(26 atomic letters, approximately 7 tokens).

## Mechanical cost and local checks

The Track B gap was real enough to test. From Table 3's 12 layers, model dimension
768, and feed-forward dimension 2,048, a standard dense forward-pass count for
the final 44–45-character inputs is about **3.77–3.86 billion
multiply-accumulates**. Appendix H's CPU throughput corresponds to roughly
0.0081–0.0083 seconds per text once the trained ALICE model is available. This is
mechanically easy but impossible to execute by hand; it is why this was Track B,
not Track A.

For an independently executable exact reference, the module also enumerated the
finite generated-text grammar, compared plaintext commitments, and derived a
consistent substitution key. On eight final-rung seeds it solved **8/8**, tested
**3,203,970** candidates in total (maximum **722,639** for one instance), and took
**1.604 seconds** locally. Its bounded-distribution complexity is
`Theta(T * 12^5 * L)`. This is the certificate-producing algorithm disclosed for
the tested distribution; it was never placed among the failing attacks.

Local evidence at the final rung was:

| measurement | result |
|---|---:|
| exact reference solver | 8/8 solved |
| structure-aware random keys | 0/200,000 valid |
| structure-aware language size | `26! = 403291461126605635584000000` |
| valid completions at measured seed | `9! = 362880` |
| ETAOIN frequency/outlier attack | 0/8 |
| first-occurrence ordering | 0/8 |
| greedy three-letter-word-as-`THE` | 0/8 |
| 4,096 random restarts per seed | 0/8 |
| in-context modal-template ansatz | 0/8 |

The `9!` valid completions are all assignments of unused letters and therefore
all represent the same committed decryption. The exact structure-aware success
probability is `9!/26!`, about `9.0e-22`; the zero sampled hits are consistent
with that value but do not estimate such a tiny probability precisely.

## Mandatory oracle result

The bare `scripts/harden.py` run used the required fresh four-vendor pool at
medium reasoning effort. Any verified solve defeats a rung.

| round | rung and parameters | normal solved / attempts | outcome |
|---:|---|---:|---|
| 0 | easy, `n=14, variant=0` | 2/3 | defeated |
| 1 | medium, `n=20, variant=0` | 2/3 | defeated |
| 2 | hard, `n=26, variant=1` | 1/3 | defeated |
| 3 | escalated, `n=26, variant=2` | 1/3 | **defeated** |

At the maximum escalation, an initial Grok call hit the 900-second hard deadline
and was correctly recorded as an API error rather than a model failure. Its
redraw then solved seed `510693196` in 668.94 seconds. The ciphertext was

```text
LHF XMIFL JRWFA DRAWFT LHF TIBLRSL SCLFJCCW.
```

Grok returned

```text
<answer>RSOMCEFHIBGTUJLPVANDWXKQYZ</answer>
```

which exactly decrypted to `THE QUIET BAKER MARKED THE DISTANT NOTEBOOK.` and
passed the digest and permutation checks. This was not a parser accident, an
answer leak, or a lucky uniform guess. The other two final-rung vendors produced
no valid witness, but one valid witness is sufficient under the protocol.

The script-owned metadata records:

```json
{
  "verdict": "too_easy",
  "escalations_used": 3,
  "axes_moved": ["n", "variant"],
  "reason": "escalate() returned None — the family cannot be made harder, and the oracle pool still solves it"
}
```

The mechanical/compact gap is therefore **not** the rejection reason; it is
large, and justified trying Track B. The rejection reason is that a no-tool
oracle actually executed the compact route at the shortest permissible rung.
Making sentences still shorter would increasingly test underdetermination and
the hidden digest rather than language-and-bijection reasoning, and tuning after
the maximum escalation would violate STEP 4.

## Other variants considered

| candidate | failed gate | reason |
|---|---|---|
| Show plaintext and ask for the key (prior triage) | H on A and B | A linear scan produces the key; mechanical and compact costs are both about `L`. |
| Ciphertext only, accept any English-looking decryption | V | Exact validity needs a language oracle and does not identify the planted plaintext. |
| Ciphertext plus hidden expected plaintext in the instance | witness rule | A checker reading it would merely compare with a disguised answer. |
| Ciphertext plus SHA-256 plaintext commitment | **STEP 4** | Exact and native, but the oracle solved every allowed difficulty rung. |
| Ask for ALICE's assignment permutation from public logits | H | Section 2.1 reduces inference-time extraction to a polynomial linear-assignment problem. |
| Turn training/generalization into the answer | G/V | Training discovers weights by optimization, and held-out linguistic accuracy is not a compact exact witness. |

## Final gate outcome

| requirement | result |
|---|---|
| G — generatable | Pass for the tested family: sample plaintext and key first, then encrypt. |
| V — exact witness checking | Pass: bijection, substitution, cribs, and digest are exact. |
| H — Track A | Fail: no distributional hardness theorem, and the paper supplies fast successful solvers. |
| H — Track B | **Fail at STEP 4:** a no-tool oracle returned a verified key at the maximum escalation. |
| Overall | **Rejected.** |

G9 hinted/placebo arms were not run because the stronger prerequisite—the bare
hardening loop—already failed. Fabricating zeroes for those arms or emitting a
passing self-test after `too_easy` would misstate the evidence.
