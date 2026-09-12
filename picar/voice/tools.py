"""Claude tool definitions for the robot, and dispatch to RobotSkills.

The tool schemas here are what the model actually sees, so the descriptions
carry the operating limits in plain language: a model that knows a drive is
capped at two seconds asks for three short hops instead of one long one, and
explains the cap to the operator rather than appearing to ignore them.

The clamping in ``skills.py`` is what *enforces* the limits - these
descriptions only make the model cooperate with them.
"""

import base64
import logging

from config.config import (
    SERVO_MAX_ANGLE,
    SERVO_MIN_ANGLE,
    VOICE_DEFAULT_SPEED,
    VOICE_MAX_MOVE_SECONDS,
    VOICE_MAX_SPEED,
    VOICE_MAX_TOTAL_MOVE_SECONDS,
)
from .skills import MovementAborted, MovementBudgetExceeded, RobotSkills

logger = logging.getLogger(__name__)


def build_tool_definitions() -> list[dict]:
    """Build the tool list, with the configured limits baked into the text."""
    return [
        {
            "name": "drive",
            "description": (
                "Drive the car straight forward or backward for a short, fixed "
                f"time, then stop automatically. A single call may run at most "
                f"{VOICE_MAX_MOVE_SECONDS:.1f} seconds and each spoken command has a "
                f"total movement budget of {VOICE_MAX_TOTAL_MOVE_SECONDS:.1f} seconds "
                "across all calls. Longer values are silently clamped, so to cover "
                "more ground make several calls and check what you can see between "
                "them. At the default speed the car covers very roughly 20-30 cm per "
                "second, but this varies with battery charge and floor surface, so "
                "treat any distance as an estimate and verify with the camera."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["forward", "backward"],
                        "description": "Which way to drive.",
                    },
                    "duration_seconds": {
                        "type": "number",
                        "description": (
                            f"How long to drive, 0.1 to {VOICE_MAX_MOVE_SECONDS:.1f} "
                            "seconds. Use 0.3-0.5 for a nudge, 1.0 for a normal move."
                        ),
                    },
                    "speed": {
                        "type": "integer",
                        "description": (
                            f"Motor power percent, 0 to {VOICE_MAX_SPEED}. "
                            f"Defaults to {VOICE_DEFAULT_SPEED}. Use a low value "
                            "indoors or near obstacles."
                        ),
                    },
                    "steering_angle": {
                        "type": "integer",
                        "description": (
                            "Optional front-wheel angle in degrees while driving; "
                            "negative is left, positive is right, 0 is straight. "
                            "Prefer the 'turn' tool for ordinary turns."
                        ),
                    },
                },
                "required": ["direction", "duration_seconds"],
            },
        },
        {
            "name": "turn",
            "description": (
                "Turn left or right. The car steers with its front wheels, so it "
                "turns only while rolling forward and cannot pivot on the spot - "
                "this drives forward with the wheels turned, then stops and "
                "re-centres them. Needs roughly half a metre of clear space ahead. "
                "Same duration cap and movement budget as 'drive'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["left", "right"],
                        "description": "Which way to turn.",
                    },
                    "duration_seconds": {
                        "type": "number",
                        "description": (
                            f"How long to hold the turn, up to "
                            f"{VOICE_MAX_MOVE_SECONDS:.1f} seconds. About 1.0 second "
                            "gives a gentle course correction."
                        ),
                    },
                    "speed": {
                        "type": "integer",
                        "description": f"Motor power percent, up to {VOICE_MAX_SPEED}.",
                    },
                    "sharpness": {
                        "type": "number",
                        "description": (
                            "How hard to turn, 0 to 1, where 1 is full steering "
                            "lock. Defaults to 1."
                        ),
                    },
                },
                "required": ["direction", "duration_seconds"],
            },
        },
        {
            "name": "stop",
            "description": (
                "Stop the motors immediately and centre the steering. Movements "
                "already stop themselves, so use this only when the operator asks "
                "you to stop or you decide mid-task that continuing is unsafe."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "look",
            "description": (
                "Aim the camera without moving the car, using its pan/tilt servos. "
                "Useful for checking beside or behind the car before driving. This "
                "moves the camera only - it does not return a picture, so call "
                "'see' afterwards to look through it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pan": {
                        "type": "integer",
                        "description": (
                            f"Left/right angle, {SERVO_MIN_ANGLE} to {SERVO_MAX_ANGLE} "
                            "degrees. Negative is left, 0 is straight ahead. Omit to "
                            "leave unchanged."
                        ),
                    },
                    "tilt": {
                        "type": "integer",
                        "description": (
                            f"Down/up angle, {SERVO_MIN_ANGLE} to {SERVO_MAX_ANGLE} "
                            "degrees. Negative looks down at the floor, which is the "
                            "useful direction for spotting obstacles. Omit to leave "
                            "unchanged."
                        ),
                    },
                },
            },
        },
        {
            "name": "see",
            "description": (
                "Take a photo through the car's camera and look at it. Use this "
                "whenever the operator asks what you can see, to identify something, "
                "or to check the way is clear before driving. Always look before "
                "driving somewhere you haven't checked."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_state",
            "description": (
                "Read the car's current pose: motor speeds, steering angle, camera "
                "angles, whether hardware is actually connected, and how much "
                "movement budget is left for this command."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
    ]


def _error_result(tool_use_id: str, message: str) -> dict:
    """A tool_result the model can reason about, rather than a dropped turn."""
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": message,
        "is_error": True,
    }


def execute_tool(skills: RobotSkills, tool_use_id: str, name: str, params: dict) -> dict:
    """Run one tool call and build its ``tool_result`` block.

    Never raises: a failure becomes an ``is_error`` result so the model gets a
    chance to explain or recover. The one thing that does propagate upward is
    an abort, which the caller detects via ``skills.aborted``.
    """
    params = params if isinstance(params, dict) else {}

    try:
        if name == "drive":
            text = skills.drive(
                direction=params.get("direction", "forward"),
                duration_seconds=params.get("duration_seconds", 1.0),
                speed=params.get("speed"),
                steering_angle=params.get("steering_angle", 0) or 0,
            )
        elif name == "turn":
            text = skills.turn(
                direction=params.get("direction", "left"),
                duration_seconds=params.get("duration_seconds", 1.0),
                speed=params.get("speed"),
                sharpness=params.get("sharpness", 1.0),
            )
        elif name == "stop":
            text = skills.stop()
        elif name == "look":
            text = skills.look(pan=params.get("pan"), tilt=params.get("tilt"))
        elif name == "get_state":
            state = skills.get_state()
            text = "\n".join(f"{key}: {value}" for key, value in state.items())
        elif name == "see":
            return _build_see_result(skills, tool_use_id)
        else:
            return _error_result(tool_use_id, f"Unknown tool: {name}")

    except MovementAborted as exc:
        return _error_result(tool_use_id, f"{exc} Tell the operator you have stopped.")
    except MovementBudgetExceeded as exc:
        return _error_result(tool_use_id, str(exc))
    except ValueError as exc:
        return _error_result(tool_use_id, f"Invalid parameters: {exc}")
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return _error_result(tool_use_id, f"The {name} command failed on the robot: {exc}")

    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}


def _build_see_result(skills: RobotSkills, tool_use_id: str) -> dict:
    """Capture a frame and return it as an image block for the model to read."""
    frame = skills.capture_view()
    if not frame:
        return _error_result(
            tool_use_id,
            "The camera returned no image. It may not be connected. "
            "Tell the operator you cannot see right now.",
        )

    state = skills.get_state()
    caption = (
        f"Live view from the car's camera, taken just now at "
        f"pan {state['camera_pan']} degrees, tilt {state['camera_tilt']} degrees."
    )
    if not state["camera_available"]:
        caption += (
            " NOTE: the camera is in simulation mode, so this is a blank "
            "placeholder image and not a real view. Say so rather than "
            "describing it."
        )

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(frame).decode("ascii"),
                },
            },
            {"type": "text", "text": caption},
        ],
    }
