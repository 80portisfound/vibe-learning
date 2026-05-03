from abc import ABC, abstractmethod
import asyncio
from collections.abc import AsyncIterator
from collections.abc import Awaitable, Callable
import os
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel

from hermes_vibe_api.dashboard.analyzer import analyze_failed_turn, analyze_successful_turn
from hermes_vibe_api.dashboard.schemas import DashboardEvent


class RuntimeMessage(BaseModel):
    role: str
    content: str
    provider: str | None = None
    model: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    system_prompt: str | None = None


class RuntimeCommandResult(BaseModel):
    returncode: int
    stdout: str = ""
    stderr: str = ""


class RuntimeCommandEvent(BaseModel):
    stream: Literal["stdout", "stderr", "exit"]
    content: str = ""
    returncode: int | None = None


RuntimeCommandRunner = Callable[[list[str], Path, dict[str, str]], Awaitable[RuntimeCommandResult]]
RuntimeCommandStreamRunner = Callable[[list[str], Path, dict[str, str]], AsyncIterator[RuntimeCommandEvent]]


class HermesRuntime(ABC):
    @abstractmethod
    async def send_message(
        self,
        session_id: str,
        message: RuntimeMessage,
    ) -> AsyncIterator[DashboardEvent]:
        pass


class InProcessHermesRuntime(HermesRuntime):
    async def send_message(
        self,
        session_id: str,
        message: RuntimeMessage,
    ) -> AsyncIterator[DashboardEvent]:
        content = f"Hermes stub received: {message.content}"
        yield DashboardEvent(
            session_id=session_id,
            type="chat.message.delta",
            payload={"role": "assistant", "content": content},
            source="hermes.stub",
        )
        yield DashboardEvent(
            session_id=session_id,
            type="chat.message.completed",
            payload={"role": "assistant", "content": content},
            source="hermes.stub",
        )


async def run_subprocess_command(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
) -> RuntimeCommandResult:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    return RuntimeCommandResult(
        returncode=process.returncode,
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
    )


