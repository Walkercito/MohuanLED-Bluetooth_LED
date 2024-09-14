# 🌈 MohuanLED Bluetooth Control
BJ_LED_M is a Python library designed to control MohuanLED brand lights via Bluetooth, directly from your laptop or PC (you’ll need a Bluetooth adapter if it’s not built-in). This library allows you to perform simple actions like turning the lights on/off, changing colors, and applying animations or reactions to external events. It also includes a PyQt6-based GUI for more intuitive control over the lights. 🌟

## 🚀 Usage
The library is fully asynchronous, so you'll need to use asyncio and await. Here's an example of how to establish a direct connection, knowing the UUID and MAC address of the LEDs:

```python
from bluelights import BJLEDInstance
import asyncio

ADDRESS = '64:11:a8:00:8b:a6'                      # Example address
UUID = '0000ee02-0000-1000-2000-00805f9b34fb'      # Example UUID

async def main():
    led = BJLEDInstance(address=ADDRESS, uuid=UUID)

    try:
      await led.turn_on()
      await led.set_color_to_rgb(255, 0, 0)          # Change color to red (RGB)

      await asyncio.sleep(5)                         # Wait 5 seconds
      await led.turn_off()                           # Turn off LEDs and disconnect
    except Exception as e:
      print(e)
      
    finally:
      await led._disconnect()                        # Clear the buffer
     
asyncio.run(main())
```

To preform a dynamic connection, you need to use `.initialize()` to make the Scanner look any LED, here an example:

```python
from bluelights import BJLEDInstance
import asyncio

async def main():
    led = BJLEDInstance()                          # The Scanner will look for 'BJ_LED_M' (name of the devices) and connect
    try:
      await led.initialize()
      await led.turn_on()
      await led.set_color_to_rgb(255, 0, 0)          # Change color to red (RGB)

      await asyncio.sleep(5)                         # Wait 5 seconds
      await led.turn_off()                           # Turn off LEDs and disconnect
    except Exception as e:
      print(e)

    finally:
      await led._disconnect()                        # Clear the buffer
     
asyncio.run(main())
```

> [!WARNING]  
> If you do not proive a MAC Address or a UUID the code WILL requiere `initialize()`


## ⚙️ Features
- Control MohuanLED lights via Bluetooth (BLE)
- Turn the LEDs on and off 💡
- Change colors across the full RGB spectrum 🎨
- Apply effects like:
  - 🔄 Color fade
  - 💡 Color strobe
  - 🌬️ Breathing effect between colors
  - 🌈 Rainbow cycle
  - 🌊 Wave effect
- Graphical user interface (GUI) using PyQt6 (In development 🛠️)
- Command Line Interface (CLI) for basic commands (In development 🛠️)
- Dynamic MohuanLED device scanner for easy connections (In development 🛠️)
- Automatic detection of UUIDs and MAC addresses

## 🛠️ Installation

### Requirements
- Python 3.8 or higher
- PyQt6 and qasync
- Built-in or external Bluetooth adapter
- MohuanLED lights

You can install the library via pip:

```bash
pip install BlueLights
```

Or install it directly from the repository:

```bash
git clone https://github.com/Walkercito/MohuanLED-Bluetooth_LED
cd BlueLights
pip install .
```

### 🌈 Applying Effects
You can add various effects to the lights, such as rainbow_cycle, wave_effect, or strobe_light. Here are a few examples:

```python
# Apply the 'rainbow_cycle' effect
await led.rainbow_cycle(duration_per_color=5.0)

# Apply the 'strobe_light' effect with 10 flashes
await led.strobe_light(color=(255, 255, 255), duration=5.0, flashes=10)
```

### 🖥️ GUI Control
The library also provides a graphical user interface (GUI) built with PyQt6 to visually control the lights.

To launch the GUI:

```bash
python -m bluelights.gui.app
```

The GUI includes sliders to adjust RGB values and buttons to control the lights and apply effects like fading and color cycling.

### ⚙️ Configuration
You can configure your setup using an .env file to store your MohuanLED light’s MAC address and UUID.

Create a .env file in the project directory with the following structure:

```bash
LED_MAC_ADDRESS=xx:xx:xx:xx:xx:xx
LED_UUID=0000xxxx-0000-1000-8000-00805f9b34fb
```
The library will automatically load these values when you instantiate the LEDs.

### 🛠️ Development
If you want to contribute or modify the project, you can set up the development environment as follows:

Clone the repository:

```bash
git clone https://github.com/Walkercito/MohuanLED-Bluetooth_LED
```
Install the dependencies:

```bash
pip install -r requirements.txt
```

### 📜 License
This project is licensed under the MIT License. See the LICENSE file for more details.

### Acknowledgments
- Bleak: For Bluetooth Low Energy (BLE) device control 🔗
- PyQt6: For creating the graphical interface 🖼️
- asyncio: For asyncronus tasks
- qasync: For handling asynchronous processes in PyQt6 ⚡
- python-dotenv: For auto-loading of LED_MAC_ADDRESS and LED_UUID in case of a `.env` file
- nest_asyncio: For asyncio control
