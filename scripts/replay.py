"""Replay all task IDs through the native OpenEnv WebSocket protocol."""

import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

import websockets

from evidence_trail.server.environment import TASKS, make_case


async def replay(base_url: str) -> None:
    request = json.loads((Path(__file__).resolve().parents[1] / "submission.json").read_text())
    with urlopen(f"{base_url}/schema") as response:
        live_schema = json.load(response)
    assert request["schema"] == {
        "action": live_schema["action"],
        "observation": live_schema["observation"],
    }
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    uri = f"{scheme}://{parsed.netloc}/ws"
    for task_id in TASKS:
        async with websockets.connect(uri) as socket:
            await socket.send(
                json.dumps({"type": "reset", "data": {"task_id": task_id, "seed": 42}})
            )
            initial = json.loads(await socket.recv())
            assert initial["type"] == "observation", initial
            assert initial["data"]["done"] is False, initial
            for path in ["brief.txt", "plan.txt", "report.txt", "updates.txt"]:
                await socket.send(json.dumps({"type": "step", "data": {"op": "read", "path": path}}))
                result = json.loads(await socket.recv())
                assert result["type"] == "observation", result
                assert result["data"]["observation"]["content"], result
            case = make_case(task_id, 42)
            await socket.send(
                json.dumps(
                    {
                        "type": "step",
                        "data": {
                            "op": "submit",
                            "entity": case.entity,
                            "delta": case.delta,
                            "evidence": sorted(case.evidence),
                        },
                    }
                )
            )
            result = json.loads(await socket.recv())
            assert result["type"] == "observation", result
            assert result["data"]["done"] is True, result
            assert result["data"]["reward"] == 1.0, result
            print(f"{task_id}: done=true reward=1.0")
        async with websockets.connect(uri) as socket:
            await socket.send(json.dumps({"type": "reset", "data": {"task_id": task_id}}))
            assert json.loads(await socket.recv())["data"]["done"] is False
            for action in request["example_actions"]:
                await socket.send(json.dumps({"type": "step", "data": action}))
                result = json.loads(await socket.recv())
            assert result["type"] == "observation", result
            assert result["data"]["done"] is True, result
            assert 0 <= result["data"]["reward"] <= 1, result
            print(f"{task_id}: admission example terminates in range")


if __name__ == "__main__":
    asyncio.run(replay(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"))
