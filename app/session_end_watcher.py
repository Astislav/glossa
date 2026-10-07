import ctypes
from ctypes import wintypes

from PySide6.QtWidgets import QWidget

WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016


class SessionEndWatcher(QWidget):
    """A hidden top-level window whose only job is to hear Windows announce
    shutdown, restart or logoff.

    A tray-only Qt app has no real top-level Qt window: the tray icon and Qt's
    internal observers use their own window procedures, so Qt never sees
    WM_QUERYENDSESSION and QGuiApplication.commitDataRequest never fires. The
    process is then killed without any teardown, and the system layout
    hotkeys stay disabled in the registry until the app starts again after the
    next logon. This widget is never shown, but forcing its native window
    makes Windows deliver the session-end messages to it.

    on_session_end runs when the session is about to end (and again when it
    actually ends — it must be idempotent). on_session_resumed runs if the
    shutdown was cancelled, so the app can take back over.
    """

    def __init__(self, on_session_end, on_session_resumed):
        super().__init__()
        self._on_session_end = on_session_end
        self._on_session_resumed = on_session_resumed
        self.winId()  # create the native window now, without ever showing it

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            self.handle_message(msg.message, msg.wParam)
        return False, 0  # never consume: Qt keeps its default handling

    def handle_message(self, message: int, w_param: int):
        if message == WM_QUERYENDSESSION:
            # Restore as early as possible: if anything goes wrong later in
            # the shutdown sequence, the system is already back to normal.
            self._on_session_end()
        elif message == WM_ENDSESSION:
            if w_param:
                self._on_session_end()       # session really ends
            else:
                self._on_session_resumed()   # shutdown was cancelled


def send_session_message(hwnd: int, message: int, w_param: int = 0, l_param: int = 0) -> int:
    """Deliver a session message synchronously, the way Windows does at
    shutdown. Used by tests and diagnostics."""
    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    user32.SendMessageW.restype = wintypes.LPARAM
    return user32.SendMessageW(hwnd, message, w_param, l_param)
