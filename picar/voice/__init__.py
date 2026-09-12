"""Voice control: talk to the PiCar and it acts, looks and answers."""

from .agent import VoiceAgent, VoiceAgentUnavailable
from .listener import ListenerUnavailable, VoiceListener, get_listener
from .skills import RobotSkills
from .speech import Speaker, get_speaker
from .transcriber import Transcriber, TranscriberUnavailable, get_transcriber

__all__ = [
    'VoiceAgent',
    'VoiceAgentUnavailable',
    'RobotSkills',
    'Speaker',
    'get_speaker',
    'Transcriber',
    'TranscriberUnavailable',
    'get_transcriber',
    'VoiceListener',
    'ListenerUnavailable',
    'get_listener',
    'get_voice_agent',
]

_voice_agent = None


def get_voice_agent() -> VoiceAgent:
    """Get or create the voice agent singleton, wired to the controllers."""
    global _voice_agent
    if _voice_agent is None:
        from ..camera import get_camera_stream
        from ..motors import get_motor_controller
        from ..servos import get_servo_controller
        from ..steering import get_steering_controller

        _voice_agent = VoiceAgent(
            motor_ctrl=get_motor_controller(),
            steering_ctrl=get_steering_controller(),
            servo_ctrl=get_servo_controller(),
            camera_stream=get_camera_stream(),
        )
    return _voice_agent
