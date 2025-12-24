from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QTextEdit, QPushButton, QLabel, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QCursor, QPalette, QColor, QFont
import threading
from typing import Optional, Callable
from utils.logger import setup_logger

logger = setup_logger("UnifiedControlPanel_Qt")


class UnifiedControlPanel(QWidget):
    """
    Qt-based unified control panel with proper Wayland support.
    No overrideredirect hacks - uses Qt's native window management.
    """
    
    # Signals for thread-safe operations
    show_signal = pyqtSignal()
    hide_signal = pyqtSignal()
    add_response_signal = pyqtSignal(str)
    
    def __init__(self, 
                 on_text_submit: Callable[[str], None],
                 ears_worker=None,
                 microphone_mode: str = "manual"):
        super().__init__()
        
        self.on_text_submit = on_text_submit
        self.ears_worker = ears_worker
        self.microphone_mode = microphone_mode
        
        self.is_listening = False
        self.is_expanded = False
        
        # Debounce for toggle hotkey
        self.last_toggle_time = 0
        self.toggle_cooldown = 1.0  # seconds
        
        # Dimensions
        self.WIDTH = 600
        self.COMPACT_HEIGHT = 120
        self.EXPANDED_HEIGHT = 450
        
        # Setup UI
        self._setup_window()
        self._setup_ui()
        
        # Connect signals
        self.show_signal.connect(self._do_show)
        self.hide_signal.connect(self._do_hide)
        self.add_response_signal.connect(self._add_response)
        
        logger.info("Qt Unified Control Panel initialized")
    
    def _setup_window(self):
        """Configure window flags for Wayland-friendly popup."""
        # Frameless but NOT overrideredirect equivalent
        # This allows keyboard input while still looking like a popup
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Prevents taskbar entry
        )
        
        # Start hidden
        self.hide()
        
        # Set initial size
        self.resize(self.WIDTH, self.COMPACT_HEIGHT)
        
        # Dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 12pt;
                color: white;
            }
            QLineEdit:focus {
                background-color: #3d3d3d;
            }
            QTextEdit {
                background-color: #1a1a1a;
                border: none;
                color: #dddddd;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                color: white;
            }
            QPushButton[listening="true"] {
                background-color: #f44336;
            }
            QPushButton[processing="true"] {
                background-color: #FF9800;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QLabel {
                color: #888888;
            }
        """)
    
    def _setup_ui(self):
        """Build the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Title bar
        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: #2d2d2d; border-radius: 5px;")
        title_frame.setFixedHeight(30)
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 5, 10, 5)
        
        title_label = QLabel("Living Assistant")
        title_label.setStyleSheet("color: white; font-weight: bold;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        close_btn = QLabel("✕")
        close_btn.setStyleSheet("color: #888; font-size: 14pt;")
        close_btn.mousePressEvent = lambda e: self.request_hide()
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_frame)
        
        # Text input
        self.text_entry = QLineEdit()
        self.text_entry.setPlaceholderText("Type your command here...")
        self.text_entry.returnPressed.connect(self._handle_text_submit)
        layout.addWidget(self.text_entry)
        
        # Microphone controls (if manual mode)
        if self.microphone_mode == "manual":
            mic_layout = QHBoxLayout()
            
            self.mic_button = QPushButton("🎤 Start Speaking")
            self.mic_button.clicked.connect(self._toggle_listening)
            mic_layout.addWidget(self.mic_button)
            
            self.mic_status = QLabel("Ready")
            self.mic_status.setStyleSheet("color: #888;")
            mic_layout.addWidget(self.mic_status)
            
            mic_layout.addStretch()
            layout.addLayout(mic_layout)
        
        # History area (initially hidden)
        self.history_area = QTextEdit()
        self.history_area.setReadOnly(True)
        self.history_area.setVisible(False)
        layout.addWidget(self.history_area)
        
        self.setLayout(layout)
    
    def request_toggle(self):
        """Request toggle from any thread (thread-safe)."""
        import time
        
        # Debounce: Ignore rapid toggles
        current_time = time.time()
        if current_time - self.last_toggle_time < self.toggle_cooldown:
            logger.debug("Toggle ignored (cooldown active)")
            return
        
        self.last_toggle_time = current_time
        
        if self.isVisible():
            self.hide_signal.emit()
        else:
            self.show_signal.emit()
    
    def request_hide(self):
        """Request hide from any thread (thread-safe)."""
        self.hide_signal.emit()
    
    def _do_show(self):
        """Show window at cursor position (main thread only)."""
        # Get cursor position
        cursor_pos = QCursor.pos()
        
        # Get screen containing the cursor (handles multi-monitor correctly)
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = self.screen()
        screen_geo = screen.geometry()
        
        # Adjust to not go off screen
        x = min(cursor_pos.x() + 10, screen_geo.right() - self.WIDTH - 20)
        y = min(cursor_pos.y() + 10, screen_geo.bottom() - self.COMPACT_HEIGHT - 20)
        x = max(screen_geo.left() + 10, x)
        y = max(screen_geo.top() + 10, y)
        
        # Set compact mode
        self._set_compact_mode()
        
        # Wayland workaround: Show first, then move after surface exists
        # This improves success rate on Wayland compositors
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(0, lambda: self.move(x, y))
        
        # Focus text entry - THIS WORKS on Wayland!
        self.text_entry.setFocus()
        
        logger.info("Panel shown at cursor")
    
    def _do_hide(self):
        """Hide window (main thread only)."""
        self.hide()
        self._set_compact_mode()
        logger.info("Panel hidden")
    
    def _set_compact_mode(self):
        """Set window to compact mode."""
        self.resize(self.WIDTH, self.COMPACT_HEIGHT)
        self.history_area.setVisible(False)
        self.is_expanded = False
    
    def _set_expanded_mode(self):
        """Expand window to show history."""
        self.resize(self.WIDTH, self.EXPANDED_HEIGHT)
        self.history_area.setVisible(True)
        self.is_expanded = True
    
    def _handle_text_submit(self):
        """Handle text submission."""
        query = self.text_entry.text().strip()
        if not query:
            return
        
        # Expand if needed
        if not self.is_expanded:
            self._set_expanded_mode()
        
        # Add to history
        self.history_area.append(f"<b>You:</b> {query}")
        self.text_entry.clear()
        
        # Process in background
        self.history_area.append("<i>Processing...</i>")
        threading.Thread(target=self.on_text_submit, args=(query,), daemon=True).start()
    
    def _toggle_listening(self):
        """Toggle microphone listening."""
        if not self.is_listening:
            # Start listening
            self.is_listening = True
            self.mic_button.setText("🔴 Stop Speaking")
            self.mic_button.setProperty("listening", True)
            self.mic_button.style().polish(self.mic_button)
            self.mic_status.setText("Listening...")
            self.mic_status.setStyleSheet("color: #f44336;")
            
            if self.ears_worker:
                threading.Thread(
                    target=self.ears_worker.start_listening,
                    daemon=True
                ).start()
            
            logger.info("Started listening")
        else:
            # Stop listening
            self.is_listening = False
            self.mic_button.setText("⏳ Processing...")
            self.mic_button.setProperty("listening", False)
            self.mic_button.setProperty("processing", True)
            self.mic_button.style().polish(self.mic_button)
            self.mic_button.setEnabled(False)
            self.mic_status.setText("Processing...")
            self.mic_status.setStyleSheet("color: #FF9800;")
            
            if self.ears_worker:
                threading.Thread(
                    target=self._stop_and_reset,
                    daemon=True
                ).start()
            
            logger.info("Stopped listening")
    
    def _stop_and_reset(self):
        """Stop listening and reset button."""
        if self.ears_worker:
            self.ears_worker.stop_listening()
        
        # Reset button (thread-safe via signal)
        QTimer.singleShot(0, self._reset_mic_button)
    
    def _reset_mic_button(self):
        """Reset mic button to initial state (main thread only)."""
        if hasattr(self, 'mic_button'):
            self.mic_button.setText("🎤 Start Speaking")
            self.mic_button.setProperty("listening", False)
            self.mic_button.setProperty("processing", False)
            self.mic_button.style().polish(self.mic_button)
            self.mic_button.setEnabled(True)
            self.mic_status.setText("Ready")
            self.mic_status.setStyleSheet("color: #888;")
    
    def on_transcription_start(self):
        """Called when transcription starts."""
        if hasattr(self, 'mic_status'):
            QTimer.singleShot(0, lambda: self.mic_status.setText("Transcribing..."))
    
    def on_transcription_complete(self):
        """Called when transcription completes."""
        logger.debug("Transcription completed")
    
    def add_response(self, text: str):
        """Add assistant response (thread-safe)."""
        logger.info(f"add_response called with: {text[:50]}...")
        self.add_response_signal.emit(text)
    
    def _add_response(self, text: str):
        """Add response to history (main thread only)."""
        logger.info(f"_add_response received: {text[:50]}...")
        
        # Remove the last "Processing..." line if present
        cursor = self.history_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        if "Processing..." in cursor.selectedText():
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # Remove the newline
        
        # Add response
        self.history_area.append(f"<b>Assistant:</b> {text}")
        
        # Auto-scroll to bottom
        scrollbar = self.history_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        logger.info("Response added to GUI")
    
    def start(self):
        """Start method for compatibility with tkinter API."""
        # Window is already created, just needs to be shown later
        logger.info("Qt Control Panel ready")
