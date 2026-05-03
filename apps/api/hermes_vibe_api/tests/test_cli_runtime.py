import asyncio
import os
from pathlib import Path
import sys

import pytest

from hermes_vibe_api.hermes.runtime import (
    HermesCLIBackedRuntime,
    RuntimeCommandEvent,
    RuntimeCommandResult,
    RuntimeMessage,
    stream_subprocess_command,
)


@pytest.mark.asyncio
async def test_cli_runtime_invokes_vendored_hermes_oneshot(tmp_path):
    calls = []

    async def fake_runner(command, cwd, env):
        calls.append((command, cwd, env))
        return RuntimeCommandResult(returncode=0, stdout="hello from hermes\n", stderr="")

    runtime = HermesCLIBackedRuntime(
        hermes_root=tmp_path / "packages" / "hermes",
        hermes_home=tmp_path / ".hermes",
        workspace_path=tmp_path / "workspace",
        model="gpt-5.4",
        provider="openai",
        runner=fake_runner,
    )

    events = [
        event
        async for event in runtime.send_message(
            session_id="s1",
            message=RuntimeMessage(role="user", content="hello"),
        )
    ]

    command, cwd, env = calls[0]
    assert command[:3] == [runtime.python_executable, str(runtime.hermes_executable), "-z"]
    assert command[3:] == ["hello", "--model", "gpt-5.4", "--provider", "openai"]
    assert cwd == tmp_path / "workspace"
    assert env["HERMES_HOME"] == str(tmp_path / ".hermes")
    assert [event.type for event in events] == [
        "agent.tool.started",
        "chat.message.delta",
        "chat.message.completed",
        "implementation.summary.updated",
        "decision.trace.created",
        "concept.detected",
        "agent.tool.completed",
    ]
    assert events[1].payload["content"] == "hello from hermes"


@pytest.mark.asyncio
async def test_cli_runtime_uses_message_model_override(tmp_path):
    calls = []

    async def fake_runner(command, cwd, env):
        calls.append(command)
        return RuntimeCommandResult(returncode=0, stdout="answer", stderr="")

    runtime = HermesCLIBackedRuntime(
        hermes_root=tmp_path / "packages" / "hermes",
        model="gpt-5.4",
        provider="openai",
        runner=fake_runner,
    )

    events = [
        event
        async for event in runtime.send_message(
            session_id="s1",
            message=RuntimeMessage(
                role="user",
                content="hello",
                provider="anthropic",
                model="claude-sonnet-4.5",
            ),
        )
    ]

    assert calls[0][-4:] == ["--model", "claude-sonnet-4.5", "--provider", "anthropic"]
    assert events[-1].type == "agent.tool.completed"


@pytest.mark.asyncio
async def test_cli_runtime_emits_debug_event_on_failed_process(tmp_path):
    async def fake_runner(command, cwd, env):
        return RuntimeCommandResult(returncode=2, stdout="", stderr="missing model")

    runtime = HermesCLIBackedRuntime(
        hermes_root=tmp_path / "packages" / "hermes",
        runner=fake_runner,
    )

    events = [
        event
        async for event in runtime.send_message(
            session_id="s1",
            message=RuntimeMessage(role="user", content="hello"),
        )
    ]

    assert events[-1].type == "debug.error.detected"
    assert events[-1].payload["error_message"] == "missing model"
    assert [event.type for event in events[-3:]] == [
        "implementation.blocker.detected",
        "error.learning_log.created",
        "debug.error.detected",
    ]


@pytest.mark.asyncio
async def test_cli_runtime_streams_stdout_chunks_before_completion(tmp_path):
    async def fake_stream_runner(command, cwd, env):
        yield RuntimeCommandEvent(stream="stdout", content="hello ")
        yield RuntimeCommandEvent(stream="stdout", content="world\n")
        yield RuntimeCommandEvent(stream="exit", returncode=0)

    runtime = HermesCLIBackedRuntime(
        hermes_root=tmp_path / "packages" / "hermes",
        stream_runner=fake_stream_runner,
    )

    events = [
        event
        async for event in runtime.send_message(
            session_id="s1",
            message=RuntimeMessage(role="user", content="hello"),
        )
    ]

    assert [event.type for event in events[:5]] == [
        "agent.tool.started",
        "agent.log.chunk",
        "chat.message.delta",
        "agent.log.chunk",
        "chat.message.delta",
    ]
    assert events[1].payload["stream"] == "stdout"
    assert events[2].payload["content"] == "hello "
    completed = [event for event in events if event.type == "chat.message.completed"]
    assert completed[0].payload["content"] == "hello world"


@pytest.mark.asyncio
async def test_cli_runtime_streams_stderr_chunks_before_failure(tmp_path):
    async def fake_stream_runner(command, cwd, env):
        yield RuntimeCommandEvent(stream="stderr", content="missing ")
        yield RuntimeCommandEvent(stream="stderr", content="model")
        yield RuntimeCommandEvent(stream="exit", returncode=2)

    runtime = HermesCLIBackedRuntime(
        hermes_root=tmp_path / "packages" / "hermes",
        stream_runner=fake_stream_runner,
    )

    events = [
        event
        async for event in runtime.send_message(
            session_id="s1",
            message=RuntimeMessage(role="user", content="hello"),
        )
    ]

    assert [event.type for event in events[:3]] == [
        "agent.tool.started",
        "agent.log.chunk",
        "agent.log.chunk",
    ]
    assert events[1].payload["stream"] == "stderr"
    assert events[-1].type == "debug.error.detected"
    assert events[-1].payload["error_message"] == "missing model"


@pytest.mark.asyncio
async def test_subprocess_stream_runner_emits_stdout_before_newline(tmp_path):
    command = [
        sys.executable,
        "-c",
        (
            "import sys, time;"
            "sys.stdout.write('partial');"
            "sys.stdout.flush();"
            "time.sleep(0.4);"
            "sys.stdout.write(' done\\n');"
            "sys.stdout.flush()"
        ),
    ]
    events = stream_subprocess_command(command, tmp_path, dict(os.environ))

    first_event = await asyncio.wait_for(events.__anext__(), timeout=0.2)

    assert first_event.stream == "stdout"
    assert first_event.content == "partial"


@pytest.mark.asyncio
async def test_subprocess_stream_runner_terminates_process_when_closed(tmp_path):
    marker = tmp_path / "finished.txt"
    command = [
        sys.executable,
        "-c",
        (
            "import pathlib, sys, time;"
            "sys.stdout.write('started');"
            "sys.stdout.flush();"
            "time.sleep(0.5);"
            f"pathlib.Path({str(marker)!r}).write_text('finished', encoding='utf-8')"
        ),
    ]
    events = stream_subprocess_command(command, tmp_path, dict(os.environ))

    first_event = await asyncio.wait_for(events.__anext__(), timeout=0.2)
    await events.aclose()
    await asyncio.sleep(0.8)

    assert first_event.content == "started"
    assert not marker.exists()
