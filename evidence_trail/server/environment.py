"""Procedural investigations with source precedence and exact rewards."""

from __future__ import annotations

import random
import secrets
from dataclasses import dataclass
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from evidence_trail.models import TrailAction, TrailObservation


TASKS = {
    "service-latency": ("software operations", "service", "latency", "ms"),
    "supply-yield": ("industrial operations", "production line", "yield", "units"),
    "lab-concentration": ("natural science", "sample", "concentration", "ppm"),
    "invoice-total": ("office reconciliation", "invoice", "billable total", "USD"),
    "portfolio-exposure": ("finance", "position", "exposure", "USD"),
    "media-duration": ("media production", "segment", "duration", "seconds"),
}
MAX_STEPS = 7


@dataclass(frozen=True)
class Case:
    files: dict[str, str]
    entity: str
    delta: int
    evidence: frozenset[str]


def make_case(task_id: str, seed: int) -> Case:
    """Generate records and their independent answer key from one seed."""
    if task_id not in TASKS:
        raise ValueError(f"unknown task_id: {task_id}")
    rng = random.Random(seed)
    domain, noun, metric, unit = TASKS[task_id]
    entities = [f"{noun.replace(' ', '-').upper()}-{n}" for n in range(1, 6)]
    plans = {entity: rng.randint(90, 220) for entity in entities}
    deltas = {entity: rng.randint(-18, 18) for entity in entities}
    winner = rng.choice(entities)
    winner_is_updated = rng.choice([True, False])
    if not winner_is_updated:
        deltas[winner] = rng.randint(26, 38)
    reports = {entity: plans[entity] + deltas[entity] for entity in entities}

    # A conspicuous draft points to the wrong entity. Only signed updates count.
    distractor = rng.choice([entity for entity in entities if entity != winner])
    signed_targets = rng.sample(
        [entity for entity in entities if entity != winner], 2 - int(winner_is_updated)
    )
    if winner_is_updated:
        signed_targets.append(winner)

    updates: list[dict[str, str | int]] = []
    for entity in signed_targets:
        value = plans[entity] + (
            rng.randint(26, 38) if entity == winner else rng.randint(-12, 16)
        )
        updates.append({"entity": entity, "seq": 1, "status": "SIGNED", "value": value})
    # This second signed record tests whether the agent uses the newest sequence.
    revised = rng.choice([entity for entity in signed_targets if entity != winner])
    updates.append(
        {
            "entity": revised,
            "seq": 2,
            "status": "SIGNED",
            "value": plans[revised] + rng.randint(-10, 17),
        }
    )
    updates.append(
        {
            "entity": distractor,
            "seq": 3,
            "status": "DRAFT",
            "value": plans[distractor] + rng.randint(45, 60),
        }
    )
    rng.shuffle(updates)

    plan_lines = []
    report_lines = []
    final_values = dict(reports)
    final_ids = {entity: f"R{index}" for index, entity in enumerate(entities, 1)}
    for index, entity in enumerate(entities, 1):
        plan_lines.append(f"P{index} | {entity} | planned {metric}: {plans[entity]} {unit}")
        report_lines.append(f"R{index} | {entity} | reported {metric}: {reports[entity]} {unit}")

    update_lines = []
    signed_sequence = {entity: 0 for entity in entities}
    for index, item in enumerate(updates, 1):
        entity = str(item["entity"])
        sequence = int(item["seq"])
        status = str(item["status"])
        update_lines.append(
            f"U{index} | {entity} | sequence {sequence} | {status} | "
            f"corrected {metric}: {item['value']} {unit}"
        )
        if status == "SIGNED" and sequence > signed_sequence[entity]:
            final_values[entity] = int(item["value"])
            final_ids[entity] = f"U{index}"
            signed_sequence[entity] = sequence

    actual_deltas = {entity: final_values[entity] - plans[entity] for entity in entities}
    assert actual_deltas[winner] > max(
        actual_deltas[entity] for entity in entities if entity != winner
    )
    winner_index = entities.index(winner) + 1
    files = {
        "brief.txt": (
            f"Case: {domain}. Compare each {noun}'s final {metric} with its plan, "
            f"in {unit}. A signed update supersedes the initial report. If multiple "
            "signed updates exist, use the highest sequence. Draft updates and "
            "informal notes have no authority. Return the largest positive "
            "difference, with its entity ID and the plan/final-actual record IDs."
        ),
        "plan.txt": "\n".join(plan_lines),
        "report.txt": "\n".join(report_lines),
        "updates.txt": "\n".join(update_lines),
        "field_notes.txt": (
            f"Informal note: {distractor} may be unusually high. This note is "
            "unverified and does not amend any numbered record."
        ),
    }
    return Case(
        files=files,
        entity=winner,
        delta=actual_deltas[winner],
        evidence=frozenset({f"P{winner_index}", final_ids[winner]}),
    )


