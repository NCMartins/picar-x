"""The voice agent: spoken command in, robot actions and a spoken reply out.

This is a manual agentic loop rather than the SDK's tool runner, for three
reasons specific to driving a robot:

* an emergency stop has to break the loop *between* tool calls, not after
  the model finishes its turn;
* camera frames come back as image blocks inside tool results, and old ones
  have to be pruned from history or every request re-uploads every photo
  the car has ever taken;
* each executed action is recorded for the web UI's activity log.

Conversation history is kept in whole turns (a user message plus the
assistant/tool exchange it produced) so that pruning can never orphan a
``tool_use`` block from its ``tool_result`` - which the API rejects.
"""

import logging
import threading

from config.config import (
    ANTHROPIC_API_KEY,
    VOICE_EFFORT,
    VOICE_ENABLED,
    VOICE_HISTORY_TURNS,
    VOICE_MAX_TOKENS,
    VOICE_MAX_TOOL_CALLS,
    VOICE_MODEL,
)
from .skills import RobotSkills
from .tools import build_tool_definitions, execute_tool

logger = logging.getLogger(__name__)

# Frames are only worth re-sending for the turn they were taken in. Older
# ones are replaced with a placeholder so the model still knows it looked,
# without paying to re-upload a stale photo on every subsequent request.
IMAGE_HISTORY_TURNS = 1

SYSTEM_PROMPT = """\
You are Claude, speaking and acting as a small four-wheeled robot car - a \
Sunfounder PiCar-X. You are not a chatbot that happens to have a robot \
attached: you *are* the car, and the person talking to you is standing \
nearby, watching you move. Answer in the first person about your own body \
("I can see a chair to my left", "I'll back up a bit").

HOW YOU EXPERIENCE THE WORLD
You have one camera on a pan/tilt mount, and that is your only sense. You \
cannot feel bumps, measure distance, or detect obstacles except by looking. \
You have no map and no memory of the room's layout beyond this conversation. \
If you don't know what's around you, the honest answer is to look, or to say \
you can't tell.

HOW YOU MOVE
You steer with your front wheels, so you turn only while rolling - you \
cannot pivot in place or move sideways. Each movement is short and stops \
itself; to go further, make several calls, looking between them. Your \
movement allowance per command is deliberately small. If you run out, say \
so plainly and ask the operator to repeat the command rather than trying to \
work around it.

SAFETY - THIS IS A REAL VEHICLE IN SOMEONE'S HOME
- Look before you drive anywhere you have not already seen. If the operator \
says "go forward" and you have no recent view ahead, take a photo first.
- Refuse to drive toward anything you can see is dangerous: stairs, a drop, \
a step down, water, pets, a person's feet, cables. Say what you can see and \
why you're not moving. The operator can pick you up and move you if they \
disagree.
- If a view is too dark or blurred to judge, treat it as unsafe, say so, and \
ask for light rather than guessing.
- Prefer the shortest movement that makes progress. When in doubt, move less.
- "Stop" always wins. Stop first, then talk.

HOW YOU TALK
Your replies are read aloud, so write for the ear: one or two short \
sentences, plain words, no lists, no markdown, no emoji, no stage \
directions. Say what you did and what you can see. If you're about to move, \
it's fine to say so in the same breath. When something failed or you \
refused, lead with that - don't bury it.

If a command is ambiguous ("go over there"), ask one short clarifying \
question instead of guessing at a direction.\
"""


class VoiceAgentUnavailable(RuntimeError):
    """Raised when the agent is asked to run without being configured."""


