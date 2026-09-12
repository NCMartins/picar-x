"""Spoken replies through the Robot Hat speaker.

Uses ``espeak-ng``, which is a few megabytes and runs comfortably on a Pi 4
with no network round-trip - important here, because the reply is often
"stop, there's a step in front of me" and a cloud TTS round-trip is the wrong
place to spend a second.

Everything degrades rather than fails: if espeak-ng isn't installed, or the
Robot Hat's amplifier can't be switched on, speaking becomes a no-op and the
caller still gets the reply text back to speak in the browser instead.
"""

import logging
import shutil
import subprocess
import threading

from config.config import (
    VOICE_TTS_AMPLITUDE,
    VOICE_TTS_COMMAND,
    VOICE_TTS_ENABLED,
    VOICE_TTS_VOICE,
    VOICE_TTS_WPM,
)

logger = logging.getLogger(__name__)

# Long enough for any sentence espeak will be handed, short enough that a
# wedged process can't hold the speech lock for the rest of the session.
_SPEAK_TIMEOUT_SECONDS = 30


class Speaker:
    """Serialized text-to-speech on the Pi's audio output."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current: subprocess.Popen | None = None
        self._binary = shutil.which(VOICE_TTS_COMMAND) if VOICE_TTS_ENABLED else None
        self._amp_enabled = False

        if VOICE_TTS_ENABLED and not self._binary:
            logger.warning(
                "%s not found - spoken replies will fall back to the browser. "
                "Install it with: sudo apt-get install -y espeak-ng",
                VOICE_TTS_COMMAND,
            )

    @property
    def available(self) -> bool:
        return self._binary is not None

    @property
    def speaking(self) -> bool:
        """True while a reply is being spoken.

        The on-board microphone sits centimetres from the speaker, so the
        listener uses this to discard audio the car is producing itself -
        without it, the car wakes on its own replies and talks to itself.
        """
        process = self._current
        return process is not None and process.poll() is None

    def _enable_amplifier(self) -> None:
        """Switch on the Robot Hat's speaker amp (once, best effort).

        Robot Hat v4 gates the speaker behind a GPIO-controlled amplifier;
        without this the audio plays into silence. The helper's location has
        moved between robot-hat releases, so try the known spellings and give
        up quietly - a silent speaker is not a reason to fail a command.
        """
        if self._amp_enabled:
            return
        self._amp_enabled = True
        try:
            import robot_hat
        except ImportError:
            return
        for attr in ("enable_speaker", "enable_amp"):
            helper = getattr(robot_hat, attr, None) or getattr(
                getattr(robot_hat, "utils", None), attr, None
            )
            if callable(helper):
                try:
                    helper()
                    logger.info("Robot Hat speaker enabled via robot_hat.%s", attr)
                except Exception as exc:
                    logger.warning("robot_hat.%s failed: %s", attr, exc)
                return
        logger.debug("No robot_hat speaker-enable helper found; assuming amp is on")

    def say(self, text: str, blocking: bool = False) -> bool:
        """Speak `text`. Returns False if TTS isn't available.

        Non-blocking by default so the HTTP response (and therefore the web
        UI) isn't held open for the length of the sentence.
        """
        if not text or not text.strip() or not self.available:
            return False

        if blocking:
            self._speak(text)
        else:
            threading.Thread(target=self._speak, args=(text,), daemon=True).start()
        return True

    def _speak(self, text: str) -> None:
        self._enable_amplifier()
        command = [
            self._binary,
            "-v", VOICE_TTS_VOICE,
            "-s", str(VOICE_TTS_WPM),
            "-a", str(VOICE_TTS_AMPLITUDE),
            "--", text,
        ]
        with self._lock:
            try:
                self._current = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                _, stderr = self._current.communicate(timeout=_SPEAK_TIMEOUT_SECONDS)
                if self._current.returncode != 0:
                    logger.warning(
                        "%s exited %s: %s",
                        VOICE_TTS_COMMAND,
                        self._current.returncode,
                        stderr.decode("utf-8", "replace").strip(),
                    )
            except subprocess.TimeoutExpired:
                logger.warning("%s timed out; killing it", VOICE_TTS_COMMAND)
                self._current.kill()
                self._current.wait()
            except Exception:
                logger.exception("Failed to speak")
            finally:
                self._current = None

    def silence(self) -> None:
        """Cut off speech in progress - used by the emergency stop.

        Deliberately does not take the lock: the point is to interrupt the
        thread that holds it.
        """
        process = self._current
        if process and process.poll() is None:
            try:
                process.kill()
            except Exception:
                logger.debug("Could not kill speech process", exc_info=True)


_speaker: Speaker | None = None


def get_speaker() -> Speaker:
    """Get or create the speaker singleton."""
    global _speaker
    if _speaker is None:
        _speaker = Speaker()
    return _speaker