def score_answer(case: Case, action: TrailAction) -> float:
    """Award grounded partial credit only for the correct entity."""
    if action.entity.strip().upper() != case.entity:
        return 0.0
    score = 0.55
    if action.delta == case.delta:
        score += 0.30
    supplied = {item.strip().upper() for item in action.evidence if item.strip()}
    if supplied:
        precision = len(supplied & case.evidence) / len(supplied)
        recall = len(supplied & case.evidence) / len(case.evidence)
        if precision + recall:
            score += 0.15 * (2 * precision * recall / (precision + recall))
    return round(min(1.0, score), 6)


class EvidenceTrailEnvironment(Environment[TrailAction, TrailObservation, State]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task_id = next(iter(TASKS))
        self._case: Case | None = None
        self._terminal: TrailObservation | None = None

    def reset(
        self, seed: int | None = None, episode_id: str | None = None, **kwargs: object
    ) -> TrailObservation:
        task_id = str(kwargs.get("task_id") or self._task_id)
        if task_id not in TASKS:
            raise ValueError(f"unknown task_id: {task_id}")
        self._task_id = task_id
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._case = make_case(task_id, seed if seed is not None else secrets.randbits(63))
        self._terminal = None
        return TrailObservation(
            task=task_id,
            message=(
                "Find the entity with the largest verified increase over plan. "
                "Read the files, then submit its ID, integer delta, and supporting "
                "plan and final-actual record IDs. Signed updates override reports; "
                "the latest signed sequence wins. Drafts do not count."
            ),
            files=list(self._case.files),
            steps_left=MAX_STEPS,
            done=False,
            reward=0.0,
        )

    def step(self, action: TrailAction, **kwargs: object) -> TrailObservation:
        if self._case is None:
            raise RuntimeError("reset before step")
        if self._terminal is not None:
            return self._terminal
        self._state.step_count += 1
        steps_left = MAX_STEPS - self._state.step_count
        if action.op == "submit":
            reward = score_answer(self._case, action)
            self._terminal = TrailObservation(
                task=self._task_id,
                message="Answer recorded.",
                steps_left=steps_left,
                done=True,
                reward=reward,
            )
            return self._terminal
        if steps_left <= 0:
            self._terminal = TrailObservation(
                task=self._task_id,
                message="Action budget exhausted.",
                steps_left=0,
                done=True,
                reward=0.0,
            )
            return self._terminal
        if action.op == "list":
            return TrailObservation(
                task=self._task_id,
                message="Available files.",
                files=list(self._case.files),
                steps_left=steps_left,
                done=False,
                reward=0.0,
            )
        content = self._case.files.get(action.path)
        return TrailObservation(
            task=self._task_id,
            message="File content." if content is not None else "No such file.",
            content=content or "",
            files=list(self._case.files) if content is None else [],
            steps_left=steps_left,
            done=False,
            reward=0.0,
        )

    @property
    def state(self) -> State:
        return self._state

    def list_splits(self) -> list[str]:
        return ["train"]

    def list_tasks(self, split: str) -> list[dict[str, str]]:
        return [self.get_task(split, index) for index in range(len(TASKS))]

    def num_tasks(self, split: str) -> int:
        return len(TASKS) if split == "train" else 0

    def get_task(self, split: str, index: int) -> dict[str, str]:
        if split != "train" or index < 0 or index >= len(TASKS):
            raise IndexError(index)
        return {"id": list(TASKS)[index], "split": split}

