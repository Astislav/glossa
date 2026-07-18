import ctypes

_ERROR_ALREADY_EXISTS = 183

# The mutex handle must outlive the call — Windows releases it when the
# process exits, which is exactly the lifetime we want.
_mutex_handle = None


def acquire_single_instance_lock(name: str = "Glossa") -> bool:
    """Returns False if another instance already holds the lock. Two
    instances at once would fight over the keyboard hook and the system
    hotkey registry keys."""
    global _mutex_handle

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, f"Local\\{name}")
    if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
        if handle:
            kernel32.CloseHandle(handle)
        return False

    _mutex_handle = handle
    return True
