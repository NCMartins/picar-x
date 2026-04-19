"""Backend utilities and helpers"""
import os
import sys
from pathlib import Path

# Add config to path
config_path = Path(__file__).parent.parent
sys.path.insert(0, str(config_path))


def setup_logging():
    """Setup logging configuration"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def get_config():
    """Get configuration from environment or use defaults"""
    from config.config import *
    return {
        'FLASK_HOST': os.getenv('FLASK_HOST', FLASK_HOST),
        'FLASK_PORT': int(os.getenv('FLASK_PORT', FLASK_PORT)),
        'FLASK_DEBUG': os.getenv('FLASK_DEBUG', FLASK_DEBUG) == 'True'
    }
