"""Wake-word detection, in two flavours, plus stop-phrase matching.

Two backends, because they trade off differently on a Pi 4:

* **transcript** (default) - the microphone's speech segments are transcribed
  anyway, so the wake word is just a string match on the result. Any phrase
  works, including "Claude", and there's no extra model to install. The cost
  is that every segment of speech in the room gets transcribed, which is a
  real CPU load in a noisy room (silence is free - the VAD gates it).
  It also allows the natural one-breath form, "Claude, drive forward a bit",
  because the words after the wake word are already transcribed.

* **openwakeword** - a small always-on ONNX classifier that watches the raw
  audio and only wakes the transcriber when it fires. Much cheaper in a noisy
  room, but limited to the phrases it has models for: the pretrained set is
  "hey_jarvis", "alexa", "hey_mycroft" and friends, with no "hey Claude"
  among them unless you train and supply your own model file.

``auto`` picks openwakeword when it's installed *and* configured with a model
it actually has, and otherwise falls back to the transcript backend.
"""

import logging
import re

from config.config import (
    VOICE_WAKE_BACKEND,
    VOICE_WAKE_MODEL,
    VOICE_WAKE_THRESHOLD,
    VOICE_WAKE_WORD,
)

logger = logging.getLogger(__name__)

# Recognisers mishear "Claude" constantly, so accept the near misses rather
# than making the operator enunciate at their own robot.
WAKE_WORD_VARIANTS = {
    "claude": ["claude", "cloud", "clode", "clod", "klaud", "closed"],
}

# Matched before anything reaches the model, so stopping never waits on an
# API call. Kept deliberately short: these are the words someone shouts.
STOP_PHRASES = {"stop", "stop stop", "halt", "whoa", "woah", "freeze", "stop it"}


def normalize(text: str) -> str:
    """Lowercase and strip punctuation, for forgiving phrase matching."""
    return re.sub(r"[^\w\s]", "", (text or "").lower()).strip()


def is_stop_phrase(text: str) -> bool:
    """True if the utterance is an emergency stop and nothing else.

    Deliberately exact rather than a substring test: "stop at the door" is an
    instruction to the model, not a panic stop, and treating it as one would
    make the car ignore half of what it's told.
    """
    return normalize(text) in STOP_PHRASES


def _wake_variants(wake_word: str) -> list[str]:
    normalized = normalize(wake_word)
    return WAKE_WORD_VARIANTS.get(normalized, [normalized])


class TranscriptWakeWord:
    """Matches the wake word in already-transcribed text."""

    streaming = False

    def __init__(self, wake_word: str = VOICE_WAKE_WORD):
        self.wake_word = wake_word
        self._variants = _wake_variants(wake_word)

    def check_transcript(self, text: str) -> tuple[bool, str]:
        """Look for the wake word and return anything said after it.

        Returns ``(detected, remainder)``. An empty remainder means the
        operator said only the wake word and the command is still coming.
        """
        words = normalize(text).split()
        if not words:
            return False, ""

        # Only near the start: "the cloud is nice" shouldn't wake the car.
        for index in range(min(2, len(words))):
            if words[index] in self._variants:
                remainder = " ".join(words[index + 1:]).strip()
                return True, _restore_case(text, remainder)
        return False, ""

    def reset(self) -> None:
        """Nothing to reset - this backend holds no audio state."""


def _restore_case(original: str, normalized_remainder: str) -> str:
    """Recover the original casing/punctuation of the remainder if we can.

    The model reads better prose than a lowercased, punctuation-stripped
    string, so prefer the original text when the tail lines up.
    """
    if not normalized_remainder:
        return ""
    words = normalized_remainder.split()
    original_words = original.split()
    if len(original_words) >= len(words):
        return " ".join(original_words[-len(words):]).strip(" ,")
    return normalized_remainder


class OpenWakeWord:
    """Always-on classifier over the raw audio stream."""

    streaming = True

    def __init__(self, model_name: str = VOICE_WAKE_MODEL,
                 threshold: float = VOICE_WAKE_THRESHOLD):
        from openwakeword.model import Model  # raises ImportError if absent

        self.threshold = threshold
        self.model_name = model_name
        self._model = Model(wakeword_models=[model_name])
        logger.info("openWakeWord loaded with model %s", model_name)

    def feed(self, frame: bytes) -> bool:
        """Feed one audio frame; True when the wake word just fired."""
        import numpy as np

        samples = np.frombuffer(frame, dtype=np.int16)
        scores = self._model.predict(samples)
        return any(score >= self.threshold for score in scores.values())

    def reset(self) -> None:
        """Clear the model's internal buffers after a detection."""
        try:
            self._model.reset()
        except Exception:
            logger.debug("openWakeWord reset failed", exc_info=True)


def build_detector(backend: str = VOICE_WAKE_BACKEND):
    """Build the configured detector, falling back when one isn't available."""
    backend = (backend or "auto").lower()

    if backend in ("auto", "openwakeword"):
        try:
            return OpenWakeWord()
        except ImportError:
            if backend == "openwakeword":
                raise RuntimeError(
                    "PICAR_VOICE_WAKE_BACKEND=openwakeword but the openwakeword "
                    "package isn't installed. Install it, or use the default "
                    "'auto' to fall back to transcript matching."
                )
            logger.info(
                "openwakeword not installed; matching the wake word in "
                "transcribed speech instead."
            )
        except Exception as exc:
            if backend == "openwakeword":
                raise
            logger.warning(
                "openWakeWord could not load model %s (%s); falling back to "
                "transcript matching.", VOICE_WAKE_MODEL, exc
            )

    return TranscriptWakeWord()
