from config.config import SERVO_MIN_ANGLE, SERVO_MAX_ANGLE


def test_set_pan_clamps_to_range(servo_controller):
    servo_controller.set_pan(SERVO_MAX_ANGLE + 30)
    assert servo_controller.pan_angle == SERVO_MAX_ANGLE

    servo_controller.set_pan(SERVO_MIN_ANGLE - 30)
    assert servo_controller.pan_angle == SERVO_MIN_ANGLE


def test_set_tilt_clamps_to_range(servo_controller):
    servo_controller.set_tilt(SERVO_MAX_ANGLE + 10)
    assert servo_controller.tilt_angle == SERVO_MAX_ANGLE

    servo_controller.set_tilt(SERVO_MIN_ANGLE - 10)
    assert servo_controller.tilt_angle == SERVO_MIN_ANGLE


def test_set_position_sets_pan_and_tilt(servo_controller):
    servo_controller.set_position(20, -15)
    assert servo_controller.pan_angle == 20
    assert servo_controller.tilt_angle == -15


def test_center_resets_pan_and_tilt_to_zero(servo_controller):
    servo_controller.set_position(30, 30)
    servo_controller.center()
    assert servo_controller.pan_angle == 0
    assert servo_controller.tilt_angle == 0
