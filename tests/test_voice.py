"""Tests for voice control, all in simulation mode with a stubbed Claude API.

Nothing here talks to the network. The agent tests drive a fake client that
replays scripted API responses, which is what makes it possible to assert on
the things that actually matter for a robot: that the safety envelope holds,
that an emergency stop breaks the loop, and that a runaway model can't chain
tool calls forever.
"""

import threading
import time

import pytest

from config.config import (
    VOICE_MAX_MOVE_SECONDS,
    VOICE_MAX_SPEED,
    VOICE_MAX_TOOL_CALLS,
    VOICE_MAX_TOTAL_MOVE_SECONDS,
)
from picar.voice.agent import VoiceAgent
from picar.voice.skills import MovementAborted, MovementBudgetExceeded, RobotSkills
from picar.voice.tools import build_tool_definitions, execute_tool


# ==================== Fake Claude API ====================

class FakeBlock:
    """Stands in for a content block from the Messages API."""

    def __init__(self, type, text=None, id=None, name=None, input=None):
        self.type = type
        self.text = text
        self.id = id
        self.name = name
        self.input = input


class FakeResponse:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            # Default: a plain reply, so a test that under-scripts still ends.
            return FakeResponse([FakeBlock("text", text="Done.")])
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses=()):
        self.messages = FakeMessages(responses)


def text_reply(text):
    return FakeResponse([FakeBlock("text", text=text)])


def tool_reply(name, params, text=None, tool_id="tool_1"):
    blocks = []
    if text:
        blocks.append(FakeBlock("text", text=text))
    blocks.append(FakeBlock("tool_use", id=tool_id, name=name, input=params))
    return FakeResponse(blocks, stop_reason="tool_use")


# ==================== Fixtures ====================

@pytest.fixture
def skills(motor_controller, steering_controller, servo_controller, camera_stream):
    component = RobotSkills(
        motor_controller, steering_controller, servo_controller, camera_stream
    )
    component.begin_command()
    return component


@pytest.fixture
def agent(motor_controller, steering_controller, servo_controller, camera_stream):
    built = VoiceAgent(
        motor_controller, steering_controller, servo_controller, camera_stream
    )
    built._client = FakeClient()
    return built


def script(agent, *responses):
    """Point the agent at a scripted sequence of API responses."""
    agent._client = FakeClient(responses)
    return agent._client


# ==================== Safety envelope ====================

def test_drive_clamps_speed_above_limit(skills):
    skills.drive("forward", duration_seconds=0.1, speed=100)
    assert skills.actions[-1].fields["speed"] == VOICE_MAX_SPEED


def test_drive_clamps_duration_above_limit(skills):
    started = time.monotonic()
    skills.drive("forward", duration_seconds=30)
    elapsed = time.monotonic() - started
    assert skills.actions[-1].fields["duration"] == VOICE_MAX_MOVE_SECONDS
    # It really waited the clamped time, not the requested one.
    assert VOICE_MAX_MOVE_SECONDS <= elapsed < VOICE_MAX_MOVE_SECONDS + 1.0


def test_drive_always_stops_the_motors_afterwards(skills, motor_controller):
    skills.drive("forward", duration_seconds=0.2, speed=40)
    assert motor_controller.left_speed == 0
    assert motor_controller.right_speed == 0


def test_negative_speed_cannot_flip_direction(skills):
    skills.drive("forward", duration_seconds=0.1, speed=-80)
    assert skills.actions[-1].fields["speed"] == VOICE_MAX_SPEED


def test_drive_rejects_unknown_direction(skills):
    with pytest.raises(ValueError):
        skills.drive("sideways", duration_seconds=0.1)


def test_movement_budget_is_enforced_across_calls(skills):
    spent = 0.0
    while spent + VOICE_MAX_MOVE_SECONDS <= VOICE_MAX_TOTAL_MOVE_SECONDS:
        skills.drive("forward", duration_seconds=VOICE_MAX_MOVE_SECONDS, speed=1)
        spent += VOICE_MAX_MOVE_SECONDS

    with pytest.raises(MovementBudgetExceeded):
        skills.drive("forward", duration_seconds=VOICE_MAX_MOVE_SECONDS, speed=1)


def test_begin_command_restores_the_budget(skills):
    skills._spent_seconds = VOICE_MAX_TOTAL_MOVE_SECONDS
    skills.begin_command()
    assert skills.budget_remaining == VOICE_MAX_TOTAL_MOVE_SECONDS


