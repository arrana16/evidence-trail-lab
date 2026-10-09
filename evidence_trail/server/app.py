"""HTTP and WebSocket entry point for the OpenEnv server."""

from openenv.core.env_server.http_server import create_app

from evidence_trail.models import TrailAction, TrailObservation
from evidence_trail.server.environment import EvidenceTrailEnvironment

app = create_app(
    EvidenceTrailEnvironment,
    TrailAction,
    TrailObservation,
    env_name="evidence_trail_lab",
    max_concurrent_envs=8,
)

