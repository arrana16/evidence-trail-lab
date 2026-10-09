"""Replay all task IDs through the native OpenEnv WebSocket protocol."""

import asyncio
import json
import sys
from urllib.parse import urlparse

import websockets

from evidence_trail.server.environment import TASKS, make_case


async def replay(base_url: str) -> None:
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


if __name__ == "__main__":
    asyncio.run(replay(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"))
