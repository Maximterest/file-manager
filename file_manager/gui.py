"""
file-manager GUI
Drag-and-drop via tkinterdnd2 (install: pip install tkinterdnd2).
"""

import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

from . import tools, utils
from .__init__ import __version__

_SETTINGS_PATH = Path(__file__).parent / "settings.json"
with open(_SETTINGS_PATH) as _f:
    SETTINGS = json.load(_f)

ICONS_DIR = Path(__file__).parent / "icons"
COLOR_KEYS = list(utils.ICON_MAP.keys())

SB_BG = "#1A1A1A"
SB_ACTIVE = "#2A2A2A"
SB_BORDER = "#2D2D2D"

BG = "#212121"
BG_CARD = "#272727"
BG_HOVER = "#303030"
ACCENT = "#3D8C7A"
ACCENT_DIM = "#2E6B5E"
ACCENT_GLOW = "#4AA090"

FG = "#D4D4D4"
FG_DIM = "#7A7A7A"
FG_MUTED = "#484848"

BORDER = "#303030"
LOG_BG = "#181818"
LOG_FG = "#5DBD8A"

FONT = ("Segoe UI", 10)
FONT_SM = ("Segoe UI", 9)
FONT_XS = ("Segoe UI", 8)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_HEAD = ("Segoe UI", 13, "bold")
FONT_MONO = ("Consolas", 9)
FONT_LABEL = ("Segoe UI", 8)

PAD = 12
R = 6


