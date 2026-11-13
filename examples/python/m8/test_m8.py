"""M8 tests. The Temporal tests start Temporal's test/dev server binaries, which the
temporalio SDK downloads on first use (no API keys, no cloud account)."""

import asyncio
import shutil
import subprocess
import uuid
from dataclasses import replace
from pathlib import Path

import pytest
from deploy import IdempotencyConflict, IdempotencyStore, Tenants, TokenBucket, redact, secret
from durable_agent import run_demo
from media_chunks import (
    TASK_QUEUE,
    Chunk,
    ChunkActivities,
    FakeTranscoder,
    FfmpegTranscoder,
    LongMediaJob,
    ffmpeg_args,
    plan_chunks,
)
from operate import Release, Run, burn_rate, diff, percentile, should_page, slo_report
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import Worker
from versioning import PublishV1, PublishV2, PublishV2Unsafe, record_history, replay_check

import aincourse  # noqa: F401  (sets PYDANTIC_AI_NO_BANNER before pydantic_ai is imported)


# ------------------------------------------------------------------ WE: kill the worker
def test_killed_worker_resumes_without_repeating_side_effects(tmp_path):
    out = asyncio.run(run_demo(tmp_path / "ledger.db"))
    assert len(out["results"]) == 10
    assert out["effects"] == 10  # every side effect exactly once
    keys = out["attempt_keys"]
    assert keys.count("6") == 2 and all(keys.count(str(i)) == 1 for i in range(1, 11) if i != 6)


# ------------------------------------------------------------------ WE: long media job
def test_plan_chunks_covers_two_hours():
    chunks = plan_chunks("j", "talk.mp4", 7200.0)
    assert len(chunks) == 12 and chunks[-1].start_s == 6600.0
    assert plan_chunks("j", "x", 1250.0)[-1].duration_s == 50.0


def test_media_job_resumes_mid_chunk_from_heartbeat(tmp_path):
    fake = FakeTranscoder(crash_at=(3, 240.0))
    acts = ChunkActivities(tmp_path, fake)

    async def go():
        async with await WorkflowEnvironment.start_local() as env:
            async with Worker(env.client, task_queue=TASK_QUEUE, workflows=[LongMediaJob],
                              activities=[acts.process_chunk]):  # fmt: skip
                return await env.client.execute_workflow(
                    LongMediaJob.run,
                    args=["job1", "talk.mp4", 7200.0],
                    id=str(uuid.uuid4()),
                    task_queue=TASK_QUEUE,
                )

    results = asyncio.run(go())
    assert len(results) == 12 and results[3].resumed_from == 240.0
    assert len(fake.pieces) == 120 and len(set(fake.pieces)) == 120  # no piece done twice
    assert sorted(p.name for p in (tmp_path / "job1").iterdir())[0] == "chunk_0000.mp4"


def test_existing_output_makes_chunk_a_no_op(tmp_path):
    fake = FakeTranscoder()
    acts = ChunkActivities(tmp_path, fake)
    chunk = Chunk("j", "talk.mp4", 0, 0.0, 120.0)
    first = asyncio.run(ActivityEnvironment().run(acts.process_chunk, chunk))
    second = asyncio.run(ActivityEnvironment().run(acts.process_chunk, chunk))
    assert (first.skipped, second.skipped, len(fake.pieces)) == (False, True, 2)


def test_ffmpeg_args_seek_before_input():
    args = ffmpeg_args("in.mp4", 600.0, 60.0, Path("o.ts"))
    assert args.index("-ss") < args.index("-i") and args[args.index("-t") + 1] == "60.000"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_ffmpeg_transcoder_on_generated_clip(tmp_path):
    src = tmp_path / "src.ts"
    lavfi = "testsrc=size=160x120:rate=10:duration=6"
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        lavfi,
        "-c:v",
        "mpeg2video",
        "-f",
        "mpegts",
    ]
    subprocess.run([*cmd, str(src)], check=True)
    acts = ChunkActivities(tmp_path / "out", FfmpegTranscoder())
    env = ActivityEnvironment()
    env.info = replace(env.info, heartbeat_details=[])
    res = asyncio.run(env.run(acts.process_chunk, Chunk("j", str(src), 1, 3.0, 3.0)))
    out = tmp_path / "out" / "j" / "chunk_0001.mp4"
    assert not res.skipped and out.stat().st_size > 0


