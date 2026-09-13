import pytest

from config.config import MAX_SPEED
from picar.motors.motor_controller import MotorController


class FakeDistanceSensor:
    """Reports a fixed clear/blocked state, independent of any real hardware."""

    def __init__(self, clear=True, distance_cm=None):
        self._clear = clear
        self.distance_cm = distance_cm

    def is_clear(self, min_distance_cm):
        return self._clear


@pytest.fixture
def blocked_motor_controller():
    controller = MotorController(distance_sensor=FakeDistanceSensor(clear=False, distance_cm=8.0))
    yield controller
    controller.cleanup()


def test_forward_sets_equal_positive_speeds(motor_controller):
    motor_controller.forward(60)
    assert motor_controller.left_speed == 60
    assert motor_controller.right_speed == 60


def test_backward_sets_equal_negative_speeds(motor_controller):
    motor_controller.backward(40)
    assert motor_controller.left_speed == -40
    assert motor_controller.right_speed == -40


def test_stop_zeroes_both_speeds(motor_controller):
    motor_controller.forward(50)
    motor_controller.stop()
    assert motor_controller.left_speed == 0
    assert motor_controller.right_speed == 0


def test_set_speed_clamps_to_max_speed(motor_controller):
    motor_controller.set_speed(MAX_SPEED + 50, -(MAX_SPEED + 50))
    assert motor_controller.left_speed == MAX_SPEED
    assert motor_controller.right_speed == -MAX_SPEED


def test_runs_in_simulation_mode_without_hardware(motor_controller):
    # No robot_hat installed in the test environment.
    assert motor_controller.initialized is False


# ==================== Obstacle safeguard ====================

def test_forward_refused_when_obstacle_close(blocked_motor_controller):
    blocked_motor_controller.forward(60)
    assert blocked_motor_controller.left_speed == 0
    assert blocked_motor_controller.right_speed == 0
    assert blocked_motor_controller.blocked_by_obstacle is True


def test_backward_still_allowed_when_obstacle_ahead(blocked_motor_controller):
    blocked_motor_controller.backward(40)
    assert blocked_motor_controller.left_speed == -40
    assert blocked_motor_controller.right_speed == -40
    assert blocked_motor_controller.blocked_by_obstacle is False


def test_pivot_turn_still_allowed_when_obstacle_ahead(blocked_motor_controller):
    # One wheel forward, one back: not pure forward motion.
    blocked_motor_controller.set_speed(40, -40)
    assert blocked_motor_controller.left_speed == 40
    assert blocked_motor_controller.right_speed == -40
    assert blocked_motor_controller.blocked_by_obstacle is False


def test_set_speed_forward_refused_when_obstacle_close(blocked_motor_controller):
    blocked_motor_controller.set_speed(30, 30)
    assert blocked_motor_controller.left_speed == 0
    assert blocked_motor_controller.right_speed == 0
    assert blocked_motor_controller.blocked_by_obstacle is True


def test_forward_allowed_once_path_clears():
    sensor = FakeDistanceSensor(clear=False, distance_cm=8.0)
    controller = MotorController(distance_sensor=sensor)
    try:
        controller.forward(50)
        assert controller.left_speed == 0
        assert controller.blocked_by_obstacle is True

        sensor._clear = True
        controller.forward(50)
        assert controller.left_speed == 50
        assert controller.right_speed == 50
        assert controller.blocked_by_obstacle is False
    finally:
        controller.cleanup()


def test_obstacle_clear_and_distance_reflect_the_sensor(blocked_motor_controller):
    assert blocked_motor_controller.obstacle_clear() is False
    assert blocked_motor_controller.obstacle_distance_cm == 8.0
