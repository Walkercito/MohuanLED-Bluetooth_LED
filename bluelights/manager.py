import os
import asyncio
import colorsys
import logging
from dotenv import load_dotenv
from bleak import BleakClient
from bleak.exc import BleakError
from .scanner import Scanner
from typing import List

LOGGER = logging.getLogger(__name__)
load_dotenv()

LED_MAC_ADDRESS = os.getenv("LED_MAC_ADDRESS")
LED_UUID = os.getenv("LED_UUID")

TURN_ON_CMD = bytearray.fromhex("69 96 02 01 01")
TURN_OFF_CMD = bytearray.fromhex("69 96 02 01 00")

class BJLEDInstance:
    def __init__(self, address: str = None, uuid: str = None, reset: bool = False, delay: int = 120) -> None:
        self.loop = asyncio.get_event_loop()
        self._mac = address or LED_MAC_ADDRESS
        self._uuid = uuid or LED_UUID
        self._reset = reset
        self._delay = delay
        self._client: BleakClient | None = None
        self._is_on = None
        self._rgb_color = None
        self._brightness = 255
        self._effect = None
        self._effect_speed = 0x64
        self._color_mode = "RGB"
        self._scanner = Scanner(timeout=15.0, retries=2)

    async def initialize(self) -> None:
        try:
            if not self._mac or not self._uuid:
                LOGGER.info("MAC or UUID not provided. Searching for LED...")
                self._mac, uuids = await self._scanner.run()
                if not self._mac:
                    raise ValueError("LED device not found. Make sure it is powered on and within range.")
                if uuids:
                    await self._test_uuids(uuids)
                if not self._uuid:
                    raise ValueError(f"No compatible UUID found for the LED device at {self._mac}.")
            LOGGER.info(f"Initialized LED with MAC: {self._mac} and UUID: {self._uuid}")
        except BleakError as e:
            if "powered" in str(e).lower() or "adapter" in str(e).lower():
                raise ValueError(f"Bluetooth adapter issue: {e}. Try: sudo bluetoothctl power on.")
            raise

    async def _test_uuids(self, uuids: List[str]) -> None:
        for uuid in uuids:
            try:
                self._uuid = uuid
                await self._ensure_connected()
                await self._write(TURN_ON_CMD)
                await self._write(TURN_OFF_CMD)
                return
            except Exception:
                await self._disconnect()
        self._uuid = None

    async def _ensure_connected(self) -> None:
        if not self._mac or not self._uuid:
            raise ValueError("MAC address or UUID is not set.")
        if self._client and self._client.is_connected:
            return
        self._client = BleakClient(self._mac)
        try:
            await asyncio.wait_for(self._client.connect(), timeout=10.0)
        except asyncio.TimeoutError:
            raise ValueError(f"Connection to {self._mac} timed out after 10 seconds")
        except Exception as e:
            raise ValueError(f"Failed to connect to {self._mac}: {e}")

    async def _disconnect(self) -> None:
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception as e:
                LOGGER.warning(f"Error during disconnect: {e}")

    async def _write(self, data: bytearray):
        await self._ensure_connected()
        try:
            await asyncio.wait_for(
                self._client.write_gatt_char(self._uuid, data, False),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            raise ValueError("Command timed out - LED may be unresponsive")
        except Exception as e:
            raise ValueError(f"Failed to send command: {e}")

    async def turn_on(self):
        await self._ensure_connected()
        await self._write(TURN_ON_CMD)
        self._is_on = True

    async def turn_off(self):
        await self._ensure_connected()
        await self._write(TURN_OFF_CMD)
        self._is_on = False

    async def set_color_to_rgb(self, red: int, green: int, blue: int, brightness: int = None):
        if brightness is None:
            brightness = self._brightness
        red = int(red * brightness / 255)
        green = int(green * brightness / 255)
        blue = int(blue * brightness / 255)
        rgb_packet = bytearray.fromhex("69 96 05 02")
        rgb_packet.append(red)
        rgb_packet.append(green)
        rgb_packet.append(blue)
        await self._write(rgb_packet)
        self._rgb_color = (red, green, blue)

    async def fade_to_color(self, start_color: tuple, end_color: tuple, duration: float):
        steps = 100
        delay = duration / steps
        r1, g1, b1 = start_color
        r2, g2, b2 = end_color
        for step in range(steps + 1):
            red = int(r1 + (r2 - r1) * step / steps)
            green = int(g1 + (g2 - g1) * step / steps)
            blue = int(b1 + (b2 - b1) * step / steps)
            await self.set_color_to_rgb(red, green, blue)
            await asyncio.sleep(delay)

    async def fade_between_colors(self, colors: list, duration_per_color: float):
        for i in range(len(colors) - 1):
            await self.fade_to_color(colors[i], colors[i + 1], duration_per_color)

    async def wave_effect(self, colors: list, duration_per_wave: float):
        steps = len(colors) - 1
        for i in range(steps):
            await self.fade_to_color(colors[i], colors[i + 1], duration_per_wave)

    async def rainbow_cycle(self, duration_per_color: float):
        steps = 360
        delay = duration_per_color / steps
        for hue in range(steps):
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue / 360, 1.0, 1.0)]
            await self.set_color_to_rgb(r, g, b)
            await asyncio.sleep(delay)

    async def breathing_light(self, color: tuple, duration: float):
        steps = 100
        delay = duration / (steps * 2)
        r, g, b = color
        for step in range(steps):
            brightness = int((step / steps) * 255)
            await self.set_color_to_rgb(r, g, b, brightness)
            await asyncio.sleep(delay)
        for step in range(steps, 0, -1):
            brightness = int((step / steps) * 255)
            await self.set_color_to_rgb(r, g, b, brightness)
            await asyncio.sleep(delay)

    async def strobe_light(self, color: tuple, duration: float, flashes: int):
        r, g, b = color
        delay = duration / (flashes * 2)
        for _ in range(flashes):
            await self.set_color_to_rgb(r, g, b)
            await asyncio.sleep(delay)
            await self.turn_off()
            await asyncio.sleep(delay)

    async def color_cycle(self, colors: list, duration_per_color: float):
        while True:
            await self.fade_between_colors(colors, duration_per_color)
