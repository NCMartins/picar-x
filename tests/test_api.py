def test_health_check(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert set(body) >= {
        "motors_initialized",
        "servos_initialized",
        "steering_initialized",
        "camera_initialized",
    }


def test_motor_forward_and_status(client):
    r = client.post("/api/motors/forward", json={"speed": 55})
    assert r.status_code == 200
    assert r.get_json()["speed"] == 55

    status = client.get("/api/motors/status").get_json()
    assert status == {"left_speed": 55, "right_speed": 55}


def test_motor_stop(client):
    client.post("/api/motors/forward", json={"speed": 80})
    r = client.post("/api/motors/stop")
    assert r.status_code == 200

    status = client.get("/api/motors/status").get_json()
    assert status == {"left_speed": 0, "right_speed": 0}


def test_set_individual_motor_speed(client):
    r = client.post(
        "/api/motors/set-speed", json={"left_speed": 30, "right_speed": -30}
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["left_speed"] == 30
    assert body["right_speed"] == -30


def test_steering_angle_and_status(client):
    r = client.post("/api/steering/angle", json={"angle": 20})
    assert r.status_code == 200
    assert r.get_json()["angle"] == 20

    status = client.get("/api/steering/status").get_json()
    assert status["angle"] == 20


def test_steering_center(client):
    client.post("/api/steering/angle", json={"angle": 20})
    r = client.post("/api/steering/center")
    assert r.get_json()["angle"] == 0


def test_steering_calibration_roundtrip(client):
    r = client.post("/api/steering/calibration", json={"offset": -4})
    assert r.status_code == 200
    assert r.get_json()["offset"] == -4

    r = client.get("/api/steering/calibration")
    assert r.get_json()["offset"] == -4

    r = client.post("/api/steering/calibration/reset")
    assert r.get_json()["offset"] == 0


def test_camera_pan_tilt_and_status(client):
    r = client.post("/api/camera/pan", json={"angle": 40})
    assert r.get_json()["pan"] == 40

    r = client.post("/api/camera/tilt", json={"angle": -25})
    assert r.get_json()["tilt"] == -25

    status = client.get("/api/camera/status").get_json()
    assert status == {"pan": 40, "tilt": -25}


def test_camera_center(client):
    client.post("/api/camera/pan", json={"angle": 40})
    r = client.post("/api/camera/center")
    assert r.status_code == 200

    status = client.get("/api/camera/status").get_json()
    assert status == {"pan": 0, "tilt": 0}


def test_404_for_unknown_route(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.get_json()["status"] == "error"