def test_abort_interrupts_a_drive_in_progress(skills, motor_controller):
    threading.Timer(0.15, skills.abort).start()

    started = time.monotonic()
    with pytest.raises(MovementAborted):
        skills.drive("forward", duration_seconds=VOICE_MAX_MOVE_SECONDS, speed=30)
    elapsed = time.monotonic() - started

    # Stopped promptly rather than running the full duration.
    assert elapsed < VOICE_MAX_MOVE_SECONDS
    assert motor_controller.left_speed == 0
    assert skills.actions[-1].aborted is True


def test_movement_refused_while_abort_is_active(skills):
    skills.abort()
    with pytest.raises(MovementAborted):
        skills.drive("forward", duration_seconds=0.1)


def test_turn_steers_within_the_mechanical_limits(skills, steering_controller):
    from config.config import STEERING_MAX_ANGLE

    skills.turn("right", duration_seconds=0.1, sharpness=5.0)
    assert skills.actions[-1].name == "turn"
    # Steering is re-centred once the turn finishes.
    assert steering_controller.angle == 0
    assert f"{STEERING_MAX_ANGLE}deg" in skills.actions[-1].detail


def test_look_clamps_servo_angles(skills, servo_controller):
    from config.config import SERVO_MAX_ANGLE, SERVO_MIN_ANGLE

    skills.look(pan=500, tilt=-500)
    assert servo_controller.pan_angle == SERVO_MAX_ANGLE
    assert servo_controller.tilt_angle == SERVO_MIN_ANGLE


def test_look_leaves_omitted_axis_untouched(skills, servo_controller):
    skills.look(pan=20, tilt=10)
    skills.look(pan=-20)
    assert servo_controller.pan_angle == -20
    assert servo_controller.tilt_angle == 10


def test_get_state_reports_budget_and_pose(skills):
    state = skills.get_state()
    assert state["moving"] is False
    assert state["steering_angle"] == 0
    assert state["movement_budget_remaining_seconds"] == VOICE_MAX_TOTAL_MOVE_SECONDS


# ==================== Tool layer ====================

def test_tool_definitions_are_well_formed():
    tools = build_tool_definitions()
    names = {tool["name"] for tool in tools}
    assert names == {"drive", "turn", "stop", "look", "see", "get_state"}
    for tool in tools:
        assert tool["description"].strip()
        assert tool["input_schema"]["type"] == "object"


def test_tool_descriptions_state_the_limits():
    drive = next(t for t in build_tool_definitions() if t["name"] == "drive")
    assert f"{VOICE_MAX_MOVE_SECONDS:.1f} seconds" in drive["description"]


def test_execute_tool_returns_a_result_block(skills):
    result = execute_tool(skills, "abc", "drive",
                          {"direction": "forward", "duration_seconds": 0.1})
    assert result["tool_use_id"] == "abc"
    assert "Drove" in result["content"]
    assert not result.get("is_error")


def test_execute_tool_reports_errors_instead_of_raising(skills):
    result = execute_tool(skills, "abc", "drive", {"direction": "upward"})
    assert result["is_error"] is True
    assert "Invalid parameters" in result["content"]


def test_unknown_tool_is_an_error_result(skills):
    result = execute_tool(skills, "abc", "launch_rocket", {})
    assert result["is_error"] is True


def test_budget_exhaustion_reaches_the_model_as_an_error(skills):
    skills._spent_seconds = VOICE_MAX_TOTAL_MOVE_SECONDS
    result = execute_tool(skills, "abc", "drive",
                          {"direction": "forward", "duration_seconds": 1.0})
    assert result["is_error"] is True
    assert "budget" in result["content"].lower()


def test_see_returns_an_image_block(skills):
    result = execute_tool(skills, "abc", "see", {})
    blocks = result["content"]
    assert blocks[0]["type"] == "image"
    assert blocks[0]["source"]["media_type"] == "image/jpeg"
    assert blocks[0]["source"]["data"]
    # In simulation the frame is a placeholder, and the model is told so.
    assert "simulation mode" in blocks[1]["text"]


def test_get_state_tool_renders_as_text(skills):
    result = execute_tool(skills, "abc", "get_state", {})
    assert "steering_angle: 0" in result["content"]