async def stream_subprocess_command(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
) -> AsyncIterator[RuntimeCommandEvent]:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None

    stdout_task = asyncio.create_task(process.stdout.read(1024))
    stderr_task = asyncio.create_task(process.stderr.read(1024))
    pending = {stdout_task: "stdout", stderr_task: "stderr"}

    try:
        while pending:
            done, _ = await asyncio.wait(pending.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                stream = pending.pop(task)
                chunk = task.result()
                if chunk:
                    yield RuntimeCommandEvent(
                        stream=stream,
                        content=chunk.decode("utf-8", errors="replace"),
                    )
                    if stream == "stdout":
                        next_task = asyncio.create_task(process.stdout.read(1024))
                    else:
                        next_task = asyncio.create_task(process.stderr.read(1024))
                    pending[next_task] = stream

        returncode = await process.wait()
        yield RuntimeCommandEvent(stream="exit", returncode=returncode)
    finally:
        for task in pending:
            task.cancel()
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


class HermesCLIBackedRuntime(HermesRuntime):
    def __init__(
        self,
        hermes_root: Path | None = None,
        hermes_home: Path | None = None,
        workspace_path: Path | None = None,
        model: str | None = None,
        provider: str | None = None,
        toolsets: str | None = None,
        runner: RuntimeCommandRunner | None = None,
        stream_runner: RuntimeCommandStreamRunner | None = None,
        python_executable: str = sys.executable,
    ):
        self.hermes_root = hermes_root or Path(__file__).resolve().parents[4] / "packages" / "hermes"
        self.hermes_home = hermes_home
        self.workspace_path = workspace_path or Path.cwd()
        self.model = model
        self.provider = provider
        self.toolsets = toolsets
        self.runner = runner
        self.stream_runner = stream_runner
        self.python_executable = python_executable

    @property
    def hermes_executable(self) -> Path:
        return self.hermes_root / "hermes"

    def build_command(self, message: RuntimeMessage) -> list[str]:
        prompt = message.content
        if message.system_prompt:
            prompt = f"{message.system_prompt.strip()}\n\nUser request:\n{message.content}"
        command = [self.python_executable, str(self.hermes_executable), "-z", prompt]
        model = message.model or self.model
        provider = message.provider or self.provider
        if model:
            command.extend(["--model", model])
        if provider:
            command.extend(["--provider", provider])
        if self.toolsets:
            command.extend(["--toolsets", self.toolsets])
        return command

    def build_environment(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.hermes_home is not None:
            env["HERMES_HOME"] = str(self.hermes_home)
        return env

    async def send_message(
        self,
        session_id: str,
        message: RuntimeMessage,
    ) -> AsyncIterator[DashboardEvent]:
        command = self.build_command(message)
        yield DashboardEvent(
            session_id=session_id,
            type="agent.tool.started",
            payload={"tool": "hermes.oneshot", "command": command},
            source="hermes.cli",
        )
        if self.stream_runner is not None or self.runner is None:
            async for event in self._send_message_streaming(session_id, message, command):
                yield event
            return

        result = await self.runner(command, self.workspace_path, self.build_environment())
        if result.returncode == 0:
            content = result.stdout.strip()
            yield DashboardEvent(
                session_id=session_id,
                type="chat.message.delta",
                payload={"role": "assistant", "content": content},
                source="hermes.cli",
            )
            yield DashboardEvent(
                session_id=session_id,
                type="chat.message.completed",
                payload={"role": "assistant", "content": content},
                source="hermes.cli",
            )
            for event in analyze_successful_turn(
                session_id=session_id,
                message=message,
                assistant_content=content,
                tool_name="hermes.oneshot",
            ):
                yield event
            yield DashboardEvent(
                session_id=session_id,
                type="agent.tool.completed",
                payload={"tool": "hermes.oneshot", "returncode": result.returncode},
                source="hermes.cli",
            )
            return

        error_message = result.stderr.strip() or result.stdout.strip() or f"Hermes exited with {result.returncode}"
        for event in analyze_failed_turn(
            session_id=session_id,
            message=message,
            error_message=error_message,
            where_it_happened="hermes.oneshot",
        ):
            yield event
        yield DashboardEvent(
            session_id=session_id,
            type="debug.error.detected",
            payload={
                "error_message": error_message,
                "where_it_happened": "hermes.oneshot",
                "returncode": result.returncode,
            },
            source="hermes.cli",
        )

    async def _send_message_streaming(
        self,
        session_id: str,
        message: RuntimeMessage,
        command: list[str],
    ) -> AsyncIterator[DashboardEvent]:
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        returncode = 0
        stream_runner = self.stream_runner or stream_subprocess_command

        async for command_event in stream_runner(command, self.workspace_path, self.build_environment()):
            if command_event.stream == "exit":
                returncode = command_event.returncode if command_event.returncode is not None else 0
                continue

            if command_event.stream == "stdout":
                stdout_parts.append(command_event.content)
            elif command_event.stream == "stderr":
                stderr_parts.append(command_event.content)

            yield DashboardEvent(
                session_id=session_id,
                type="agent.log.chunk",
                payload={
                    "tool": "hermes.oneshot",
                    "stream": command_event.stream,
                    "content": command_event.content,
                },
                source="hermes.cli",
            )
            if command_event.stream == "stdout":
                yield DashboardEvent(
                    session_id=session_id,
                    type="chat.message.delta",
                    payload={"role": "assistant", "content": command_event.content},
                    source="hermes.cli",
                )

        stdout = "".join(stdout_parts).strip()
        stderr = "".join(stderr_parts).strip()
        if returncode == 0:
            yield DashboardEvent(
                session_id=session_id,
                type="chat.message.completed",
                payload={"role": "assistant", "content": stdout},
                source="hermes.cli",
            )
            for event in analyze_successful_turn(
                session_id=session_id,
                message=message,
                assistant_content=stdout,
                tool_name="hermes.oneshot",
            ):
                yield event
            yield DashboardEvent(
                session_id=session_id,
                type="agent.tool.completed",
                payload={"tool": "hermes.oneshot", "returncode": returncode},
                source="hermes.cli",
            )
            return

        error_message = stderr or stdout or f"Hermes exited with {returncode}"
        for event in analyze_failed_turn(
            session_id=session_id,
            message=message,
            error_message=error_message,
            where_it_happened="hermes.oneshot",
        ):
            yield event
        yield DashboardEvent(
            session_id=session_id,
            type="debug.error.detected",
            payload={
                "error_message": error_message,
                "where_it_happened": "hermes.oneshot",
                "returncode": returncode,
            },
            source="hermes.cli",
        )
