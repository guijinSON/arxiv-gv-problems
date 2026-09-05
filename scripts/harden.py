#!/usr/bin/env python3
"""The LLM hardening loop.  Usage: python3 scripts/harden.py <path to gen_*.py>

This file, not the builder, owns the loop.  The builder writes gen_<id>.py and
runs this; everything about which model is asked, with which seed, and when a
family is declared too easy is decided here.  That is deliberate: a builder that
reports its own hardening result has an obvious incentive not to report a
failure, and a transcript whose schema is chosen per run cannot be validated.

Requires OPENROUTER_API_KEY.  The oracle pool spans four vendors, so a single
OpenAI key is not enough.  Standard library only.
"""

import importlib.util
import json
import os
import random
import sys
import threading
import time
import ssl
import urllib.error
import urllib.request

# --- configuration ----------------------------------------------------------
# The oracle pool.  Four vendors at the same price tier as the model this
# replaced (openai/gpt-5.6-terra, $2/$12 per M tokens).  A model is drawn afresh
# for every single call: a family that only defeats one model's blind spots is
# not hard, it is overfitted to.
#
# openai/gpt-5.6-sol is deliberately absent — it is the builder model, and a
# family checked against its own author proves nothing.
# Two-model pool as of 2026-09-05. The property that matters is that no single
# vendor's blind spot can carry a family through, and two vendors still give that.
# ATTEMPTS_PER_PRESET stays 3, so a level is tried three times; with two models one
# is drawn twice, on a DIFFERENT instance seed each time.
DEFAULT_POOL = [
    "openai/gpt-5.6-terra",
    "google/gemini-3.8-flash",
]
ORACLE_POOL = [m.strip() for m in os.environ.get(
    "ORACLE_POOL", ",".join(DEFAULT_POOL)).split(",") if m.strip()]

ORACLE_EFFORT = os.environ.get("ORACLE_EFFORT", "medium")
ATTEMPTS_PER_PRESET = 3      # distinct models per difficulty level
# Raises of difficulty before the family is given up on.  This was 3, and 7 of the
# 13 too_easy verdicts on disk came from EXHAUSTING IT rather than from the family
# running out of hardness: 1612.03280 stopped at n=149 with escalate() still willing
# to climb to 237 before it would have said cap_bound.  A budget is not a property of
# the paper, so hitting it is now reported as `budget_bound`, not `too_easy` -- see
# the end of main().  The budget still exists because each level costs a full pool
# sweep; it is env-overridable so a park can be re-run with a bigger one.
MAX_ESCALATIONS = int(os.environ.get("ORACLE_MAX_ESCALATIONS", "6"))
MAX_ERROR_RETRIES = 3        # per attempt; API errors do not count as attempts
MAX_TOKENS = int(os.environ.get("ORACLE_MAX_TOKENS", "32000"))
# Reasoning tokens are billed against max_tokens on some vendors, so a budget
# sized for the answer alone comes back HTTP 200 with an empty body — observed
# live at 16000 against claude-sonnet-5 on a 2030-character statement.
REQUEST_TIMEOUT = 900
# urlopen(timeout=) is a per-socket-operation timeout, NOT a total deadline: a
# provider that trickles bytes (or holds a streaming connection open) resets it on
# every read, so a single call can hang indefinitely.  Observed live -- one call
# sat open 44 minutes against a 900s "timeout" and blocked the paper for 74.  The
# request therefore runs on a worker thread under a hard wall-clock deadline.
TOTAL_DEADLINE = int(os.environ.get("ORACLE_TOTAL_DEADLINE", str(REQUEST_TIMEOUT)))

# The published answer cap (prompts/codex_task.md): <= 2000 chars and <= 256 atoms.
ANSWER_CHAR_CAP  = 2000
ANSWER_ATOM_CAP  = 256
# How close to the cap counts as "the cap is what stopped you". A ladder that has
# already consumed most of the budget had nowhere left to go along the axis it was
# using, whatever escalate() says about the mathematics.
CAP_NEAR_FRACTION = 0.6


