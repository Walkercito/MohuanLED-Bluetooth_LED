# MohuanLED Bluetooth Control

**BJ_LED_M** es una librería de Python diseñada para controlar los LEDs de la marca MohuanLED mediante Bluetooth directamente destu Laptop u Ordenador de mesa (en este caso es necesario un adaptador Bluetooth). Esta librería hace desde cosas simples como encender/apagar, cambiar colores hasta aplicar animaciones, reacciones a acciones del exterior, entre otros. También incluye un GUI construido sobre **PyQt6** para un control más intuitivo sobre las luces.

## Uso
La librería es completamente asíncrona, por lo tanto es necesario el uso de `asyncio` y `await`. En este ejemplo se establece una conección directa conociendo el UUID y la dirección de los LEDs
```python
from bj_led import BJLEDInstance
import asyncio

ADRESS = '64:11:a8:00:8b:a6'                       # dirección de ejemplo
UUID = '0000ee02-0000-1000-2000-00805f9b34fb'      # UUID de ejemplo

async def main():
    led = BJLEDInstance(address = ADRESS, uuid = UUID)

    await led.turn_on()
    await led.set_color_to_rgb(255, 0, 0)          # Se cambia el color a rojo en RGB

    asyncio.sleep(5)                               # Se espera 5 segundos
    await led.turn_off()                           # Se apagan los LEDs y se desconecta correctamente
    await led._disconnect()                        # para limpiar el buffer correctamente
 

asyncio.run(main())
```

## Funcionalidades

- Controlar MohuanLED via Bluetooth (BLE).
- Apagar y encender los LEDs
- Cambiar de color en todo el expectro RGB
- Aplicar efectos como:
  - Desbanecimiento de color.
  - Parpadeo de color.
  - Efecto de respiración entre colores.
  - Ciclo arcoíris.
  - Efecto de olas
- Interfaz gráfica usando **PyQt6** (En desarrollo).
- Soporte de CLI para comandos básicos (En desarrollo).
- Escaner de dispositivos de la marca llamados 'BJ_LED' para conecciones dinámicas (En desarrollo).
- Detector de UUIDs y direcciones de forma dinámica 

## Instalación

### Requisitos

- Python 3.8 o superior.
- PyQt6 y qasync.
- Chip Bluetooth integrado o adaptador.
- Luces de MohuanLED.

La librería puede ser instalada mediante `pip`:
```bash
pip install BJ_LED_M
```

O instalar directamente desde la raíz:
```bash
git clone https://github.com/Walkercito/MohuanLED-Bluetooth_LED
cd BJ_LED_M
pip install .
```

Aplicando efectos.
Puedes añadir diferentes efectos a las luces como los pueden ser `rainbow_cycle`, `wave_effect`, `strobe_light`, etc.
```python
# Aplica el efecto 'rainbow_cycle'
await led.rainbow_cycle(duration_per_color = 5.0)

# Aplica el efecto `'strobe_light' con 10 parpadeos
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
git clone https://github.com/Walkercito/MohuanLED-Bluetooth_LED
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

License
Este proyecto está resguardado tras MIT Licence - vea el archivo LICENCE para más infomación.

### Acknowledgments
- Bleak: Para manipular dispositvos Bluetooth de Baja Energía (BLE).
- PyQt6: Para los gráficos del interfaz.
- qasync: Para manejar prosecos asíncronos dentro de PyQt6
