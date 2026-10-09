"""Reward and episode checks against the real OpenEnv model types."""

import pytest

from evidence_trail.models import TrailAction
from evidence_trail.server.environment import (
    MAX_STEPS,
    TASKS,
    EvidenceTrailEnvironment,
    make_case,
)


@pytest.mark.parametrize("task_id", TASKS)
def test_oracle_wrong_answer_and_reset(task_id: str) -> None:
    env = EvidenceTrailEnvironment()
    for seed in range(100):
        initial = env.reset(seed=seed, task_id=task_id)
        case = make_case(task_id, seed)
        assert not initial.done
        assert 0 <= initial.reward <= 1
        assert env.step(TrailAction(op="read", path="updates.txt")).content == case.files[
            "updates.txt"
        ]
        result = env.step(
            TrailAction(
                op="submit",
                entity=case.entity,
                delta=case.delta,
                evidence=sorted(case.evidence),
            )
        )
        assert result.done and result.reward == 1.0
        assert env.step(TrailAction(op="list")) == result

        env.reset(seed=seed, task_id=task_id)
        wrong = env.step(TrailAction(op="submit", entity="WRONG", delta=case.delta))
        assert wrong.done and wrong.reward == 0.0


def test_partial_credit_and_evidence_spam() -> None:
    case = make_case("invoice-total", 42)
    env = EvidenceTrailEnvironment()
    env.reset(seed=42, task_id="invoice-total")
    partial = env.step(TrailAction(op="submit", entity=case.entity))
    assert partial.reward == 0.55

    env.reset(seed=42, task_id="invoice-total")
    spam = env.step(
        TrailAction(
            op="submit",
            entity=case.entity,
            delta=case.delta,
            evidence=sorted(case.evidence) + ["P999", "R999"],
        )
    )
    assert 0.85 < spam.reward < 1.0


def test_budget_ends_episode() -> None:
    env = EvidenceTrailEnvironment()
    env.reset(seed=7)
    for _ in range(MAX_STEPS - 1):
        assert not env.step(TrailAction(op="list")).done
    final = env.step(TrailAction(op="list"))
    assert final.done and final.reward == 0.0

