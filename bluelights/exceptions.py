#!/usr/bin/env python3
"""
Custom exceptions for the LED controller library.
"""

class BlueLightsException(Exception):
    """Base exception for all LED controller errors."""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

class ConnectionError(BlueLightsException):
    """Raised when there are connection issues with the LED device."""
    
    def __init__(self, message: str = "Failed to connect to LED device"):
        super().__init__(message, "CONNECTION_ERROR")

class DeviceNotFoundError(BlueLightsException):
    """Raised when the LED device cannot be found."""
    
    def __init__(self, message: str = "LED device not found"):
        super().__init__(message, "DEVICE_NOT_FOUND")

class BluetoothNotAvailableError(BlueLightsException):
    """Raised when Bluetooth is not available or not enabled."""
    
    def __init__(self, message: str = "Bluetooth is not available or not enabled"):
        super().__init__(message, "BLUETOOTH_NOT_AVAILABLE")

class CommandFailedError(BlueLightsException):
    """Raised when a command to the LED device fails."""
    
    def __init__(self, command: str, message: str = None):
        if message is None:
            message = f"Command '{command}' failed"
        super().__init__(message, "COMMAND_FAILED")
        self.command = command

class InvalidParameterError(BlueLightsException):
    """Raised when invalid parameters are provided."""
    
    def __init__(self, parameter: str, value, message: str = None):
        if message is None:
            message = f"Invalid value '{value}' for parameter '{parameter}'"
        super().__init__(message, "INVALID_PARAMETER")
        self.parameter = parameter
        self.value = value

class DeviceTimeoutError(BlueLightsException):
    """Raised when communication with the device times out."""
    
    def __init__(self, timeout_seconds: float, message: str = None):
        if message is None:
            message = f"Device communication timed out after {timeout_seconds} seconds"
        super().__init__(message, "DEVICE_TIMEOUT")
        self.timeout_seconds = timeout_seconds

class UnsupportedOperationError(BlueLightsException):
    """Raised when an unsupported operation is attempted."""
    
    def __init__(self, operation: str, message: str = None):
        if message is None:
            message = f"Operation '{operation}' is not supported"
        super().__init__(message, "UNSUPPORTED_OPERATION")
        self.operation = operation

class ConfigurationError(BlueLightsException):
    """Raised when there are configuration issues."""
    
    def __init__(self, message: str = "Configuration error"):
        super().__init__(message, "CONFIGURATION_ERROR")

class AuthenticationError(BlueLightsException):
    """Raised when authentication with the device fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR")
