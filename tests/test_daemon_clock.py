"""Daemon schedule evaluation against an injected clock pinned on the hour."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from autoresearch.config import GlobalConfig
from autoresearch.daemon import DaemonRunner, is_due
from autoresearch.marker import (
    AgentConfig,
    Marker,
    MarkerFile,
    MarkerStatus,
    Metric,
    Schedule,
    Target,
)
from autoresearch.state import AppState, TrackedMarker

ON_THE_HOUR = datetime(2026, 10, 28, 1, 0, tzinfo=timezone.utc)
HOURLY = Schedule(type="cron", cron="0 * * * *")


def _hourly_marker() -> Marker:
    return Marker(
        name="test",
        target=Target(mutable=["src/main.py"]),
        metric=Metric(
            command="echo 1", extract=r"\d+", direction="higher", baseline=1.0
        ),
        agent=AgentConfig(
            model="sonnet", budget_per_experiment="5m", max_experiments=10
        ),
        schedule=HOURLY,
    )


def test_run_thirty_seconds_before_the_hour_is_due_on_the_hour():
    last = (ON_THE_HOUR - timedelta(seconds=30)).isoformat()
    assert is_due(HOURLY, last, ON_THE_HOUR) is True


@pytest.mark.parametrize(
    ("now", "spawned"),
    [
        (ON_THE_HOUR + timedelta(minutes=59, seconds=30), False),
        (ON_THE_HOUR + timedelta(hours=1), True),
    ],
)
def test_tick_reads_injected_clock(now, spawned):
    tracked = TrackedMarker(
        id="repo:test",
        repo_path="/tmp/fakerepo",
        repo_name="repo",
        marker_name="test",
        last_run=ON_THE_HOUR.isoformat(),
    )
    runner = DaemonRunner(config=GlobalConfig(), clock=lambda: now)
    with (
        patch(
            "autoresearch.daemon.load_state",
            return_value=AppState(markers=[tracked]),
        ),
        patch(
            "autoresearch.daemon.find_marker_file",
            return_value=Path("/tmp/.autoresearch.yaml"),
        ),
        patch(
            "autoresearch.daemon.load_markers",
            return_value=MarkerFile(markers=[_hourly_marker()]),
        ),
        patch(
            "autoresearch.daemon.get_effective_status",
            return_value=MarkerStatus.ACTIVE,
        ),
        patch.object(runner, "_run_marker_thread"),
    ):
        runner._tick()
    assert ("repo:test" in runner._active_runs) is spawned
