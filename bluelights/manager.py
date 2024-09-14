import os
import asyncio
import colorsys
import logging
from dotenv import load_dotenv
from bleak import BleakClient
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
        self._scanner = Scanner()

    async def initialize(self) -> None:
        if not self._mac or not self._uuid:
            LOGGER.info("MAC or UUID not provided. Searching for LED...")
            self._mac, uuids = await self._scanner.run()
            if not self._mac:
                raise ValueError("LED device not found. Make sure it is powered on and within range.")
            if uuids:
                await self._test_uuids(uuids)
            if not self._uuid:
                raise ValueError("No compatible UUID found for the LED device.")
        
        LOGGER.info(f"Initialized LED with MAC: {self._mac} and UUID: {self._uuid}")

    async def _test_uuids(self, uuids: List[str]) -> None:
        for uuid in uuids:
            try:
                self._uuid = uuid
                await self._ensure_connected()
                await self._write(TURN_ON_CMD)
                await self._write(TURN_OFF_CMD)
                LOGGER.info(f"Found compatible UUID: {uuid}")
                return
            except Exception as e:
                LOGGER.debug(f"UUID {uuid} not compatible: {str(e)}")
                await self._disconnect()
        self._uuid = None

    async def _ensure_connected(self) -> None:
        if not self._mac or not self._uuid:
            raise ValueError("MAC address or UUID is not set. Cannot connect.")
        
        if self._client and self._client.is_connected:
            return
        
        LOGGER.debug(f"Connecting to LED with MAC: {self._mac}")
        self._client = BleakClient(self._mac)
        await self._client.connect()
        LOGGER.debug(f"Connected to LED at {self._mac}")

    async def _disconnect(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            LOGGER.debug(f"Disconnected from LED at {self._mac}")

    async def _write(self, data: bytearray):
        await self._ensure_connected()
        await self._client.write_gatt_char(self._uuid, data, False)
        LOGGER.debug(f"Command {data.hex()} sent to LED at {self._mac}")

    async def turn_on(self):
        await self._ensure_connected()
        await self._write(TURN_ON_CMD)
        self._is_on = True
        LOGGER.info(f"LED at {self._mac} turned on")

    async def turn_off(self):
        await self._ensure_connected()
        await self._write(TURN_OFF_CMD)
        self._is_on = False
        LOGGER.info(f"LED at {self._mac} turned off")


    async def set_color_to_rgb(self, red: int, green: int, blue: int, brightness: int = None):
        """Set the LED to a specific RGB color."""

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
        LOGGER.info(f"LED at {self._mac} set to RGB color: {self._rgb_color}")

    
    async def fade_to_color(self, start_color: tuple, end_color: tuple, duration: float):
        """Fade effect between two colors."""
        steps = 100
        delay = duration / steps

        r1, g1, b1 = start_color
        r2, g2, b2 = end_color

        for step in range (steps + 1):
            red = int(r1 + (r2 - r1) * step / steps)
            green = int(g1 + (g2 - g1) * step / steps)
            blue = int(b1 + (b2 - b1) * step / steps)

            await self.set_color_to_rgb(red, green, blue)
            await  asyncio.sleep(delay)

        LOGGER.info(f"LED at {self._mac} faded to color: {self._rgb_color}")

    
    async def fade_between_colors(self, colors: list, duration_per_color: float):
        """Fade effect between multiple colors."""
        
        for i in range(len(colors) - 1):
            start_color = colors[i]
            end_color = colors[i + 1]
            await self.fade_to_color(start_color, end_color, duration_per_color)
        
        LOGGER.info(f"Completed fade between {len(colors)} colors.")


    async def wave_effect(self, colors: list, duration_per_wave: float):
        """Efecto de onda entre múltiples colores."""
        steps = len(colors) - 1
        delay = duration_per_wave / steps

        for i in range(steps):
            start_color = colors[i]
            end_color = colors[i + 1]
            await self.fade_to_color(start_color, end_color, duration_per_wave)

        LOGGER.info(f"Completed wave effect.")


    async def rainbow_cycle(self, duration_per_color: float):
        """Animación de ciclo de arcoíris."""
        steps = 360
        delay = duration_per_color / steps

        for hue in range(steps):
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue / 360, 1.0, 1.0)]
            await self.set_color_to_rgb(r, g, b)
            await asyncio.sleep(delay)

        LOGGER.info(f"Completed rainbow cycle.")


    async def breathing_light(self, color: tuple, duration: float):
        """"Breathing effect."""

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

        LOGGER.info(f"Completed breathing effect with color {color}")


    async def strobe_light(self, color: tuple, duration: float, flashes: int):
        """Efecto de 'strobe light' (parpadeo rápido)."""
        r, g, b = color
        delay = duration / (flashes * 2)

        for _ in range(flashes):
            await self.set_color_to_rgb(r, g, b)
            await asyncio.sleep(delay)
            await self.turn_off()
            await asyncio.sleep(delay)

        LOGGER.info(f"Completed strobe effect with color {color} and {flashes} flashes.")

    
    async def color_cycle(self, colors: list, duration_per_color: float):
        """Basic animation to cycle through a list of colors."""
        while True:
            await self.fade_between_colors(colors, duration_per_color)