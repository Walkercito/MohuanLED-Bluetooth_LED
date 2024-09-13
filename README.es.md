# 🌈MohuanLED Bluetooth Control

**BJ_LED_M** es una librería de Python diseñada para controlar los LEDs de la marca **MohuanLED** mediante Bluetooth desde tu laptop o PC (se requiere un adaptador Bluetooth si no tienes uno integrado). Esta librería te permite realizar acciones simples como encender/apagar, cambiar colores, hasta aplicar animaciones y reacciones a eventos externos. También incluye una **GUI** construida con **PyQt6** para un control más intuitivo sobre las luces. 🌟

## 🚀Uso
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
    await led.turn_off()                           # Se apagan los LEDs
    await led._disconnect()                        # Se desconecta y limpia el buffer
 

asyncio.run(main())
```

## ⚙️Funcionalidades

- Controlar MohuanLED via Bluetooth (BLE).
- Encender y apagar las luces 💡
- Cambiar colores en todo el espectro RGB 🎨
- Aplicar efectos como:
  - 🔄 Desvanecimiento de color
  - 💡 Parpadeo de color
  - 🌬️ Efecto de respiración entre colores
  - 🌈 Ciclo arcoíris
  - 🌊 Efecto de olas
- Interfaz gráfica (GUI) con **PyQt6** (En desarrollo 🛠️)
- Soporte de CLI para comandos básicos (En desarrollo 🛠️)
- Escáner de dispositivos MohuanLED para conexiones dinámicas (En desarrollo 🛠️)
- Detección automática de UUIDs y direcciones MAC

## 🛠️ Instalación

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

### 🌈 Aplicando Efectos
Puedes añadir diferentes efectos a las luces como los pueden ser `rainbow_cycle`, `wave_effect`, `strobe_light`, etc.
```python
# Aplica el efecto 'rainbow_cycle'
await led.rainbow_cycle(duration_per_color = 5.0)

# Aplica el efecto `'strobe_light' con 10 parpadeos
await led.strobe_light(color=(255, 255, 255), duration=5.0, flashes=10)
```

### 🖥️ Control mediante GUI
La librería también ofrece una interfaz gráfica (GUI) construida con PyQt6 para controlar las luces de manera visual.

Para lanzar la GUI:
```bash
python -m bj_led.gui.app
```
La GUI incluye deslizadores para ajustar los valores RGB y botones para controlar las luces y aplicar efectos como desvanecimientos y ciclos de color.

### ⚙️ Configuración
Puedes usar un archivo `.env` para almacenar la dirección MAC y el UUID de tus luces **MohuanLED** o establecerlas directamente en tu código.

Crea un archivo `.env` en el directorio del proyecto con la siguiente estructura:

```bash
LED_MAC_ADDRESS = "xx:xx:xx:xx:xx:xx"
LED_UUID = "0000xxxx-0000-1000-8000-00805f9b34fb"
```
La librería cargará estos valores automáticamente al instanciar los LEDs.

### 🛠️ Desarrollo
Si deseas contribuir o modificar el proyecto, puedes configurar el entorno de desarrollo de la siguiente manera:

Clona el repositorio:
```bash
git clone https://github.com/Walkercito/MohuanLED-Bluetooth_LED
```

Instala las dependencias:
```bash
pip install -r requirements.txt
```

### 📜 Licencia
Este proyecto está licenciado bajo la **MIT License**. Consulta el archivo LICENSE para más detalles.

### Agradecimientos
- Bleak: Para manipulación de dispositivos Bluetooth Low Energy (BLE) 🔗
- PyQt6: Para la creación de la interfaz gráfica 🖼️
- qasync: Para manejar procesos asíncronos en PyQt6 ⚡
