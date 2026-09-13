"""Tests for the front-facing obstacle safeguard's sensor logic.

No robot_hat in this environment, so hardware-backed reads aren't exercised
here - `DistanceSensor` accepts an injected fake with the same shape as
`robot_hat.Ultrasonic` (a `read(times=1)` method) so the caching/staleness
logic can be tested without real GPIO, the same pattern the voice listener's
`MicrophoneSource` uses.
"""

import time

import pytest

from config.config import DISTANCE_STALE_AFTER
from picar.sensors.distance_sensor import DistanceSensor


class FakeUltrasonic:
    def __init__(self, readings):
        self._readings = list(readings)

    def read(self, times=1):
        return self._readings.pop(0) if self._readings else -1


@pytest.fixture
def sensor():
    # auto_start=False: drive _record_reading directly rather than racing a
    # background thread.
    s = DistanceSensor(sensor=FakeUltrasonic([]), auto_start=False)
    yield s
    s.cleanup()


def test_runs_in_simulation_mode_without_hardware(monkeypatch):
    # Forced rather than relying on robot_hat being absent: this suite also
    # runs on the real Pi, where robot_hat imports fine even with no sensor
    # physically wired up.
    import picar.sensors.distance_sensor as distance_sensor_module

    monkeypatch.setattr(distance_sensor_module, "HARDWARE_AVAILABLE", False)
    sensor = distance_sensor_module.DistanceSensor()
    try:
        assert sensor.hardware_available is False
        assert sensor.distance_cm is None
        assert sensor.is_clear(15) is True
    finally:
        sensor.cleanup()


def test_records_a_successful_reading(sensor):
    sensor._record_reading(42.0)
    assert sensor.distance_cm == 42.0
    assert sensor.stale is False


def test_timeout_reading_means_nothing_in_range(sensor):
    sensor._record_reading(-1)
    assert sensor.distance_cm is None
    assert sensor.stale is False
    assert sensor.is_clear(15) is True


def test_failed_reading_keeps_last_known_distance(sensor):
    sensor._record_reading(10.0)
    sensor._record_reading(-2)  # measurement failed
    assert sensor.distance_cm == 10.0


def test_is_clear_when_distance_at_or_above_threshold(sensor):
    sensor._record_reading(15.0)
    assert sensor.is_clear(15) is True
    sensor._record_reading(14.9)
    assert sensor.is_clear(15) is False


def test_zero_threshold_disables_the_check(sensor):
    sensor._record_reading(1.0)
    assert sensor.is_clear(0) is True


def test_stale_reading_fails_open(sensor):
    sensor._record_reading(5.0)
    assert sensor.is_clear(15) is False
    sensor._last_read_time = time.monotonic() - (DISTANCE_STALE_AFTER + 1)
    assert sensor.stale is True
    assert sensor.is_clear(15) is True


def test_never_read_is_stale(sensor):
    assert sensor.stale is True
    assert sensor.is_clear(15) is True
