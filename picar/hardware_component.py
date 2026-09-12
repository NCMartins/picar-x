"""Shared base for hardware controllers with a simulation-mode fallback.

Every controller in this package (motors, servos, steering, camera) follows
the same shape: try to import the real hardware library, fall back to a
"simulation mode" flag if it's missing, track whether init actually
succeeded, and guard every hardware call with that combination. This class
holds the parts of that pattern that don't vary between controllers.
"""

import threading


class HardwareComponent:
    """Base class capturing the simulation-mode guard pattern.

    Subclasses pass whether the underlying hardware library imported
    successfully, and set ``self.initialized = True`` once their specific
    hardware has been set up. ``ready`` combines both checks so subclasses
    don't need to repeat ``HARDWARE_AVAILABLE and self.initialized``
    everywhere they touch real hardware.
    """

    def __init__(self, hardware_available: bool):
        self.hardware_available = hardware_available
        self.initialized = False
        self.lock = threading.Lock()

    @property
    def ready(self) -> bool:
        """True once the hardware library is available and this instance
        finished initializing it successfully."""
        return self.hardware_available and self.initialized
