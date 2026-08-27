# artifacts/

Emitted dataset instances, one JSONL per paper: `artifacts/<arxiv_id>.jsonl`.

Written by `scripts/emit.sh <arxiv_id> [count] [difficulty]`, which `submit.sh` runs
automatically. Each line is one ready-to-use problem:

```json
{
  "paper": "1912.09051",
  "difficulty": "medium",
  "params": {"n": 80, "seed": 10000},
  "question": "Find a connected spanning central surface in ...",
  "answer": [8, 2, 5, ...],
  "search_space": 7.1e120
}
```

`question` is self-contained — a solver needs nothing else, and it ends with the
`<answer></answer>` contract that the paper's `parse_answer` consumes.

To grade a model's reply:

```python
import importlib.util, json
s = importlib.util.spec_from_file_location("m", "results/<id>/gen_<id>.py")
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
inst = m.make_instance(**rec["params"])          # regenerates the exact instance
ok, why = m.verify(inst, m.parse_answer(model_reply))
```

Instances are cheap to regenerate, so this directory is a **sample** (20 per paper by
default), not the dataset itself. For bulk generation call `make_instance` directly with
your own seed range.
