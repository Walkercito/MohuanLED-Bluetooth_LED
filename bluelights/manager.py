import os
import asyncio
import colorsys
import logging
from typing import List, Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from bleak import BleakClient
from bleak.exc import BleakError
from .scanner import ImprovedScanner
from .exceptions import *

logger = logging.getLogger(__name__)
load_dotenv()

LED_MAC_ADDRESS = os.getenv("LED_MAC_ADDRESS")
LED_UUID = os.getenv("LED_UUID")

# Comandos mejorados basados en gatt_bytes.txt
TURN_ON_CMD = bytearray.fromhex("69 96 02 01 01")
TURN_OFF_CMD = bytearray.fromhex("69 96 02 01 00")

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class LEDStatus:
    is_on: bool = False
    red: int = 0
    green: int = 0  
    blue: int = 0
    brightness: int = 255
    effect: Optional[str] = None
    connection_state: ConnectionState = ConnectionState.DISCONNECTED

class BJLEDInstance:
    def __init__(self, 
                 address: str = None, 
                 uuid: str = None, 
                 auto_reconnect: bool = True,
                 connection_timeout: float = 15.0,
                 command_timeout: float = 5.0,
                 debug: bool = False) -> None:
        
        self.loop = asyncio.get_event_loop()
        self._mac = address or LED_MAC_ADDRESS
        self._uuid = uuid or LED_UUID
        self._auto_reconnect = auto_reconnect
        self._connection_timeout = connection_timeout
        self._command_timeout = command_timeout
        self._debug = debug
        
        # Estado interno
        self._client: Optional[BleakClient] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._status = LEDStatus()
        self._last_error: Optional[str] = None
        
        # Callbacks para estado
        self._state_callbacks: List[Callable[[ConnectionState], None]] = []
        self._status_callbacks: List[Callable[[LEDStatus], None]] = []
        
        # Scanner mejorado
        self._scanner = ImprovedScanner(timeout=15.0, retries=2)
        
        # Lock para operaciones concurrentes
        self._operation_lock = asyncio.Lock()
        
        if self._debug:
            logging.getLogger().setLevel(logging.DEBUG)

    def add_state_change_callback(self, callback: Callable[[ConnectionState], None]):
        """Añade callback para cambios de estado de conexión"""
        self._state_callbacks.append(callback)

    def add_status_change_callback(self, callback: Callable[[LEDStatus], None]):
        """Añade callback para cambios de estado del LED"""
        self._status_callbacks.append(callback)

    def _notify_state_change(self, new_state: ConnectionState):
        """Notifica cambio de estado"""
        old_state = self._connection_state
        self._connection_state = new_state
        self._status.connection_state = new_state
        
        logger.debug(f"State change: {old_state.value} -> {new_state.value}")
        
        for callback in self._state_callbacks:
            try:
                callback(new_state)
            except Exception as e:
                logger.error(f"Error in state callback: {e}")

    def _notify_status_change(self):
        """Notifica cambio de estado del LED"""
        for callback in self._status_callbacks:
            try:
                callback(self._status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")

    async def initialize(self, force_rescan: bool = False) -> bool:
        """Inicializa la conexión con el LED"""
        async with self._operation_lock:
            try:
                self._notify_state_change(ConnectionState.CONNECTING)
                
                # Si no tenemos MAC o UUID, o se fuerza rescan
                if not self._mac or not self._uuid or force_rescan:
                    logger.info("Searching for LED devices...")
                    await self._discover_led()
                
                if not self._mac:
                    raise DeviceNotFoundError("No LED device found. Make sure it is powered on and within range.")
                
                if not self._uuid:
                    raise DeviceNotFoundError(f"No compatible UUID found for device {self._mac}")
                
                # Intentar conexión
                await self._connect()
                
                # Verificar que funciona enviando un comando de test
                await self._test_connection()
                
                self._notify_state_change(ConnectionState.CONNECTED)
                logger.info(f"✅ Successfully connected to LED at {self._mac}")
                return True
                
            except Exception as e:
                self._last_error = str(e)
                self._notify_state_change(ConnectionState.ERROR)
                logger.error(f"Failed to initialize: {e}")
                
                # Re-raise con tipo apropiado
                if isinstance(e, BlueLightsException):
                    raise
                elif "powered" in str(e).lower() or "adapter" in str(e).lower():
                    raise BluetoothNotAvailableError(f"Bluetooth issue: {e}")
                else:
                    raise ConnectionError(f"Initialization failed: {e}")

    async def _discover_led(self):
        """Descubre dispositivos LED automáticamente"""
        try:
            devices = await self._scanner.scan_all_devices(detailed=True)
            
            if not devices:
                raise DeviceNotFoundError("No Bluetooth devices found")
            
            # Filtrar candidatos LED
            led_candidates = [d for d in devices if d.is_led_candidate]
            
            if led_candidates:
                # Seleccionar el mejor candidato
                best_candidate = max(led_candidates, key=lambda x: x.confidence)
                self._mac = best_candidate.address
                logger.info(f"🎯 Selected LED: {best_candidate.name} ({self._mac}) - {int(best_candidate.confidence * 100)}% confidence")
                
                # Intentar encontrar UUID compatible
                await self._find_compatible_uuid()
            else:
                # Mostrar dispositivos disponibles para debug
                logger.warning("No LED candidates found. Available devices:")
                for i, device in enumerate(devices[:5], 1):
                    signal = f" ({device.rssi}dBm)" if device.rssi else ""
                    logger.warning(f"  {i}. {device.name or 'Unknown'} ({device.address}){signal}")
                
                raise DeviceNotFoundError(
                    "No LED devices found. Looking for devices with LED-like names or services. "
                    "Try connecting manually with a specific MAC address."
                )
                
        except BleakError as e:
            if "powered" in str(e).lower():
                raise BluetoothNotAvailableError(f"Bluetooth adapter not powered: {e}")
            raise

    async def _find_compatible_uuid(self):
        """Encuentra UUID compatible para el dispositivo"""
        try:
            uuids = await self._scanner.scan_uuids(self._mac)
            
            # UUIDs conocidos para LEDs (en orden de preferencia)
            known_led_uuids = [
                "0000ee02-0000-1000-2000-00805f9b34fb",
                "0000ee01-0000-1000-8000-00805f9b34fb", 
                "0000ffe0-0000-1000-8000-00805f9b34fb",
                "0000ffd0-0000-1000-8000-00805f9b34fb",
            ]
            
            # Buscar UUID conocido primero
            for known_uuid in known_led_uuids:
                if any(known_uuid.lower() == str(uuid).lower() for uuid in uuids):
                    self._uuid = known_uuid
                    logger.info(f"✅ Found known LED UUID: {self._uuid}")
                    return
            
            # Si no encuentra uno conocido, probar los disponibles
            logger.info(f"Testing {len(uuids)} UUIDs for compatibility...")
            
            for uuid in uuids:
                try:
                    await self._test_uuid_compatibility(str(uuid))
                    self._uuid = str(uuid)
                    logger.info(f"✅ Found compatible UUID: {self._uuid}")
                    return
                except:
                    continue
            
            logger.warning(f"No compatible UUID found among {len(uuids)} candidates")
            
        except Exception as e:
            logger.error(f"Error scanning UUIDs: {e}")

    async def _test_uuid_compatibility(self, uuid: str):
        """Prueba si un UUID es compatible"""
        test_client = None
        try:
            test_client = BleakClient(self._mac)
            await asyncio.wait_for(test_client.connect(), timeout=5.0)
            
            # Intentar escribir comando de test
            await asyncio.wait_for(
                test_client.write_gatt_char(uuid, TURN_ON_CMD, False),
                timeout=3.0
            )
            
            # Si llegamos aquí, el UUID funciona
            await test_client.write_gatt_char(uuid, TURN_OFF_CMD, False)
            
        finally:
            if test_client and test_client.is_connected:
                await test_client.disconnect()

    async def _connect(self):
        """Establece conexión con el dispositivo"""
        if self._client and self._client.is_connected:
            return
            
        try:
            self._client = BleakClient(self._mac)
            await asyncio.wait_for(
                self._client.connect(), 
                timeout=self._connection_timeout
            )
            logger.debug(f"Connected to {self._mac}")
            
        except asyncio.TimeoutError:
            raise ConnectionError(f"Connection timeout after {self._connection_timeout}s")
        except BleakError as e:
            if "not found" in str(e).lower():
                raise DeviceNotFoundError(f"Device {self._mac} not found")
            raise ConnectionError(f"Connection failed: {e}")

    async def _test_connection(self):
        """Prueba que la conexión funciona"""
        try:
            # Enviar comando de test silencioso
            await self._write_command(TURN_OFF_CMD)
            logger.debug("Connection test passed")
        except Exception as e:
            raise ConnectionError(f"Connection test failed: {e}")

    async def disconnect(self):
        """Desconecta del dispositivo"""
        async with self._operation_lock:
            await self._disconnect_internal()

    async def _disconnect_internal(self):
        """Desconexión interna"""
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
                logger.debug("Disconnected from device")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._client = None
                
        self._notify_state_change(ConnectionState.DISCONNECTED)

    async def _write_command(self, data: bytearray, retry: bool = True):
        """Escribe comando al dispositivo con manejo de errores"""
        if not self._client or not self._client.is_connected:
            if self._auto_reconnect and retry:
                logger.debug("Auto-reconnecting...")
                await self._connect()
            else:
                raise ConnectionError("Device not connected")
        
        try:
            await asyncio.wait_for(
                self._client.write_gatt_char(self._uuid, data, False),
                timeout=self._command_timeout
            )
            logger.debug(f"Command sent: {data.hex()}")
            
        except asyncio.TimeoutError:
            raise DeviceTimeoutError(self._command_timeout, "Command timed out")
        except BleakError as e:
            if "not connected" in str(e).lower() and retry and self._auto_reconnect:
                logger.debug("Connection lost, retrying...")
                await self._connect()
                await self._write_command(data, retry=False)  # No recursive retry
            else:
                raise CommandFailedError("write", f"Command failed: {e}")

    # Métodos públicos del LED
    async def turn_on(self):
        """Enciende el LED"""
        async with self._operation_lock:
            await self._write_command(TURN_ON_CMD)
            self._status.is_on = True
            self._notify_status_change()
            logger.info("LED turned ON")

    async def turn_off(self):
        """Apaga el LED"""
        async with self._operation_lock:
            await self._write_command(TURN_OFF_CMD)
            self._status.is_on = False
            self._notify_status_change()
            logger.info("LED turned OFF")

    async def set_color_to_rgb(self, red: int, green: int, blue: int, brightness: int = None):
        """Establece color RGB"""
        # Validar parámetros
        for color, value in [("red", red), ("green", green), ("blue", blue)]:
            if not 0 <= value <= 255:
                raise InvalidParameterError(color, value, "RGB values must be 0-255")
        
        if brightness is None:
            brightness = self._status.brightness
        elif not 0 <= brightness <= 255:
            raise InvalidParameterError("brightness", brightness, "Brightness must be 0-255")
        
        async with self._operation_lock:
            # Aplicar brillo
            final_red = int(red * brightness / 255)
            final_green = int(green * brightness / 255)
            final_blue = int(blue * brightness / 255)
            
            # Construir comando RGB basado en gatt_bytes.txt
            rgb_packet = bytearray.fromhex("69 96 05 02")
            rgb_packet.extend([final_red, final_green, final_blue])
            
            await self._write_command(rgb_packet)
            
            # Actualizar estado
            self._status.red = red
            self._status.green = green
            self._status.blue = blue
            self._status.brightness = brightness
            self._notify_status_change()
            
            logger.debug(f"Color set to RGB({red}, {green}, {blue}) with brightness {brightness}")

    async def set_brightness(self, brightness: int):
        """Establece brillo manteniendo el color actual"""
        if not 0 <= brightness <= 255:
            raise InvalidParameterError("brightness", brightness, "Brightness must be 0-255")
        
        await self.set_color_to_rgb(
            self._status.red, 
            self._status.green, 
            self._status.blue, 
            brightness
        )

    # Efectos mejorados
    async def fade_to_color(self, start_color: Tuple[int, int, int], end_color: Tuple[int, int, int], duration: float):
        """Transición suave entre colores"""
        if duration <= 0:
            raise InvalidParameterError("duration", duration, "Duration must be positive")
        
        steps = max(50, int(duration * 20))  # 20 steps per second minimum
        delay = duration / steps
        
        r1, g1, b1 = start_color
        r2, g2, b2 = end_color
        
        for step in range(steps + 1):
            progress = step / steps
            red = int(r1 + (r2 - r1) * progress)
            green = int(g1 + (g2 - g1) * progress)
            blue = int(b1 + (b2 - b1) * progress)
            
            await self.set_color_to_rgb(red, green, blue)
            await asyncio.sleep(delay)

    async def rainbow_cycle(self, duration_per_color: float):
        """Ciclo de arco iris mejorado"""
        if duration_per_color <= 0:
            raise InvalidParameterError("duration_per_color", duration_per_color, "Duration must be positive")
        
        self._status.effect = "rainbow_cycle"
        self._notify_status_change()
        
        try:
            steps = 360
            delay = duration_per_color / steps
            
            for hue in range(steps):
                r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue / 360, 1.0, 1.0)]
                await self.set_color_to_rgb(r, g, b)
                await asyncio.sleep(delay)
        finally:
            self._status.effect = None
            self._notify_status_change()

    async def breathing_light(self, color: Tuple[int, int, int], duration: float):
        """Efecto de respiración"""
        if duration <= 0:
            raise InvalidParameterError("duration", duration, "Duration must be positive")
        
        self._status.effect = "breathing"
        self._notify_status_change()
        
        try:
            steps = 100
            delay = duration / (steps * 2)
            r, g, b = color
            
            # Subir brillo
            for step in range(steps):
                brightness = int((step / steps) * 255)
                await self.set_color_to_rgb(r, g, b, brightness)
                await asyncio.sleep(delay)
            
            # Bajar brillo  
            for step in range(steps, 0, -1):
                brightness = int((step / steps) * 255)
                await self.set_color_to_rgb(r, g, b, brightness)
                await asyncio.sleep(delay)
        finally:
            self._status.effect = None
            self._notify_status_change()

    async def strobe_light(self, color: Tuple[int, int, int], duration: float, flashes: int):
        """Efecto estroboscópico"""
        if duration <= 0:
            raise InvalidParameterError("duration", duration, "Duration must be positive")
        if flashes <= 0:
            raise InvalidParameterError("flashes", flashes, "Flashes must be positive")
        
        self._status.effect = "strobe"
        self._notify_status_change()
        
        try:
            r, g, b = color
            delay = duration / (flashes * 2)
            
            for _ in range(flashes):
                await self.set_color_to_rgb(r, g, b)
                await asyncio.sleep(delay)
                await self.turn_off()
                await asyncio.sleep(delay)
        finally:
            self._status.effect = None
            self._notify_status_change()

    # Propiedades de estado
    @property
    def is_connected(self) -> bool:
        """Indica si está conectado"""
        return self._connection_state == ConnectionState.CONNECTED

    @property
    def connection_state(self) -> ConnectionState:
        """Estado actual de conexión"""
        return self._connection_state

    @property
    def status(self) -> LEDStatus:
        """Estado actual del LED"""
        return self._status

    @property
    def mac_address(self) -> Optional[str]:
        """Dirección MAC del dispositivo"""
        return self._mac

    @property
    def uuid(self) -> Optional[str]:
        """UUID de comunicación"""
        return self._uuid

    @property
    def last_error(self) -> Optional[str]:
        """Último error ocurrido"""
        return self._last_error

    # Métodos de compatibilidad hacia atrás
    async def _ensure_connected(self):
        """Método de compatibilidad"""
        if not self.is_connected:
            await self.initialize()

    async def _disconnect(self):
        """Método de compatibilidad"""
        await self.disconnect()