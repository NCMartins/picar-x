"""Optional on-Pi speech-to-text, for running untethered from a phone.

The default input path needs none of this: the browser's Web Speech API does
the listening on your phone and POSTs plain text, which costs no CPU on the
Pi and needs no extra hardware. Use this module instead when you want the car
to listen through a USB microphone of its own - then the phone is no longer
in the loop at all.

Needs ``faster-whisper`` (``uv pip install faster-whisper``) and enough
patience for a Pi 4: the ``base.en`` model transcribes a short command in
roughly one to three seconds. ``tiny.en`` is about twice as fast and noticeably
worse with names. The model is loaded lazily on the first request, so an
install that never uses this path never pays the ~150 MB of RAM.
"""

import logging
import threading

from config.config import VOICE_STT_DEVICE, VOICE_STT_MODEL

logger = logging.getLogger(__name__)


class TranscriberUnavailable(RuntimeError):
    """Raised when transcription is requested without faster-whisper installed."""


class Transcriber:
    """Lazily-loaded local Whisper transcription."""

    def __init__(self):
        self._model = None
        self._lock = threading.Lock()
        self._load_failed = False

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        if self._load_failed:
            raise TranscriberUnavailable(
                "faster-whisper is not installed on the Pi. Either install it "
                "(uv pip install faster-whisper) to use a USB microphone, or use "
                "the browser microphone, which needs no extra software."
            )

        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                self._load_failed = True
                raise TranscriberUnavailable(
                    "faster-whisper is not installed on the Pi. Either install it "
                    "(uv pip install faster-whisper) to use a USB microphone, or "
                    "use the browser microphone, which needs no extra software."
                )

            logger.info("Loading Whisper model %s (this takes a moment)", VOICE_STT_MODEL)
            self._model = WhisperModel(
                VOICE_STT_MODEL, device="cpu", compute_type=VOICE_STT_DEVICE
            )
            logger.info("Whisper model loaded")
        return self._model

    def transcribe(self, audio) -> str:
        """Transcribe audio to text. Returns "" if nothing was said.

        Accepts a path or an open binary file object - the on-board listener
        passes an in-memory WAV so a short command never touches the SD card.
        """
        model = self._ensure_model()
        segments, _info = model.transcribe(
            audio,
            language="en",
            beam_size=1,          # greedy: this is a short command, not a lecture
            vad_filter=True,      # drop the silence around a push-to-talk clip
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


_transcriber: Transcriber | None = None


def get_transcriber() -> Transcriber:
    """Get or create the transcriber singleton."""
    global _transcriber
    if _transcriber is None:
        _transcriber = Transcriber()
    return _transcriber
