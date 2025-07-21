import winreg

from engine.dto.keyboard_layout import KeyboardLayout
from engine.interfaces.keyboard_layout_registry_interface import KeyboardLayoutRegistryInterface
from engine.windows.keyboard_layout_id import WindowsKeyboardLayoutId


class WindowsKeyboardLayoutsRegistry(KeyboardLayoutRegistryInterface):
    def layouts(self) -> list[KeyboardLayout]:
        klid_preload_branch = r"Keyboard Layout\\Preload"
        result = []

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, klid_preload_branch) as key:
            i = 0
            while True:
                try:
                    _, klid, _ = winreg.EnumValue(key, i)
                    klid = self._resolve_substitute(WindowsKeyboardLayoutId(klid))

                    layout = KeyboardLayout(self._layout_name(klid), klid)
                    result.append(layout)
                    i += 1
                except OSError:
                    break
        return result

    def layout_exists(self, keyboard_layout_id: WindowsKeyboardLayoutId) -> bool:
        for registered_layout in self.layouts():
            if registered_layout.layout_id == keyboard_layout_id:
                return True

        return False

    # noinspection PyMethodMayBeStatic
    def _layout_name(self, klid: WindowsKeyboardLayoutId) -> str:
        klid_layouts_branch = r"SYSTEM\\CurrentControlSet\\Control\\Keyboard Layouts"

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, fr"{klid_layouts_branch}\{klid.to_string}") as key:
                name, _ = winreg.QueryValueEx(key, "Layout Text")

                return name
        except FileNotFoundError:
            return "(unknown)"

    @staticmethod
    def _resolve_substitute(klid: WindowsKeyboardLayoutId) -> WindowsKeyboardLayoutId:
        klid_substitutes_branch = r"Keyboard Layout\\Substitutes"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, klid_substitutes_branch) as subs_key:
                substitute_value, _ = winreg.QueryValueEx(subs_key, klid.to_string)

                return WindowsKeyboardLayoutId(substitute_value)
        except FileNotFoundError:
            return klid