# ==================== Agent loop ====================

def test_simple_reply_without_tools(agent):
    script(agent, text_reply("I'm parked and ready."))
    result = agent.handle_command("hello")
    assert result["reply"] == "I'm parked and ready."
    assert result["actions"] == []
    assert result["tool_calls"] == 0


def test_agent_executes_a_tool_then_replies(agent, motor_controller):
    script(
        agent,
        tool_reply("drive", {"direction": "forward", "duration_seconds": 0.2}),
        text_reply("Moved forward a little."),
    )
    result = agent.handle_command("go forward a bit")

    assert result["reply"] == "Moved forward a little."
    assert result["tool_calls"] == 1
    assert result["actions"][0]["name"] == "drive"
    assert motor_controller.left_speed == 0


def test_agent_sends_tools_and_a_cached_system_prompt(agent):
    script(agent, text_reply("Hi."))
    agent.handle_command("hello")

    request = agent._client.messages.calls[0]
    assert {tool["name"] for tool in request["tools"]} >= {"drive", "see"}
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_tool_call_limit_stops_a_runaway_loop(agent):
    # A model that asks to drive forever and never gives up. The loop has to
    # terminate on its own: a fake that only ever returns tool calls would
    # hang here if the limit didn't take tools away for the final turn.
    class RunawayMessages(FakeMessages):
        def create(self, **kwargs):
            self.calls.append(kwargs)
            if "tools" not in kwargs:
                # Tools withdrawn - the model can only talk now.
                return text_reply("I had to stop.")
            return tool_reply(
                "drive",
                {"direction": "forward", "duration_seconds": 0.05},
                tool_id=f"t{len(self.calls)}",
            )

    agent._client = FakeClient()
    agent._client.messages = RunawayMessages([])

    result = agent.handle_command("drive forever")

    assert result["hit_tool_limit"] is True
    assert result["tool_calls"] <= VOICE_MAX_TOOL_CALLS
    assert result["reply"] == "I had to stop."
    # The final request must have gone out with no tools attached.
    assert "tools" not in agent._client.messages.calls[-1]


def test_emergency_stop_breaks_the_loop(agent, motor_controller):
    script(
        agent,
        tool_reply("drive", {"direction": "forward",
                             "duration_seconds": VOICE_MAX_MOVE_SECONDS}),
        text_reply("Stopped."),
        text_reply("Stopped."),
    )
    threading.Timer(0.2, agent.emergency_stop).start()

    result = agent.handle_command("drive forward")
    assert result["aborted"] is True
    assert motor_controller.left_speed == 0


def test_refusal_is_handled_gracefully(agent):
    script(agent, FakeResponse([], stop_reason="refusal"))
    result = agent.handle_command("do something disallowed")
    assert result["reply"]
    assert result["actions"] == []


def test_second_command_while_busy_is_rejected(agent):
    agent._busy.acquire()
    try:
        with pytest.raises(RuntimeError, match="previous command"):
            agent.handle_command("go")
    finally:
        agent._busy.release()


def test_unconfigured_agent_refuses_clearly(agent):
    from picar.voice.agent import VoiceAgentUnavailable

    agent._client = None
    with pytest.raises(VoiceAgentUnavailable, match="ANTHROPIC_API_KEY"):
        agent.handle_command("go")


# ==================== History management ====================

def test_history_carries_across_commands(agent):
    script(agent, text_reply("One."), text_reply("Two."))
    agent.handle_command("first")
    agent.handle_command("second")

    sent = agent._client.messages.calls[-1]["messages"]
    assert sent[0]["content"] == "first"
    assert sent[-1]["content"] == "second"


def test_history_is_trimmed_to_the_configured_turn_count(agent):
    from config.config import VOICE_HISTORY_TURNS

    script(agent, *[text_reply(f"reply {i}") for i in range(VOICE_HISTORY_TURNS + 5)])
    for i in range(VOICE_HISTORY_TURNS + 5):
        agent.handle_command(f"command {i}")

    assert len(agent._turns) == VOICE_HISTORY_TURNS