def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle on a Canvas."""
    canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, **kw)
    canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, **kw)
    canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, **kw)
    canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, **kw)
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, **kw)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, **kw)


class RoundedButton(tk.Canvas):
    """Flat rounded button drawn on a Canvas."""

    def __init__(
        self,
        parent,
        text,
        command,
        bg=ACCENT,
        fg="#FFFFFF",
        hover_bg=None,
        font=FONT,
        padx=14,
        pady=7,
        radius=R,
        **kw,
    ):
        super().__init__(parent, highlightthickness=0, bd=0, bg=parent.cget("bg"), **kw)
        self._text = text
        self._command = command
        self._bg = bg
        self._fg = fg
        self._hover = hover_bg or self._darken(bg)
        self._font = font
        self._padx = padx
        self._pady = pady
        self._radius = radius
        self._current_bg = bg

        # Size after rendering one frame
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>", lambda _: command())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        # Measure text to set canvas size
        tmp = tk.Label(font=font)
        w = tmp.tk.call("font", "measure", font, text) + padx * 2
        h = tmp.tk.call("font", "metrics", font, "-linespace") + pady * 2
        self.configure(width=w, height=h)

    def _darken(self, hex_color):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return "#{:02x}{:02x}{:02x}".format(
            max(0, r - 20), max(0, g - 20), max(0, b - 20)
        )

    def _draw(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        fill = self._current_bg
        _rounded_rect(self, 1, 1, w - 1, h - 1, self._radius, fill=fill, outline=fill)
        self.create_text(
            w // 2, h // 2, text=self._text, fill=self._fg, font=self._font
        )

    def _on_enter(self, _):
        self._current_bg = self._hover
        self._draw()

    def _on_leave(self, _):
        self._current_bg = self._bg
        self._draw()


class RoundedEntry(tk.Frame):
    """
    Rounded input field with optional Browse button and drag-and-drop.
    DnD works when tkinterdnd2 is installed AND the root window is TkinterDnD.Tk.
    """

    def __init__(self, parent, placeholder="Drop a folder here or browse…", **kw):
        super().__init__(parent, bg=parent.cget("bg"), **kw)
        self.placeholder = placeholder
        self._dragging = False

        # Canvas border
        self._cv = tk.Canvas(
            self, highlightthickness=0, bd=0, bg=parent.cget("bg"), height=36
        )
        self._cv.pack(fill="x")

        # Entry widget overlaid
        self._var = tk.StringVar()
        self._entry = tk.Entry(
            self._cv,
            textvariable=self._var,
            bg=BG_CARD,
            fg=FG_DIM,
            insertbackground=FG,
            relief="flat",
            bd=0,
            font=FONT,
        )

        # Browse button
        self._btn = tk.Label(
            self._cv,
            text="Browse…",
            bg=BG_CARD,
            fg=FG_DIM,
            font=FONT_SM,
        )
        self._btn.bind("<Button-1>", lambda _: self._browse())
        self._btn.bind("<Enter>", lambda _: self._btn.configure(fg=FG))
        self._btn.bind("<Leave>", lambda _: self._btn.configure(fg=FG_DIM))

        self._var.set(placeholder)
        self._entry.bind("<FocusIn>", self._focus_in)
        self._entry.bind("<FocusOut>", self._focus_out)
        self._cv.bind("<Configure>", self._layout)

        # Drag-and-drop
        self._setup_dnd()

    def _layout(self, _=None):
        w = self._cv.winfo_width()
        h = self._cv.winfo_height()
        if w < 4:
            return
        self._cv.delete("all")
        bc = ACCENT_GLOW if self._dragging else BORDER
        _rounded_rect(self._cv, 0, 0, w - 1, h - 1, R, fill=BG_CARD, outline=bc)
        # place entry and button inside
        btn_w = 60
        self._entry.place(x=R + 4, y=4, width=w - btn_w - R * 2 - 8, height=h - 8)
        self._btn.place(x=w - btn_w - R, y=4, width=btn_w, height=h - 8)

    def _focus_in(self, _):
        if self._var.get() == self.placeholder:
            self._var.set("")
            self._entry.configure(fg=FG)

    def _focus_out(self, _):
        if not self._var.get().strip():
            self._var.set(self.placeholder)
            self._entry.configure(fg=FG_DIM)

    def _browse(self):
        d = filedialog.askdirectory(title="Select folder")
        if d:
            self.set_path(d)

    def _setup_dnd(self):
        try:
            from tkinterdnd2 import DND_FILES

            for widget in (self._entry, self._cv):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop)
                widget.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                widget.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        except Exception:
            pass

    def _on_drag_enter(self, event):
        self._dragging = True
        self._layout()
        return event.action

    def _on_drag_leave(self, event):
        self._dragging = False
        self._layout()

    def _on_drop(self, event):
        self._dragging = False
        raw = event.data.strip()
        # Windows wraps paths with spaces in curly braces
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        # Multiple files: take first
        if "} {" in raw:
            raw = raw.split("} {")[0]
        self.set_path(raw)
        self._layout()
        return event.action

    def set_path(self, path: str):
        self._var.set(path)
        self._entry.configure(fg=FG)

    def get(self) -> str:
        v = self._var.get().strip()
        return "" if v == self.placeholder else v


class LogStrip:
    def __init__(self, parent):
        outer = tk.Frame(parent, bg=LOG_BG, height=130)
        outer.pack(fill="x", side="bottom")
        outer.pack_propagate(False)

        hdr = tk.Frame(outer, bg=LOG_BG)
        hdr.pack(fill="x", padx=PAD, pady=(5, 0))
        tk.Label(hdr, text="Output", bg=LOG_BG, fg=FG_DIM, font=FONT_XS).pack(
            side="left"
        )
        tk.Label(hdr, text="Clear", bg=LOG_BG, fg=FG_MUTED, font=FONT_XS).pack(
            side="right"
        )
        hdr.winfo_children()[-1].bind("<Button-1>", lambda _: self.clear())
        hdr.winfo_children()[-1].bind(
            "<Enter>", lambda _: hdr.winfo_children()[-1].configure(fg=FG_DIM)
        )
        hdr.winfo_children()[-1].bind(
            "<Leave>", lambda _: hdr.winfo_children()[-1].configure(fg=FG_MUTED)
        )

        self.text = tk.Text(
            outer,
            height=4,
            bg=LOG_BG,
            fg=LOG_FG,
            font=FONT_MONO,
            relief="flat",
            bd=0,
            state="disabled",
            wrap="word",
            selectbackground=BG_HOVER,
        )
        self.text.pack(fill="both", expand=True, padx=PAD, pady=(2, 6))

    def write(self, msg: str):
        self.text.configure(state="normal")
        self.text.insert("end", msg)
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def flush(self):
        pass


class ColorPicker(tk.Frame):
    """
    A flat image-grid color picker.
    Shows one row of color icons; clicking one selects it.
    Displays a preview swatch + the name of the selected color.
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._selected = tk.StringVar(value="red")
        self._images: dict[str, ImageTk.PhotoImage] = {}
        self._cells: dict[str, tk.Label] = {}

        self._load_thumbs()
        self._build()

    def _load_thumbs(self):
        for name in COLOR_KEYS:
            path = ICONS_DIR / f"{name}.png"
            if not path.exists():
                ico_path = ICONS_DIR / utils.ICON_MAP[name]
                img = (
                    Image.open(ico_path).convert("RGBA").resize((28, 28), Image.LANCZOS)
                )
            else:
                img = Image.open(path).convert("RGBA").resize((28, 28), Image.LANCZOS)
            self._images[name] = ImageTk.PhotoImage(img)

    def _build(self):
        wrap = tk.Frame(
            self, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER
        )
        wrap.pack(fill="x")

        grid = tk.Frame(wrap, bg=BG_CARD)
        grid.pack(padx=6, pady=6)

        for i, name in enumerate(COLOR_KEYS):
            row, col = divmod(i, 10)
            cell = tk.Label(
                grid,
                image=self._images[name],
                bg=BG_CARD,
                padx=2,
                pady=2,
            )
            cell.grid(row=row, column=col, padx=2, pady=2)
            cell.bind("<Button-1>", lambda _, n=name: self._select(n))
            cell.bind("<Enter>", lambda _, c=cell: c.configure(bg=BG_HOVER))
            self._cells[name] = cell

        self._select("red")

    def _restore_cell(self, cell):
        name = [k for k, v in self._cells.items() if v is cell]
        bg = ACCENT_DIM if (name and name[0] == self._selected.get()) else BG_CARD
        cell.configure(bg=bg)

    def _select(self, name: str):
        prev = self._selected.get()
        if prev in self._cells:
            self._cells[prev].configure(bg=BG_CARD)
        self._selected.set(name)
        self._cells[name].configure(bg=ACCENT_DIM)

    def get(self) -> str:
        return self._selected.get()


