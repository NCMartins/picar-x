"""Shared pytest fixtures for the PiCar-X test suite.

All tests run in simulation mode (no robot_hat/picamera2 installed in CI),
which is exactly the mode these controllers are designed to support.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture
def motor_controller():
    from picar.motors.motor_controller import MotorController
    controller = MotorController()
    yield controller
    controller.cleanup()


@pytest.fixture
def servo_controller():
    from picar.servos.servo_controller import ServoController
    controller = ServoController()
    yield controller
    controller.cleanup()


@pytest.fixture
def steering_controller(tmp_path):
    from picar.steering.steering_controller import SteeringController
    controller = SteeringController()
    # Redirect calibration persistence away from the repo's real file.
    controller._calibration_file = tmp_path / "steering_calibration.json"
    yield controller
    controller.cleanup()


@pytest.fixture
def camera_stream():
    from picar.camera.camera_stream import CameraStream
    stream = CameraStream()
    yield stream
    stream.cleanup()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by the app's real (singleton) controllers.

    Resets motor/servo/steering state before each test and redirects
    steering calibration writes to a temp file so tests never touch the
    repo's real config/steering_calibration.json.
    """
    import backend.app as app_module

    monkeypatch.setattr(
        app_module.steering_ctrl,
        "_calibration_file",
        tmp_path / "steering_calibration.json",
    )
    app_module.motor_ctrl.stop()
    app_module.steering_ctrl.center()
    app_module.servo_ctrl.center()

    with app_module.app.test_client() as test_client:
        yield test_client