# ------------------------------------------------------------------ L8.5 versioning
def test_patched_change_replays_old_histories_unpatched_does_not():
    async def go():
        async with await WorkflowEnvironment.start_time_skipping() as env:
            history = await record_history(env.client, PublishV1)
        return await replay_check(history, PublishV2), await replay_check(history, PublishV2Unsafe)

    safe, unsafe = asyncio.run(go())
    assert safe is None
    assert unsafe is not None and "Nondeterminism" in unsafe


# ------------------------------------------------------------------ L8.3 Pydantic AI on Temporal
def test_pydantic_ai_agent_runs_durably():
    from pydantic_temporal import TOOL_CALLS, ask

    async def go():
        async with await WorkflowEnvironment.start_time_skipping() as env:
            return await ask(env.client, "How long is talk.mp4?")

    assert asyncio.run(go()) == "The recording is 7200 seconds long."
    assert TOOL_CALLS == ["talk.mp4"]


# ------------------------------------------------------------------ L8.4 deployment plumbing
def test_idempotency_store():
    store, calls = IdempotencyStore(), []

    def charge():
        calls.append(1)
        return "ch_1"

    assert store.run("k1", {"amount": 5}, charge) == ("ch_1", True)
    assert store.run("k1", {"amount": 5}, charge) == ("ch_1", False)
    with pytest.raises(IdempotencyConflict):
        store.run("k1", {"amount": 9}, charge)
    assert len(calls) == 1


def test_token_bucket_and_tenants():
    b = TokenBucket(rate=1, capacity=2)
    assert [b.allow(0), b.allow(0), b.allow(0), b.allow(1.0)] == [True, True, False, True]
    t = Tenants(daily_usd={"acme": 1.0, "tiny": 0.1})
    assert t.admit("acme", 0.2, now=0) == "admitted"
    assert t.admit("tiny", 0.2, now=0) == "rejected: daily budget"
    assert t.admit("ghost", 0.1, now=0) == "rejected: unknown tenant"
    assert [t.admit("acme", 0.01, now=0) for _ in range(4)][-1] == "throttled"
    assert t.queue("acme") == "agents-acme"


def test_secrets_stay_out_of_text(monkeypatch):
    assert redact("key sk-abcdefghijklmnop1234 used") == "key [REDACTED] used"
    monkeypatch.setenv("MEDIA_API_KEY", "s3cr3t")
    assert secret("MEDIA_API_KEY") == "s3cr3t"
    with pytest.raises(RuntimeError):
        secret("NOPE_NOT_SET")


# ------------------------------------------------------------------ L8.5 operations
def test_slo_and_burn_rate():
    runs = [Run(True, 10.0, 0.01)] * 95 + [Run(False, 50.0, 0.02)] * 5
    report = slo_report(runs, target=0.95, p95_budget_s=30.0)
    assert report["success_rate"] == 0.95 and report["error_budget_used"] == 1.0
    assert report["p95_latency_s"] == 10.0 and report["meets_slo"] is True
    assert percentile([1, 2, 3, 4], 50) == 2
    assert burn_rate(5, 100, 0.99) == pytest.approx(5.0)
    assert should_page(15.0, 14.5) and not should_page(15.0, 2.0)


def test_release_fingerprint_changes_with_any_pinned_part():
    a = Release("v3", "model-a", "prompt-v7", ("probe", "upload"))
    b = Release("v3", "model-a", "prompt-v8", ("probe", "upload"))
    assert a.fingerprint != b.fingerprint and diff(a, b) == ["prompt"]
