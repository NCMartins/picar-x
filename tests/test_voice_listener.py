"""Tests for the on-board microphone path, with a fake microphone.

The audio source, VAD, transcriber, speaker and agent are all injected, so
these exercise the real segmentation and wake-word logic without needing a
microphone, PortAudio, or a Whisper model.
"""

import importlib.util

import pytest

from picar.voice.listener import FRAME_SAMPLES, VoiceListener
from picar.voice.wakeword import (
    STOP_PHRASES,
    TranscriptWakeWord,
    is_stop_phrase,
    normalize,
)

SPEECH_FRAME = b"\x01\x02" * FRAME_SAMPLES
SILENCE_FRAME = b"\x00\x00" * FRAME_SAMPLES

# Comfortably above the configured minimum segment length and end-of-speech
# silence, so a test utterance is always segmented the way a real one is.
SPEECH_FRAMES = 20
SILENCE_FRAMES = 30


def utterance():
    """One utterance: speech followed by enough silence to end the segment."""
    return [SPEECH_FRAME] * SPEECH_FRAMES + [SILENCE_FRAME] * SILENCE_FRAMES


# ==================== Fakes ====================

class FakeSource:
    """Replays a fixed list of frames, then signals end of stream."""

    def __init__(self, frames):
        self._frames = list(frames)
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def read(self):
        if not self._frames:
            return None          # ends the listener loop
        return self._frames.pop(0)

    def stop(self):
        self.stopped = True


class FakeVad:
    """Treats any non-zero frame as speech."""

    def is_speech(self, frame, sample_rate):
        return any(frame)


class FakeTranscriber:
    def __init__(self, texts):
        self._texts = list(texts)
        self.calls = 0

    def transcribe(self, audio):
        self.calls += 1
        return self._texts.pop(0) if self._texts else ""


class FakeSpeaker:
    def __init__(self):
        self.said = []
        self.speaking = False
        self.silenced = 0

    def say(self, text, blocking=False):
        self.said.append(text)
        return True

    def silence(self):
        self.silenced += 1


class FakeAgent:
    def __init__(self, reply="Done.", raises=None):
        self.commands = []
        self.stops = 0
        self._reply = reply
        self._raises = raises

    def handle_command(self, text):
        self.commands.append(text)
        if self._raises:
            raise self._raises
        return {"reply": self._reply, "actions": [], "aborted": False}

    def emergency_stop(self):
        self.stops += 1


def run_listener(frames, transcripts, agent=None, speaker=None):
    """Run the listener over a fixed audio stream until it's exhausted."""
    agent = agent or FakeAgent()
    speaker = speaker or FakeSpeaker()
    listener = VoiceListener(
        agent=agent,
        speaker=speaker,
        transcriber=FakeTranscriber(transcripts),
        source=FakeSource(frames),
        detector=TranscriptWakeWord("claude"),
    )
    listener._vad = FakeVad()
    listener.start()
    listener._thread.join(timeout=10)
    assert not listener._thread.is_alive(), "listener thread did not finish"
    return listener, agent, speaker


# ==================== Wake word matching ====================

def test_wake_word_with_command_in_one_breath():
    detector = TranscriptWakeWord("claude")
    detected, remainder = detector.check_transcript("Claude, drive forward a bit")
    assert detected is True
    assert "drive forward a bit" in remainder.lower()


def test_bare_wake_word_has_no_remainder():
    detected, remainder = TranscriptWakeWord("claude").check_transcript("Claude?")
    assert detected is True
    assert remainder == ""


def test_common_mishearings_still_wake_the_car():
    detector = TranscriptWakeWord("claude")
    for variant in ("cloud", "clode", "Clod,"):
        detected, _ = detector.check_transcript(f"{variant} stop there")
        assert detected is True, variant


def test_wake_word_must_come_near_the_start():
    detector = TranscriptWakeWord("claude")
    detected, _ = detector.check_transcript(
        "I was reading about the cloud yesterday"
    )
    assert detected is False


def test_unrelated_speech_does_not_wake():
    detected, _ = TranscriptWakeWord("claude").check_transcript(
        "did you watch the match last night"
    )
    assert detected is False


def test_custom_wake_word():
    detected, remainder = TranscriptWakeWord("rover").check_transcript(
        "Rover go forward"
    )
    assert detected is True
    assert remainder.lower() == "go forward"


def test_empty_transcript_does_not_wake():
    assert TranscriptWakeWord("claude").check_transcript("") == (False, "")


# ==================== Stop phrases ====================

@pytest.mark.parametrize("phrase", sorted(STOP_PHRASES))
def test_stop_phrases_are_recognised(phrase):
    assert is_stop_phrase(phrase)
    assert is_stop_phrase(phrase.upper() + "!")


def test_stop_inside_a_sentence_is_not_an_emergency_stop():
    # "stop at the door" is an instruction for the model, not a panic stop.
    assert is_stop_phrase("stop at the door") is False
    assert is_stop_phrase("don't stop") is False


def test_normalize_strips_punctuation_and_case():
    assert normalize("  Claude, STOP! ") == "claude stop"


