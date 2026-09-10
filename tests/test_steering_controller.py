import json

from config.config import STEERING_MIN_ANGLE, STEERING_MAX_ANGLE, STEERING_CENTER_ANGLE


def test_set_angle_clamps_to_range(steering_controller):
    steering_controller.set_angle(STEERING_MAX_ANGLE + 20)
    assert steering_controller.angle == STEERING_MAX_ANGLE

    steering_controller.set_angle(STEERING_MIN_ANGLE - 20)
    assert steering_controller.angle == STEERING_MIN_ANGLE


def test_center_returns_to_center_angle(steering_controller):
    steering_controller.set_angle(15)
    steering_controller.center()
    assert steering_controller.angle == STEERING_CENTER_ANGLE


def test_set_calibration_offset_persists_to_disk(steering_controller):
    steering_controller.set_calibration_offset(5)

    assert steering_controller.calibration_offset == 5
    assert steering_controller._calibration_file.exists()
    saved = json.loads(steering_controller._calibration_file.read_text())
    assert saved["offset"] == 5


def test_reset_calibration_clears_offset(steering_controller):
    steering_controller.set_calibration_offset(7)
    steering_controller.reset_calibration()
    assert steering_controller.calibration_offset == 0


def test_load_calibration_reads_existing_file(tmp_path):
    cal_file = tmp_path / "steering_calibration.json"
    cal_file.write_text(json.dumps({"offset": 9}))

    from picar.steering.steering_controller import SteeringController
    controller = SteeringController()
    controller._calibration_file = cal_file
    controller._load_calibration()

    assert controller.calibration_offset == 9
    controller.cleanup()


def test_load_calibration_is_noop_when_file_missing(tmp_path):
    from picar.steering.steering_controller import SteeringController
    controller = SteeringController()
    controller._calibration_file = tmp_path / "does_not_exist.json"
    controller.calibration_offset = 0
    controller._load_calibration()

    assert controller.calibration_offset == 0
    controller.cleanup()
