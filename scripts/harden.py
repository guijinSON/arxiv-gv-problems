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
DEFAULT_POOL = [
    "openai/gpt-5.6-terra",
    "anthropic/claude-sonnet-5",
    "google/gemini-3.1-pro-preview",
    "x-ai/grok-4.6",
]
ORACLE_POOL = [m.strip() for m in os.environ.get(
    "ORACLE_POOL", ",".join(DEFAULT_POOL)).split(",") if m.strip()]

ORACLE_EFFORT = os.environ.get("ORACLE_EFFORT", "medium")
ATTEMPTS_PER_PRESET = 3      # distinct models per difficulty level
MAX_ESCALATIONS = 3          # raises of difficulty before the family is given up on
MAX_ERROR_RETRIES = 3        # per attempt; API errors do not count as attempts
MAX_TOKENS = int(os.environ.get("ORACLE_MAX_TOKENS", "32000"))
# Reasoning tokens are billed against max_tokens on some vendors, so a budget
# sized for the answer alone comes back HTTP 200 with an empty body — observed
# live at 16000 against claude-sonnet-5 on a 2030-character statement.
REQUEST_TIMEOUT = 900

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
def ask(model, prompt, key):
    """Return (reply_text, http_status, finish_reason, error).

    Exactly one of reply/error is set.  An empty body is reported as an error,
    not as a reply: a model that spent its whole token budget on reasoning and
    returned nothing has not failed to solve the instance, and scoring it as a
    failure manufactures hardness out of a truncated response.

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
        return None, e.code, None, f"http {e.code}: {e.read()[:400].decode('utf-8', 'replace')}"
    except Exception as e:                                    # noqa: BLE001
        return None, None, None, f"{type(e).__name__}: {e}"
    try:
        choice = payload["choices"][0]
        text = choice["message"]["content"]
        finish = choice.get("finish_reason") or choice.get("native_finish_reason")
    except (KeyError, IndexError, TypeError):
        return None, status, None, f"unparseable response: {json.dumps(payload)[:400]}"
    if not (text or "").strip():
        usage = payload.get("usage") or {}
        return None, status, finish, (
            f"empty reply (finish_reason={finish}, usage={json.dumps(usage)[:160]}) — "
            f"the model returned no content, most likely because reasoning consumed "
            f"max_tokens={MAX_TOKENS}; raise ORACLE_MAX_TOKENS")
    return text, status, finish, None


def attempt(mod, model, params, seed, key):
    """One oracle call.  Returns the transcript record for it."""
    inst = mod.make_instance(seed=seed, **params)
    t0 = time.time()
    reply, status, finish, error = ask(model, mod.render(inst), key)
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
    which is exactly how a hardness claim gets manufactured out of a 500.
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

    ladder = [dict(p, _preset=name) for name, p in mod.DIFFICULTY.items()]
    params = ladder[0]
    rung = 0
    verdict = None

    with open(TRANSCRIPT, "w") as out:
        for escalation_round in range(MAX_ESCALATIONS + 1):
            shown = {k: v for k, v in params.items() if k != "_preset"}
            print(f"[round {escalation_round}] {params.get('_preset')} {shown}", file=sys.stderr)
            call = {k: v for k, v in params.items() if k != "_preset"}
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
                if nxt is None:
                    verdict = {"verdict": "too_easy", "escalations_used": escalation_round,
                               "reason": "escalate() returned None — the family cannot be "
                                         "made harder, and the oracle pool still solves it"}
                    break
                params = dict(nxt, _preset="escalated")
        else:
            verdict = {"verdict": "too_easy", "escalations_used": MAX_ESCALATIONS,
                       "reason": f"the oracle pool solved every level through "
                                 f"{MAX_ESCALATIONS} escalations"}

    update_meta(harden_verdict=verdict)
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["verdict"] == "hardened" else 9


if __name__ == "__main__":
    sys.exit(main())
