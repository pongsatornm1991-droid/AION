"""Windows Credential Manager bridge for locally scoped AION secrets.

The encrypted operating-system vault holds the value; repository files,
dashboard responses, logs and error messages must never contain it.
"""

import ctypes
import os
import re
from ctypes import wintypes


TARGET = "AION/Finance/OpenAIAdminCostRead"
_KEY_PATTERN = re.compile(r"^sk-admin-[A-Za-z0-9_-]{20,}$")


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", ctypes.c_byte * 8),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _available():
    return os.name == "nt"


def save_openai_admin_key(value):
    """Save a validated value in the current user's encrypted vault."""
    key = str(value or "").strip()
    if not _KEY_PATTERN.fullmatch(key):
        raise ValueError("รูปแบบ Admin key ไม่ถูกต้อง")
    if not _available():
        raise OSError("Windows Credential Manager is required on this machine")
    raw = key.encode("utf-16-le")
    blob = (ctypes.c_byte * len(raw)).from_buffer_copy(raw)
    credential = _Credential(
        0, 1, TARGET, "AION read-only OpenAI cost access", (ctypes.c_byte * 8)(),
        len(raw), blob, 2, 0, None, None, "AION Finance",
    )
    if not ctypes.windll.advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise OSError("ไม่สามารถบันทึกกุญแจใน Windows Credential Manager ได้")


def load_openai_admin_key():
    """Return a local vault secret or None, without ever persisting it elsewhere."""
    if not _available():
        return None
    pointer = ctypes.POINTER(_Credential)()
    if not ctypes.windll.advapi32.CredReadW(TARGET, 1, 0, ctypes.byref(pointer)):
        return None
    try:
        raw = ctypes.string_at(pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize)
        return raw.decode("utf-16-le")
    finally:
        ctypes.windll.advapi32.CredFree(pointer)
