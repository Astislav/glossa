from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface


class UnifiedHotkeyEdit(QWidget):
    """Unified widget to capture both standard hotkeys and modifier-only combinations"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create the edit field
        self.edit = QLineEdit()
        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText("Press any key combination (including modifier-only)")
        self.layout.addWidget(self.edit)

        # Set focus policy to make widget focusable
        self.setFocusPolicy(Qt.StrongFocus)

        # Initialize state variables
        self.modifiers = Qt.KeyboardModifier.NoModifier
        self.key = None
        self.modifier_only = False

        # Variables to store the last valid hotkey state
        self.last_modifiers = Qt.KeyboardModifier.NoModifier
        self.last_key = None
        self.last_modifier_only = False
        self.hotkey_set = False

        self.updateText()

    def focusInEvent(self, event):
        # When widget gets focus, prepare for new input but don't clear the display
        # if a valid hotkey has been set
        self.edit.setFocus()

        # Reset current state for new input, but preserve last valid state
        self.modifiers = Qt.KeyboardModifier.NoModifier
        self.key = None

        # Update the display - this will show the last valid hotkey if one is set
        self.updateText()

        super().focusInEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        # Capture the key press
        self.modifiers = event.modifiers()

        # Check if it's a modifier key
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
                          Qt.Key.Key_Meta, Qt.Key.Key_AltGr):
            # It's a modifier key, so we're potentially in modifier-only mode
            self.modifier_only = True
            self.key = None

            # Update last valid state for modifier-only hotkeys
            if self.modifiers != Qt.KeyboardModifier.NoModifier:
                self.last_modifiers = self.modifiers
                self.last_key = None
                self.last_modifier_only = True
                self.hotkey_set = True
        else:
            # It's a regular key, so we're in standard hotkey mode
            self.modifier_only = False
            self.key = event.key()

            # Update last valid state for standard hotkeys
            if self.modifiers != Qt.KeyboardModifier.NoModifier or event.key() != Qt.Key.Key_unknown:
                self.last_modifiers = self.modifiers
                self.last_key = self.key
                self.last_modifier_only = False
                self.hotkey_set = True

        self.updateText()
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent):
        # Update current modifiers on key release
        self.modifiers = event.modifiers()

        # If all keys are released, we should display the last valid hotkey
        # but continue tracking current key state for new input
        if self.modifiers == Qt.KeyboardModifier.NoModifier and event.key() != Qt.Key.Key_unknown:
            # Clear current key state for new input
            self.key = None

            # We don't reset self.modifiers or self.modifier_only here
            # because we want to keep tracking new input

            # The last valid state (self.last_modifiers, self.last_key, self.last_modifier_only)
            # is preserved and will be used for display

        self.updateText()
        event.accept()

    def updateText(self):
        """Update the displayed text based on current key combination or last valid hotkey"""
        # If we're currently pressing keys, show the current state
        if self.modifiers != Qt.KeyboardModifier.NoModifier or self.key:
            text = []

            # Add modifiers
            if self.modifiers & Qt.KeyboardModifier.ControlModifier:
                text.append("Ctrl")
            if self.modifiers & Qt.KeyboardModifier.AltModifier:
                text.append("Alt")
            if self.modifiers & Qt.KeyboardModifier.ShiftModifier:
                text.append("Shift")
            if self.modifiers & Qt.KeyboardModifier.MetaModifier:
                text.append("Meta")

            # Add the key if it's not a modifier-only hotkey
            if not self.modifier_only and self.key:
                key_text = QKeySequence(self.key).toString()
                if key_text:
                    text.append(key_text)

            self.edit.setText("+".join(text) if text else "")

        # If no keys are currently pressed but we have a valid hotkey set,
        # show the last valid hotkey
        elif self.hotkey_set:
            text = []

            # Add last valid modifiers
            if self.last_modifiers & Qt.KeyboardModifier.ControlModifier:
                text.append("Ctrl")
            if self.last_modifiers & Qt.KeyboardModifier.AltModifier:
                text.append("Alt")
            if self.last_modifiers & Qt.KeyboardModifier.ShiftModifier:
                text.append("Shift")
            if self.last_modifiers & Qt.KeyboardModifier.MetaModifier:
                text.append("Meta")

            # Add the last valid key if it's not a modifier-only hotkey
            if not self.last_modifier_only and self.last_key:
                key_text = QKeySequence(self.last_key).toString()
                if key_text:
                    text.append(key_text)

            self.edit.setText("+".join(text) if text else "")

        # If no keys are pressed and no valid hotkey is set, clear the text
        else:
            self.edit.setText("")

    def getHotkey(self):
        """Return the current hotkey as text"""
        # The edit field will always show the correct hotkey text
        # thanks to our updateText method
        return self.edit.text()

    def setHotkey(self, text):
        """Set hotkey from text representation"""
        if not text:
            # Clear both current and last valid states
            self.modifiers = Qt.KeyboardModifier.NoModifier
            self.key = None
            self.modifier_only = False
            self.last_modifiers = Qt.KeyboardModifier.NoModifier
            self.last_key = None
            self.last_modifier_only = False
            self.hotkey_set = False
            self.updateText()
            return

        parts = text.split("+")

        # Check if it's a modifier-only hotkey
        is_modifier_only = all(part.lower() in ["ctrl", "alt", "shift", "meta"] for part in parts)

        # Reset both current and last valid states
        self.modifiers = Qt.KeyboardModifier.NoModifier
        self.key = None
        self.last_modifiers = Qt.KeyboardModifier.NoModifier
        self.last_key = None

        # Process each part
        for part in parts:
            part_lower = part.lower()
            if part_lower == "ctrl":
                self.modifiers |= Qt.KeyboardModifier.ControlModifier
                self.last_modifiers |= Qt.KeyboardModifier.ControlModifier
            elif part_lower == "alt":
                self.modifiers |= Qt.KeyboardModifier.AltModifier
                self.last_modifiers |= Qt.KeyboardModifier.AltModifier
            elif part_lower == "shift":
                self.modifiers |= Qt.KeyboardModifier.ShiftModifier
                self.last_modifiers |= Qt.KeyboardModifier.ShiftModifier
            elif part_lower == "meta":
                self.modifiers |= Qt.KeyboardModifier.MetaModifier
                self.last_modifiers |= Qt.KeyboardModifier.MetaModifier
            elif not is_modifier_only:
                # It's a regular key
                key_code = QKeySequence(part)[0]
                self.key = key_code
                self.last_key = key_code

        # Set modifier_only flag for both current and last valid states
        self.modifier_only = is_modifier_only
        self.last_modifier_only = is_modifier_only

        # Mark that a valid hotkey has been set
        self.hotkey_set = True

        self.updateText()


class HotkeyDialog(QDialog):
    def __init__(self, parent=None, current_hotkey=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Hotkey")

        # Create layout
        layout = QVBoxLayout(self)

        # Add instruction label
        layout.addWidget(QLabel("Press any key combination (including modifier-only like Ctrl+Alt):"))

        # Add unified hotkey edit control
        self.hotkey_edit = UnifiedHotkeyEdit(self)
        if current_hotkey:
            self.hotkey_edit.setHotkey(current_hotkey)
        layout.addWidget(self.hotkey_edit)

        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setMinimumWidth(400)
        self.setMinimumHeight(200)

    def get_hotkey(self):
        return self.hotkey_edit.getHotkey()


class SettingsWindow(QWidget):
    def __init__(self, registry: KeyboardLayoutRegistryInterface):
        super().__init__()
        self.setWindowTitle("Настройки")
        self.registry = registry
        self.layout_checkboxes = []
        self.hotkey_buttons = {}  # Dictionary to store hotkey buttons
        self.layout_hotkeys = {}  # Dictionary to store hotkeys for each layout ID

        main_layout = QVBoxLayout(self)

        # Create a label
        main_layout.addWidget(QLabel("Выберите раскладки клавиатуры:"))

        # Create a scroll area for checkboxes and hotkey buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Add checkboxes and hotkey buttons for each layout
        for layout in self.registry.layouts():
            # Create horizontal layout for each row
            row_layout = QHBoxLayout()

            # Add checkbox
            checkbox = QCheckBox(layout.layout_name)
            # Store the layout ID as a property of the checkbox
            layout_id = layout.layout_id.to_string
            checkbox.setProperty("layout_id", layout_id)
            self.layout_checkboxes.append(checkbox)
            row_layout.addWidget(checkbox)

            # Add hotkey button
            hotkey_btn = QPushButton("Configure Hotkey")
            hotkey_btn.clicked.connect(lambda checked, lid=layout_id: self.configure_hotkey(lid))
            self.hotkey_buttons[layout_id] = hotkey_btn
            row_layout.addWidget(hotkey_btn)

            # Add row to scroll layout
            scroll_layout.addLayout(row_layout)

        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Create buttons layout
        buttons_layout = QHBoxLayout()

        # Add Show button
        show_btn = QPushButton("Show")
        show_btn.clicked.connect(self.show_selected_layouts)
        buttons_layout.addWidget(show_btn)

        # Add Close button
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(close_btn)

        main_layout.addLayout(buttons_layout)
        self.setMinimumSize(400, 300)

    def configure_hotkey(self, layout_id):
        """Open dialog to configure hotkey for the specified layout"""
        current_hotkey = self.layout_hotkeys.get(layout_id, "")
        dialog = HotkeyDialog(self, current_hotkey)

        if dialog.exec():
            # Get the configured hotkey
            hotkey = dialog.get_hotkey()

            # Store the hotkey
            if hotkey:
                self.layout_hotkeys[layout_id] = hotkey
                # Update button text to show the hotkey
                self.hotkey_buttons[layout_id].setText(f"Hotkey: {hotkey}")
            else:
                # If hotkey is empty, remove it from the dictionary
                if layout_id in self.layout_hotkeys:
                    del self.layout_hotkeys[layout_id]
                self.hotkey_buttons[layout_id].setText("Configure Hotkey")

    def show_selected_layouts(self):
        """Display a popup with IDs and hotkeys of selected layouts"""
        selected_layouts = []

        # Collect IDs and hotkeys of selected layouts
        for checkbox in self.layout_checkboxes:
            if checkbox.isChecked():
                layout_id = checkbox.property("layout_id")
                hotkey = self.layout_hotkeys.get(layout_id, "Not configured")
                selected_layouts.append(f"{layout_id} - Hotkey: {hotkey}")

        # Create message text
        if selected_layouts:
            message = "Selected layouts:\n" + "\n".join(selected_layouts)
        else:
            message = "No layouts selected"

        # Show popup
        QMessageBox.information(self, "Selected Layouts", message)
