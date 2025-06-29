#!/usr/bin/env python3
"""
Modern LED Controller GUI with proper async integration and error handling.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer, Qt, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QSystemTrayIcon, QMenu, QMessageBox,
    QProgressBar, QFrame, QGroupBox, QGridLayout, QSpacerItem,
    QSizePolicy, QStatusBar, QComboBox, QSpinBox
)
import qasync
from dotenv import load_dotenv

# Try to import the LED manager - handle import errors gracefully
try:
    from bluelights.manager import BJLEDInstance
except ImportError:
    print("Warning: bluelights module not found. Running in demo mode.")
    BJLEDInstance = None

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class LEDState:
    """Represents the current state of the LED."""
    is_on: bool = False
    red: int = 0
    green: int = 0
    blue: int = 0
    brightness: int = 255
    effect: Optional[str] = None
    connection_state: ConnectionState = ConnectionState.DISCONNECTED

class LEDController(QObject):
    """Async LED controller that runs in a separate thread."""
    
    # Signals to communicate with the GUI
    connection_state_changed = pyqtSignal(ConnectionState)
    led_state_changed = pyqtSignal(LEDState)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # message, level
    
    def __init__(self):
        super().__init__()
        self.led_instance: Optional[BJLEDInstance] = None
        self.current_state = LEDState()
        self._mac_address = os.getenv('LED_MAC_ADDRESS')
        self._uuid = os.getenv('LED_UUID')
        
    async def initialize(self) -> bool:
        """Initialize the LED connection."""
        try:
            self.connection_state_changed.emit(ConnectionState.CONNECTING)
            self.log_message.emit("Initializing LED connection...", "info")
            
            if BJLEDInstance is None:
                raise ImportError("LED module not available")
                
            self.led_instance = BJLEDInstance(
                address=self._mac_address,
                uuid=self._uuid
            )
            
            await self.led_instance.initialize()
            
            self.current_state.connection_state = ConnectionState.CONNECTED
            self.connection_state_changed.emit(ConnectionState.CONNECTED)
            self.led_state_changed.emit(self.current_state)
            self.log_message.emit("LED connected successfully!", "success")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize LED: {str(e)}"
            self.error_occurred.emit(error_msg)
            self.log_message.emit(error_msg, "error")
            self.current_state.connection_state = ConnectionState.ERROR
            self.connection_state_changed.emit(ConnectionState.ERROR)
            return False
    
    async def disconnect(self):
        """Disconnect from the LED."""
        try:
            if self.led_instance:
                await self.led_instance._disconnect()
            self.current_state.connection_state = ConnectionState.DISCONNECTED
            self.connection_state_changed.emit(ConnectionState.DISCONNECTED)
            self.log_message.emit("LED disconnected", "info")
        except Exception as e:
            self.error_occurred.emit(f"Error disconnecting: {str(e)}")
    
    async def turn_on(self):
        """Turn on the LED."""
        try:
            if not self.led_instance:
                raise ValueError("LED not initialized")
            await self.led_instance.turn_on()
            self.current_state.is_on = True
            self.led_state_changed.emit(self.current_state)
            self.log_message.emit("LED turned ON", "success")
        except Exception as e:
            self.error_occurred.emit(f"Failed to turn on LED: {str(e)}")
    
    async def turn_off(self):
        """Turn off the LED."""
        try:
            if not self.led_instance:
                raise ValueError("LED not initialized")
            await self.led_instance.turn_off()
            self.current_state.is_on = False
            self.led_state_changed.emit(self.current_state)
            self.log_message.emit("LED turned OFF", "success")
        except Exception as e:
            self.error_occurred.emit(f"Failed to turn off LED: {str(e)}")
    
    async def set_color(self, red: int, green: int, blue: int):
        """Set LED color."""
        try:
            if not self.led_instance:
                raise ValueError("LED not initialized")
            await self.led_instance.set_color_to_rgb(red, green, blue)
            self.current_state.red = red
            self.current_state.green = green
            self.current_state.blue = blue
            self.led_state_changed.emit(self.current_state)
            self.log_message.emit(f"Color set to RGB({red}, {green}, {blue})", "info")
        except Exception as e:
            self.error_occurred.emit(f"Failed to set color: {str(e)}")
    
    async def apply_effect(self, effect_name: str, **kwargs):
        """Apply an effect to the LED."""
        try:
            if not self.led_instance:
                raise ValueError("LED not initialized")
            
            self.current_state.effect = effect_name
            self.led_state_changed.emit(self.current_state)
            
            if effect_name == "rainbow_cycle":
                duration = kwargs.get('duration', 5.0)
                await self.led_instance.rainbow_cycle(duration)
            elif effect_name == "breathing":
                color = kwargs.get('color', (255, 255, 255))
                duration = kwargs.get('duration', 3.0)
                await self.led_instance.breathing_light(color, duration)
            elif effect_name == "strobe":
                color = kwargs.get('color', (255, 255, 255))
                duration = kwargs.get('duration', 2.0)
                flashes = kwargs.get('flashes', 10)
                await self.led_instance.strobe_light(color, duration, flashes)
            
            self.current_state.effect = None
            self.led_state_changed.emit(self.current_state)
            self.log_message.emit(f"Effect '{effect_name}' completed", "success")
            
        except Exception as e:
            self.current_state.effect = None
            self.led_state_changed.emit(self.current_state)
            self.error_occurred.emit(f"Failed to apply effect: {str(e)}")

class ColorPreview(QWidget):
    """Widget to preview the current color."""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(60, 60)
        self.color = QColor(0, 0, 0)
    
    def set_color(self, red: int, green: int, blue: int):
        """Update the preview color."""
        self.color = QColor(red, green, blue)
        self.update()
    
    def paintEvent(self, event):
        """Paint the color preview."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.color)
        painter.setPen(QColor(200, 200, 200))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)

