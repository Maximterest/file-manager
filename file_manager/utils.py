import ctypes
import io
import sys
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS

ICON_MAP = {
    "blue": "blue.ico",
    "space": "space.ico",
    "navy": "navy.ico",
    "race_blue": "race blue.ico",
    "teal": "teal.ico",
    "light_blue": "light blue.ico",
    "green": "green.ico",
    "olive": "olive.ico",
    "lime": "lime.ico",
    "mint": "mint.ico",
    "red": "red.ico",
    "orange": "orange.ico",
    "pink": "pink.ico",
    "purple": "purple.ico",
    "maroon": "maroon.ico",
    "coffee": "coffee.ico",
    "yellow": "yellow.ico",
    "white": "white.ico",
    "gray": "gray.ico",
    "dark_gray": "dark gray.ico",
}
ICON_DIR = Path(__file__).parent / "icons"

# Windows API constants
FCS_FORCEWRITE = 0x00000002
FCSM_ICONFILE = 0x00000010


def make_pathlib(path: str):
    """Convert a string path to a Path object, raising if it does not exist."""
    base_path = Path(path)

    if not base_path.exists():
        sys.tracebacklimit = 0
        raise ValueError("Path does not exist")

    return base_path


def get_exif_data(filepath: str):
    """Return a tag->value dict of EXIF data for an image, or None on failure."""
    try:
        with open(filepath, "rb") as f:
            data = f.read()

        start = data.find(b"\xff\xd8")
        image = Image.open(io.BytesIO(data[start:]))
        exif = image._getexif()
        if exif is None:
            return None

        return {TAGS.get(tag, tag): value for tag, value in exif.items()}

    except Exception:
        return None


def get_exif_date(filepath: str):
    """Return the EXIF shoot date formatted as YYMMDD, or None."""
    exif_data = get_exif_data(filepath)
    if not exif_data:
        return None

    date_str = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")
    if not date_str:
        return None

    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").strftime("%y%m%d")


def get_exif_camera_model(filepath: str):
    """Return the camera model string from EXIF, or None."""
    exif_data = get_exif_data(filepath)
    if not exif_data:
        return None

    return exif_data.get("Model")


def set_folder_color(folder_path: str, color: str):
    """
    Set a Windows Explorer folder icon color.
    On non-Windows platforms this is a no-op so other commands stay cross-platform.
    """
    if sys.platform != "win32":
        return

    icon_path = ICON_DIR / ICON_MAP[color]

    path = make_pathlib(folder_path)
    if not Path(path).is_dir():
        sys.tracebacklimit = 0
        raise ValueError(f"Expected a folder path: {folder_path}")

    # Define necessary structures
    class SHFOLDERCUSTOMSETTINGS(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("dwMask", wintypes.DWORD),
            ("pvid", ctypes.c_void_p),
            ("pszWebViewTemplate", wintypes.LPWSTR),
            ("cchWebViewTemplate", wintypes.DWORD),
            ("pszWebViewTemplateVersion", wintypes.LPWSTR),
            ("pszInfoTip", wintypes.LPWSTR),
            ("cchInfoTip", wintypes.DWORD),
            ("pclsid", ctypes.c_void_p),
            ("dwFlags", wintypes.DWORD),
            ("pszIconFile", wintypes.LPWSTR),
            ("cchIconFile", wintypes.DWORD),
            ("iIconIndex", ctypes.c_int),
            ("pszLogo", wintypes.LPWSTR),
            ("cchLogo", wintypes.DWORD),
        ]

    fcs = SHFOLDERCUSTOMSETTINGS()
    fcs.dwSize = ctypes.sizeof(SHFOLDERCUSTOMSETTINGS)
    fcs.dwMask = FCSM_ICONFILE
    fcs.pszIconFile = str(icon_path)
    fcs.iIconIndex = 0

    result = ctypes.windll.shell32.SHGetSetFolderCustomSettings(
        ctypes.byref(fcs), folder_path, FCS_FORCEWRITE
    )

    if result != 0:
        raise ctypes.WinError(result)


def list_subfiles(path: str, target_extensions: list, skip_folders=True):
    """Return a list of files in path matching target_extensions."""
    base_path = make_pathlib(path)
    files = []

    for file in base_path.iterdir():
        if skip_folders and file.is_dir():
            continue

        if target_extensions and file.suffix.lower() not in target_extensions:
            continue

        files.append(file)

    return files
