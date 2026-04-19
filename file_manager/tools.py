import json
import shutil
from pathlib import Path

from . import utils

with open(Path(__file__).parent / "settings.json", "r") as f:
    SETTINGS = json.load(f)


def photo_organize(path: str):
    """
    Move photos into date-named sub-folders (YYMMDD) based on EXIF data.
    RAW files go into a dedicated sub-folder inside each date folder.
    """
    base_path = utils.make_pathlib(path)

    folders_created = []

    target_extensions = SETTINGS["photo_extensions"] + SETTINGS["raw_extensions"]
    files = utils.list_subfiles(path, target_extensions)
    for file in files:
        # Create folder based on EXIF date
        date = utils.get_exif_date(file)
        if not date:
            print(f"Skipping (no EXIF): {file.name}")
            continue

        target_dir = base_path / date
        target_dir.mkdir(parents=True, exist_ok=True)
        utils.set_folder_color(str(target_dir), "red")

        # RAW files process
        if file.suffix.lower() in SETTINGS["raw_extensions"] and SETTINGS["raw_folder"]:
            target_dir = target_dir / SETTINGS["raw_folder"]
            target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / file.name
        # Avoid duplicates
        if target_file.exists():
            print(f"  Skipping duplicate: {file.name}")
            continue

        shutil.move(str(file), str(target_file))
        print(f"  Moving: {file.name} -> {target_dir.name}/")

        if date not in folders_created:
            folders_created.append(date)

    print("\nFolders Created:")
    if folders_created:
        print("\n".join(f"- {folder}" for folder in folders_created))
    else:
        print("  (None)")


def photo_rename(path: str):
    """
    Rename photos to <CameraModel>_<YYMMDD>_<index>.<ext>.
    Matching RAW files are renamed in sync.
    """
    base_path = utils.make_pathlib(path)
    raw_dir = base_path / SETTINGS["raw_folder"] if SETTINGS["raw_folder"] else base_path

    target_extensions = SETTINGS["photo_extensions"] + SETTINGS["raw_extensions"]
    files = utils.list_subfiles(path, target_extensions)
    if not files:
        files = utils.list_subfiles(raw_dir, target_extensions)

    for index, file in enumerate(files):
        base_name = file.stem
        date = utils.get_exif_date(str(file))
        camera_model = utils.get_exif_camera_model(str(file))
        padding = str(index + 1).zfill(3)

        # Look for matching RAW
        raw = None
        for ext in SETTINGS["raw_extensions"]:
            candidate = raw_dir / f"{base_name}{ext.upper()}"
            if candidate.exists():
                raw = candidate
                break

        for photo in [file, raw]:
            if not photo or not photo.exists():
                continue

            new_name = f"{camera_model}_{date}_{padding}{photo.suffix}"
            if photo.name == new_name:
                continue

            photo.rename(photo.with_name(new_name))
            print(f"  {photo.name} -> {new_name}")

    print("Renaming done.")


def photo_clean(path: str):
    """
    Delete orphaned RAW files (no matching JPEG) then rename all photos.
    Finally marks the folder green (Windows only).
    """
    base_path = utils.make_pathlib(path)
    raw_dir = base_path / SETTINGS["raw_folder"] if SETTINGS["raw_folder"] else base_path
    deleted_count = 0

    photos = utils.list_subfiles(base_path, SETTINGS["photo_extensions"])
    raws = utils.list_subfiles(raw_dir, SETTINGS["raw_extensions"])
    for raw in raws:
        if not photos:
            break

        base_name = raw.stem
        found = any(
            (base_path / f"{base_name}{ext}").exists()
            for ext in SETTINGS["photo_extensions"]
        )
        if not found:
            print(f"  Deleting orphaned RAW: {raw.name}")
            raw.unlink()
            deleted_count += 1

    print("Deleting RAW done.")
    photo_rename(path)
    utils.set_folder_color(str(base_path), "mint")
    print(f"\nCleaning done. RAW files deleted: {deleted_count}")


def set_subfolders_color(path: str, color: str):
    """Apply a colour to every direct sub-folder of path (Windows only)."""
    base_path = utils.make_pathlib(path)
    for item in base_path.iterdir():
        if item.is_dir():
            utils.set_folder_color(str(item), color)
            print(f"  Colored: {item.name}")
