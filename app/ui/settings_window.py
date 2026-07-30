from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QToolButton, QVBoxLayout, QWidget,
)

from app.services.autostart import Autostart
from app.services.settings_store import SettingsStore
from engine.dto.key_combination import KeyCombination
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.keyboard_layout_manager import KeyboardLayoutManager
from engine.keyboard_layout_manager_setup import KeyboardLayoutManagerSetup


class HotkeyEdit(QLineEdit):
    """Inline hotkey capture field. Click it and press a combination —
    modifier-only combos (Alt+Shift) are allowed. Produces canonical
    keyboard-library strings like 'alt+shift+g'."""

    capture_started = Signal()
    capture_finished = Signal()

    _MODIFIER_KEYS = (
        Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
        Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("—")
        self.setToolTip("Click and press a key combination")
        self._hotkey = ""

    def hotkey(self) -> str:
        return self._hotkey

    def set_hotkey(self, hotkey: str):
        self._hotkey = hotkey or ""
        self._render()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.setPlaceholderText("press a combination…")
        self.capture_started.emit()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.setPlaceholderText("—")
        self._render()
        self.capture_finished.emit()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.clearFocus()
            event.accept()
            return

        key = event.key()
        modifiers = event.modifiers()
        pressed_modifiers = {
            "ctrl": bool(modifiers & Qt.KeyboardModifier.ControlModifier) or key == Qt.Key.Key_Control,
            "alt": bool(modifiers & Qt.KeyboardModifier.AltModifier) or key in (Qt.Key.Key_Alt, Qt.Key.Key_AltGr),
            "shift": bool(modifiers & Qt.KeyboardModifier.ShiftModifier) or key == Qt.Key.Key_Shift,
            "windows": bool(modifiers & Qt.KeyboardModifier.MetaModifier) or key == Qt.Key.Key_Meta,
        }
        parts = [name for name, pressed in pressed_modifiers.items() if pressed]

        if key not in self._MODIFIER_KEYS and key != Qt.Key.Key_unknown:
            key_text = QKeySequence(key).toString()
            if key_text:
                parts.append(key_text.lower())

        if parts:
            self._hotkey = "+".join(parts)
            self._render()

        event.accept()

    def _render(self):
        self.setText("+".join(part.capitalize() for part in self._hotkey.split("+")) if self._hotkey else "")


class _LayoutRow:
    def __init__(self, layout):
        self.klid = layout.layout_id
        self.checkbox = QCheckBox(layout.layout_name)
        self.checkbox.setToolTip(f"KLID: {layout.layout_id.to_string}")
        self.hotkey_edit = HotkeyEdit()
        self.clear_button = QToolButton()
        self.clear_button.setText("✕")
        self.clear_button.setToolTip("Clear the direct hotkey")
        self.clear_button.clicked.connect(lambda: self.hotkey_edit.set_hotkey(""))
        self.up_button = QToolButton()
        self.up_button.setText("↑")
        self.up_button.setToolTip("Move up — higher means earlier in the carousel cycle")
        self.down_button = QToolButton()
        self.down_button.setText("↓")
        self.down_button.setToolTip("Move down — lower means later in the carousel cycle")


class SettingsWindow(QWidget):
    settings_applied = Signal()

    _FEEDBACK_EMAIL = "astislav+glossa@gmail.com"
    # A mailto: link is a dead end on machines without a mail client (it
    # just opens a blank browser) — copy the address instead.
    _FEEDBACK_LINK = '<a href="copy" style="color: gray; text-decoration: none;">email the author</a>'

    def __init__(
            self,
            registry: KeyboardLayoutRegistryInterface,
            setup: KeyboardLayoutManagerSetup,
            settings_store: SettingsStore,
            manager: KeyboardLayoutManager,
            autostart: Autostart,
    ):
        super().__init__()
        self._registry = registry
        self._setup = setup
        self._settings_store = settings_store
        self._manager = manager
        self._autostart = autostart
        self._rows: list[_LayoutRow] = []

        self.setWindowTitle("Glossa — Settings")
        self._build_ui()

    def showEvent(self, event):
        self._load_state()
        super().showEvent(event)

    # --- UI construction ---

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        carousel_group = QGroupBox("Carousel")
        carousel_layout = QVBoxLayout(carousel_group)
        hotkey_row = QHBoxLayout()
        hotkey_row.addWidget(QLabel("Hotkey:"))
        self._carousel_hotkey_edit = HotkeyEdit()
        hotkey_row.addWidget(self._carousel_hotkey_edit, stretch=1)
        carousel_layout.addLayout(hotkey_row)
        hint = QLabel("Cycles through the layouts checked below.")
        hint.setStyleSheet("color: gray;")
        carousel_layout.addWidget(hint)
        main_layout.addWidget(carousel_group)

        layouts_group = QGroupBox("Layouts")
        layouts_outer = QVBoxLayout(layouts_group)
        self._layouts_grid = QGridLayout()
        self._layouts_grid.setColumnStretch(0, 1)
        header_carousel = QLabel("In carousel")
        header_hotkey = QLabel("Direct hotkey")
        header_order = QLabel("Order")
        header_carousel.setStyleSheet("color: gray;")
        header_hotkey.setStyleSheet("color: gray;")
        header_order.setStyleSheet("color: gray;")
        self._layouts_grid.addWidget(header_carousel, 0, 0)
        self._layouts_grid.addWidget(header_hotkey, 0, 1)
        self._layouts_grid.addWidget(header_order, 0, 3, 1, 2)
        layouts_outer.addLayout(self._layouts_grid)
        direct_hint = QLabel(
            "Same direct hotkey on several layouts cycles them as another "
            "carousel. Use ↑↓ to set cycle order — top comes first."
        )
        direct_hint.setStyleSheet("color: gray;")
        direct_hint.setWordWrap(True)
        layouts_outer.addWidget(direct_hint)
        main_layout.addWidget(layouts_group)

        self._autostart_checkbox = QCheckBox("Start with Windows")
        main_layout.addWidget(self._autostart_checkbox)

        main_layout.addStretch(1)

        buttons_layout = QHBoxLayout()
        self._feedback_label = QLabel(self._FEEDBACK_LINK)
        self._feedback_label.setToolTip(f"Astislav Bozhevolnov · {self._FEEDBACK_EMAIL}\nClick to copy the address")
        self._feedback_label.linkActivated.connect(self._copy_feedback_address)
        small_font = self._feedback_label.font()
        small_font.setPointSizeF(small_font.pointSizeF() * 0.85)
        self._feedback_label.setFont(small_font)
        buttons_layout.addWidget(self._feedback_label)
        buttons_layout.addStretch(1)
        save_button = QPushButton("Save")
        save_button.setDefault(True)
        save_button.clicked.connect(self._on_save)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.close)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        main_layout.addLayout(buttons_layout)

        # While a capture field is focused, the global hook must not react
        # to the combination being tried out.
        self._connect_capture_pause(self._carousel_hotkey_edit)

        self.setMinimumWidth(480)

    def _connect_capture_pause(self, edit: HotkeyEdit):
        edit.capture_started.connect(self._manager.pause_hotkeys)
        edit.capture_finished.connect(self._manager.resume_hotkeys)

    def _rebuild_rows(self, layouts):
        # The set of installed layouts can change while the app runs (the
        # user adds a language in Windows settings) — rebuild on every open.
        for row in self._rows:
            for widget in (
                row.checkbox, row.hotkey_edit, row.clear_button,
                row.up_button, row.down_button,
            ):
                self._layouts_grid.removeWidget(widget)
                widget.deleteLater()
        self._rows.clear()

        for layout in layouts:
            row = _LayoutRow(layout)
            self._rows.append(row)
            self._connect_capture_pause(row.hotkey_edit)
            # lambdas bind the row object, not the changing loop index
            row.up_button.clicked.connect(lambda checked=False, r=row: self._move_row(r, -1))
            row.down_button.clicked.connect(lambda checked=False, r=row: self._move_row(r, +1))

        self._relayout_rows()

    def _relayout_rows(self):
        for row_index, row in enumerate(self._rows, start=1):
            self._layouts_grid.addWidget(row.checkbox, row_index, 0)
            self._layouts_grid.addWidget(row.hotkey_edit, row_index, 1)
            self._layouts_grid.addWidget(row.clear_button, row_index, 2)
            self._layouts_grid.addWidget(row.up_button, row_index, 3)
            self._layouts_grid.addWidget(row.down_button, row_index, 4)
            row.up_button.setEnabled(row_index > 1)
            row.down_button.setEnabled(row_index < len(self._rows))

    def _move_row(self, row: _LayoutRow, delta: int):
        index = self._rows.index(row)
        new_index = index + delta
        if new_index < 0 or new_index >= len(self._rows):
            return
        self._rows[index], self._rows[new_index] = self._rows[new_index], self._rows[index]
        self._relayout_rows()

    def _ordered_layouts_for_display(self):
        """Show saved carousel/binding order first so ↑↓ matches what cycles."""
        by_klid = {layout.layout_id.to_string: layout for layout in self._registry.layouts()}
        ordered = []
        seen: set[str] = set()

        for klid in self._setup.in_loop_keyboard_layout_ids:
            key = klid.to_string
            if key in by_klid and key not in seen:
                ordered.append(by_klid[key])
                seen.add(key)

        for klid in self._setup.klid_to_hotkey_bindings:
            key = klid.to_string
            if key in by_klid and key not in seen:
                ordered.append(by_klid[key])
                seen.add(key)

        for layout in self._registry.layouts():
            key = layout.layout_id.to_string
            if key not in seen:
                ordered.append(layout)

        return ordered

    # --- state <-> widgets ---

    def _load_state(self):
        self._rebuild_rows(self._ordered_layouts_for_display())
        self._carousel_hotkey_edit.set_hotkey(self._setup.next_layout_in_loop_hotkey.to_hotkey_string())

        in_loop = {klid.to_string for klid in self._setup.in_loop_keyboard_layout_ids}
        bindings = {klid.to_string: hotkey.to_hotkey_string()
                    for klid, hotkey in self._setup.klid_to_hotkey_bindings.items()}

        for row in self._rows:
            row.checkbox.setChecked(row.klid.to_string in in_loop)
            row.hotkey_edit.set_hotkey(bindings.get(row.klid.to_string, ""))

        self._autostart_checkbox.setChecked(self._autostart.is_enabled())

    def _on_save(self):
        carousel_hotkey = self._carousel_hotkey_edit.hotkey()
        if not carousel_hotkey:
            QMessageBox.warning(self, "Settings", "Set the carousel hotkey.")
            return

        carousel_klids = [row.klid for row in self._rows if row.checkbox.isChecked()]
        if not carousel_klids:
            QMessageBox.warning(self, "Settings", "Check at least one layout for the carousel.")
            return

        bindings = {row.klid: row.hotkey_edit.hotkey() for row in self._rows if row.hotkey_edit.hotkey()}

        # Direct hotkeys may share a combo (that group becomes another
        # carousel). The primary carousel hotkey must stay unique.
        duplicate = self._find_exact_duplicate(carousel_hotkey, bindings)
        if duplicate:
            QMessageBox.warning(
                self, "Settings",
                f"Hotkey \"{duplicate}\" is already the carousel hotkey.\n"
                f"Pick a different combination for the direct binding\n"
                f"(or give several layouts the same direct hotkey to cycle them)."
            )
            return

        if len(carousel_klids) == 1:
            answer = QMessageBox.question(
                self, "Settings",
                "Only one layout is in the carousel — the carousel hotkey will simply activate it. Save anyway?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self._setup.next_layout_in_loop_hotkey = KeyCombination.from_hotkey_string(carousel_hotkey)
        self._setup.in_loop_keyboard_layout_ids = carousel_klids
        self._setup.klid_to_hotkey_bindings = {
            klid: KeyCombination.from_hotkey_string(hotkey) for klid, hotkey in bindings.items()
        }

        self._settings_store.save()
        self._manager.reload()

        if self._autostart_checkbox.isChecked():
            self._autostart.enable()
        else:
            self._autostart.disable()

        self.settings_applied.emit()
        self.close()

    def _copy_feedback_address(self):
        QGuiApplication.clipboard().setText(self._FEEDBACK_EMAIL)
        self._feedback_label.setText(f'<span style="color: gray;">{self._FEEDBACK_EMAIL} — copied</span>')
        QTimer.singleShot(2500, lambda: self._feedback_label.setText(self._FEEDBACK_LINK))

    @staticmethod
    def _find_exact_duplicate(carousel_hotkey: str, bindings: dict) -> str | None:
        # Exact duplicates among direct hotkeys are allowed — they form an
        # extra carousel. Only a clash with the primary carousel hotkey is
        # rejected.
        carousel_combo = KeyCombination.from_hotkey_string(carousel_hotkey).as_frozenset()
        for hotkey in bindings.values():
            if KeyCombination.from_hotkey_string(hotkey).as_frozenset() == carousel_combo:
                return hotkey
        return None
