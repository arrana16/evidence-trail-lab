---
language:
- en
license: mit
task_categories:
- question-answering
tags:
- openenv
- reinforcement-learning
- reasoning
configs:
- config_name: default
  data_files:
  - split: train
    path: tasks.jsonl
---

# Evidence Trail Lab tasks

This dataset lists the six synthetic task families used by the [Evidence Trail Lab](https://github.com/arrana16/evidence-trail-lab) OpenEnv server. Each row is a resettable task ID; the server generates a fresh numerical case on each unseeded reset. `example_seed` is a reproducible sample for inspection. The container image, not this dataset, runs the generator and verifier.

The agent reads plan, report, update, and note records. It must apply the latest signed update, ignore drafts, compute the largest positive actual-minus-plan difference, and cite the supporting record IDs. Reward is 0.55 for the correct entity, 0.30 for the exact integer delta, and up to 0.15 for citation F1. A wrong entity earns zero. Submission and action-budget exhaustion both terminate the episode.

All records and names are synthetic. No private data or evaluation tasks are included.

