from PySide6.QtCore import QObject, QTimer


class ReadinessController(QObject):
    """Waits (non-blocking, on the Qt event loop) until the OS keyboard
    subsystem is ready, then fires the activation callback exactly once.

    On a cold boot the app can autostart before Windows has populated the
    keyboard layout registry. Instead of blocking, we poll on a timer and
    keep the app passive until layouts appear — the system's own hotkeys keep
    working in the meantime. There is no timeout: an app that can't enumerate
    layouts has nothing useful to do anyway, so it simply keeps waiting.
    """

    _POLL_MS = 500

    def __init__(self, registry, on_ready, parent=None):
        super().__init__(parent)
        self._registry = registry
        self._on_ready = on_ready
        self._waited = False
        self._timer = QTimer(self)
        self._timer.setInterval(self._POLL_MS)
        self._timer.timeout.connect(self._poll)

    def start(self):
        # Most launches: the registry is already ready — activate immediately,
        # no timer, no toast. Only a cold boot falls through to polling.
        if not self._poll():
            self._waited = True
            self._timer.start()

    def _poll(self) -> bool:
        if not self._is_ready():
            return False

        self._timer.stop()
        self._on_ready(self._waited)
        return True

    def _is_ready(self) -> bool:
        try:
            return bool(self._registry.layouts())
        except OSError:
            return False
