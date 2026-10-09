# Evidence Trail Lab

Evidence Trail Lab is an OpenEnv environment for short, source-aware investigations. Each episode presents five entities across a plan, an initial report, signed updates, drafts, and informal notes. The agent must find the entity with the largest verified increase over plan, compute the integer difference, and cite the plan and final-actual record IDs.

Six task families cover software operations, industrial operations, natural science, office reconciliation, finance, and media production. Each reset generates new values and shuffled updates. An explicit seed reproduces a case for testing; an unseeded reset generates a fresh case. The verifier computes its answer from the structured records before formatting the files. No external service or secret is needed at runtime.

## Actions and reward

Use `{"op":"list"}` to list files, `{"op":"read","path":"plan.txt"}` to inspect one, and `{"op":"submit","entity":"SERVICE-1","delta":27,"evidence":["P1","U2"]}` to end the episode. The last example illustrates the shape; its values are case-dependent. Seven actions are available. A submission or budget exhaustion always returns `done: true` and a reward in `[0, 1]`.

The correct entity earns 0.55, its exact delta earns 0.30, and the evidence IDs earn up to 0.15 using F1 over the plan and final-actual record IDs. A wrong entity earns zero. Duplicate or extra citations cannot improve the evidence score. This makes partial progress visible while requiring both arithmetic and source selection for full reward.

## Run locally

The project pins OpenEnv to the Arena revision `86a180ede21e044f7929b9a7783ad83aa67d83a3` in `pyproject.toml`.

```sh
python3.11 -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/pytest -q
.venv/bin/uvicorn evidence_trail.server.app:app --host 0.0.0.0 --port 8000
```

In another shell:

```sh
.venv/bin/openenv validate --url http://localhost:8000
.venv/bin/python scripts/replay.py http://localhost:8000
```

The public image is built from this directory using `openenv build -t ghcr.io/arrana16/evidence-trail-lab:v1`. The Arena submission request is in `submission.json`; it should only be sent after a fresh anonymous pull and human approval.

Public dataset: https://huggingface.co/datasets/arrana16/evidence-trail-lab

