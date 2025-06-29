import os
import sys
import time
import json
import logging
import platform
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum

import asyncio
from bleak import BleakClient, BleakScanner


class LogLevel(Enum):
    """Custom log levels for LED debugging."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

@dataclass
class BluetoothDebugInfo:
    """Bluetooth adapter and system information."""
    system: str
    platform: str
    python_version: str
    bleak_version: str
    adapters: List[Dict[str, Any]]
    adapter_powered: bool
    service_status: Optional[str] = None
    permissions: Optional[str] = None

@dataclass
class DeviceDebugInfo:
    """LED device debug information."""
    mac_address: Optional[str]
    device_name: Optional[str]
    rssi: Optional[int]
    uuids: List[str]
    services: List[Dict[str, Any]]
    characteristics: List[Dict[str, Any]]
    connection_attempts: int
    last_error: Optional[str]
    command_history: List[Dict[str, Any]]

@dataclass
class SessionDebugInfo:
    """Debug session information."""
    session_id: str
    start_time: str
    bluetooth_info: BluetoothDebugInfo
    device_info: Optional[DeviceDebugInfo]
    errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]

class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for console output."""
    
    COLORS = {
        'TRACE': '\033[90m',
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m',
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        record.levelname = f"{level_color}{record.levelname}{reset_color}"
        
        formatted = super().format(record)
        
        if hasattr(record, 'led_context'):
            formatted = f"{formatted} [{record.led_context}]"
        
        return formatted

class DebugFileHandler(logging.FileHandler):
    """Custom file handler that creates debug directories and rotates logs."""
    
    def __init__(self, base_path: Path, max_files: int = 10):
        self.base_path = Path(base_path)
        self.max_files = max_files
        
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.base_path.parent / f"bluelights_debug_{timestamp}.log"
        
        super().__init__(filename, mode='w', encoding='utf-8')
        
        self._cleanup_old_logs()
    
    def _cleanup_old_logs(self):
        """Remove old log files, keeping only the most recent ones."""
        try:
            debug_files = list(self.base_path.parent.glob("bluelights_debug_*.log"))
            debug_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for old_file in debug_files[self.max_files:]:
                old_file.unlink()
                
        except Exception as e:
            print(f"Warning: Could not cleanup old logs: {e}")

class LEDDebugger:
    """Advanced debugging system for LED operations."""
    
    def __init__(self, 
                 enable_file_logging: bool = True,
                 enable_performance_tracking: bool = True,
                 log_level: Union[str, int] = logging.INFO,
                 debug_dir: Optional[Path] = None):
        """
        Initialize the debug system.
        
        Args:
            enable_file_logging: Whether to log to files
            enable_performance_tracking: Whether to track performance metrics
            log_level: Logging level
            debug_dir: Directory for debug files
        """
        self.enable_file_logging = enable_file_logging
        self.enable_performance_tracking = enable_performance_tracking
        
        if debug_dir is None:
            if os.name == 'nt':
                debug_dir = Path.home() / "AppData" / "Local" / "LEDController" / "debug"
            else:
                debug_dir = Path.home() / ".config" / "led_controller" / "debug"
        
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.start_time = datetime.now(timezone.utc).isoformat()
        
        self.bluetooth_info: Optional[BluetoothDebugInfo] = None
        self.device_info: Optional[DeviceDebugInfo] = None
        self.errors: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.command_timings: List[Dict[str, Any]] = []
        
        self._setup_logging(log_level)
        
        if self.enable_performance_tracking:
            self._start_performance_tracking()
    
    def _setup_logging(self, log_level: Union[str, int]):
        """Setup advanced logging configuration."""
        logging.addLevelName(LogLevel.TRACE.value, "TRACE")
        
        self.logger = logging.getLogger("bluelights")
        self.logger.setLevel(LogLevel.TRACE.value)
        
        self.logger.handlers.clear()
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        if self.enable_file_logging:
            file_handler = DebugFileHandler(
                self.debug_dir / "bluelights_debug.log",
                max_files=10
            )
            file_handler.setLevel(LogLevel.TRACE.value)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        self.bt_logger = logging.getLogger("bluelights.bluetooth")
        self.bt_logger.setLevel(LogLevel.TRACE.value)
        
        self.cmd_logger = logging.getLogger("bluelights.commands")
        self.cmd_logger.setLevel(LogLevel.TRACE.value)
    
    def _start_performance_tracking(self):
        """Initialize performance tracking."""
        self.performance_metrics = {
            'session_start': time.time(),
            'connection_attempts': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'commands_sent': 0,
            'command_failures': 0,
            'total_bytes_sent': 0,
            'avg_command_time': 0.0,
            'max_command_time': 0.0,
            'min_command_time': float('inf')
        }
    
    async def collect_bluetooth_info(self) -> BluetoothDebugInfo:
        """Collect comprehensive Bluetooth system information."""
        self.logger.info("Collecting Bluetooth system information...")
        
        try:
            system_info = {
                'system': platform.system(),
                'platform': platform.platform(),
                'python_version': platform.python_version(),
            }
            
            try:
                import bleak
                bleak_version = bleak.__version__
            except:
                bleak_version = "unknown"
            
            adapters = []
            adapter_powered = False
            
            try:
                devices = await asyncio.wait_for(
                    BleakScanner.discover(timeout=3.0), 
                    timeout=5.0
                )
                adapter_powered = True
                adapters.append({
                    'status': 'working',
                    'devices_found': len(devices),
                    'device_list': [
                        {
                            'name': d.name,
                            'address': d.address,
                            'rssi': getattr(d, 'rssi', None)
                        } for d in devices[:5]
                    ]
                })
            except Exception as e:
                adapters.append({
                    'status': 'error',
                    'error': str(e)
                })
            
            service_status = None
            permissions = None
            
            if platform.system().lower() == 'linux':
                service_status = await self._get_linux_bluetooth_status()
                permissions = await self._get_linux_permissions()
            
            self.bluetooth_info = BluetoothDebugInfo(
                system=system_info['system'],
                platform=system_info['platform'],
                python_version=system_info['python_version'],
                bleak_version=bleak_version,
                adapters=adapters,
                adapter_powered=adapter_powered,
                service_status=service_status,
                permissions=permissions
            )
            
            self.logger.info(f"Bluetooth info collected: {len(adapters)} adapters found")
            return self.bluetooth_info
            
        except Exception as e:
            self.logger.error(f"Failed to collect Bluetooth info: {e}")
            self.log_error("bluetooth_info_collection", e)
            raise
    
    async def _get_linux_bluetooth_status(self) -> Optional[str]:
        """Get Linux Bluetooth service status."""
        try:
            import subprocess
            result = subprocess.run(
                ['systemctl', 'status', 'bluetooth'],
                capture_output=True, text=True, timeout=5
            )
            return f"exit_code: {result.returncode}, output: {result.stdout[:200]}"
        except Exception as e:
            return f"error: {str(e)}"
    
    async def _get_linux_permissions(self) -> Optional[str]:
        """Check Linux Bluetooth permissions."""
        try:
            import subprocess
            import os
            
            result = subprocess.run(['groups'], capture_output=True, text=True)
            groups = result.stdout.strip()
            
            in_bluetooth_group = 'bluetooth' in groups
            
            return f"user: {os.getenv('USER', 'unknown')}, groups: {groups}, in_bluetooth_group: {in_bluetooth_group}"
        except Exception as e:
            return f"error: {str(e)}"
    
    async def collect_device_info(self, mac_address: str) -> DeviceDebugInfo:
        """Collect detailed information about a specific LED device."""
        self.logger.info(f"Collecting device info for {mac_address}")
        
        try:
            device_info = DeviceDebugInfo(
                mac_address=mac_address,
                device_name=None,
                rssi=None,
                uuids=[],
                services=[],
                characteristics=[],
                connection_attempts=0,
                last_error=None,
                command_history=[]
            )
            
            client = BleakClient(mac_address)
            
            try:
                await client.connect()
                device_info.connection_attempts += 1
                
                try:
                    device_info.device_name = client._device_info.get('name', 'Unknown')
                except:
                    pass
                
                services = await client.get_services()
                
                for service in services:
                    service_info = {
                        'uuid': service.uuid,
                        'description': service.description,
                        'characteristics': []
                    }
                    
                    device_info.uuids.append(service.uuid)
                    
                    for char in service.characteristics:
                        char_info = {
                            'uuid': char.uuid,
                            'description': char.description,
                            'properties': char.properties,
                            'handle': char.handle
                        }
                        service_info['characteristics'].append(char_info)
                        device_info.characteristics.append(char_info)
                        device_info.uuids.append(char.uuid)
                    
                    device_info.services.append(service_info)
                
                await client.disconnect()
                
            except Exception as e:
                device_info.last_error = str(e)
                self.log_error("device_info_collection", e)
            
            self.device_info = device_info
            self.logger.info(f"Device info collected: {len(device_info.services)} services, {len(device_info.characteristics)} characteristics")
            return device_info
            
        except Exception as e:
            self.logger.error(f"Failed to collect device info: {e}")
            raise
    
    @contextmanager
    def command_timer(self, command_name: str, command_data: bytes = None):
        """Context manager to time LED commands."""
        start_time = time.time()
        command_info = {
            'name': command_name,
            'start_time': start_time,
            'data': command_data.hex() if command_data else None,
            'success': False,
            'duration': 0.0,
            'error': None
        }
        
        try:
            self.cmd_logger.log(LogLevel.TRACE.value, f"Starting command: {command_name}")
            yield command_info
            command_info['success'] = True
            
        except Exception as e:
            command_info['error'] = str(e)
            self.cmd_logger.error(f"Command {command_name} failed: {e}")
            raise
            
        finally:
            end_time = time.time()
            duration = end_time - start_time
            command_info['duration'] = duration
            
            if self.enable_performance_tracking:
                self._update_command_metrics(command_info)
            
            self.cmd_logger.log(
                LogLevel.TRACE.value,
                f"Command {command_name} completed in {duration:.3f}s - {'SUCCESS' if command_info['success'] else 'FAILED'}"
            )
            
            self.command_timings.append(command_info)
            if self.device_info:
                self.device_info.command_history.append(command_info)
    
    def _update_command_metrics(self, command_info: Dict[str, Any]):
        """Update performance metrics with command timing."""
        duration = command_info['duration']
        
        self.performance_metrics['commands_sent'] += 1
        if not command_info['success']:
            self.performance_metrics['command_failures'] += 1
        
        if command_info.get('data'):
            self.performance_metrics['total_bytes_sent'] += len(bytes.fromhex(command_info['data']))
        
        if duration > self.performance_metrics['max_command_time']:
            self.performance_metrics['max_command_time'] = duration
        
        if duration < self.performance_metrics['min_command_time']:
            self.performance_metrics['min_command_time'] = duration
        
        total_time = self.performance_metrics['avg_command_time'] * (self.performance_metrics['commands_sent'] - 1) + duration
        self.performance_metrics['avg_command_time'] = total_time / self.performance_metrics['commands_sent']
    
    def log_error(self, context: str, error: Exception, extra_data: Dict[str, Any] = None):
        """Log an error with full context and traceback."""
        error_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'extra_data': extra_data or {}
        }
        
        self.errors.append(error_info)
        
        self.logger.error(
            f"Error in {context}: {error}",
            extra={'led_context': context}
        )
        
        self.logger.log(LogLevel.TRACE.value, f"Full traceback:\n{error_info['traceback']}")
    
    def log_connection_attempt(self, mac_address: str, success: bool, error: Exception = None):
        """Log a connection attempt."""
        if self.enable_performance_tracking:
            self.performance_metrics['connection_attempts'] += 1
            if success:
                self.performance_metrics['successful_connections'] += 1
            else:
                self.performance_metrics['failed_connections'] += 1
        
        if success:
            self.bt_logger.info(f"Successfully connected to {mac_address}")
        else:
            self.bt_logger.error(f"Failed to connect to {mac_address}: {error}")
            if error:
                self.log_error("connection_attempt", error, {'mac_address': mac_address})
    
    def export_debug_report(self, filepath: Optional[Path] = None) -> Path:
        """Export comprehensive debug report."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.debug_dir / f"debug_report_{timestamp}.json"
        
        session_duration = time.time() - self.performance_metrics.get('session_start', time.time())
        
        report = SessionDebugInfo(
            session_id=self.session_id,
            start_time=self.start_time,
            bluetooth_info=self.bluetooth_info,
            device_info=self.device_info,
            errors=self.errors,
            performance_metrics={
                **self.performance_metrics,
                'session_duration': session_duration,
                'command_timings': self.command_timings[-10:]
            }
        )
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            
            self.logger.info(f"Debug report exported to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to export debug report: {e}")
            raise
    
    def print_summary(self):
        """Print a summary of the debug session."""
        print("\n" + "="*60)
        print("LED CONTROLLER DEBUG SUMMARY")
        print("="*60)
        
        duration = time.time() - self.performance_metrics.get('session_start', time.time())
        print(f"Session ID: {self.session_id}")
        print(f"Duration: {duration:.1f} seconds")
        
        if self.bluetooth_info:
            print(f"\nBluetooth Status:")
            print(f"  System: {self.bluetooth_info.system}")
            print(f"  Adapter Powered: {self.bluetooth_info.adapter_powered}")
            print(f"  Adapters Found: {len(self.bluetooth_info.adapters)}")
        
        if self.device_info:
            print(f"\nDevice Info:")
            print(f"  MAC: {self.device_info.mac_address}")
            print(f"  Name: {self.device_info.device_name}")
            print(f"  Services: {len(self.device_info.services)}")
            print(f"  UUIDs: {len(self.device_info.uuids)}")
        
        print(f"\nPerformance:")
        print(f"  Commands Sent: {self.performance_metrics.get('commands_sent', 0)}")
        print(f"  Command Failures: {self.performance_metrics.get('command_failures', 0)}")
        print(f"  Avg Command Time: {self.performance_metrics.get('avg_command_time', 0):.3f}s")
        print(f"  Connection Attempts: {self.performance_metrics.get('connection_attempts', 0)}")
        print(f"  Successful Connections: {self.performance_metrics.get('successful_connections', 0)}")
        
        print(f"\nErrors: {len(self.errors)}")
        for error in self.errors[-3:]:
            print(f"  - {error['context']}: {error['error_message']}")
        
        print("="*60)

_debugger: Optional[LEDDebugger] = None

def get_debugger(enable_debug: bool = None) -> LEDDebugger:
    """Get or create the global debugger instance."""
    global _debugger
    
    if _debugger is None:
        debug_enabled = enable_debug
        if debug_enabled is None:
            debug_enabled = os.getenv('LED_DEBUG', 'false').lower() == 'true'
        
        log_level = os.getenv('LED_LOG_LEVEL', 'INFO').upper()
        
        _debugger = LEDDebugger(
            enable_file_logging=debug_enabled,
            enable_performance_tracking=True,
            log_level=getattr(logging, log_level, logging.INFO)
        )
    
    return _debugger

def enable_debug_mode():
    """Enable comprehensive debug mode."""
    debugger = get_debugger(enable_debug=True)
    debugger.logger.info("Debug mode enabled")
    return debugger