"""
Camera streaming for PiCar-X
Provides MJPEG streaming and camera control
"""

import logging
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

logger = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
    from PIL import Image
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    logger.warning("picamera2 not available - running in simulation mode")


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
            
            # Use video configuration for continuous streaming
            config = self.camera.create_video_configuration(
                main={"size": CAMERA_RESOLUTION, "format": "RGB888"}
            )
            
            self.camera.configure(config)
            self.camera.start()
            self.initialized = True
            logger.info("Camera initialized successfully")
        except Exception as e:
            logger.error("Error initializing camera: %s", e)
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
            logger.error("Error capturing frame: %s", e)
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
                logger.info("Camera cleaned up")
            except Exception as e:
                logger.error("Error cleaning up camera: %s", e)


# Singleton instance
_camera_stream = None


def get_camera_stream() -> CameraStream:
    """Get or create camera stream singleton"""
    global _camera_stream
    if _camera_stream is None:
        _camera_stream = CameraStream()
    return _camera_stream
