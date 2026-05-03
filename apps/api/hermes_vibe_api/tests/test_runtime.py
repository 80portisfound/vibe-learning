import pytest

from hermes_vibe_api.hermes.runtime import InProcessHermesRuntime, RuntimeMessage


@pytest.mark.asyncio
async def test_stub_runtime_streams_user_message_echo_events():
    runtime = InProcessHermesRuntime()

    events = [
        event
        async for event in runtime.send_message(
            session_id="s1",
            message=RuntimeMessage(role="user", content="hello"),
        )
    ]

    assert [event.type for event in events] == [
        "chat.message.delta",
        "chat.message.completed",
    ]
    assert events[0].payload["content"] == "Hermes stub received: hello"
