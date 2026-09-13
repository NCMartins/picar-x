"""Always-on microphone: the car listens for its own name, no phone involved.

The pipeline is deliberately boring:

    microphone ──► 30 ms frames ──► VAD ──► speech segment ──► wake word?
                                                                  │
                              spoken reply ◄── agent ◄── transcribe

Voice activity detection gates everything, so a silent room costs almost no
CPU - the expensive parts (transcription, and the model) only run once
someone has actually said something.

Two details that matter more than they look:

* **The car hears itself.** Its speaker is a few centimetres from the
  microphone, so audio captured while it's talking is discarded. Otherwise it
  wakes itself up on its own replies and talks to itself indefinitely.
* **"Stop" never reaches the model.** It's matched on the transcript and goes
  straight to the abort path, just like the button in the web UI.

The audio source is an injectable object rather than a hard dependency on
PortAudio, which is what makes this testable without a microphone.
"""

import logging
import threading
import time
from collections import deque

from config.config import (
    VOICE_COMMAND_WINDOW_SECONDS,
    VOICE_MAX_SEGMENT_SECONDS,
    VOICE_MIC_DEVICE,
    VOICE_MIC_SAMPLE_RATE,
    VOICE_MIN_SEGMENT_MS,
    VOICE_SEGMENT_SILENCE_MS,
    VOICE_VAD_AGGRESSIVENESS,
)
from .wakeword import build_detector, is_stop_phrase

logger = logging.getLogger(__name__)

FRAME_MS = 30                                    # webrtcvad accepts 10/20/30
FRAME_SAMPLES = VOICE_MIC_SAMPLE_RATE * FRAME_MS // 1000
FRAME_BYTES = FRAME_SAMPLES * 2                  # 16-bit mono

# Audio captured just before the wake word is kept, so a command spoken in one
# breath ("Claude, drive forward") isn't clipped at the front.
PREROLL_FRAMES = 10


class ListenerUnavailable(RuntimeError):
    """Raised when the microphone stack isn't installed or no mic is present."""


class MicrophoneSource:
    """Microphone frames via sounddevice/PortAudio."""

    def __init__(self, device=VOICE_MIC_DEVICE, sample_rate=VOICE_MIC_SAMPLE_RATE):
        try:
            import sounddevice
        except ImportError:
            raise ListenerUnavailable(
                "sounddevice isn't installed, so the car can't listen through "
                "its own microphone. Install the microphone extras "
                "(uv pip install -e '.[mic]') and the PortAudio system library "
                "(sudo apt-get install -y libportaudio2), or drive it from the "
                "browser microphone instead."
            )
        self._sounddevice = sounddevice
        self._device = device
        self._sample_rate = sample_rate
        self._stream = None

    def start(self) -> None:
        try:
            self._stream = self._sounddevice.RawInputStream(
                samplerate=self._sample_rate,
                blocksize=FRAME_SAMPLES,
                device=self._device,
                dtype="int16",
                channels=1,
            )
            self._stream.start()
        except Exception as exc:
            raise ListenerUnavailable(f"Could not open the microphone: {exc}")

    def read(self) -> bytes:
        """Read one frame. Overflows are expected and not worth logging."""
        data, _overflowed = self._stream.read(FRAME_SAMPLES)
        return bytes(data)

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                logger.debug("Error closing the microphone stream", exc_info=True)
            self._stream = None


class _AlwaysVoiced:
    """VAD stand-in used when webrtcvad isn't installed.

    Everything still works, just less efficiently: without voice activity
    detection every frame counts as speech, so segments are cut purely on the
    length limit and the transcriber runs more than it needs to.
    """

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        return True


def _build_vad():
    try:
        import webrtcvad
    except ImportError:
        logger.warning(
            "webrtcvad isn't installed - listening without voice activity "
            "detection, which uses noticeably more CPU."
        )
        return _AlwaysVoiced()
    return webrtcvad.Vad(VOICE_VAD_AGGRESSIVENESS)


