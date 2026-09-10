from config.config import MAX_SPEED


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