def _heading(parent, title, subtitle):
    tk.Label(parent, text=title, bg=BG, fg=FG, font=FONT_HEAD).pack(
        anchor="w", padx=PAD, pady=(PAD, 1)
    )
    tk.Label(
        parent, text=subtitle, bg=BG, fg=FG_DIM, font=FONT_SM, justify="left"
    ).pack(anchor="w", padx=PAD)


def _divider(parent):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=8)


def _label(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=FG, font=FONT_LABEL).pack(
        anchor="w", padx=PAD, pady=(0, 4)
    )


class PhotosPanel(tk.Frame):
    def __init__(self, parent, log):
        super().__init__(parent, bg=BG)
        self._log = log

        _heading(
            self,
            "PHOTOS",
            "Organise, rename and clean photo folders using EXIF metadata.",
        )
        _divider(self)
        _label(self, "FOLDER")

        self._drop = RoundedEntry(self)
        self._drop.pack(fill="x", padx=PAD, pady=(0, PAD))

        _divider(self)
        _label(self, "ACTIONS")

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=PAD)

        self._mk_btn(
            row,
            "ORGANIZE",
            self._run_organize,
            primary=True,
            tip="Move photos into YYMMDD/ sub-folders",
        )
        self._mk_btn(
            row,
            "CLEAN",
            self._run_clean,
            primary=True,
            tip="Delete orphaned RAWs, then rename",
        )
        self._mk_btn(
            row,
            "RENAME",
            self._run_rename,
            primary=True,
            tip="Format:\n<Camera>_<Date>_<NNN>",
        )

    def _mk_btn(self, parent, label, cmd, primary, tip):
        col = tk.Frame(parent, bg=BG)
        col.pack(side="left", expand=True, fill="x", padx=(0, 8))
        bg = ACCENT if primary else BG_CARD
        hv = ACCENT_DIM if primary else BG_HOVER
        fg = "#FFFFFF" if primary else FG
        RoundedButton(
            col, text=label, command=cmd, bg=bg, hover_bg=hv, fg=fg, font=FONT
        ).pack(fill="x", ipady=2)
        tk.Label(
            col,
            text=tip,
            bg=BG,
            fg=FG_MUTED,
            font=FONT_XS,
            wraplength=150,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    def _get_path(self):
        p = self._drop.get()
        if not p:
            messagebox.showwarning("No folder", "Please select a photo folder first.")
            return None
        return p

    def _run(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _run_organize(self):
        if p := self._get_path():
            print(f"\n▶ Organising: {p}\n")
            self._run(tools.photo_organize, p)

    def _run_rename(self):
        if p := self._get_path():
            print(f"\n▶ Renaming: {p}\n")
            self._run(tools.photo_rename, p)

    def _run_clean(self):
        if p := self._get_path():
            if messagebox.askyesno(
                "Confirm", "This will permanently delete orphaned RAW files.\nContinue?"
            ):
                print(f"\n▶ Cleaning: {p}\n")
                self._run(tools.photo_clean, p)


class ColorPanel(tk.Frame):
    def __init__(self, parent, log):
        super().__init__(parent, bg=BG)

        _heading(self, "FOLDER COLOR", "Set a custom icon color in Windows Explorer.")

        if sys.platform != "win32":
            _divider(self)
            tk.Label(
                self,
                text="Folder coloring is Windows-only.\n"
                "Not available on your platform.",
                bg=BG,
                fg="#C0504D",
                font=FONT,
                justify="left",
            ).pack(anchor="w", padx=PAD, pady=20)
            return

        _divider(self)
        _label(self, "TARGET FOLDER")
        self._drop = RoundedEntry(self)
        self._drop.pack(fill="x", padx=PAD, pady=(0, PAD))

        _divider(self)
        _label(self, "COLOR")
        self._picker = ColorPicker(self)
        self._picker.pack(fill="x", padx=PAD, pady=(0, PAD))

        # Checkbox — plain, no box frame
        self._sub_var = tk.BooleanVar()
        chk = tk.Checkbutton(
            self,
            text="Apply to sub-folders",
            variable=self._sub_var,
            bg=BG,
            fg=FG_DIM,
            selectcolor=BG_CARD,
            activebackground=BG,
            activeforeground=FG_DIM,
            font=FONT_SM,
        )
        chk.pack(anchor="w", padx=PAD, pady=(0, PAD))

        _divider(self)
        RoundedButton(
            self,
            text="APPLY",
            command=self._apply,
            bg=ACCENT,
            hover_bg=ACCENT_DIM,
        ).pack(anchor="w", padx=PAD, pady=(4, PAD), ipadx=4, ipady=4)

    def _apply(self):
        p = self._drop.get()
        if not p:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return
        color = self._picker.get()
        if self._sub_var.get():
            print(f"\n▶ coloring sub-folders of {p} → {color}\n")
            threading.Thread(
                target=tools.set_subfolders_color, args=(p, color), daemon=True
            ).start()
        else:
            print(f"\n▶ coloring {p} → {color}\n")
            threading.Thread(
                target=utils.set_folder_color, args=(p, color), daemon=True
            ).start()


class SettingsPanel(tk.Frame):
    """
    Displays every key in settings.json as an editable field.
    String → Entry, list → multi-line Text.
    Save writes back to settings.json.
    """

    def __init__(self, parent, log):
        super().__init__(parent, bg=BG)
        self._log = log
        self._widgets: dict[str, tk.Widget] = {}

        _heading(self, "SETTINGS", "All settings.json keys — edit and save.")
        _divider(self)

        # Scrollable inner area
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(
            self, orient="vertical", command=canvas.yview, bg=BG, troughcolor=BG_CARD
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=PAD)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Build one row per setting
        with open(_SETTINGS_PATH) as f:
            data = json.load(f)

        for key, value in data.items():
            self._build_row(inner, key, value)

        _divider(self)
        RoundedButton(
            self,
            text="Save settings",
            command=self._save,
            bg=ACCENT,
            hover_bg=ACCENT_DIM,
        ).pack(anchor="e", padx=PAD, pady=(0, PAD), ipadx=4, ipady=2)

    def _build_row(self, parent, key: str, value):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=4)
        row.columnconfigure(1, weight=1)

        tk.Label(
            row, text=key, bg=BG, fg=FG_DIM, font=FONT_SM, width=22, anchor="w"
        ).grid(row=0, column=0, sticky="nw", padx=(0, 8))

        if isinstance(value, list):
            # Multi-line Text for lists
            frame = tk.Frame(
                row, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER
            )
            frame.grid(row=0, column=1, sticky="ew")
            t = tk.Text(
                frame,
                bg=BG_CARD,
                fg=FG,
                insertbackground=FG,
                font=FONT_MONO,
                relief="flat",
                bd=0,
                height=len(value) or 1,
                padx=6,
                pady=4,
                wrap="none",
            )
            t.pack(fill="x")
            t.insert("1.0", "\n".join(str(v) for v in value))
            self._widgets[key] = t
        else:
            # Single-line Entry
            frame = tk.Frame(
                row, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER
            )
            frame.grid(row=0, column=1, sticky="ew")
            var = tk.StringVar(value=str(value))
            e = tk.Entry(
                frame,
                textvariable=var,
                bg=BG_CARD,
                fg=FG,
                insertbackground=FG,
                relief="flat",
                bd=0,
                font=FONT_MONO,
            )
            e.pack(fill="x", ipady=5, padx=6)
            self._widgets[key] = var

    def _save(self):
        # Read current settings.json to know types
        with open(_SETTINGS_PATH) as f:
            original = json.load(f)

        new_data = {}
        for key, widget in self._widgets.items():
            orig_val = original.get(key)
            if isinstance(widget, tk.StringVar):
                raw = widget.get().strip()
                if raw.lower() == "true":
                    new_data[key] = True
                elif raw.lower() in ["false", "null"]:
                    print("FALSE FOUND")
                    new_data[key] = False

                # Try to cast back to original type
                elif isinstance(orig_val, int):
                    try:
                        new_data[key] = int(raw)
                    except ValueError:
                        new_data[key] = raw
                else:
                    new_data[key] = raw
            else:
                # Text widget → list
                lines = [
                    l.strip()
                    for l in widget.get("1.0", "end").splitlines()
                    if l.strip()
                ]
                new_data[key] = lines

        with open(_SETTINGS_PATH, "w") as f:
            json.dump(new_data, f, indent=4)

        import importlib

        from . import tools as _t

        importlib.reload(_t)
        print("\nSettings saved.\n")


NAV = [
    ("Photos", PhotosPanel),
    ("Color", ColorPanel),
    ("Settings", SettingsPanel),
]


class Sidebar(tk.Frame):
    def __init__(self, parent, on_select):
        super().__init__(parent, bg=SB_BG, width=158)
        self.pack_propagate(False)
        self._on_select = on_select
        self._rows: dict[str, tk.Frame] = {}
        self._labels: dict[str, tk.Label] = {}
        self._active = None

        # Header
        hdr = tk.Frame(self, bg=SB_BG)
        hdr.pack(fill="x", pady=(PAD, 0))
        tk.Label(
            hdr, text="FILE MANAGER", bg=SB_BG, fg=FG, font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=PAD)
        tk.Label(
            self, text=f"    v{__version__}", bg=SB_BG, fg=FG_MUTED, font=FONT_XS
        ).pack(pady=0, anchor="w")

        _divider(self)

        tk.Label(self, text="TOOLS", bg=SB_BG, fg=ACCENT, font=FONT_BOLD).pack(
            anchor="w", padx=PAD, pady=(10, 4)
        )

        for name, _ in NAV:
            self._mk_item(name)

        tk.Frame(self, bg=SB_BG).pack(fill="both", expand=True)

    def _mk_item(self, name: str):
        row = tk.Frame(self, bg=SB_BG)
        row.pack(fill="x", padx=6, pady=1)

        lbl = tk.Label(
            row,
            text=name,
            bg=SB_BG,
            fg=FG_DIM,
            font=FONT_BOLD,
            anchor="w",
            padx=10,
            pady=7,
        )
        lbl.pack(fill="x")

        def click(_=None, n=name):
            self._activate(n)
            self._on_select(n)

        def enter(_=None):
            if self._active != name:
                row.configure(bg=SB_ACTIVE)
                lbl.configure(bg=SB_ACTIVE, fg=FG)

        def leave(_=None):
            if self._active != name:
                row.configure(bg=SB_BG)
                lbl.configure(bg=SB_BG, fg=FG_DIM)

        for w in (row, lbl):
            w.bind("<Button-1>", click)
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

        self._rows[name] = row
        self._labels[name] = lbl

    def _activate(self, name: str):
        if self._active:
            self._rows[self._active].configure(bg=SB_BG)
            self._labels[self._active].configure(bg=SB_BG, fg=FG_DIM)
        self._active = name
        # Draw rounded active indicator using canvas
        self._rows[name].configure(bg=ACCENT)
        self._labels[name].configure(bg=ACCENT, fg="#FFFFFF")

    def select(self, name: str):
        self._activate(name)


class App:
    """
    Wraps either a TkinterDnD.Tk (for drag-and-drop) or plain tk.Tk.
    """

    def __init__(self):
        root = self._make_root()
        root.title("file-manager")
        root.configure(bg=BG)
        root.geometry("820x580")
        root.minsize(700, 480)
        self._root = root

        # Log (bottom)
        self._log = LogStrip(root)

        # Body
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True)

        self._sidebar = Sidebar(body, self._show)
        self._sidebar.pack(side="left", fill="y")
        tk.Frame(body, bg=SB_BORDER, width=1).pack(side="left", fill="y")

        self._content = tk.Frame(body, bg=BG)
        self._content.pack(side="left", fill="both", expand=True)

        self._panels: dict[str, tk.Frame] = {}
        for name, Cls in NAV:
            self._panels[name] = Cls(self._content, self._log)

        sys.stdout = self._log
        self._show("Photos")
        self._sidebar.select("Photos")

    @staticmethod
    def _make_root():
        try:
            from tkinterdnd2 import TkinterDnD

            return TkinterDnD.Tk()
        except Exception:
            return tk.Tk()

    def _show(self, name: str):
        for n, p in self._panels.items():
            p.pack_forget() if n != name else p.pack(fill="both", expand=True)

    def run(self):
        self._root.mainloop()


def launch():
    App().run()
