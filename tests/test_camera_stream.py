import pytest


def test_get_frame_returns_dummy_jpeg_in_simulation_mode(camera_stream):
    frame = camera_stream.get_frame()
    assert frame is not None
    assert frame.startswith(b"\xff\xd8")  # JPEG magic bytes


def test_stream_generator_yields_mjpeg_frames(camera_stream):
    gen = camera_stream.stream_generator()
    chunk = next(gen)
    assert chunk.startswith(b"--BOUNDARY")
    assert b"Content-Type: image/jpeg" in chunk
    gen.close()


def test_stop_streaming_ends_the_generator(camera_stream):
    gen = camera_stream.stream_generator()
    next(gen)
    camera_stream.stop_streaming()
    with pytest.raises(StopIteration):
        next(gen)
