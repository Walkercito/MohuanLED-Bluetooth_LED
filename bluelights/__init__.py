__version__ = "0.2.0"
__author__ = "Walkercito"
__email__ = "walkercitoliver@gmail.com"

from .manager import BJLEDInstance
from .scanner import Scanner
from .exceptions import (
    BlueLightsException,
    ConnectionError,
    DeviceNotFoundError,
    BluetoothNotAvailableError,
    CommandFailedError,
    InvalidParameterError,
    DeviceTimeoutError,
    UnsupportedOperationError,
    ConfigurationError,
    AuthenticationError
)

__all__ = [
    "BJLEDInstance",
    "Scanner", 
    "BlueLightsException",
    "ConnectionError",
    "DeviceNotFoundError", 
    "BluetoothNotAvailableError",
    "CommandFailedError",
    "InvalidParameterError",
    "DeviceTimeoutError",
    "UnsupportedOperationError",
    "ConfigurationError",
    "AuthenticationError"
]