def test_old_camera_images_are_stripped_from_history(agent):
    script(
        agent,
        tool_reply("see", {}),
        text_reply("I see a placeholder."),
        text_reply("Nothing new."),
        text_reply("Still nothing."),
    )
    agent.handle_command("what do you see")
    agent.handle_command("and now")
    agent.handle_command("and now again")

    sent = agent._client.messages.calls[-1]["messages"]
    images = [
        part
        for message in sent
        if isinstance(message.get("content"), list)
        for block in message["content"]
        if isinstance(block, dict) and block.get("type") == "tool_result"
        and isinstance(block.get("content"), list)
        for part in block["content"]
        if isinstance(part, dict) and part.get("type") == "image"
    ]
    assert images == []


def test_transcript_lists_both_sides(agent):
    script(agent, text_reply("Ready."))
    agent.handle_command("hello there")

    transcript = agent.get_transcript()
    assert {"role": "operator", "text": "hello there"} in transcript
    assert {"role": "claude", "text": "Ready."} in transcript


def test_reset_clears_the_conversation(agent):
    script(agent, text_reply("Ready."))
    agent.handle_command("hello")
    agent.reset()
    assert agent.get_transcript() == []


# ==================== HTTP API ====================

@pytest.fixture
def voice_client(client, monkeypatch):
    """Flask test client with the app's voice agent wired to a fake API."""
    import backend.app as app_module

    app_module.voice_agent.reset()
    monkeypatch.setattr(app_module.voice_agent, "_client", FakeClient())
    return client


def test_voice_status_endpoint(voice_client):
    body = voice_client.get("/api/voice/status").get_json()
    assert set(body) >= {"enabled", "available", "busy", "max_speed", "max_move_seconds"}


def test_health_reports_voice_fields(voice_client):
    body = voice_client.get("/api/health").get_json()
    assert set(body) >= {"voice_enabled", "voice_available", "voice_busy"}


def test_command_endpoint_runs_a_turn(voice_client, monkeypatch):
    import backend.app as app_module

    monkeypatch.setattr(
        app_module.voice_agent, "_client", FakeClient([text_reply("All clear.")])
    )
    response = voice_client.post("/api/voice/command", json={"text": "what do you see"})
    body = response.get_json()

    assert response.status_code == 200
    assert body["reply"] == "All clear."
    assert body["transcript"] == "what do you see"


def test_command_endpoint_rejects_an_empty_body(voice_client):
    response = voice_client.post("/api/voice/command", json={})
    assert response.status_code == 400


def test_command_endpoint_rejects_a_non_string(voice_client):
    response = voice_client.post("/api/voice/command", json={"text": 42})
    assert response.status_code == 400


def test_command_endpoint_reports_an_unconfigured_agent(voice_client, monkeypatch):
    import backend.app as app_module

    monkeypatch.setattr(app_module.voice_agent, "_client", None)
    response = voice_client.post("/api/voice/command", json={"text": "go"})
    assert response.status_code == 503


def test_command_endpoint_is_busy_while_one_runs(voice_client, monkeypatch):
    import backend.app as app_module

    app_module.voice_agent._busy.acquire()
    try:
        response = voice_client.post("/api/voice/command", json={"text": "go"})
        assert response.status_code == 409
    finally:
        app_module.voice_agent._busy.release()


def test_emergency_stop_endpoint_stops_the_motors(voice_client):
    import backend.app as app_module

    app_module.motor_ctrl.forward(60)
    response = voice_client.post("/api/voice/stop")

    assert response.status_code == 200
    assert app_module.motor_ctrl.left_speed == 0
    assert app_module.voice_agent.skills.aborted is True


def test_audio_endpoint_without_a_file(voice_client):
    response = voice_client.post("/api/voice/audio")
    assert response.status_code == 400


def test_audio_endpoint_without_faster_whisper(voice_client):
    import io

    response = voice_client.post(
        "/api/voice/audio",
        data={"audio": (io.BytesIO(b"not really audio"), "clip.wav")},
        content_type="multipart/form-data",
    )
    # 501 when faster-whisper isn't installed, which is the CI case.
    assert response.status_code in (400, 500, 501)


def test_reset_and_transcript_endpoints(voice_client, monkeypatch):
    import backend.app as app_module

    monkeypatch.setattr(
        app_module.voice_agent, "_client", FakeClient([text_reply("Hi.")])
    )
    voice_client.post("/api/voice/command", json={"text": "hello"})
    assert voice_client.get("/api/voice/transcript").get_json()["transcript"]

    voice_client.post("/api/voice/reset")
    assert voice_client.get("/api/voice/transcript").get_json()["transcript"] == []
