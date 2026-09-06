"""Call a model on freshly generated instances and grade with the family's own verifier.

Lives in <repo>/notebooks/, so the repo root is one level up.
"""
import os, io, json, glob, hashlib, pickle, time, contextlib, importlib.util, urllib.request

REPO_DIR   = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ENDPOINT   = "https://openrouter.ai/api/v1/chat/completions"

MODEL      = "openai/gpt-5.6-terra"   # any OpenRouter model id
EFFORT     = "medium"                 # reasoning effort
MAX_TOKENS = 32000
CACHE_DIR  = "/home/work/onelineai/instances_cache"   # pickles written by save_instances()

_families = {}


def families():
    """arXiv ids of every family in results/ that shipped a generator."""
    return sorted(os.path.basename(os.path.dirname(p))
                  for p in glob.glob(os.path.join(REPO_DIR, "results", "*", "gen_*.py")))


def load_family(paper):
    """Import results/<paper>/gen_*.py once and cache the module."""
    if paper not in _families:
        path = glob.glob(os.path.join(REPO_DIR, "results", paper, "gen_*.py"))[0]
        spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
        mod  = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):   # some generators print on import
            spec.loader.exec_module(mod)
        _families[paper] = mod
    return _families[paper]


def make_instance(paper, preset="hard", seed=0, **overrides):
    """Build one fresh instance of a family at a named preset ("demo", "easy", "medium", "hard").

    `overrides` replace individual make_instance kwargs from the preset. Returns
    (fam, inst, question): the module, the instance object verify() needs, and the rendered
    problem statement to send to the model.
    """
    fam  = load_family(paper)
    inst = fam.make_instance(seed=seed, **{**fam.DIFFICULTY[preset], **overrides})
    return fam, inst, fam.render(inst)


# --- HF dataset helpers --------------------------------------------------------------------
# The HF datasets store `paper` as a float, which drops the leading/trailing zeros of arXiv ids
# ('0705.4246' -> 705.4246, '1109.3180' -> 1109.318). paper_id() maps the float back to the real
# id via the generator folders that actually exist under results/.

_by_float = None


def paper_id(p):
    """results/<id>/ folder name for a dataset `paper` value (a float, or an id string)."""
    global _by_float
    if _by_float is None:
        fams = families()
        _by_float = {float(f): f for f in fams}
        assert len(_by_float) == len(fams), "two family ids collapse to the same float"
    return _by_float[float(p)]


def gen_sha(paper):
    """Short sha of results/<paper>/gen_*.py, so a cache built from a different generator is caught."""
    path = glob.glob(os.path.join(REPO_DIR, "results", paper, "gen_*.py"))[0]
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def cache_path(dataset, split="train"):
    return os.path.join(CACHE_DIR, f"{dataset.split('/')[-1]}.{split}.pkl")


def save_instances(ds, instances, dataset, split="train", path=None):
    """Pickle the [(fam, inst), ...] list built for every row of `ds` (an HF split) so that
    load_instances() can hand it back without re-running the generators. Modules cannot be
    pickled, so the paper id is stored per row and the module is re-imported on load."""
    papers = [paper_id(p) for p in ds["paper"]]
    insts  = [inst for _, inst in instances]
    assert len(insts) == len(ds), "one instance per dataset row expected"
    cache = {"dataset": dataset, "split": split, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
             "ids": ds["id"], "papers": papers, "insts": insts,
             "gen_sha": {p: gen_sha(p) for p in set(papers)}}
    path = path or cache_path(dataset, split)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    return path


def load_instances(ds, dataset, split="train", path=None):
    """[(fam, inst), ...] saved by save_instances() for `ds`, row-aligned. Refuses a cache whose
    rows do not match the dataset or whose generators changed since it was built."""
    path = path or cache_path(dataset, split)
    with open(path, "rb") as f:
        cache = pickle.load(f)
    assert cache["dataset"] == dataset and cache["ids"] == ds["id"], "cache rows do not line up with the dataset"
    stale = [p for p, h in cache["gen_sha"].items() if gen_sha(p) != h]
    assert not stale, f"generator changed since the cache was built: {stale[:10]}"
    return [(load_family(p), inst) for p, inst in zip(cache["papers"], cache["insts"])]


def ask(prompt, model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS, timeout=1800):
    """One OpenRouter call, same request body as scripts/harden.py: the rendered question is
    the whole user message, no extra framing. Returns the reply text, "" if the model
    returned no content (usually reasoning consumed max_tokens)."""
    body = json.dumps({"model": model, "reasoning": {"effort": effort}, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["choices"][0]["message"]["content"] or ""


def grade(fam, inst, reply):
    """(correct, reason, answer) using the family's own parse_answer() and verify()."""
    answer = fam.parse_answer(reply)
    if answer is None:
        return False, "no well-formed answer in the reply", None
    ok, reason = fam.verify(inst, answer)
    return ok, reason, answer


def evaluate(paper, model=MODEL, preset="hard", seed=0, **ask_kwargs):
    """Generate one instance, ask the model, grade. Returns a flat record."""
    fam, inst, question = make_instance(paper, preset, seed)
    reply = ask(question, model, **ask_kwargs)
    correct, reason, answer = grade(fam, inst, reply)
    return {"paper": paper, "preset": preset, "seed": seed, "model": model,
            "correct": correct, "reason": reason, "answer": answer, "reply": reply}
