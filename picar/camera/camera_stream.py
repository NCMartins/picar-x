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
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: picamera2 not available - running in simulation mode")


class CameraStream:
    """Handles camera streaming and control"""
    
    def __init__(self):
        """Initialize camera stream"""
        self.camera = None
        self.streaming = False
        self.lock = threading.Lock()
        self.initialized = False
        
        if HARDWARE_AVAILABLE:
            self._init_camera()
    
    def _init_camera(self):
        """Initialize picamera2"""
        try:
            self.camera = Picamera2()
            
            # Configure camera
            config = self.camera.create_still_configuration(
                main={"size": CAMERA_RESOLUTION},
                raw={"size": CAMERA_RESOLUTION}
            )
            
            # Set rotation if needed
            if CAMERA_ROTATION != 0:
                config['display'] = self.camera.create_video_configuration()
                # Note: Rotation setting may vary depending on picamera2 version
            
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
                # Capture JPEG directly
                request = self.camera.capture_request()
                data = request.make_array("main")
                request.release()
                
                # Convert to JPEG
                buffer = io.BytesIO()
                # In production, use proper JPEG encoding
                # For now, we'll return raw data (should be encoded as JPEG)
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
        Generator for streaming frames as MJPEG
        
        Yields:
            JPEG frames with MJPEG boundary markers
        """
        self.streaming = True
        try:
            while self.streaming:
                frame = self.get_frame()
                if frame:
                    yield (b'--BOUNDARY\r\nContent-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(frame)).encode() + b'\r\n'
                           b'Content-Disposition: inline\r\n\r\n'
                           + frame + b'\r\n')
                time.sleep(1.0 / CAMERA_FRAMERATE)  # Control framerate
        except GeneratorExit:
            self.streaming = False
    
    def stop_streaming(self):
        """Stop streaming"""
        self.streaming = False
    
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