class VoiceListener:
    """Background thread: wake word in, robot action and spoken reply out."""

    def __init__(self, agent, speaker, transcriber, source=None, detector=None):
        self._agent = agent
        self._speaker = speaker
        self._transcriber = transcriber
        self._source = source
        self._detector = detector
        self._vad = None

        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._error: str | None = None
        self._last_heard: str | None = None
        self._awaiting_command_until = 0.0

    # ---------- lifecycle ----------

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def status(self) -> dict:
        return {
            "running": self.running,
            "awaiting_command": time.monotonic() < self._awaiting_command_until,
            "last_heard": self._last_heard,
            "error": self._error,
            "backend": type(self._detector).__name__ if self._detector else None,
        }

    def start(self) -> None:
        """Start listening. Raises ListenerUnavailable if the stack is missing."""
        if self.running:
            return

        self._error = None
        if self._detector is None:
            self._detector = build_detector()
        if self._vad is None:
            self._vad = _build_vad()
        if self._source is None:
            self._source = MicrophoneSource()

        self._source.start()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="voice-listener", daemon=True
        )
        self._thread.start()
        logger.info("Listening for the wake word via %s", type(self._detector).__name__)

    def stop(self, timeout: float = 3.0) -> None:
        """Stop listening and release the microphone."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None
        if self._source is not None:
            self._source.stop()

    # ---------- the loop ----------

    def _run(self) -> None:
        preroll: deque[bytes] = deque(maxlen=PREROLL_FRAMES)
        segment: list[bytes] = []
        silence_frames = 0
        voiced_frames = 0
        woken_by_stream = False

        silence_limit = max(1, VOICE_SEGMENT_SILENCE_MS // FRAME_MS)
        max_frames = int(VOICE_MAX_SEGMENT_SECONDS * 1000 // FRAME_MS)
        min_frames = max(1, VOICE_MIN_SEGMENT_MS // FRAME_MS)

        while not self._stop.is_set():
            try:
                frame = self._source.read()
            except Exception as exc:
                self._error = f"Microphone read failed: {exc}"
                logger.exception("Microphone read failed; stopping the listener")
                return

            if frame is None:                       # source exhausted (tests)
                break
            if len(frame) != FRAME_BYTES:           # short read at shutdown
                continue

            # Ignore whatever the car itself is saying, or it wakes on its
            # own replies and holds a conversation with itself.
            if self._speaker.speaking:
                segment.clear()
                preroll.clear()
                silence_frames = 0
                continue

            if self._detector.streaming and not segment:
                try:
                    if self._detector.feed(frame):
                        logger.info("Wake word detected")
                        woken_by_stream = True
                        self._detector.reset()
                        self._awaiting_command_until = (
                            time.monotonic() + VOICE_COMMAND_WINDOW_SECONDS
                        )
                except Exception:
                    logger.exception("Wake word detector failed")

            is_speech = self._vad.is_speech(frame, VOICE_MIC_SAMPLE_RATE)

            if not segment:
                preroll.append(frame)
                if is_speech:
                    segment = list(preroll)
                    preroll.clear()
                    silence_frames = 0
                    voiced_frames = 1
                continue

            segment.append(frame)
            if is_speech:
                silence_frames = 0
                voiced_frames += 1
            else:
                silence_frames += 1

            if silence_frames >= silence_limit or len(segment) >= max_frames:
                # Drop the trailing silence that ended the segment - it's not
                # speech, and feeding it to the transcriber only costs time.
                captured = segment[:len(segment) - silence_frames] or segment
                spoken_frames = voiced_frames

                segment = []
                silence_frames = 0
                voiced_frames = 0

                # Measure the speech in the segment, not its total length:
                # otherwise the trailing silence pads a cough out past the
                # minimum and every door slam reaches the transcriber.
                if spoken_frames >= min_frames:
                    self._handle_segment(b"".join(captured), woken_by_stream)
                woken_by_stream = False

    def _handle_segment(self, audio: bytes, woken_by_stream: bool) -> None:
        """Decide whether a captured utterance is for us, and act on it."""
        awaiting = time.monotonic() < self._awaiting_command_until

        # A streaming detector has already decided this is for us; a
        # transcript detector needs the words first.
        if not (woken_by_stream or awaiting) and self._detector.streaming:
            return

        try:
            text = self._transcribe(audio)
        except Exception as exc:
            logger.warning("Could not transcribe what I heard: %s", exc)
            return

        if not text:
            return
        self._last_heard = text
        logger.info("Heard: %s", text)

        command = text
        if not (woken_by_stream or awaiting):
            detected, remainder = self._detector.check_transcript(text)
            if not detected:
                return
            if not remainder:
                # Just the name: wait for the command in the next breath.
                self._awaiting_command_until = (
                    time.monotonic() + VOICE_COMMAND_WINDOW_SECONDS
                )
                self._speaker.say("Yes?")
                return
            command = remainder

        self._awaiting_command_until = 0.0
        self._dispatch(command)

    def _transcribe(self, audio: bytes) -> str:
        import wave
        import io

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(VOICE_MIC_SAMPLE_RATE)
            handle.writeframes(audio)
        buffer.seek(0)
        return self._transcriber.transcribe(buffer)

    def _dispatch(self, command: str) -> None:
        """Run one command, exactly as the web UI would."""
        if is_stop_phrase(command):
            logger.info("Emergency stop by voice")
            self._agent.emergency_stop()
            self._speaker.silence()
            return

        try:
            result = self._agent.handle_command(command)
        except RuntimeError as exc:
            # Busy with a command from the web UI. Queueing would act on a
            # world the operator has already changed, so say so and drop it.
            logger.info("Ignoring '%s': %s", command, exc)
            self._speaker.say("One moment, I'm still working on the last thing.")
            return
        except Exception:
            logger.exception("Voice command failed")
            self._speaker.say("Something went wrong with that command.")
            return

        if result["reply"]:
            self._speaker.say(result["reply"])


_listener: VoiceListener | None = None


def get_listener() -> VoiceListener:
    """Get or create the listener singleton, wired to the voice stack."""
    global _listener
    if _listener is None:
        from . import get_voice_agent
        from .speech import get_speaker
        from .transcriber import get_transcriber

        _listener = VoiceListener(
            agent=get_voice_agent(),
            speaker=get_speaker(),
            transcriber=get_transcriber(),
        )
    return _listener
