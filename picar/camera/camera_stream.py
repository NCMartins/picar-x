"""
Camera streaming for PiCar-X
Provides MJPEG streaming and camera control
"""

import threading
import io
import time
from typing import Generator
import sys
from pathlib import Path

# Add config to path
config_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(config_path))

from config.config import (
    CAMERA_RESOLUTION, CAMERA_FRAMERATE,
    CAMERA_ROTATION, STREAM_QUALITY,
    MJPEG_BOUNDARY, MJPEG_CONTENT_TYPE
)

try:
    from picamera2 import Picamera2
    from PIL import Image
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: picamera2 not available - running in simulation mode")


class CameraStream:
    """Handles camera streaming and control"""
    
    def __init__(self):
        """Initialize camera stream"""
        self.camera = None
        # True when at least one client has an active MJPEG stream.
        self.streaming = False
        self.lock = threading.Lock()
        self.initialized = False

        # Multiple browser tabs/clients can each open their own /stream
        # connection. _active_stream_count tracks how many are currently
        # running so one client disconnecting doesn't kill the others.
        # _stop_event is a broadcast signal used by stop_streaming() to
        # tell every currently active stream to end.
        self._active_stream_count = 0
        self._count_lock = threading.Lock()
        self._stop_event = threading.Event()

        if HARDWARE_AVAILABLE:
            self._init_camera()
    
    def _init_camera(self):
        """Initialize picamera2"""
        try:
            self.camera = Picamera2()
            
            # Use video configuration for continuous streaming
            config = self.camera.create_video_configuration(
                main={"size": CAMERA_RESOLUTION, "format": "RGB888"}
            )
            
            self.camera.configure(config)
            self.camera.start()
            self.initialized = True
            print("Camera initialized successfully")
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.camera = None
    
    def get_frame(self) -> bytes | None:
        """
        Capture a single frame from camera
        
        Returns:
            JPEG frame as bytes, or None if unavailable
        """
        if not HARDWARE_AVAILABLE or not self.initialized or not self.camera:
            # Return dummy JPEG in simulation mode
            return self._get_dummy_frame()
        
        try:
            with self.lock:
                # Capture frame as numpy array and encode as JPEG
                data = self.camera.capture_array()
                img = Image.fromarray(data)
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=STREAM_QUALITY)
                return buffer.getvalue()
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None
    
    def _get_dummy_frame(self) -> bytes:
        """Generate a dummy JPEG frame for testing"""
        # In simulation mode, return a simple placeholder
        # This is just for testing without actual hardware
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4\xff\xd9'
    
    def stream_generator(self) -> Generator[bytes, None, None]:
        """
        Generator for streaming frames as MJPEG. Each client connection gets
        its own generator instance; this only stops when that client
        disconnects (GeneratorExit) or stop_streaming() broadcasts a stop to
        every active stream - never as a side effect of another client's
        stream ending.

        Yields:
            JPEG frames with MJPEG boundary markers
        """
        self._stop_event.clear()
        with self._count_lock:
            self._active_stream_count += 1
            self.streaming = True
        try:
            while not self._stop_event.is_set():
                frame = self.get_frame()
                if frame:
                    yield (b'--BOUNDARY\r\nContent-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(frame)).encode() + b'\r\n'
                           b'Content-Disposition: inline\r\n\r\n'
                           + frame + b'\r\n')
                time.sleep(1.0 / CAMERA_FRAMERATE)  # Control framerate
        finally:
            with self._count_lock:
                self._active_stream_count = max(0, self._active_stream_count - 1)
                self.streaming = self._active_stream_count > 0

    def stop_streaming(self):
        """Signal every currently active stream to stop."""
        self._stop_event.set()
    
    def cleanup(self):
        """Cleanup camera resources"""
        if self.camera:
            try:
                self.stop_streaming()
                self.camera.stop()
                print("Camera cleaned up")
            except Exception as e:
                print(f"Error cleaning up camera: {e}")


# Singleton instance
_camera_stream = None


def get_camera_stream() -> CameraStream:
    """Get or create camera stream singleton"""
    global _camera_stream
    if _camera_stream is None:
        _camera_stream = CameraStream()
    return _camera_stream