class VoiceAgent:
    """Runs spoken commands through Claude with the robot's tools attached."""

    def __init__(self, motor_ctrl, steering_ctrl, servo_ctrl, camera_stream):
        self.skills = RobotSkills(motor_ctrl, steering_ctrl, servo_ctrl, camera_stream)
        self.tools = build_tool_definitions()

        # Whole-turn history: each entry is the list of messages for one
        # exchange, always beginning with the operator's user message.
        self._turns: list[list[dict]] = []
        self._history_lock = threading.Lock()

        # One command at a time. A second request while the car is driving is
        # rejected rather than queued - queued driving commands act on a
        # world the operator has already changed.
        self._busy = threading.Lock()

        self._client = None
        self._drop_tuning_params = False
        if VOICE_ENABLED:
            self._client = self._build_client()

    def _build_client(self):
        try:
            import anthropic
        except ImportError:
            logger.error(
                "anthropic package not installed - voice control disabled. "
                "Install it with: uv pip install anthropic"
            )
            return None
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def busy(self) -> bool:
        return self._busy.locked()

    def reset(self) -> None:
        """Forget the conversation so far."""
        with self._history_lock:
            self._turns = []

    def emergency_stop(self) -> None:
        """Abort whatever is running and stop the car. Safe from any thread."""
        self.skills.abort()

    # ---------- the loop ----------

    def handle_command(self, text: str) -> dict:
        """Run one spoken command to completion.

        Returns a dict with the spoken `reply`, the `actions` taken, and
        whether the command was `aborted` or hit the tool-call `limit`.
        """
        if not self.available:
            raise VoiceAgentUnavailable(
                "Voice control is not configured. Set ANTHROPIC_API_KEY on the Pi "
                "and restart the server."
            )
        if not self._busy.acquire(blocking=False):
            raise RuntimeError("Still working on the previous command.")

        try:
            return self._run_turn(text)
        finally:
            self._busy.release()

    def _run_turn(self, text: str) -> dict:
        self.skills.begin_command()
        turn: list[dict] = [{"role": "user", "content": text}]
        tool_calls_used = 0
        hit_limit = False
        reply = ""

        while True:
            # Once the limit is hit the model gets one more turn to explain
            # itself, with no tools attached. Without that it could keep
            # requesting tools against a counter that never advances.
            response = self._create_message(
                self._flatten_history() + turn,
                with_tools=not hit_limit,
            )

            if response.stop_reason == "refusal":
                reply = "I can't help with that one, sorry."
                turn.append({"role": "assistant", "content": reply})
                break

            turn.append({"role": "assistant", "content": response.content})
            reply = self._extract_text(response) or reply

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                break

            if hit_limit or tool_calls_used + len(tool_uses) > VOICE_MAX_TOOL_CALLS:
                hit_limit = True
                turn.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": (
                                "Command cancelled: too many actions for one "
                                "instruction. Tell the operator briefly what you "
                                "managed to do and stop."
                            ),
                            "is_error": True,
                        }
                        for block in tool_uses
                    ],
                })
                continue

            results = []
            for block in tool_uses:
                results.append(execute_tool(self.skills, block.id, block.name, block.input))
                tool_calls_used += 1
            turn.append({"role": "user", "content": results})

            if self.skills.aborted:
                # Let the model say one closing line about having stopped,
                # but give it no further tools to call.
                reply = self._closing_line_after_abort(turn) or "Stopped."
                break

        self._commit_turn(turn)
        return {
            "reply": reply.strip(),
            "actions": [
                {"name": a.name, "detail": a.detail, "aborted": a.aborted}
                for a in self.skills.actions
            ],
            "aborted": self.skills.aborted,
            "tool_calls": tool_calls_used,
            "hit_tool_limit": hit_limit,
            "state": self.skills.get_state(),
        }

    def _closing_line_after_abort(self, turn: list[dict]) -> str:
        """Ask for one short sentence acknowledging the stop, without tools."""
        try:
            response = self._create_message(
                self._flatten_history() + turn,
                with_tools=False,
            )
            return self._extract_text(response)
        except Exception:
            logger.exception("Failed to get closing line after abort")
            return ""

    def _create_message(self, messages: list[dict], with_tools: bool = True):
        """One Messages API call, with the tuning params degrading gracefully.

        ``VOICE_MODEL`` is operator-configurable, and the thinking/effort
        parameters aren't accepted by every model (Haiku, for instance, takes
        neither). Rather than make the model choice a footgun, drop those two
        parameters and retry once if the API rejects them, then remember to
        leave them off for the rest of the process.
        """
        import anthropic

        kwargs = {
            "model": VOICE_MODEL,
            "max_tokens": VOICE_MAX_TOKENS,
            # One cache breakpoint at the end of the system prompt covers the
            # tool definitions too (tools render before system), so the whole
            # stable prefix is cached and only the conversation varies.
            "system": [{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            "messages": messages,
        }
        if with_tools:
            kwargs["tools"] = self.tools

        if not self._drop_tuning_params and VOICE_EFFORT.lower() != "none":
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["output_config"] = {"effort": VOICE_EFFORT}

        try:
            return self._client.messages.create(**kwargs)
        except anthropic.BadRequestError:
            if self._drop_tuning_params or "thinking" not in kwargs:
                raise
            logger.warning(
                "Model %s rejected the thinking/effort parameters; retrying "
                "without them and leaving them off from now on.",
                VOICE_MODEL,
            )
            self._drop_tuning_params = True
            kwargs.pop("thinking", None)
            kwargs.pop("output_config", None)
            return self._client.messages.create(**kwargs)

    # ---------- history ----------

    @staticmethod
    def _extract_text(response) -> str:
        return " ".join(
            block.text.strip() for block in response.content
            if block.type == "text" and block.text.strip()
        )

    def _commit_turn(self, turn: list[dict]) -> None:
        with self._history_lock:
            self._turns.append(turn)
            if len(self._turns) > VOICE_HISTORY_TURNS:
                self._turns = self._turns[-VOICE_HISTORY_TURNS:]
            # Strip photos out of everything but the most recent turns.
            for turn_messages in self._turns[:-IMAGE_HISTORY_TURNS]:
                _strip_images(turn_messages)

    def _flatten_history(self) -> list[dict]:
        with self._history_lock:
            return [message for turn in self._turns for message in turn]

    def get_transcript(self) -> list[dict]:
        """The conversation so far, flattened for display."""
        transcript = []
        for turn in self._flatten_history():
            if turn["role"] == "user" and isinstance(turn["content"], str):
                transcript.append({"role": "operator", "text": turn["content"]})
            elif turn["role"] == "assistant":
                content = turn["content"]
                if isinstance(content, str):
                    transcript.append({"role": "claude", "text": content})
                else:
                    text = " ".join(
                        block.text for block in content
                        if getattr(block, "type", None) == "text" and block.text.strip()
                    )
                    if text.strip():
                        transcript.append({"role": "claude", "text": text.strip()})
        return transcript


def _strip_images(messages: list[dict]) -> None:
    """Replace image blocks in tool results with a text placeholder in place."""
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            inner = block.get("content")
            if not isinstance(inner, list):
                continue
            block["content"] = [
                {"type": "text", "text": "[earlier camera view, no longer attached]"}
                if isinstance(part, dict) and part.get("type") == "image"
                else part
                for part in inner
            ]