class StatusIndicator(QWidget):
    """Connection status indicator."""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(20, 20)
        self.state = ConnectionState.DISCONNECTED
    
    def set_state(self, state: ConnectionState):
        """Update the connection state."""
        self.state = state
        self.update()
    
    def paintEvent(self, event):
        """Paint the status indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = {
            ConnectionState.DISCONNECTED: QColor(128, 128, 128),
            ConnectionState.CONNECTING: QColor(255, 165, 0),
            ConnectionState.CONNECTED: QColor(0, 255, 0),
            ConnectionState.ERROR: QColor(255, 0, 0)
        }
        
        painter.setBrush(colors.get(self.state, QColor(128, 128, 128)))
        painter.setPen(QColor(0, 0, 0))
        painter.drawEllipse(self.rect().adjusted(2, 2, -2, -2))

class ModernLEDControllerGUI(QMainWindow):
    """Modern LED Controller main window."""
    
    def __init__(self):
        super().__init__()
        self.led_controller = LEDController()
        self.current_state = LEDState()
        self.is_demo_mode = BJLEDInstance is None
        
        self.setup_ui()
        self.setup_connections()
        self.setup_tray_icon()
        
        # Timer for periodic updates and debouncing
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui_state)
        self.update_timer.start(100)  # Update every 100ms
        
        # Debounce timer for color changes
        self.color_debounce_timer = QTimer()
        self.color_debounce_timer.setSingleShot(True)
        self.color_debounce_timer.timeout.connect(self._send_color_to_led)
        self._pending_color = None
        
        if self.is_demo_mode:
            self.show_demo_mode_warning()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("LED Controller v2.0")
        self.setMinimumSize(400, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header with status
        header_layout = QHBoxLayout()
        self.status_indicator = StatusIndicator()
        self.connection_label = QLabel("Disconnected")
        self.connection_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        header_layout.addWidget(QLabel("Status:"))
        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(self.connection_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Connection controls
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout(conn_group)
        
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.disconnect_btn)
        
        layout.addWidget(conn_group)
        
        # Power controls
        power_group = QGroupBox("Power Control")
        power_layout = QHBoxLayout(power_group)
        
        self.on_btn = QPushButton("Turn ON")
        self.off_btn = QPushButton("Turn OFF")
        self.on_btn.setEnabled(False)
        self.off_btn.setEnabled(False)
        
        power_layout.addWidget(self.on_btn)
        power_layout.addWidget(self.off_btn)
        
        layout.addWidget(power_group)
        
        # Color controls
        color_group = QGroupBox("Color Control")
        color_layout = QVBoxLayout(color_group)
        
        # Color preview
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("Preview:"))
        self.color_preview = ColorPreview()
        preview_layout.addWidget(self.color_preview)
        preview_layout.addStretch()
        color_layout.addLayout(preview_layout)
        
        # RGB sliders
        self.rgb_sliders = {}
        for color_name, color_char in [("Red", "R"), ("Green", "G"), ("Blue", "B")]:
            slider_layout = QHBoxLayout()
            
            label = QLabel(f"{color_name}:")
            label.setMinimumWidth(50)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(255)
            slider.setValue(0)
            
            value_label = QLabel("0")
            value_label.setMinimumWidth(30)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            
            slider_layout.addWidget(label)
            slider_layout.addWidget(slider)
            slider_layout.addWidget(value_label)
            
            color_layout.addLayout(slider_layout)
            
            self.rgb_sliders[color_char.lower()] = {
                'slider': slider,
                'label': value_label
            }
        
        layout.addWidget(color_group)
        
        # Effects
        effects_group = QGroupBox("Effects")
        effects_layout = QGridLayout(effects_group)
        
        self.effect_buttons = {}
        effects = [
            ("Rainbow Cycle", "rainbow_cycle"),
            ("Breathing", "breathing"),
            ("Strobe Light", "strobe")
        ]
        
        for i, (name, effect_id) in enumerate(effects):
            btn = QPushButton(name)
            btn.setEnabled(False)
            self.effect_buttons[effect_id] = btn
            effects_layout.addWidget(btn, i // 2, i % 2)
        
        layout.addWidget(effects_group)
        
        # Progress bar for effects
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Stretch
        layout.addStretch()
    
    def setup_connections(self):
        """Setup signal connections."""
        # LED controller signals
        self.led_controller.connection_state_changed.connect(self.on_connection_state_changed)
        self.led_controller.led_state_changed.connect(self.on_led_state_changed)
        self.led_controller.error_occurred.connect(self.on_error_occurred)
        self.led_controller.log_message.connect(self.on_log_message)
        
        # Button connections
        self.connect_btn.clicked.connect(self.connect_led)
        self.disconnect_btn.clicked.connect(self.disconnect_led)
        self.on_btn.clicked.connect(self.turn_on_led)
        self.off_btn.clicked.connect(self.turn_off_led)
        
        # Slider connections - separate preview from LED communication
        for color, components in self.rgb_sliders.items():
            slider = components['slider']
            slider.valueChanged.connect(self.on_color_preview_changed)  # Immediate visual feedback
            slider.sliderReleased.connect(self.on_color_changed)  # Send to LED when released
            slider.sliderPressed.connect(self.on_slider_pressed)  # Stop debounce when pressed
        
        # Effect button connections
        for effect_id, btn in self.effect_buttons.items():
            btn.clicked.connect(lambda checked, e=effect_id: self.apply_effect(e))
    
    def setup_tray_icon(self):
        """Setup system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 150, 255))
        self.tray_icon.setIcon(QIcon(pixmap))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.close_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def show_demo_mode_warning(self):
        """Show warning about demo mode."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Demo Mode")
        msg.setText("LED module not found. Running in demo mode.")
        msg.setInformativeText("Install the bluelights module to control real LEDs.")
        msg.show()
    
    # Slot methods
    def on_connection_state_changed(self, state: ConnectionState):
        """Handle connection state changes."""
        self.status_indicator.set_state(state)
        
        state_texts = {
            ConnectionState.DISCONNECTED: "Disconnected",
            ConnectionState.CONNECTING: "Connecting...",
            ConnectionState.CONNECTED: "Connected",
            ConnectionState.ERROR: "Error"
        }
        
        self.connection_label.setText(state_texts.get(state, "Unknown"))
        
        # Update button states
        is_connected = state == ConnectionState.CONNECTED
        self.connect_btn.setEnabled(not is_connected)
        self.disconnect_btn.setEnabled(is_connected)
        self.on_btn.setEnabled(is_connected)
        self.off_btn.setEnabled(is_connected)
        
        for btn in self.effect_buttons.values():
            btn.setEnabled(is_connected)
    
    def on_led_state_changed(self, state: LEDState):
        """Handle LED state changes."""
        self.current_state = state
        
        # Update color preview and sliders
        self.color_preview.set_color(state.red, state.green, state.blue)
        
        self.rgb_sliders['r']['slider'].setValue(state.red)
        self.rgb_sliders['g']['slider'].setValue(state.green)
        self.rgb_sliders['b']['slider'].setValue(state.blue)
        
        self.rgb_sliders['r']['label'].setText(str(state.red))
        self.rgb_sliders['g']['label'].setText(str(state.green))
        self.rgb_sliders['b']['label'].setText(str(state.blue))
        
        # Update effect state
        if state.effect:
            self.progress_bar.setVisible(True)
            for btn in self.effect_buttons.values():
                btn.setEnabled(False)
        else:
            self.progress_bar.setVisible(False)
            is_connected = state.connection_state == ConnectionState.CONNECTED
            for btn in self.effect_buttons.values():
                btn.setEnabled(is_connected)
    
    def on_error_occurred(self, error_message: str):
        """Handle errors."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText(error_message)
        msg.show()
    
    def on_log_message(self, message: str, level: str):
        """Handle log messages."""
        self.status_bar.showMessage(message, 3000)  # Show for 3 seconds
    
    def on_slider_pressed(self):
        """Called when user starts dragging a slider."""
        # Stop any pending debounced color changes
        self.color_debounce_timer.stop()
    
    def on_color_preview_changed(self):
        """Update only the visual preview while dragging (no LED communication)."""
        red = self.rgb_sliders['r']['slider'].value()
        green = self.rgb_sliders['g']['slider'].value()
        blue = self.rgb_sliders['b']['slider'].value()
        
        # Update labels immediately for responsive UI
        self.rgb_sliders['r']['label'].setText(str(red))
        self.rgb_sliders['g']['label'].setText(str(green))
        self.rgb_sliders['b']['label'].setText(str(blue))
        
        # Update preview immediately
        self.color_preview.set_color(red, green, blue)
        
        # Store pending color but don't send yet
        self._pending_color = (red, green, blue)
    
    def on_color_changed(self):
        """Handle color slider changes when released."""
        if self._pending_color and self.current_state.connection_state == ConnectionState.CONNECTED:
            # Use debounce timer to avoid rapid fire requests
            self.color_debounce_timer.start(100)  # 100ms delay
    
    def _send_color_to_led(self):
        """Actually send the color to the LED (called by debounce timer)."""
        if self._pending_color and self.current_state.connection_state == ConnectionState.CONNECTED:
            red, green, blue = self._pending_color
            asyncio.create_task(self.led_controller.set_color(red, green, blue))
            self._pending_color = None
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
            self.raise_()
    
    def update_ui_state(self):
        """Periodic UI updates."""
        # You can add periodic updates here if needed
        pass
    
    # Action methods
    def connect_led(self):
        """Connect to LED."""
        asyncio.create_task(self.led_controller.initialize())
    
    def disconnect_led(self):
        """Disconnect from LED."""
        asyncio.create_task(self.led_controller.disconnect())
    
    def turn_on_led(self):
        """Turn on LED."""
        asyncio.create_task(self.led_controller.turn_on())
    
    def turn_off_led(self):
        """Turn off LED."""
        asyncio.create_task(self.led_controller.turn_off())
    
    def apply_effect(self, effect_name: str):
        """Apply an effect."""
        current_color = (
            self.current_state.red,
            self.current_state.green,
            self.current_state.blue
        )
        
        kwargs = {'color': current_color}
        asyncio.create_task(self.led_controller.apply_effect(effect_name, **kwargs))
    
    def closeEvent(self, event):
        """Handle window close event."""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self.close_application()
    
    def close_application(self):
        """Close the application properly."""
        asyncio.create_task(self._shutdown())
    
    async def _shutdown(self):
        """Shutdown sequence."""
        try:
            if self.current_state.connection_state == ConnectionState.CONNECTED:
                # Turn off LED and disconnect
                await self.led_controller.turn_off()
                await self.led_controller.disconnect()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            QApplication.quit()

def cli_main():
    """Entry point for the CLI command."""
    app = QApplication(sys.argv)
    
    # Set up the async event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create and show the main window
    window = ModernLEDControllerGUI()
    window.show()
    
    try:
        with loop:
            loop.run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    cli_main()