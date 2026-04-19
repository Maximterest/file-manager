"""
file-manager CLI
~~~~~~~~~~~~~~~~
Command-line interface for photo organisation and folder coloring.

Commands
--------
  photo_organize (porga)   Move photos into YYMMDD date folders
  photo_rename   (prename) Rename photos to <Camera>_<Date>_<Padding>
  photo_clean    (pclean)  Delete orphaned RAWs, then rename photos
  color                    Set a folder icon color
  gui                      Launch the graphical interface

Run any command with --help for full options, e.g.:
  fm photo_organize --help
"""

import argparse

from . import tools, utils

COLORS = list(utils.ICON_MAP.keys())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fm",
        description=(
            "file-manager — photo organisation and files utilities.\n\n"
            "Use 'fm <command> --help' for help on a specific command."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  fm photo_organize "../PHOTOS"\n'
            '  fm porga "../PHOTOS "\n'
            '  fm photo_rename "../PHOTOS/260418"\n'
            '  fm photo_clean "../PHOTOS/260418"\n'
            '  fm color "../PHOTOS/260418" green\n'
            '  fm color "../PHOTOS" teal --subfolders\n'
            "  fm gui\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    # --- PHOTO ORGANIZE ---
    org = subparsers.add_parser(
        "photo_organize",
        aliases=["porga"],
        help="Move photos into YYMMDD sub-folders using EXIF date",
        description=(
            "Scan a folder for photos (and RAW files) and move them into\n"
            "sub-folders named by their EXIF shoot date (YYMMDD).\n\n"
            "RAW files are placed in a nested RAW/ sub-folder (configurable\n"
            "in settings.json). Files without EXIF data are skipped."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='example:\n  fm photo_organize "../PHOTOS"',
    )
    org.add_argument("path", help="Folder containing the photos to organise")

    # --- PHOTO RENAME ---
    ren = subparsers.add_parser(
        "photo_rename",
        aliases=["prename"],
        help="Rename photos to <Camera>_<YYMMDD>_<padding>.<ext>",
        description=(
            "Rename every photo (and its matching RAW) inside a folder to\n"
            "<CameraModel>_<YYMMDD>_<NNN>.<ext>.\n\n"
            "Files without EXIF data receive 'Unknown' as the camera model."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='example:\n  fm photo_rename "../PHOTOS/260418"',
    )
    ren.add_argument("path", help="Folder containing the photos to rename")

    # --- PHOTO CLEAN ---
    cln = subparsers.add_parser(
        "photo_clean",
        aliases=["pclean"],
        help="Delete orphaned RAW files, then rename all photos",
        description=(
            "Two-step cleanup for a date folder:\n"
            "  1. Delete any RAW file that has no matching JPEG/PNG/HEIC.\n"
            "  2. Rename all remaining photos (same as photo_rename).\n\n"
            "The folder icon is set to mint (green) when finished (Windows only)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='example:\n  fm photo_clean "../PHOTOS/260418"',
    )
    cln.add_argument("path", help="Folder to clean")

    # --- COLOR ---
    col = subparsers.add_parser(
        "color",
        help="Set a folder icon color  [Windows only]",
        description=(
            "Change the icon color of a folder in Windows Explorer.\n"
            "This feature is Windows-only; on other platforms it is a no-op.\n\n"
            f"Available colors: {', '.join(COLORS)}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  fm color "../PHOTOS/260418" green\n'
            '  fm color ."../PHOTOS/260418" teal --subfolderas'
        ),
    )
    col.add_argument("path", help="Target folder")
    col.add_argument(
        "color",
        nargs="?",
        default="red",
        choices=COLORS,
        metavar="COLOR",
        help=f"Color name (default: red). One of: {', '.join(COLORS)}",
    )
    col.add_argument(
        "-sub",
        "--subfolders",
        action="store_true",
        help="Apply the color to every direct sub-folder instead of the folder itself",
    )

    # --- GUI ---
    subparsers.add_parser(
        "gui",
        help="Launch the graphical user interface",
        description="Open the file-manager GUI window.",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "gui":
        from .gui import launch

        launch()
        return

    if args.command in ("photo_organize", "porga"):
        tools.photo_organize(args.path)

    elif args.command in ("photo_rename", "prename"):
        tools.photo_rename(args.path)

    elif args.command in ("photo_clean", "pclean"):
        tools.photo_clean(args.path)

    elif args.command == "color":
        if args.subfolders:
            tools.set_subfolders_color(args.path, color=args.color)
        else:
            utils.set_folder_color(args.path, color=args.color)
