import os
import sys
import asyncio
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QSlider, QLabel, QSystemTrayIcon, QMenu
from qasync import QEventLoop
from dotenv import load_dotenv

from bluelights.manager import BJLEDInstance as Instance

load_dotenv()

LED_MAC_ADDRESS = os.getenv('LED_MAC_ADDRESS')
LED_UUID = os.getenv('LED_UUID')


class LEDController(QWidget):
    def __init__(self, led_instance):
        super().__init__()
        self.led_instance = led_instance
        self.init_ui()
        self.init_tray_icon()

    def init_ui(self):
        self.setWindowTitle('LED Controller')
        layout = QVBoxLayout()

        # Botón de encender
        self.on_button = QPushButton('Turn ON')
        self.on_button.clicked.connect(lambda: asyncio.create_task(self.turn_on_with_initial_color()))
        layout.addWidget(self.on_button)

        # Botón de apagar
        self.off_button = QPushButton('Turn OFF')
        self.off_button.clicked.connect(lambda: asyncio.create_task(self.led_instance.turn_off()))
        layout.addWidget(self.off_button)

        # Slider de color rojo
        self.red_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_slider.setMaximum(255)
        self.red_slider.setValue(0)
        self.red_slider.valueChanged.connect(self.update_color)
        layout.addWidget(QLabel("Red"))
        layout.addWidget(self.red_slider)

        # Slider de color verde
        self.green_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_slider.setMaximum(255)
        self.green_slider.setValue(0)
        self.green_slider.valueChanged.connect(self.update_color)
        layout.addWidget(QLabel("Green"))
        layout.addWidget(self.green_slider)

        # Slider de color azul
        self.blue_slider = QSlider(Qt.Orientation.Horizontal)
        self.blue_slider.setMaximum(255)
        self.blue_slider.setValue(0)
        self.blue_slider.valueChanged.connect(self.update_color)
        layout.addWidget(QLabel("Blue"))
        layout.addWidget(self.blue_slider)

        # Botón para la animación del ciclo arcoíris
        self.rainbow_button = QPushButton('Rainbow Cycle')
        self.rainbow_button.clicked.connect(lambda: asyncio.create_task(self.led_instance.rainbow_cycle(5.0)))
        layout.addWidget(self.rainbow_button)

        # Botón para el efecto "fade" entre colores
        self.fade_button = QPushButton('Fade Colors')
        self.fade_button.clicked.connect(lambda: asyncio.create_task(self.fade_colors()))
        layout.addWidget(self.fade_button)

        self.setLayout(layout)

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(QIcon("avatar.jpg"), parent=self)
        self.tray_icon.setToolTip("LED Controller")

        # Crear menú contextual para el icono en la bandeja
        self.tray_menu = QMenu()
        self.exit_action = QAction("Exit")
        self.exit_action.triggered.connect(self.exit_application)
        self.tray_menu.addAction(self.exit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)  # Conectar la señal de activación
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        """Maneja los clics en el ícono de la bandeja."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()  # Mostrar la ventana principal

    def closeEvent(self, event):
        """Override closeEvent to minimize to tray instead of closing."""
        self.hide()
        event.ignore()

    def exit_application(self):
        """Apaga los LEDs con un titileo rojo y luego cierra la aplicación."""
        # Ejecutar el efecto de titileo rojo usando asyncio.run_coroutine_threadsafe
        asyncio.run_coroutine_threadsafe(self._exit_application(), asyncio.get_event_loop())

    async def _exit_application(self):
        """Coroutine para manejar el apagado y desconexión."""
        # Ejecutar efecto de titileo rojo
        await self.led_instance.strobe_light(color=(255, 0, 0), duration=5.0, flashes=10)
        await self.led_instance.turn_off()  # Apagar los LEDs
        await self.led_instance._disconnect()  # Desconectar
        QApplication.quit()  # Cerrar la aplicación

    async def turn_on_with_initial_color(self):
        """Enciende los LEDs y ajusta el color inicial basado en los valores de los sliders."""
        await self.led_instance.turn_on()

        # Obtener los valores actuales de los sliders
        red = self.red_slider.value()
        green = self.green_slider.value()
        blue = self.blue_slider.value()

        # Validar si los sliders están en 0 (para evitar aplicar color blanco)
        if red == 0 and green == 0 and blue == 0:
            # Si todos están en 0, aplicar un color predeterminado (e.g., rojo)
            red, green, blue = 255, 0, 0  # Color rojo como predeterminado

        # Establecer el color inicial al encender
        await self.led_instance.set_color_to_rgb(red, green, blue)

    def update_color(self):
        """Método para actualizar el color RGB cuando los sliders cambian."""
        red = self.red_slider.value()
        green = self.green_slider.value()
        blue = self.blue_slider.value()
        asyncio.create_task(self.led_instance.set_color_to_rgb(red, green, blue))

    async def fade_colors(self):
        """Método para ejecutar el efecto fade entre dos colores."""
        start_color = (self.red_slider.value(), self.green_slider.value(), self.blue_slider.value())
        end_color = (255, 0, 0)  # Ejemplo: fade hacia rojo
        await self.led_instance.fade_to_color(start_color, end_color, 5.0)


async def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)  # Integrar el bucle de eventos de Qt con asyncio
    asyncio.set_event_loop(loop)

    led_instance = Instance(address=LED_MAC_ADDRESS, uuid=LED_UUID)  # Reemplaza con tu instancia LED
    controller = LEDController(led_instance)
    controller.show()

    with loop:
        await loop.run_forever()

asyncio.run(main())