def _answer_size(mod, params):
    """(atoms, chars) of the serialised planted answer at these parameters.

    Returns (None, None) if it cannot be measured -- never raises, because this is
    diagnostic and must not be able to fail a run.
    """
    try:
        inst = mod.make_instance(seed=98765, **{k: v for k, v in params.items()
                                                if k != "_preset"})
        ans = inst["answer"]
        blob = json.dumps(ans, default=str)

        def atoms(a):
            if isinstance(a, dict):  return sum(atoms(v) for v in a.values())
            if isinstance(a, (list, tuple)): return sum(atoms(v) for v in a)
            return 1
        return atoms(ans), len(blob)
    except Exception:                                   # noqa: BLE001
        return None, None

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def _ssl_context():
    """A context with a CA bundle that actually exists.

    A python.org build on macOS whose "Install Certificates.command" was never
    run has openssl_cafile pointing at a file that is not there, and every call
    dies with CERTIFICATE_VERIFY_FAILED.  The loop treats that as an API error
    and refuses to make a hardness claim, which is the right failure, but it is
    a failure of the machine and not of the family — so find a usable bundle
    first.  Never fall back to an unverified context: this call carries an API
    key.
    """
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0) > 0:
        return ctx
    candidates = [os.environ.get("SSL_CERT_FILE"), "/etc/ssl/cert.pem",
                  "/etc/pki/tls/certs/ca-bundle.crt",
                  "/etc/ssl/certs/ca-certificates.crt"]
    try:
        import certifi
        candidates.append(certifi.where())
    except ImportError:
        pass
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ssl.create_default_context(cafile=path)
            except Exception:                                 # noqa: BLE001
                continue
    sys.exit("ERROR: no usable CA bundle — TLS verification would fail for every "
             "oracle call. On a python.org build, run the bundled "
             "'Install Certificates.command', or set SSL_CERT_FILE.")


SSL_CONTEXT = None
SCHEMA_VERSION = 2

TRANSCRIPT = "llm_loop_transcript.jsonl"
META = ".meta.json"


