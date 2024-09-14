import asyncio
import logging
from bluelights.manager import BJLEDInstance

logging.basicConfig(level=logging.DEBUG)

async def main():
    led = BJLEDInstance()
    
    try:
        await led.initialize()
        await led.turn_on()
        await asyncio.sleep(2)
        await led.turn_off()
    except ValueError as e:
        print(f"Error: {e}")
    finally:
        await led._disconnect()

if __name__ == "__main__":
    asyncio.run(main())