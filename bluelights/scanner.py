import asyncio
import logging
from typing import Tuple, List, Optional, Dict, Any
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    address: str
    name: Optional[str]
    rssi: Optional[int]
    metadata: Dict[str, Any]
    is_led_candidate: bool = False
    confidence: float = 0.0

class ImprovedScanner:
    def __init__(self, timeout: float = 10.0, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        
        # Patrones conocidos para LEDs Bluetooth
        self.led_patterns = [
            "BJ_LED_M",      # Original pattern
            "LED",           # Generic LED
            "Light",         # Generic Light
            "Strip",         # LED Strip
            "Bulb",          # LED Bulb
            "RGB",           # RGB devices
            "LEDBLE",        # Common LED BLE naming
            "ELK-BLEDOM",    # Another common LED controller
            "QHM-",          # Some LED controllers
            "TRIONES",       # TRIONES LED controllers
            "Magic",         # Magic Light controllers
        ]
        
        # UUIDs conocidos para servicios de LED
        self.led_service_uuids = [
            "0000ee02-0000-1000-2000-00805f9b34fb",  # Common LED service
            "0000ee01-0000-1000-8000-00805f9b34fb",  # Alternative LED service
            "0000ffe0-0000-1000-8000-00805f9b34fb",  # Another common one
            "0000ffd0-0000-1000-8000-00805f9b34fb",  # Yet another
        ]

    async def scan_all_devices(self, detailed: bool = False) -> List[DeviceInfo]:
        """Escanea todos los dispositivos y los categoriza"""
        devices_found = []
        
        for attempt in range(self.retries + 1):
            try:
                logger.info(f"Scanning for devices (attempt {attempt + 1})...")
                
                # Intentar con datos de advertising primero
                try:
                    devices_with_adv = await asyncio.wait_for(
                        BleakScanner.discover(timeout=self.timeout, return_adv=True),
                        timeout=self.timeout + 5
                    )
                    
                    logger.info(f"Found {len(devices_with_adv)} devices")
                    
                    for device, adv_data in devices_with_adv.items():
                        device_info = DeviceInfo(
                            address=device.address,
                            name=device.name,
                            rssi=adv_data.rssi if adv_data else None,
                            metadata={
                                'services': list(adv_data.service_uuids) if adv_data and adv_data.service_uuids else [],
                                'manufacturer_data': dict(adv_data.manufacturer_data) if adv_data and adv_data.manufacturer_data else {},
                                'service_data': dict(adv_data.service_data) if adv_data and adv_data.service_data else {},
                            }
                        )
                        
                        # Analizar si es candidato a LED
                        device_info.is_led_candidate, device_info.confidence = self._analyze_led_candidate(device_info)
                        devices_found.append(device_info)
                
                except Exception as adv_error:
                    # Fallback: escaneo simple sin datos de advertising
                    logger.debug(f"Advanced scan failed ({adv_error}), trying simple scan...")
                    
                    devices_simple = await asyncio.wait_for(
                        BleakScanner.discover(timeout=self.timeout),
                        timeout=self.timeout + 5
                    )
                    
                    logger.info(f"Found {len(devices_simple)} devices")
                    
                    for device in devices_simple:
                        device_info = DeviceInfo(
                            address=device.address,
                            name=device.name,
                            rssi=getattr(device, 'rssi', None),
                            metadata={
                                'services': [],
                                'manufacturer_data': {},
                                'service_data': {},
                            }
                        )
                        
                        # Analizar si es candidato a LED
                        device_info.is_led_candidate, device_info.confidence = self._analyze_led_candidate(device_info)
                        devices_found.append(device_info)
                
                if devices_found:
                    self._log_discovered_devices(devices_found, detailed)
                    return devices_found
                    
                if attempt < self.retries:
                    logger.info(f"No devices found, retrying in 2 seconds...")
                    await asyncio.sleep(2)
                    
            except asyncio.TimeoutError:
                logger.warning(f"Scan timeout on attempt {attempt + 1}")
                if attempt < self.retries:
                    await asyncio.sleep(1)
            except BleakError as e:
                logger.error(f"Bluetooth error: {e}")
                if "powered" in str(e).lower() or "adapter" in str(e).lower():
                    raise RuntimeError(f"Bluetooth adapter issue: {e}. Try: sudo bluetoothctl power on")
                if attempt < self.retries:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error during scan: {e}")
                if attempt < self.retries:
                    await asyncio.sleep(1)
        
        return devices_found

    def _analyze_led_candidate(self, device_info: DeviceInfo) -> Tuple[bool, float]:
        """Analiza si un dispositivo es candidato a ser un LED"""
        confidence = 0.0
        
        # Analizar nombre
        if device_info.name:
            name_lower = device_info.name.lower()
            for pattern in self.led_patterns:
                if pattern.lower() in name_lower:
                    confidence += 0.4  # High confidence from name
                    break
            
            # Patrones adicionales que pueden indicar LEDs
            led_keywords = ['light', 'lamp', 'color', 'rgb', 'smart', 'strip', 'bulb']
            for keyword in led_keywords:
                if keyword in name_lower:
                    confidence += 0.2
                    break
        
        # Analizar servicios UUID
        services = device_info.metadata.get('services', [])
        for service_uuid in services:
            if str(service_uuid).lower() in [uuid.lower() for uuid in self.led_service_uuids]:
                confidence += 0.5  # Very high confidence from known LED service
                break
        
        # Analizar datos del fabricante
        manufacturer_data = device_info.metadata.get('manufacturer_data', {})
        if manufacturer_data:
            confidence += 0.1  # Small boost for having manufacturer data
        
        # Si la señal es muy débil, reducir confianza
        if device_info.rssi and device_info.rssi < -80:
            confidence *= 0.8
        
        # Es candidato si tiene alguna confianza
        is_candidate = confidence > 0.0
        
        return is_candidate, min(confidence, 1.0)

    def _log_discovered_devices(self, devices: List[DeviceInfo], detailed: bool = False):
        """Log de dispositivos descubiertos"""
        led_candidates = [d for d in devices if d.is_led_candidate]
        other_devices = [d for d in devices if not d.is_led_candidate]
        
        if led_candidates:
            logger.info("🎯 LED CANDIDATES FOUND:")
            for device in sorted(led_candidates, key=lambda x: x.confidence, reverse=True):
                confidence_percent = int(device.confidence * 100)
                signal_info = f", Signal: {device.rssi}dBm" if device.rssi else ""
                logger.info(f"  ✨ {device.name or 'Unknown'} ({device.address}) - {confidence_percent}% confidence{signal_info}")
                
                if detailed and device.metadata['services']:
                    logger.info(f"     Services: {device.metadata['services'][:3]}")  # Show first 3 services
        
        if detailed and other_devices:
            logger.info(f"📱 OTHER DEVICES ({len(other_devices)}):")
            for device in other_devices[:5]:  # Show first 5 only
                signal_info = f", Signal: {device.rssi}dBm" if device.rssi else ""
                logger.info(f"  • {device.name or 'Unknown'} ({device.address}){signal_info}")
            
            if len(other_devices) > 5:
                logger.info(f"  ... and {len(other_devices) - 5} more devices")

    async def scan_led(self, auto_select: bool = True) -> Tuple[Optional[str], Optional[DeviceInfo]]:
        """Busca dispositivos LED con lógica mejorada"""
        devices = await self.scan_all_devices(detailed=True)
        
        if not devices:
            logger.warning("No devices found during scan")
            return None, None
        
        # Filtrar candidatos LED
        led_candidates = [d for d in devices if d.is_led_candidate]
        
        if not led_candidates:
            logger.warning("No LED candidates found. Discovered devices:")
            for i, device in enumerate(devices[:10], 1):  # Show first 10
                signal_info = f" (Signal: {device.rssi}dBm)" if device.rssi else ""
                logger.warning(f"  {i}. {device.name or 'Unknown'} ({device.address}){signal_info}")
            
            # Sugerir el dispositivo con mejor señal como posible candidato
            if devices:
                best_signal_device = max(devices, key=lambda x: x.rssi or -999)
                logger.info(f"💡 Try connecting manually to: {best_signal_device.address}")
            
            return None, None
        
        if auto_select:
            # Seleccionar automáticamente el mejor candidato
            best_candidate = max(led_candidates, key=lambda x: x.confidence)
            logger.info(f"🎯 Auto-selected best LED candidate: {best_candidate.name} ({best_candidate.address}) - {int(best_candidate.confidence * 100)}% confidence")
            return best_candidate.address, best_candidate
        else:
            # Devolver el primer candidato para compatibilidad
            return led_candidates[0].address, led_candidates[0]

    async def scan_uuids(self, address: str) -> List[str]:
        """Escanea UUIDs de un dispositivo específico"""
        try:
            logger.info(f"Scanning UUIDs for {address}...")
            async with BleakClient(address) as client:
                services = await client.get_services()
                uuids = []
                
                for service in services:
                    uuids.append(service.uuid)
                    for char in service.characteristics:
                        uuids.append(char.uuid)
                        
                logger.info(f"Found {len(uuids)} UUIDs for {address}")
                
                # Log UUIDs conocidos encontrados
                known_uuids = [uuid for uuid in uuids if str(uuid).lower() in [u.lower() for u in self.led_service_uuids]]
                if known_uuids:
                    logger.info(f"🎯 Known LED UUIDs found: {known_uuids}")
                
                return uuids
                
        except Exception as e:
            logger.error(f"Failed to scan UUIDs for {address}: {e}")
            raise

    async def run(self) -> Tuple[Optional[str], List[str]]:
        """Método principal de escaneo (compatibilidad hacia atrás)"""
        mac_address, device_info = await self.scan_led()
        if mac_address:
            try:
                uuids = await self.scan_uuids(mac_address)
                return mac_address, uuids
            except Exception as e:
                logger.error(f"UUID scan failed: {e}")
                return mac_address, []
        return None, []

# Alias para compatibilidad hacia atrás
Scanner = ImprovedScanner