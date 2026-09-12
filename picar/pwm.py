"""Shared robot-hat PWM/servo setup.

Both the pan/tilt servo controller and the steering controller talk to
servos on the same Sunfounder Robot Hat v4 and need the same driver
bring-up plus a fallback for the legacy (pre-v2.3) robot-hat API, which
constructed a Servo directly from a channel index instead of a
driver+channel pair.
"""

import inspect

try:
    from robot_hat import Servo, PWMFactory, PWMDriverConfig
    ROBOT_HAT_AVAILABLE = True
except ImportError:
    ROBOT_HAT_AVAILABLE = False


def _servo_uses_new_api() -> bool:
    """True if the installed robot-hat Servo takes driver/channel kwargs (v2.3+)."""
    params = inspect.signature(Servo.__init__).parameters
    return "driver" in params and "channel" in params


def create_pwm_driver():
    """Create a shared PWM driver for the Sunfounder Robot Hat v4.

    Returns None when running against the legacy robot-hat API, which
    talks to servos directly by channel index instead of through a driver.
    Only call this once robot_hat has imported successfully.
    """
    if not _servo_uses_new_api():
        return None

    pwm_config = PWMDriverConfig(
        address=0x14,
        name="Sunfounder",
        bus=1,
        frame_width=20000,
        freq=50,
    )
    driver = PWMFactory.create_pwm_driver(pwm_config)
    driver.set_pwm_freq(50)
    return driver


def create_servo(channel: str, driver=None) -> "Servo":
    """Create a Servo on the given robot-hat channel (e.g. "P0").

    Uses `driver` (robot-hat v2.3+ API) when one is given, otherwise falls
    back to the legacy per-channel-index constructor.
    """
    if driver is not None:
        return Servo(driver=driver, channel=channel)
    return Servo(int(channel[1:]))