# ==================== Listener behaviour ====================

def test_command_in_one_breath_is_dispatched():
    _listener, agent, speaker = run_listener(
        utterance(), ["Claude, drive forward a bit"]
    )
    assert len(agent.commands) == 1
    assert "drive forward" in agent.commands[0].lower()
    assert speaker.said == ["Done."]


def test_bare_wake_word_then_command_in_the_next_breath():
    _listener, agent, speaker = run_listener(
        utterance() * 2, ["Claude?", "what can you see"]
    )
    assert speaker.said[0] == "Yes?"
    assert agent.commands == ["what can you see"]


def test_speech_without_the_wake_word_is_ignored():
    _listener, agent, speaker = run_listener(
        utterance(), ["did you watch the match last night"]
    )
    assert agent.commands == []
    assert speaker.said == []


def test_spoken_stop_bypasses_the_model():
    _listener, agent, speaker = run_listener(utterance() * 2, ["Claude?", "stop"])
    assert agent.stops == 1
    assert agent.commands == []      # never reached the model
    assert speaker.silenced == 1


def test_the_car_ignores_its_own_voice():
    # Everything the microphone picks up while the car is talking is dropped,
    # or it wakes on its own replies and talks to itself.
    speaker = FakeSpeaker()
    speaker.speaking = True
    _listener, agent, _ = run_listener(
        utterance(), ["Claude, drive forward"], speaker=speaker
    )
    assert agent.commands == []


def test_a_busy_agent_is_reported_rather_than_queued():
    agent = FakeAgent(raises=RuntimeError("Still working on the previous command."))
    _listener, agent, speaker = run_listener(
        utterance(), ["Claude, drive forward"], agent=agent
    )
    assert agent.commands == ["drive forward"]
    assert "One moment" in speaker.said[0]


def test_an_agent_failure_is_spoken_not_swallowed():
    agent = FakeAgent(raises=ValueError("boom"))
    _listener, _agent, speaker = run_listener(
        utterance(), ["Claude, drive forward"], agent=agent
    )
    assert "went wrong" in speaker.said[0]


def test_blips_too_short_to_be_speech_are_dropped():
    # A cough: a couple of frames, below the minimum segment length.
    frames = [SPEECH_FRAME] * 2 + [SILENCE_FRAME] * SILENCE_FRAMES
    listener, agent, _ = run_listener(frames, ["Claude, go"])
    assert listener._transcriber.calls == 0
    assert agent.commands == []


def test_silence_alone_never_reaches_the_transcriber():
    listener, agent, _ = run_listener([SILENCE_FRAME] * 100, [])
    assert listener._transcriber.calls == 0
    assert agent.commands == []


def test_unintelligible_audio_is_dropped():
    _listener, agent, speaker = run_listener(utterance(), [""])
    assert agent.commands == []
    assert speaker.said == []


def test_listener_reports_what_it_last_heard():
    listener, _agent, _speaker = run_listener(utterance(), ["Claude, go forward"])
    assert listener.status["last_heard"] == "Claude, go forward"
    assert listener.status["backend"] == "TranscriptWakeWord"


def test_stop_releases_the_microphone():
    source = FakeSource([SILENCE_FRAME] * 10_000)
    listener = VoiceListener(
        agent=FakeAgent(),
        speaker=FakeSpeaker(),
        transcriber=FakeTranscriber([]),
        source=source,
        detector=TranscriptWakeWord("claude"),
    )
    listener._vad = FakeVad()
    listener.start()
    assert listener.running is True

    listener.stop()
    assert listener.running is False
    assert source.stopped is True


def test_a_microphone_failure_stops_the_listener_cleanly():
    class BrokenSource(FakeSource):
        def read(self):
            raise OSError("microphone unplugged")

    listener = VoiceListener(
        agent=FakeAgent(),
        speaker=FakeSpeaker(),
        transcriber=FakeTranscriber([]),
        source=BrokenSource([]),
        detector=TranscriptWakeWord("claude"),
    )
    listener._vad = FakeVad()
    listener.start()
    listener._thread.join(timeout=5)

    assert listener.running is False
    assert "microphone unplugged" in listener.status["error"]


def test_missing_audio_stack_gives_an_actionable_error():
    from picar.voice.listener import ListenerUnavailable, MicrophoneSource

    if importlib.util.find_spec("sounddevice") is not None:
        pytest.skip("sounddevice is installed, so this path isn't taken here")

    with pytest.raises(ListenerUnavailable, match="sounddevice"):
        MicrophoneSource()


# ==================== HTTP surface ====================

def test_listener_endpoints(client):
    status = client.get("/api/voice/listener").get_json()
    assert set(status) >= {"configured", "running", "wake_word", "last_heard"}

    # Stopping an idle listener is a no-op, not an error.
    assert client.post("/api/voice/listener/stop").status_code == 200


def test_listener_start_requires_voice_to_be_configured(client, monkeypatch):
    import backend.app as app_module

    monkeypatch.setattr(app_module, "VOICE_ENABLED", False)
    assert client.post("/api/voice/listener/start").status_code == 503
