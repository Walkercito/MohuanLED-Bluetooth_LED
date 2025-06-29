import asyncio
import logging
from typing import Tuple, List, Optional
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

logger = logging.getLogger(__name__)

class Scanner:
    def __init__(self, timeout: float = 10.0, retries: int = 2):
        self.timeout = timeout
        self.retries = retries

    async def scan_led(self) -> Tuple[Optional[str], Optional[object]]:
        for attempt in range(self.retries + 1):
            try:
                logger.info(f"Scanning for devices (attempt {attempt + 1})...")
                devices = await asyncio.wait_for(
                    BleakScanner.discover(timeout=self.timeout),
                    timeout=self.timeout + 5
                )
                for device in devices:
                    name = device.name or ""
                    if "BJ_LED_M" in name:
                        logger.info(f"Found LED: {name} ({device.address})")
                        return device.address, device
                if attempt == self.retries:
                    return None, None
                await asyncio.sleep(2)
            except asyncio.TimeoutError:
                if attempt == self.retries:
                    raise
                await asyncio.sleep(1)
            except BleakError as e:
                logger.error(f"Bluetooth error: {e}")
                if "powered" in str(e).lower() or "adapter" in str(e).lower():
                    raise
                if attempt == self.retries:
                    raise
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt == self.retries:
                    raise
                await asyncio.sleep(1)
        return None, None

    async def scan_uuids(self, address: str) -> List[str]:
        try:
            logger.info(f"Scanning UUIDs for {address}...")
            async with BleakClient(address) as client:
                services = await client.get_services()
                return [char.uuid for service in services for char in service.characteristics]
        except Exception as e:
            logger.error(f"Failed to scan UUIDs for {address}: {e}")
            raise

    async def run(self) -> Tuple[Optional[str], List[str]]:
        mac_address, device = await self.scan_led()
        if mac_address:
            try:
                uuids = await self.scan_uuids(mac_address)
                return mac_address, uuids
            except Exception as e:
                logger.error(f"UUID scan failed: {e}")
                return mac_address, []
        return None, []
