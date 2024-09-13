# BJ_LED_M

**BJ_LED_M** is a Python library designed for controlling MohuanLED Bluetooth lights. With this library, you can turn lights on/off, change colors, and apply various effects such as fading, strobe, and rainbow cycles. It also includes a GUI using **PyQt6** for intuitive control of the lights.

## Features

- Control MohuanLED lights via Bluetooth (BLE).
- Turn lights on and off.
- Change colors using RGB values.
- Apply effects such as:
  - Color fading
  - Strobe light effect
  - Breathing light effect
  - Rainbow color cycle
  - Wave effects between colors
- GUI interface using **PyQt6**.
- CLI support for basic operations.

## Installation

### Requirements

- Python 3.8 or above
- Bluetooth-enabled device
- MohuanLED lights

You can install the library using `pip`:

```bash
pip install BJ_LED_M
```
Alternatively, you can install directly from the source:
```bash
git clone https://github.com/yourusername/BJ_LED_M.git
cd BJ_LED_M
pip install .
```
Usage
Command Line Interface (CLI)
After installation, you can control the lights using the CLI. For example, to turn on the lights:

bash
Copiar código
bjled-cli --on
To turn off the lights:

bash
Copiar código
bjled-cli --off
Python API
You can also control the lights programmatically in your Python scripts. Below are some examples of how to use the library.

Basic Example
python
Copiar código
from bj_led import BJLEDInstance

# Create an instance of the LED controller
led = BJLEDInstance(address="xx:xx:xx:xx:xx", uuid="0000xxxx-0000-1000-8000-00805f9b34fb")

# Turn the LED on
led.turn_on()

# Change the LED color to red
led.set_color_to_rgb(255, 0, 0)

# Turn the LED off
led.turn_off()
Applying Effects
You can apply different effects to the lights, such as a rainbow cycle or a strobe effect.

```python
# Apply a rainbow cycle effect
await led.rainbow_cycle(duration_per_color=5.0)

# Apply a strobe effect with 10 flashes
await led.strobe_light(color=(255, 255, 255), duration=5.0, flashes=10)
```

GUI Control
The library also provides a graphical user interface (GUI) built with PyQt6 to control the lights visually.

To launch the GUI:
```bash
python -m bj_led.gui.app
```
The GUI provides sliders for adjusting the RGB values and buttons to control the lights and apply effects like fading and color cycling.

Configuration
To configure your setup, you can use an .env file to store your MohuanLED light's MAC address and UUID.

Create a .env file in the project directory with the following structure:

```bash
LED_MAC_ADDRESS=xx:xx:xx:xx:xx:xx
LED_UUID=0000xxxx-0000-1000-8000-00805f9b34fb
```
The library will automatically load these values when instantiated.

Development
If you want to contribute or modify the project, you can set up the development environment as follows:

Clone the repository:
```bash
git clone https://github.com/yourusername/BJ_LED_M.git
```

Install the dependencies:
```bash
pip install -r requirements.txt
Run the tests:
```

```bash
pytest
```

License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
- Bleak: For handling Bluetooth Low Energy (BLE) connections.
- PyQt6: For the graphical user interface framework.