# --- module loading ---------------------------------------------------------
def load_module(path):
    spec = importlib.util.spec_from_file_location("gen", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for fn in ("make_instance", "render", "parse_answer", "verify", "escalate"):
        if not callable(getattr(mod, fn, None)):
            sys.exit(f"ERROR: {path} has no callable {fn}() — see prompts/codex_task.md STEP 1")
    if not isinstance(getattr(mod, "DIFFICULTY", None), dict) or not mod.DIFFICULTY:
        sys.exit(f"ERROR: {path} has no non-empty DIFFICULTY dict")
    return mod


# --- metadata ---------------------------------------------------------------
def read_meta():
    try:
        with open(META) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def update_meta(**fields):
    meta = read_meta()
    meta.update(fields)
    with open(META, "w") as f:
        json.dump(meta, f, indent=1)


# --- the oracle call --------------------------------------------------------
def _ask_blocking(model, prompt, key):
    """Return (reply_text, http_status, finish_reason, error, empty).

    Exactly one of reply/error is set.  An empty body is NOT an API error: it is
    flagged via `empty`, and attempt() scores it as an unsolved attempt.  A model
    that spends its whole budget on reasoning and emits nothing did not produce a
    witness under the conditions the pool is measured at, so it consumes its slot
    rather than being redrawn.  The diagnostic is preserved in verify_reason so a
    level hardened this way can still be told apart from one hardened on wrong
    answers -- if ORACLE_MAX_TOKENS is the real constraint, raise it and re-run.

    Every model in the default pool accepts OpenRouter's normalised `reasoning`
    field, so no per-vendor body mapping is needed.  A model that rejects it is
    reported as an error rather than silently retried without it — dropping the
    effort setting would change what the hardness claim means.
    """
    body = json.dumps({
        "model": model,
        "reasoning": {"effort": ORACLE_EFFORT},
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT,
                                    context=SSL_CONTEXT) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return None, e.code, None, f"http {e.code}: {e.read()[:400].decode('utf-8', 'replace')}", False
    except Exception as e:                                    # noqa: BLE001
        return None, None, None, f"{type(e).__name__}: {e}", False
    try:
        choice = payload["choices"][0]
        text = choice["message"]["content"]
        finish = choice.get("finish_reason") or choice.get("native_finish_reason")
    except (KeyError, IndexError, TypeError):
        return None, status, None, f"unparseable response: {json.dumps(payload)[:400]}", False
    if not (text or "").strip():
        usage = payload.get("usage") or {}
        return None, status, finish, (
            f"empty reply (finish_reason={finish}, usage={json.dumps(usage)[:160]}) — "
            f"the model returned no content, most likely because reasoning consumed "
            f"max_tokens={MAX_TOKENS}; raise ORACLE_MAX_TOKENS"), True
    return text, status, finish, None, False


def ask(model, prompt, key):
    """_ask_blocking under a hard wall-clock deadline.

    A deadline overrun is reported as an ERROR, not a failure to solve: the model
    never got to answer, so scoring it as unsolved would manufacture hardness out
    of a hung socket.  attempt() redraws against a different vendor.
    """
    box = {}

    def run():
        try:
            box["v"] = _ask_blocking(model, prompt, key)
        except Exception as e:                                # noqa: BLE001
            box["v"] = (None, None, None, f"{type(e).__name__}: {e}", False)

    # daemon=True matters: a wedged socket must not keep the interpreter alive at
    # exit, which is exactly what a ThreadPoolExecutor worker would do.
    t = threading.Thread(target=run, daemon=True, name=f"oracle-{model}")
    t.start()
    t.join(TOTAL_DEADLINE)
    if t.is_alive():
        return (None, None, None,
                f"total deadline exceeded: no complete response in {TOTAL_DEADLINE}s",
                False)
    return box.get("v", (None, None, None, "worker produced no result", False))


def attempt(mod, model, params, seed, key):
    """One oracle call.  Returns the transcript record for it."""
    inst = mod.make_instance(seed=seed, **params)
    t0 = time.time()
    reply, status, finish, error, empty = ask(model, mod.render(inst), key)
    elapsed = round(time.time() - t0, 2)

    rec = {
        "schema_version": SCHEMA_VERSION,
        "model": model,
        "effort": ORACLE_EFFORT,
        "params": dict(params),
        "seed": seed,
        "solved": "error",
        "parsed": False,
        "verify_ok": None,
        "verify_reason": None,
        "reply": reply,
        "error": error,
        "elapsed_sec": elapsed,
        "http_status": status,
        "finish_reason": finish,
    }
    if empty:
        # Scored as an unsolved attempt, not an API error: the model returned no
        # witness within its budget.  error stays None so the invariant
        # "error is not None => solved == 'error'" holds.
        rec["solved"] = "failed"
        rec["verify_reason"] = f"empty length-limited response ({error})"
        rec["error"] = None
        return rec
    if error is not None:
        return rec

    ans = mod.parse_answer(reply)
    rec["parsed"] = ans is not None
    if ans is None:
        # Not an error, and not evidence of hardness either: a reply that
        # visibly contains an answer but does not parse is a renderer bug.
        rec["solved"] = "failed"
        rec["verify_reason"] = "parse_answer returned None"
        return rec

    ok, why = mod.verify(inst, ans)
    rec["verify_ok"] = bool(ok)
    rec["verify_reason"] = why
    rec["solved"] = "solved" if ok else "failed"
    return rec


# --- the loop ---------------------------------------------------------------
def run_level(mod, params, preset, escalation_round, rng, key, out):
    """Ask the pool to solve this difficulty.  Returns True if any model solved it.

    Draws distinct models where the pool allows, so three failures are three
    vendors failing rather than one vendor failing three times.  A call that
    errors out is redrawn against a different model and does not consume an
    attempt: an API outage must never be recorded as the model failing to solve,
    which is exactly how a hardness claim gets manufactured out of a 500.  An
    empty length-limited reply is NOT an error -- it is scored as a failure and
    consumes its slot (see ask()).
    """
    k = min(ATTEMPTS_PER_PRESET, len(ORACLE_POOL))
    schedule = rng.sample(ORACLE_POOL, k)
    while len(schedule) < ATTEMPTS_PER_PRESET:
        schedule.append(rng.choice(ORACLE_POOL))

    # A redraw after an error has to keep the level spread across vendors.  One
    # model that reliably errors on a family — a reasoning budget it never
    # escapes at this size, say — would otherwise hand its slot to a vendor that
    # is either already here or queued next, and "three vendors failed" quietly
    # becomes "two vendors failed, one of them twice".  Observed live: at n=80 a
    # sonnet-5 timeout put gpt-5.6-terra in two of three slots.  So a substitute
    # must avoid whoever has spoken AND whoever is still pending.
    spoke = set()
    solved_any = False
    for slot in range(len(schedule)):
        model = schedule[slot]
        pending = set(schedule[slot + 1:])
        tried, rec = 0, None
        while tried <= MAX_ERROR_RETRIES:
            seed = rng.randrange(1, 2**31 - 1)
            if tried == 0:
                use = model
            else:
                fresh = [m for m in ORACLE_POOL if m not in spoke and m not in pending]
                use = rng.choice(fresh or [m for m in ORACLE_POOL if m not in spoke]
                                 or ORACLE_POOL)
            rec = attempt(mod, use, params, seed, key)
            rec["preset"] = preset
            rec["escalation_round"] = escalation_round
            out.write(json.dumps(rec) + "\n")
            out.flush()
            if rec["solved"] != "error":
                spoke.add(use)
                break
            tried += 1
            print(f"  ! {use} errored ({rec['error'][:80]}) — redrawing", file=sys.stderr)
        if rec is None or rec["solved"] == "error":
            sys.exit("ERROR: the oracle pool is unreachable — cannot make a hardness claim.")
        mark = {"solved": "SOLVED", "failed": "failed"}[rec["solved"]]
        print(f"  {rec['model']:38s} seed={rec['seed']:<12d} {mark}", file=sys.stderr)
        if rec["solved"] == "solved":
            solved_any = True
    return solved_any


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 scripts/harden.py <path to gen_*.py>")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("ERROR: OPENROUTER_API_KEY is required — the oracle pool spans four "
                 "vendors, so an OpenAI key alone cannot reach it.")

    global SSL_CONTEXT
    SSL_CONTEXT = _ssl_context()

    mod = load_module(sys.argv[1])

    # One master seed governs every draw below — model choice and instance
    # seeds alike — and is recorded, so a run is reproducible without any seed
    # being fixed in advance.
    master = int(os.environ.get("HARDEN_MASTER_SEED") or
                 int.from_bytes(os.urandom(8), "big"))
    rng = random.Random(master)
    update_meta(schema_version=SCHEMA_VERSION, harden_master_seed=master,
                oracle_pool=ORACLE_POOL, oracle_effort=ORACLE_EFFORT,
                max_escalations=MAX_ESCALATIONS)

    # `demo` is a hand-scale illustration rung, built to be solvable.  Starting
    # the ladder there would spend one of MAX_ESCALATIONS proving that, so the
    # hardening ladder begins at `easy`.
    ladder = [dict(p, _preset=name) for name, p in mod.DIFFICULTY.items()
              if name != "demo"]
    params = ladder[0]
    rung = 0
    verdict = None

    with open(TRANSCRIPT, "w") as out:
        axes_moved = set()          # every param key any level transition changed
        prev_call = None
        for escalation_round in range(MAX_ESCALATIONS + 1):
            shown = {k: v for k, v in params.items() if k != "_preset"}
            print(f"[round {escalation_round}] {params.get('_preset')} {shown}", file=sys.stderr)
            call = {k: v for k, v in params.items() if k != "_preset"}
            # Record which dials moved since the previous level. This has to cover
            # the fixed ladder as well as escalate(): 2601.05272 climbed
            # n=64,72,80,84 through its LADDER and only then called escalate(), so
            # counting escalate()'s moves alone would have seen no axis at all.
            if prev_call is not None:
                for _k, _v in call.items():
                    if prev_call.get(_k) != _v:
                        axes_moved.add(_k)
            prev_call = dict(call)
            preset = params.get("_preset", "escalated")
            if not run_level(mod, call, preset, escalation_round, rng, key, out):
                verdict = {"verdict": "hardened", "escalations_used": escalation_round,
                           "shipping_params": call, "preset": preset}
                break
            print("  -> solved; escalating", file=sys.stderr)

            rung += 1
            if rung < len(ladder):
                params = ladder[rung]
            else:
                nxt = mod.escalate(call)
                # A module may say "I could go harder, but the answer would no
                # longer fit under the cap" by returning the string "cap_bound".
                # That is NOT the same verdict as "this family has no hardness
                # left": the first is a property of our answer format, the second
                # is a property of the paper. Ten rejections were papers whose
                # escalate() stopped at the cap and were then discarded as
                # too_easy -- judged un-writable, not unsuitable.
                if nxt == "cap_bound":
                    verdict = {"verdict": "cap_bound",
                               "escalations_used": escalation_round,
                               "reason": "the family can be made harder, but only by "
                                         "lengthening the answer past the output cap. "
                                         "This is a limit of the answer format, not of "
                                         "the paper -- do not reject it as too_easy."}
                    break
                if nxt is None:
                    # Do not take "None" at face value. cap_bound has been documented
                    # in the escalate() contract and in STEP 0, and builders still
                    # return None when what they mean is "the answer would not fit":
                    # 2601.05272 climbed n=64,72,80,84 and stopped at 249 atoms
                    # against a 256 cap, then reported "the family cannot be made
                    # harder", which was false. Measure it here instead of asking.
                    _atoms, _chars = _answer_size(mod, call)
                    _near = False
                    if _atoms is not None:
                        _near = (_atoms >= CAP_NEAR_FRACTION * ANSWER_ATOM_CAP
                                 or _chars >= CAP_NEAR_FRACTION * ANSWER_CHAR_CAP)
                    _one_dial = len(axes_moved) <= 1
                    if _near or _one_dial:
                        verdict = {
                            "verdict": "cap_bound",
                            "escalations_used": escalation_round,
                            "answer_atoms": _atoms, "answer_chars": _chars,
                            "atom_cap": ANSWER_ATOM_CAP, "char_cap": ANSWER_CHAR_CAP,
                            "axes_moved": sorted(axes_moved),
                            # Two different diagnoses share this verdict, and the
                            # cure differs. "answer_cap": the format genuinely
                            # blocked the ladder -- needs a fixed-length witness.
                            # "single_axis": the ladder only ever turned one dial,
                            # so the family was never actually explored -- often
                            # with a tiny answer and enormous headroom left.
                            "signal": "+".join(
                                x for x in (("answer_cap" if _near else ""),
                                            ("single_axis" if _one_dial else "")) if x),
                            "reason": (
                                "escalate() returned None, but this looks like the ANSWER "
                                "CAP rather than a hardness ceiling"
                                + (f": the answer is already {_atoms} atoms / {_chars} chars "
                                   f"against a {ANSWER_ATOM_CAP}-atom, {ANSWER_CHAR_CAP}-char cap"
                                   if _atoms is not None else "")
                                + (f"; the ladder only ever moved {sorted(axes_moved) or ['nothing']}, "
                                   "so no fixed-answer-length axis was tried"
                                   if _one_dial else "")
                                + ".  PARK this paper -- do not write REJECTED.md.  Harden at "
                                  "fixed answer length instead (bigger ground set with the same "
                                  "witness size, larger modulus, denser decoys, tighter "
                                  "constraints) and re-run."),
                        }
                        break
                    verdict = {"verdict": "too_easy", "escalations_used": escalation_round,
                               "axes_moved": sorted(axes_moved),
                               "answer_atoms": _atoms,
                               "reason": "escalate() returned None — the family cannot be "
                                         "made harder, and the oracle pool still solves it"}
                    break
                params = dict(nxt, _preset="escalated")
        else:
            # The loop ran out of ESCALATIONS, which says nothing about the family
            # until we ask whether it had anywhere left to go.  Ask.
            _atoms, _chars = _answer_size(mod, prev_call or {})
            try:
                _more = mod.escalate(dict(prev_call or {}))
            except Exception:                               # noqa: BLE001
                _more = None
            if _more is not None:
                verdict = {
                    "verdict": "budget_bound",
                    "escalations_used": MAX_ESCALATIONS,
                    "axes_moved": sorted(axes_moved),
                    "answer_atoms": _atoms, "answer_chars": _chars,
                    "next_level": None if _more == "cap_bound" else _more,
                    "escalate_says": "cap_bound" if _more == "cap_bound" else "more levels",
                    "reason": (
                        f"the oracle pool solved every level through {MAX_ESCALATIONS} "
                        f"escalations, but escalate() was STILL WILLING TO CLIMB "
                        f"({'it would next report cap_bound' if _more == 'cap_bound' else _more}). "
                        "The binding constraint was this harness's escalation budget, not "
                        "the paper.  PARK it -- do not write REJECTED.md.  Re-run with "
                        "ORACLE_MAX_ESCALATIONS raised, or ship at a higher preset."),
                }
            else:
                verdict = {"verdict": "too_easy", "escalations_used": MAX_ESCALATIONS,
                           "axes_moved": sorted(axes_moved),
                           "answer_atoms": _atoms, "answer_chars": _chars,
                           "reason": f"the oracle pool solved every level through "
                                     f"{MAX_ESCALATIONS} escalations, and escalate() "
                                     f"has nothing further to offer"}

    update_meta(harden_verdict=verdict)
    print(json.dumps(verdict, indent=1))
    # 0 hardened / 9 too_easy (give the paper up) / 10 park it -- the paper is fine
    # and the binding constraint is ours: the answer format (cap_bound) or the
    # escalation budget (budget_bound).
    return {"hardened": 0, "cap_bound": 10, "budget_bound": 10}.get(verdict["verdict"], 9)


if __name__ == "__main__":
    sys.exit(main())
