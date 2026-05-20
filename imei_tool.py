import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import re
import threading
import queue
import time
import json
import csv
from datetime import datetime


# ─── Utilities ───────────────────────────────────────────────────────────────

class HistoryManager:
    """Manages session history of actions."""
    def __init__(self):
        self.entries = []

    def add(self, action_type, details, count=0):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": action_type,
            "details": details,
            "count": count
        }
        self.entries.insert(0, entry)  # Newest first
        if len(self.entries) > 50:
            self.entries.pop()

    def clear(self):
        self.entries = []


class ToolTip:
    """Custom hover tooltip for Tkinter widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Use theme-aware colors
        bg = "#1E2333" if CURRENT_THEME == DARK_THEME else "#FAF6F0"
        fg = "#FFFFFF" if CURRENT_THEME == DARK_THEME else "#2C1E16"
        border = "#00E5FF" if CURRENT_THEME == DARK_THEME else "#5E4028"

        label = tk.Label(tw, text=self.text, justify="left",
                         background=bg, foreground=fg, relief="solid", borderwidth=1,
                         font=(FONT_UI, 9), padx=8, pady=4, highlightthickness=1,
                         highlightbackground=border)
        label.pack()

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class ThreadedTask:
    """Helper to run long-running tasks in a background thread."""
    def __init__(self, widget, target, on_complete, on_error=None):
        self.widget = widget
        self.target = target
        self.on_complete = on_complete
        self.on_error = on_error
        self.queue = queue.Queue()

    def start(self, *args, **kwargs):
        def wrapper():
            try:
                result = self.target(*args, **kwargs)
                self.queue.put(("SUCCESS", result))
            except Exception as e:
                self.queue.put(("ERROR", str(e)))
        
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        self._check_queue()

    def _check_queue(self):
        try:
            status, result = self.queue.get_nowait()
            if status == "SUCCESS":
                self.on_complete(result)
            elif self.on_error:
                self.on_error(result)
            else:
                messagebox.showerror("Task Error", result)
        except queue.Empty:
            # Poll again
            self.widget.after(100, self._check_queue)


# ─── IMEI Logic ───────────────────────────────────────────────────────────────

def luhn_checksum(number_str: str) -> int:
    """Return the Luhn check digit for a 14-digit string."""
    if len(number_str) != 14:
        raise ValueError(f"luhn_checksum expects exactly 14 digits, got {len(number_str)}.")
    digits = [int(d) for d in number_str]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def validate_imei(imei: str) -> tuple[bool, str]:
    """Validate an IMEI string. Returns (is_valid, message)."""
    imei = imei.strip().replace(" ", "").replace("-", "")
    if not imei.isdigit():
        return False, "IMEI must contain digits only."
    if len(imei) != 15:
        return False, f"IMEI must be 15 digits (got {len(imei)})."
    expected = luhn_checksum(imei[:14])
    actual = int(imei[14])
    if expected == actual:
        return True, "Valid IMEI ✓"
    return False, f"Invalid check digit (expected {expected}, got {actual})."


def tac_to_imei(tac: str, count: int = 10, mode: str = "random") -> list[str] | str:
    """Generate IMEIs from an 8-digit TAC."""
    tac = tac.strip().replace(" ", "")
    if not tac.isdigit():
        return "TAC must be numeric."
    if len(tac) != 8:
        return f"TAC must be 8 digits (got {len(tac)})."
    
    imeis = []
    seen = set()
    
    if mode == "sequential":
        max_serials = 1_000_000  # 000000–999999
        actual_count = min(count, max_serials)
        for i in range(actual_count):
            serial = f"{i:06d}"
            base = tac + serial
            check = luhn_checksum(base)
            imeis.append(base + str(check))
        return imeis

    attempts = 0
    while len(imeis) < count and attempts < count * 10:
        attempts += 1
        serial = f"{random.randint(0, 999999):06d}"
        base = tac + serial
        check = luhn_checksum(base)
        imei = base + str(check)
        if imei not in seen:
            seen.add(imei)
            imeis.append(imei)
    if not imeis:
        return f"Could not generate any IMEIs for TAC {tac}."
    return imeis


def generate_by_mask(mask: str, count: int = 10, mode: str = "random") -> list[str] | str:
    """
    Generate IMEIs based on a mask where 'X' is a random/sequential digit.
    e.g. 35693803XXXXXX
    """
    mask = mask.strip().replace(" ", "").upper()
    if len(mask) != 14:
        return f"Mask must be exactly 14 characters (excluding check digit). Got {len(mask)}."
    
    if not all(c.isdigit() or c == 'X' for c in mask):
        return "Mask must contain only digits and 'X'."

    imeis = []
    seen = set()
    
    x_indices = [i for i, char in enumerate(mask) if char == 'X']
    if not x_indices and mode == "random":
        # Fixed 14 digits, only one possible IMEI
        base = mask
        imeis.append(base + str(luhn_checksum(base)))
        return imeis

    if mode == "sequential":
        max_val = 10 ** len(x_indices)
        target = min(count, max_val)
        truncated = target < count
        for i in range(target):
            res_list = list(mask)
            # Fill Xs with digits of i
            fill = f"{i:0{len(x_indices)}d}"
            for idx, char in zip(x_indices, fill):
                res_list[idx] = char
            base = "".join(res_list)
            imeis.append(base + str(luhn_checksum(base)))
        if truncated:
            imeis.append(f"[Note: only {max_val} unique combination(s) possible with {len(x_indices)} wildcard(s); generated {target} instead of {count}]")
        return imeis

    attempts = 0
    max_attempts = max(count * 10, 2000)
    while len(imeis) < count and attempts < max_attempts:
        attempts += 1
        res_list = list(mask)
        for idx in x_indices:
            res_list[idx] = str(random.randint(0, 9))
        
        base = "".join(res_list)
        check = luhn_checksum(base)
        imei = base + str(check)
        if imei not in seen:
            seen.add(imei)
            imeis.append(imei)
            
    if not imeis:
        return "Could not generate unique IMEIs from mask."
    return imeis


def generate_by_pattern(imei1: str, imei2: str, count: int = 10, mode: str = "random") -> list[str] | str:
    """
    Generate IMEIs based on the pattern of two IMEIs.
    """
    i1 = imei1.strip().replace(" ", "").replace("-", "")
    i2 = imei2.strip().replace(" ", "").replace("-", "")

    v1, m1 = validate_imei(i1)
    v2, m2 = validate_imei(i2)
    if not v1:
        return f"IMEI 1: {m1}"
    if not v2:
        return f"IMEI 2: {m2}"

    s1, s2 = i1[:14], i2[:14]

    # Mark every position where the two IMEIs differ as a wildcard.
    # The old approach only marked positions from the first mismatch onward,
    # which incorrectly treated later re-matching digits as fixed.
    mask_list = []
    for c1, c2 in zip(s1, s2):
        mask_list.append('X' if c1 != c2 else c1)

    if 'X' not in mask_list and mode == "random":
        return "Both IMEIs are identical. Please provide two different IMEIs to define a pattern."
    
    return generate_by_mask("".join(mask_list), count, mode)


# ─── Themes & Palettes ────────────────────────────────────────────────────────

DARK_THEME = {
    "bg": "#090A0F",
    "panel": "#141722",
    "card": "#1E2333",
    "border": "#2C344A",
    "accent": "#00E5FF",
    "accent2": "#9D82FF",
    "success": "#00E676",
    "error": "#FF4C6A",
    "warning": "#FFB800",
    "text": "#FFFFFF",
    "subtext": "#A1A9B8",
}

# Cream & Mocha Light Theme
LIGHT_THEME = {
    "bg": "#E9E2D9",
    "panel": "#FFFFFF",
    "card": "#FAF6F0",
    "border": "#D4C9B8",
    "accent": "#5E4028",
    "accent2": "#A98262",
    "success": "#2E7D32",
    "error": "#D32F2F",
    "warning": "#F57C00",
    "text": "#2C1E16",
    "subtext": "#6A5A4D",
}

# Default colors (will be updated by theme)
CURRENT_THEME = DARK_THEME  # tracks the active theme dict; used by GlowButton
BG       = DARK_THEME["bg"]
PANEL    = DARK_THEME["panel"]
CARD     = DARK_THEME["card"]
BORDER   = DARK_THEME["border"]
ACCENT   = DARK_THEME["accent"]
ACCENT2  = DARK_THEME["accent2"]
SUCCESS  = DARK_THEME["success"]
ERROR    = DARK_THEME["error"]
WARNING  = DARK_THEME["warning"]
TEXT     = DARK_THEME["text"]
SUBTEXT  = DARK_THEME["subtext"]
FONT_MONO = "Consolas"
FONT_UI   = "Segoe UI"

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


# ─── Custom Widgets ───────────────────────────────────────────────────────────

class RoundedCard(tk.Canvas):
    def __init__(self, parent, bg_color=None, border_color=None, radius=10, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.radius = radius
        self.bg_key = bg_color  # "card" to use theme color, or None for CARD default
        self.border_key = border_color  # "border" to use theme color, or None for BORDER default
        self.bind("<Configure>", self._draw)

    def update_theme(self):
        self._draw()

    def _draw(self, event=None):
        self.delete("all")
        bg_col = CARD if self.bg_key in (None, "card") else self.bg_key
        border_col = BORDER if self.border_key in (None, "border") else self.border_key
        self.configure(bg=self.master["bg"])
        
        w = self.winfo_width()
        h = self.winfo_height()
        r = self.radius
        if w <= 1 or h <= 1:
            return
            
        x0, y0, x1, y1 = 1, 1, w-1, h-1
        
        # Shadow (Subtle)
        self.create_rectangle(x0+2, y0+2, x1+2, y1+2, fill=self.master["bg"], outline="")
        
        self.create_arc(x0, y0, x0+r*2, y0+r*2, start=90, extent=90, fill=bg_col, outline=border_col)
        self.create_arc(x1-r*2, y0, x1, y0+r*2, start=0, extent=90, fill=bg_col, outline=border_col)
        self.create_arc(x1-r*2, y1-r*2, x1, y1, start=270, extent=90, fill=bg_col, outline=border_col)
        self.create_arc(x0, y1-r*2, x0+r*2, y1, start=180, extent=90, fill=bg_col, outline=border_col)
        
        self.create_rectangle(x0+r, y0, x1-r, y1, fill=bg_col, outline=bg_col)
        self.create_rectangle(x0, y0+r, x1, y1-r, fill=bg_col, outline=bg_col)
        
        self.create_line(x0+r, y0, x1-r, y0, fill=border_col)
        self.create_line(x0+r, y1, x1-r, y1, fill=border_col)
        self.create_line(x0, y0+r, x0, y1-r, fill=border_col)
        self.create_line(x1, y0+r, x1, y1-r, fill=border_col)


class ModernEntry(tk.Frame):
    def __init__(self, parent, placeholder="", width=28, **kwargs):
        super().__init__(parent, bg=CARD, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT)
        self.placeholder = placeholder
        self._has_focus = False

        self.entry = tk.Entry(self, font=(FONT_MONO, 11), bg=CARD, fg=TEXT,
                              insertbackground=ACCENT, relief="flat",
                              width=width, bd=0, **kwargs)
        self.entry.pack(padx=12, pady=8, fill="x")
        self._set_placeholder()

        self.entry.bind("<FocusIn>",  self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Enter>", lambda e: self._on_hover(True))
        self.bind("<Leave>", lambda e: self._on_hover(False))

    def update_theme(self):
        entry_bg = "#FAF6F0" if CURRENT_THEME == LIGHT_THEME else CARD
        self.configure(bg=entry_bg, highlightbackground=ACCENT if self._has_focus else BORDER)
        self.entry.configure(bg=entry_bg, fg=TEXT if (self.entry.get() != self.placeholder) else SUBTEXT,
                             insertbackground=ACCENT)

    def _on_hover(self, entering):
        if not self._has_focus:
            self.configure(highlightbackground=ACCENT2 if entering else BORDER)

    def _set_placeholder(self):
        if not self.entry.get():
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=SUBTEXT)

    def _on_focus_in(self, _=None):
        self._has_focus = True
        self.configure(highlightbackground=ACCENT)
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, "end")
            self.entry.config(fg=TEXT)

    def _on_focus_out(self, _=None):
        self._has_focus = False
        self.configure(highlightbackground=BORDER)
        if not self.entry.get():
            self._set_placeholder()

    def get(self):
        val = self.entry.get()
        return "" if val == self.placeholder else val

    def set(self, val):
        self.entry.delete(0, "end")
        if val:
            self.entry.insert(0, val)
            self.entry.config(fg=TEXT)
        else:
            self._set_placeholder()

    def clear(self):
        self.entry.delete(0, "end")
        self._set_placeholder()


class GlowButton(tk.Canvas):
    def __init__(self, parent, text, command=None, color=ACCENT, width=160, height=38, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.command = command
        self.color = color
        self.text = text
        self.w, self.h = width, height
        self.hovered = False
        self._draw()
        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", lambda e: self._click())

    def update_theme(self, color=None):
        if color: 
            self.color = color
        else:
            if self.color in [DARK_THEME["accent"], LIGHT_THEME["accent"]]: self.color = ACCENT
            elif self.color in [DARK_THEME["accent2"], LIGHT_THEME["accent2"]]: self.color = ACCENT2
            elif self.color in [DARK_THEME["success"], LIGHT_THEME["success"]]: self.color = SUCCESS
            elif self.color in [DARK_THEME["error"], LIGHT_THEME["error"]]: self.color = ERROR
            elif self.color in [DARK_THEME["warning"], LIGHT_THEME["warning"]]: self.color = WARNING
            elif self.color in [DARK_THEME["subtext"], LIGHT_THEME["subtext"]]: self.color = SUBTEXT
        self.configure(bg=self.master["bg"])
        self._draw()

    def _on_enter(self, _):
        self.hovered = True
        self._draw()

    def _on_leave(self, _):
        self.hovered = False
        self._draw()

    def _draw(self):
        self.delete("all")
        fill = self.color if self.hovered else CARD
        outline = self.color
        r = 6
        w, h = self.w, self.h
        
        x0, y0, x1, y1 = 1, 1, w-1, h-1
        
        self.create_arc(x0, y0, x0+r*2, y0+r*2, start=90, extent=90, fill=fill, outline=outline)
        self.create_arc(x1-r*2, y0, x1, y0+r*2, start=0, extent=90, fill=fill, outline=outline)
        self.create_arc(x1-r*2, y1-r*2, x1, y1, start=270, extent=90, fill=fill, outline=outline)
        self.create_arc(x0, y1-r*2, x0+r*2, y1, start=180, extent=90, fill=fill, outline=outline)
        
        self.create_rectangle(x0+r, y0, x1-r, y1, fill=fill, outline=fill)
        self.create_rectangle(x0, y0+r, x1, y1-r, fill=fill, outline=fill)
        
        self.create_line(x0+r, y0, x1-r, y0, fill=outline)
        self.create_line(x0+r, y1, x1-r, y1, fill=outline)
        self.create_line(x0, y0+r, x0, y1-r, fill=outline)
        self.create_line(x1, y0+r, x1, y1-r, fill=outline)

        text_color = CURRENT_THEME["bg"] if self.hovered else self.color
        self.create_text(w//2, h//2, text=self.text, font=(FONT_UI, 10, "bold"),
                         fill=text_color)

    def _click(self):
        if self.command:
            self.command()


class ResultBox(tk.Frame):
    def __init__(self, parent, height=8, **kwargs):
        super().__init__(parent, bg=CARD, highlightthickness=1,
                         highlightbackground=BORDER)
        self.text = tk.Text(self, font=(FONT_MONO, 10), bg=CARD, fg=TEXT,
                            relief="flat", bd=0, height=height,
                            insertbackground=ACCENT, selectbackground=ACCENT2,
                            wrap="none", state="disabled")
        self.scroll = tk.Scrollbar(self, orient="vertical", command=self.text.yview,
                              bg=PANEL, troughcolor=CARD, width=10,
                              relief="flat", bd=0)
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.pack(side="left", fill="both", expand=True, padx=(10, 2), pady=10)
        self.scroll.pack(side="right", fill="y", pady=10, padx=(0, 4))

        self._configure_tags()

    def _configure_tags(self):
        self.text.tag_configure("valid",   foreground=SUCCESS)
        self.text.tag_configure("invalid", foreground=ERROR)
        self.text.tag_configure("dim",     foreground=SUBTEXT)
        self.text.tag_configure("accent",  foreground=ACCENT)
        self.text.tag_configure("heading", foreground=ACCENT2, font=(FONT_UI, 10, "bold"))

    def update_theme(self):
        self.configure(bg=CARD, highlightbackground=BORDER)
        self.text.configure(bg=CARD, fg=TEXT, insertbackground=ACCENT, selectbackground=ACCENT2)
        self.scroll.configure(bg=PANEL, troughcolor=CARD)
        self._configure_tags()

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def append(self, line, tag=None):
        self.text.configure(state="normal")
        if tag:
            self.text.insert("end", line + "\n", tag)
        else:
            self.text.insert("end", line + "\n")
        self.text.configure(state="disabled")
        self.text.see("end")

    def set_lines(self, lines, tag=None):
        self.clear()
        for ln in lines:
            self.append(ln, tag)


class StatLabel(tk.Frame):
    def __init__(self, parent, label, color):
        super().__init__(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        self.label_text = label
        self.color = color
        
        self.title = tk.Label(self, text=label, font=(FONT_UI, 8, "bold"), bg=CARD, fg=SUBTEXT)
        self.title.pack(padx=14, pady=(8, 0))
        
        self.value = tk.Label(self, text="—", font=(FONT_UI, 16, "bold"), bg=CARD, fg=color)
        self.value.pack(padx=14, pady=(0, 8))

    def update_theme(self):
        st_bg = CARD
        if self.color in [DARK_THEME["text"], LIGHT_THEME["text"]]: self.color = TEXT
        elif self.color in [DARK_THEME["success"], LIGHT_THEME["success"]]: self.color = SUCCESS
        elif self.color in [DARK_THEME["error"], LIGHT_THEME["error"]]: self.color = ERROR
        
        self.configure(bg=st_bg, highlightbackground=BORDER)
        self.title.configure(bg=st_bg, fg=SUBTEXT)
        self.value.configure(bg=st_bg, fg=self.color)

    def set(self, val):
        self.value.configure(text=str(val))

    def clear(self):
        self.value.configure(text="—")


class StatusBar(tk.Label):
    def __init__(self, parent):
        super().__init__(parent, text="Ready", font=(FONT_UI, 9),
                         bg=PANEL, fg=SUBTEXT, anchor="w", padx=12, pady=4)

    def update(self, msg, color=None):
        if color is None: color = SUBTEXT
        self.configure(text=msg, fg=color)

    def update_theme(self):
        self.configure(bg=PANEL, fg=SUBTEXT)


# ─── Tabs ─────────────────────────────────────────────────────────────────────

class TabButton(tk.Label):
    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, text=text, font=(FONT_UI, 10, "bold"),
                         bg=PANEL, fg=SUBTEXT, padx=18, pady=10,
                         cursor="hand2", **kwargs)
        self.command = command
        self.is_active = False
        self.bind("<Button-1>", lambda e: self.command())

    def update_theme(self):
        if self.is_active:
            self.activate()
        else:
            self.deactivate()

    def activate(self):
        self.is_active = True
        self.configure(fg=ACCENT, bg=BG)

    def deactivate(self):
        self.is_active = False
        self.configure(fg=SUBTEXT, bg=PANEL)


# ─── Main App ─────────────────────────────────────────────────────────────────

class IMEIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IMEI Generator")
        self.configure(bg=BG)
        self.history = HistoryManager()
        self._build_ui()
        
        # Responsive setup
        self.minsize(850, 650)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # Container row

        self.geometry("850x650")
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _toggle_theme(self):
        global BG, PANEL, CARD, BORDER, ACCENT, ACCENT2, SUCCESS, ERROR, WARNING, TEXT, SUBTEXT, CURRENT_THEME
        new_theme = LIGHT_THEME if BG == DARK_THEME["bg"] else DARK_THEME
        CURRENT_THEME = new_theme
        
        BG       = new_theme["bg"]
        PANEL    = new_theme["panel"]
        CARD     = new_theme["card"]
        BORDER   = new_theme["border"]
        ACCENT   = new_theme["accent"]
        ACCENT2  = new_theme["accent2"]
        SUCCESS  = new_theme["success"]
        ERROR    = new_theme["error"]
        WARNING  = new_theme["warning"]
        TEXT     = new_theme["text"]
        SUBTEXT  = new_theme["subtext"]
        
        # Flush any pending Tk events before redrawing so all global color
        # variables are fully committed before any widget calls _draw().
        self.configure(bg=BG)
        self.update_idletasks()
        self._update_all_widgets_theme()
        self.status.update(f"Switched to {'Light' if new_theme == LIGHT_THEME else 'Dark'} theme.", ACCENT)

    def _show_about(self):
        """Display a professional About dialog."""
        win = tk.Toplevel(self)
        win.title("About — IMEI Generator")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        w, h = 500, 600
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # ── Developer Banner ──────────────────────────────────────────────
        banner = tk.Frame(win, bg=PANEL, pady=28)
        banner.pack(fill="x")

        tk.Label(banner, text="GIANT",
                 font=(FONT_UI, 36, "bold"), bg=PANEL, fg=ACCENT).pack()
        tk.Label(banner, text="Developer  ·  Creator  ·  Engineer",
                 font=(FONT_UI, 10), bg=PANEL, fg=SUBTEXT).pack(pady=(4, 0))
        tk.Label(banner, text="Crafting precision tools with purpose.",
                 font=(FONT_UI, 9, "italic"), bg=PANEL, fg=ACCENT2).pack(pady=(2, 0))

        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24)

        # ── About Section ─────────────────────────────────────────────────
        about_frame = tk.Frame(win, bg=BG, padx=28, pady=18)
        about_frame.pack(fill="x")

        tk.Label(about_frame, text="About This Tool",
                 font=(FONT_UI, 11, "bold"), bg=BG, fg=TEXT, anchor="w").pack(anchor="w")
        tk.Label(about_frame,
                 text=(
                     "IMEI Generator is a professional-grade desktop utility for\n"
                     "generating and validating IMEI numbers with precision. Built\n"
                     "entirely with Python and a fully custom Tkinter UI framework,\n"
                     "it delivers a modern, responsive experience without any\n"
                     "external dependencies."
                 ),
                 font=(FONT_UI, 9), bg=BG, fg=SUBTEXT,
                 justify="left", anchor="w").pack(anchor="w", pady=(8, 0))

        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24)

        # ── Feature List ──────────────────────────────────────────────────
        feat_frame = tk.Frame(win, bg=BG, padx=28, pady=18)
        feat_frame.pack(fill="x")

        tk.Label(feat_frame, text="Key Features",
                 font=(FONT_UI, 11, "bold"), bg=BG, fg=TEXT, anchor="w").pack(anchor="w", pady=(0, 10))

        features = [
            ("⚡", "Pattern & Mask-based IMEI generation (supports 'X' wildcards)"),
            ("📡", "TAC-based generation with collision handling & sequential mode"),
            ("✔",  "Batch Luhn validation with real-time duplicate detection"),
            ("📂", "File import support for .txt and .csv batch inputs"),
            ("💾", "Multi-format export — .txt, .csv, and .json"),
            ("🕓", "Session History Log tracking all generation & validation activity"),
            ("🎨", "Dynamic Dark Mode and Cream & Mocha theme switching"),
            ("⚙",  "Threaded background execution — zero UI freezing on large batches"),
        ]

        for icon, desc in features:
            row = tk.Frame(feat_frame, bg=BG)
            row.pack(anchor="w", pady=3)
            tk.Label(row, text=icon, font=(FONT_UI, 10), bg=BG,
                     fg=ACCENT, width=3, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=(FONT_UI, 9), bg=BG,
                     fg=SUBTEXT, anchor="w").pack(side="left")

        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24)

        # ── Footer ────────────────────────────────────────────────────────
        foot = tk.Frame(win, bg=PANEL, pady=16)
        foot.pack(fill="x")

        tk.Label(foot, text="© 2026 GIANT  ·  All Rights Reserved",
                 font=(FONT_UI, 8), bg=PANEL, fg=SUBTEXT).pack()
        GlowButton(foot, "Close", command=win.destroy,
                   color=ACCENT2, width=110, height=30).pack(pady=(10, 0))

    def _update_all_widgets_theme(self):
        self.hdr.configure(bg=PANEL)
        self.hdr_title.configure(bg=PANEL, fg=ACCENT)
        self.hdr_subtitle.configure(bg=PANEL, fg=SUBTEXT)
        self.sep1.configure(bg=BORDER)
        self.tab_bar.configure(bg=PANEL)
        self.container.configure(bg=BG)
        self.sep2.configure(bg=BORDER)
        self.status.update_theme()
        self.theme_btn.update_theme()
        self.about_btn.update_theme()

        for page in self.pages.values():
            page.configure(bg=BG)
            for child in page.winfo_children():
                self._recursive_theme_update(child)

        for btn in self.tab_btns.values():
            btn.update_theme()

        if hasattr(self, 'val_inp_frame'):
            self.val_inp_frame.configure(bg=CARD)
            self.val_input.configure(bg=CARD, fg=TEXT, insertbackground=ACCENT, selectbackground=ACCENT2)
            self.val_sc.configure(bg=PANEL, troughcolor=CARD)
        
        if hasattr(self, 'hist_box'):
            self.hist_box.update_theme()
        
        self._switch_tab(self._active_tab)

    def _recursive_theme_update(self, widget):
        if hasattr(widget, "update_theme"):
            widget.update_theme()
        elif isinstance(widget, tk.Frame):
            current_bg = widget.cget("bg")
            if current_bg in (DARK_THEME["bg"], LIGHT_THEME["bg"]):
                widget.configure(bg=BG)
            elif current_bg in (DARK_THEME["card"], LIGHT_THEME["card"]):
                widget.configure(bg=CARD)
        elif isinstance(widget, tk.Label):
            fg = widget.cget("fg")
            if fg in [DARK_THEME["text"], LIGHT_THEME["text"]]:
                widget.configure(bg=BG, fg=TEXT)
            elif fg in [DARK_THEME["accent2"], LIGHT_THEME["accent2"]]:
                widget.configure(bg=BG, fg=ACCENT2)
            elif fg in [DARK_THEME["success"], LIGHT_THEME["success"]]:
                widget.configure(bg=BG, fg=SUCCESS)
            elif fg in [DARK_THEME["error"], LIGHT_THEME["error"]]:
                widget.configure(bg=BG, fg=ERROR)
            else:
                widget.configure(bg=BG, fg=SUBTEXT)
        elif isinstance(widget, tk.Radiobutton):
            widget.configure(bg=CARD, fg=TEXT, activebackground=CARD, selectcolor=BORDER)
        
        for child in widget.winfo_children():
            self._recursive_theme_update(child)

    def _export_results(self, result_box, valid_only=False):
        """Export IMEIs from a result box.

        valid_only=True  -> skip lines with a failure marker (Validator tab).
        valid_only=False -> export every 15-digit number found (generator tabs).
        """
        content = result_box.text.get("1.0", "end")
        imeis = []
        for line in content.splitlines():
            if valid_only and "\u2717" in line:   # ✗
                continue
            found = re.findall(r"\b\d{15}\b", line)
            if found:
                imeis.extend(found)
        if not imeis:
            messagebox.showwarning("Export", "No IMEIs found to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Export IMEIs"
        )
        if file_path:
            try:
                if file_path.endswith(".csv"):
                    with open(file_path, "w", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(["IMEI"])
                        for imei in imeis: writer.writerow([imei])
                elif file_path.endswith(".json"):
                    with open(file_path, "w") as f:
                        json.dump({"imeis": imeis}, f, indent=4)
                else:
                    with open(file_path, "w") as f:
                        f.write("\n".join(imeis) + "\n")
                
                self.status.update(f"Exported {len(imeis)} IMEIs to {file_path}", SUCCESS)
                self.history.add("Export", f"Exported {len(imeis)} IMEIs to {file_path.split('/')[-1]}", len(imeis))
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not save file: {e}")

    def _build_ui(self):
        self.hdr = tk.Frame(self, bg=PANEL, height=56)
        self.hdr.pack(fill="x")
        self.hdr_title = tk.Label(self.hdr, text="⬡  IMEI GENERATOR", font=(FONT_UI, 15, "bold"),
                                  bg=PANEL, fg=ACCENT)
        self.hdr_title.pack(side="left", padx=20, pady=14)
        self.hdr_subtitle = tk.Label(self.hdr, text="Generate · Validate · Explore",
                                     font=(FONT_UI, 9), bg=PANEL, fg=SUBTEXT)
        self.hdr_subtitle.pack(side="left")

        self.theme_btn = GlowButton(self.hdr, "🌓 Theme", command=self._toggle_theme,
                                    color=ACCENT2, width=100, height=30)
        self.theme_btn.pack(side="right", padx=(0, 20))

        self.about_btn = GlowButton(self.hdr, "ℹ  About", command=self._show_about,
                                    color=ACCENT, width=100, height=30)
        self.about_btn.pack(side="right", padx=(0, 8))

        self.sep1 = tk.Frame(self, bg=BORDER, height=1)
        self.sep1.pack(fill="x")

        self.tab_bar = tk.Frame(self, bg=PANEL)
        self.tab_bar.pack(fill="x")

        self.pages = {}
        self.tab_btns = {}
        self._active_tab = None

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True, padx=20, pady=16)

        for name in ("Pattern Generator", "TAC Generator", "Validator", "History"):
            page = tk.Frame(self.container, bg=BG)
            self.pages[name] = page
            btn = TabButton(self.tab_bar, name, lambda n=name: self._switch_tab(n))
            btn.pack(side="left")
            self.tab_btns[name] = btn

        self._build_range_tab(self.pages["Pattern Generator"])
        self._build_tac_tab(self.pages["TAC Generator"])
        self._build_validator_tab(self.pages["Validator"])
        self._build_history_tab(self.pages["History"])

        self.sep2 = tk.Frame(self, bg=BORDER, height=1)
        self.sep2.pack(fill="x")
        self.status = StatusBar(self)
        self.status.pack(fill="x")

        self._switch_tab("Pattern Generator")

    def _build_history_tab(self, page):
        tk.Label(page, text="Session History",
                 font=(FONT_UI, 14, "bold"), bg=BG, fg=TEXT).pack(anchor="w", pady=(10, 8))
        tk.Label(page, text="Recent activity in the current session.",
                 font=(FONT_UI, 9), bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(0, 16))

        row = tk.Frame(page, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        GlowButton(row, "✕  Clear History", command=self._clear_history,
                   color=ERROR, width=140, height=32).pack(side="left")
        
        self.hist_box = ResultBox(page, height=18)
        self.hist_box.pack(fill="both", expand=True)

    def _clear_history(self):
        self.history.clear()
        self.hist_box.clear()
        self.status.update("History cleared.")

    def _update_history_display(self):
        self.hist_box.clear()
        if not self.history.entries:
            self.hist_box.append("  No history yet.", "dim")
            return
        
        for e in self.history.entries:
            self.hist_box.append(f"  [{e['timestamp']}]  {e['type']:<15} {e['details']}", 
                                 "valid" if e['count'] > 0 else "accent")

    def _switch_tab(self, name):
        if self._active_tab:
            self.pages[self._active_tab].pack_forget()
            self.tab_btns[self._active_tab].deactivate()
        self.pages[name].pack(fill="both", expand=True)
        self.tab_btns[name].activate()
        self._active_tab = name
        
        if name == "History":
            self._update_history_display()

        if hasattr(self, "_tab_indicator") and self._tab_indicator:
            self._tab_indicator.destroy()
        self._tab_indicator = tk.Frame(self.tab_bar, bg=ACCENT, height=2)
        self._tab_indicator.place(in_=self.tab_btns[name], relx=0, rely=1.0, relwidth=1.0, y=-2, anchor="sw")

    def _build_range_tab(self, page):
        tk.Label(page, text="Generate IMEIs Based on Pattern / Mask",
                 font=(FONT_UI, 14, "bold"), bg=BG, fg=TEXT).pack(anchor="w", pady=(10, 16))

        inp_card = RoundedCard(page, bg_color="card", border_color="border", radius=10, height=130)
        inp_card.pack(fill="x", pady=(0, 16))
        
        inp = tk.Frame(inp_card, bg=CARD)
        inp.place(relx=0.02, rely=0.5, anchor="w", relwidth=0.96)

        col1 = tk.Frame(inp, bg=CARD)
        col1.pack(side="left", padx=(10, 16))
        
        h1 = tk.Frame(col1, bg=CARD)
        h1.pack(anchor="w")
        tk.Label(h1, text="Samples / Mask", font=(FONT_UI, 9, "bold"), bg=CARD, fg=SUBTEXT).pack(side="left", pady=(0, 6))
        info_m = tk.Label(h1, text=" ⓘ", font=(FONT_UI, 9), bg=CARD, fg=ACCENT, cursor="hand2")
        info_m.pack(side="left", pady=(0, 6))
        ToolTip(info_m, "Enter two IMEIs to find their pattern,\nor use 'X' for random digits (e.g. 35693803XXXXXX).")

        self.rng_e1 = ModernEntry(col1, placeholder="Sample IMEI 1 or Mask", width=22)
        self.rng_e1.pack(pady=(0, 4))
        self.rng_e2 = ModernEntry(col1, placeholder="Sample IMEI 2 (Optional)", width=22)
        self.rng_e2.pack()

        col2 = tk.Frame(inp, bg=CARD)
        col2.pack(side="left", padx=(0, 16))
        tk.Label(col2, text="Count", font=(FONT_UI, 9, "bold"), bg=CARD, fg=SUBTEXT).pack(anchor="w", pady=(0, 6))
        self.rng_count = ModernEntry(col2, placeholder="10", width=8)
        self.rng_count.pack()

        col3 = tk.Frame(inp, bg=CARD)
        col3.pack(side="left")
        tk.Label(col3, text="Mode", font=(FONT_UI, 9, "bold"), bg=CARD, fg=SUBTEXT).pack(anchor="w", pady=(0, 6))
        self.rng_mode = tk.StringVar(value="random")
        rm_f = tk.Frame(col3, bg=CARD)
        rm_f.pack()
        tk.Radiobutton(rm_f, text="Random", variable=self.rng_mode, value="random", 
                       bg=CARD, fg=TEXT, activebackground=CARD, selectcolor=BORDER).pack(side="left")
        tk.Radiobutton(rm_f, text="Sequential", variable=self.rng_mode, value="sequential", 
                       bg=CARD, fg=TEXT, activebackground=CARD, selectcolor=BORDER).pack(side="left")

        btns = tk.Frame(page, bg=BG)
        btns.pack(anchor="w", pady=(4, 16))
        self.rng_gen_btn = GlowButton(btns, "⚡  Generate", command=self._gen_range,
                                      color=ACCENT, width=150)
        self.rng_gen_btn.pack(side="left", padx=(0, 12))
        GlowButton(btns, "✕  Clear", command=self._clear_range,
                   color=SUBTEXT, width=110).pack(side="left")

        row = tk.Frame(page, bg=BG)
        row.pack(fill="x", pady=(10, 8))
        tk.Label(row, text="Results", font=(FONT_UI, 11, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        self.rng_counter = tk.Label(row, text="", font=(FONT_UI, 10),
                                    bg=BG, fg=ACCENT2)
        self.rng_counter.pack(side="left", padx=12)
        
        btns_right = tk.Frame(row, bg=BG)
        btns_right.pack(side="right")
        
        GlowButton(btns_right, "⎘  Copy All", command=self._copy_range,
                   color=ACCENT2, width=120, height=32).pack(side="left", padx=(0, 12))
        GlowButton(btns_right, "💾  Export", command=lambda: self._export_results(self.rng_result),
                   color=SUCCESS, width=110, height=32).pack(side="left")

        self.rng_result = ResultBox(page, height=13)
        self.rng_result.pack(fill="both", expand=True)

    def _gen_range(self):
        val1, val2 = self.rng_e1.get().strip(), self.rng_e2.get().strip()
        mode = self.rng_mode.get()
        try:
            cnt = int(self.rng_count.get().strip() or "10")
            cnt = max(1, min(cnt, 1000))
        except ValueError:
            cnt = 10

        self.status.update("Generating...", ACCENT)
        self.rng_gen_btn.configure(state="disabled")

        def perform_gen():
            if 'X' in val1.upper():
                return generate_by_mask(val1, cnt, mode)
            elif val1 and val2:
                return generate_by_pattern(val1, val2, cnt, mode)
            elif val1:
                # Treat as TAC if 8 digits, or mask if shorter/longer (handled by mask logic)
                if len(val1) == 8 and val1.isdigit():
                    return tac_to_imei(val1, cnt, mode)
                return generate_by_mask(val1, cnt, mode)
            return "Please provide a mask or two IMEIs."

        def on_done(result):
            self.rng_gen_btn.configure(state="normal")
            if isinstance(result, str):
                self.rng_result.set_lines([f"  ✗  {result}"], "invalid")
                self.rng_counter.configure(text="")
                self.status.update(f"Error: {result}", ERROR)
            else:
                self.rng_result.clear()
                self.rng_result.append(f"  Mode: {mode.capitalize()} | Count: {len(result)}", "dim")
                self.rng_result.append("", )
                for idx, imei in enumerate(result, 1):
                    self.rng_result.append(f"  {idx:>3}.  {imei}", "valid")
                self.rng_counter.configure(text=f"{len(result)} IMEIs")
                self.status.update(f"Generated {len(result)} IMEIs.", SUCCESS)
                self.history.add("Generate", f"Pattern/Mask generation ({mode})", len(result))

        ThreadedTask(self, perform_gen, on_done).start()

    def _clear_range(self):
        self.rng_e1.clear(); self.rng_e2.clear()
        self.rng_result.clear(); self.rng_counter.configure(text="")
        self.status.update("Cleared.")

    def _copy_range(self):
        content = self.rng_result.text.get("1.0", "end")
        imeis = re.findall(r"\b\d{15}\b", content)
        if imeis:
            self.clipboard_clear(); self.clipboard_append("\n".join(imeis))
            self.status.update(f"Copied {len(imeis)} IMEIs.", ACCENT)

    def _build_tac_tab(self, page):
        tk.Label(page, text="Generate IMEIs from TAC",
                 font=(FONT_UI, 14, "bold"), bg=BG, fg=TEXT).pack(anchor="w", pady=(10, 16))

        inp_card = RoundedCard(page, bg_color="card", border_color="border", radius=10, height=90)
        inp_card.pack(fill="x", pady=(0, 12))
        
        inp = tk.Frame(inp_card, bg=CARD)
        inp.place(relx=0.02, rely=0.5, anchor="w", relwidth=0.96)

        col1 = tk.Frame(inp, bg=CARD)
        col1.pack(side="left", padx=(10, 16))
        
        h1 = tk.Frame(col1, bg=CARD)
        h1.pack(anchor="w")
        tk.Label(h1, text="TAC  (8 digits)", font=(FONT_UI, 9, "bold"), bg=CARD, fg=SUBTEXT).pack(side="left", pady=(0, 6))
        info_t = tk.Label(h1, text=" ⓘ", font=(FONT_UI, 9), bg=CARD, fg=ACCENT2, cursor="hand2")
        info_t.pack(side="left", pady=(0, 6))
        ToolTip(info_t, "Type Allocation Code (TAC) identifies the device model.\nIt is the first 8 digits of an IMEI.")

        self.tac_entry = ModernEntry(col1, placeholder="e.g. 35693803", width=18)
        self.tac_entry.pack()

        col2 = tk.Frame(inp, bg=CARD)
        col2.pack(side="left", padx=(0, 16))
        tk.Label(col2, text="Count", font=(FONT_UI, 9, "bold"), bg=CARD, fg=SUBTEXT).pack(anchor="w", pady=(0, 6))
        self.tac_count = ModernEntry(col2, placeholder="10", width=8)
        self.tac_count.pack()

        col3 = tk.Frame(inp, bg=CARD)
        col3.pack(side="left")
        tk.Label(col3, text="Mode", font=(FONT_UI, 9, "bold"), bg=CARD, fg=SUBTEXT).pack(anchor="w", pady=(0, 6))
        self.tac_mode = tk.StringVar(value="random")
        rm_f = tk.Frame(col3, bg=CARD)
        rm_f.pack()
        tk.Radiobutton(rm_f, text="Random", variable=self.tac_mode, value="random", 
                       bg=CARD, fg=TEXT, activebackground=CARD, selectcolor=BORDER).pack(side="left")
        tk.Radiobutton(rm_f, text="Sequential", variable=self.tac_mode, value="sequential", 
                       bg=CARD, fg=TEXT, activebackground=CARD, selectcolor=BORDER).pack(side="left")

        btns = tk.Frame(page, bg=BG)
        btns.pack(anchor="w", pady=(12, 16))
        self.tac_gen_btn = GlowButton(btns, "⚡  Generate", command=self._gen_tac,
                                      color=ACCENT2, width=150)
        self.tac_gen_btn.pack(side="left", padx=(0, 12))
        GlowButton(btns, "✕  Clear", command=self._clear_tac,
                   color=SUBTEXT, width=110).pack(side="left")

        row = tk.Frame(page, bg=BG)
        row.pack(fill="x", pady=(10, 8))
        tk.Label(row, text="Results", font=(FONT_UI, 11, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        self.tac_counter = tk.Label(row, text="", font=(FONT_UI, 10), bg=BG, fg=ACCENT2)
        self.tac_counter.pack(side="left", padx=12)

        btns_right = tk.Frame(row, bg=BG)
        btns_right.pack(side="right")

        GlowButton(btns_right, "⎘  Copy All", command=self._copy_tac,
                   color=ACCENT2, width=120, height=32).pack(side="left", padx=(0, 12))
        GlowButton(btns_right, "💾  Export", command=lambda: self._export_results(self.tac_result),
                   color=SUCCESS, width=110, height=32).pack(side="left")

        self.tac_result = ResultBox(page, height=13)
        self.tac_result.pack(fill="both", expand=True)

    def _gen_tac(self):
        tac = self.tac_entry.get().strip()
        mode = self.tac_mode.get()
        try:
            cnt = int(self.tac_count.get().strip() or "10")
            cnt = max(1, min(cnt, 1000))
        except ValueError:
            cnt = 10
        
        self.status.update("Generating...", ACCENT2)
        self.tac_gen_btn.configure(state="disabled")

        def on_done(result):
            self.tac_gen_btn.configure(state="normal")
            if isinstance(result, str):
                self.tac_result.set_lines([f"  ✗  {result}"], "invalid")
                self.tac_counter.configure(text="")
                self.status.update(f"Error: {result}", ERROR)
            else:
                self.tac_result.clear()
                self.tac_result.append(f"  TAC: {tac} | Mode: {mode.capitalize()}", "dim")
                self.tac_result.append("")
                for idx, imei in enumerate(result, 1):
                    self.tac_result.append(f"  {idx:>3}.  {imei}", "valid")
                self.tac_counter.configure(text=f"{len(result)} IMEIs")
                self.status.update(f"Generated {len(result)} IMEIs from TAC {tac}.", SUCCESS)
                self.history.add("Generate", f"TAC generation ({tac}, {mode})", len(result))

        ThreadedTask(self, lambda: tac_to_imei(tac, cnt, mode), on_done).start()

    def _clear_tac(self):
        self.tac_entry.clear()
        self.tac_result.clear(); self.tac_counter.configure(text="")
        self.status.update("Cleared.")

    def _copy_tac(self):
        content = self.tac_result.text.get("1.0", "end")
        imeis = re.findall(r"\b\d{15}\b", content)
        if imeis:
            self.clipboard_clear(); self.clipboard_append("\n".join(imeis))
            self.status.update(f"Copied {len(imeis)} IMEIs.", ACCENT)

    def _build_validator_tab(self, page):
        h_row = tk.Frame(page, bg=BG)
        h_row.pack(anchor="w", pady=(10, 4))
        tk.Label(h_row, text="Validate IMEIs (Luhn Check)",
                 font=(FONT_UI, 14, "bold"), bg=BG, fg=TEXT).pack(side="left")
        info_v = tk.Label(h_row, text=" ⓘ", font=(FONT_UI, 9), bg=BG, fg=ACCENT, cursor="hand2")
        info_v.pack(side="left", padx=6)
        ToolTip(info_v, "Luhn algorithm is a checksum formula used to validate identification numbers.\n"
                        "The 15th digit of an IMEI is the check digit.")

        tk.Label(page, text="Enter one IMEI per line, or paste a comma/space-separated list.",
                 font=(FONT_UI, 9), bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(0, 16))

        self.val_inp_frame = tk.Frame(page, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        self.val_inp_frame.pack(fill="x", pady=(0, 12))
        self.val_input = tk.Text(self.val_inp_frame, font=(FONT_MONO, 11), bg=CARD, fg=TEXT,
                                 insertbackground=ACCENT, relief="flat", bd=0,
                                 height=6, wrap="none", selectbackground=ACCENT2)
        self.val_sc = tk.Scrollbar(self.val_inp_frame, orient="vertical", command=self.val_input.yview,
                              bg=PANEL, troughcolor=CARD, width=10, relief="flat", bd=0)
        self.val_input.configure(yscrollcommand=self.val_sc.set)
        self.val_input.pack(side="left", fill="both", expand=True, padx=(12, 4), pady=12)
        self.val_sc.pack(side="right", fill="y", pady=12, padx=(0, 4))
        
        self.val_input.bind("<FocusIn>",  lambda e: self.val_inp_frame.configure(highlightbackground=ACCENT))
        self.val_input.bind("<FocusOut>", lambda e: self.val_inp_frame.configure(highlightbackground=BORDER))

        btns = tk.Frame(page, bg=BG)
        btns.pack(anchor="w", pady=(0, 16))
        self.val_btn = GlowButton(btns, "✔  Validate All", command=self._validate_all,
                                  color=ACCENT, width=160)
        self.val_btn.pack(side="left", padx=(0, 12))
        GlowButton(btns, "📂  Load File", command=self._load_file,
                   color=ACCENT2, width=140).pack(side="left", padx=(0, 12))
        GlowButton(btns, "✕  Clear", command=self._clear_val,
                   color=SUBTEXT, width=110).pack(side="left")
        GlowButton(btns, "💾  Export Valid", command=lambda: self._export_results(self.val_result, valid_only=True),
                   color=SUCCESS, width=150).pack(side="left", padx=(12, 0))

        stats = tk.Frame(page, bg=BG)
        stats.pack(fill="x", pady=(10, 12))
        self.val_total  = StatLabel(stats, "TOTAL",   TEXT)
        self.val_total.pack(side="left", padx=(0, 16))
        self.val_valid  = StatLabel(stats, "VALID",   SUCCESS)
        self.val_valid.pack(side="left", padx=(0, 16))
        self.val_invalid = StatLabel(stats, "INVALID", ERROR)
        self.val_invalid.pack(side="left", padx=(0, 16))
        self.val_dupes = StatLabel(stats, "DUPES", WARNING)
        self.val_dupes.pack(side="left", padx=(0, 16))

        self.val_result = ResultBox(page, height=13)
        self.val_result.pack(fill="both", expand=True)

    def _load_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")],
            title="Load IMEIs"
        )
        if file_path:
            try:
                with open(file_path, "r") as f:
                    if file_path.endswith(".csv"):
                        reader = csv.reader(f)
                        content = "\n".join(["".join(row) for row in reader])
                    else:
                        content = f.read()
                self.val_input.delete("1.0", "end")
                self.val_input.insert("1.0", content)
                self.status.update(f"Loaded file: {file_path.split('/')[-1]}", ACCENT2)
            except Exception as e:
                messagebox.showerror("Load Error", f"Could not read file: {e}")

    def _validate_all(self):
        raw = self.val_input.get("1.0", "end")
        tokens = re.split(r"[\n,\s]+", raw.strip())
        imeis = [t.strip() for t in tokens if t.strip()]
        if not imeis:
            self.status.update("No IMEIs entered.", WARNING)
            return

        self.status.update("Validating...", ACCENT)
        self.val_btn.configure(state="disabled")

        def perform_val():
            results = []
            seen = {}
            for imei in imeis:
                clean = imei.replace(" ", "").replace("-", "")
                ok, msg = validate_imei(clean)
                is_dupe = False
                if clean in seen:
                    seen[clean] += 1
                    is_dupe = True
                else:
                    seen[clean] = 1
                results.append((clean, ok, msg, is_dupe))
            return results

        def on_done(results):
            self.val_btn.configure(state="normal")
            self.val_result.clear()
            valid_c = invalid_c = dupe_c = 0
            for clean, ok, msg, is_dupe in results:
                tag = "valid" if ok else "invalid"
                prefix = "✓" if ok else "✗"
                dupe_str = " [DUPE]" if is_dupe else ""
                if is_dupe: dupe_c += 1
                
                self.val_result.append(f"  {prefix}  {clean:<17}  {msg}{dupe_str}", tag)
                if ok: valid_c += 1
                else: invalid_c += 1

            total = len(results)
            self.val_total.set(total)
            self.val_valid.set(valid_c)
            self.val_invalid.set(invalid_c)
            self.val_dupes.set(dupe_c)
            
            self.status.update(
                f"Validated {total} IMEIs — {valid_c} valid, {invalid_c} invalid, {dupe_c} duplicates.",
                SUCCESS if invalid_c == 0 else WARNING
            )
            self.history.add("Validate", f"Validated {total} IMEIs ({valid_c} valid)", total)

        ThreadedTask(self, perform_val, on_done).start()

    def _clear_val(self):
        self.val_input.delete("1.0", "end")
        self.val_result.clear()
        self.val_total.clear()
        self.val_valid.clear()
        self.val_invalid.clear()
        self.val_dupes.clear()
        self.status.update("Cleared.")


if __name__ == "__main__":
    app = IMEIApp()
    app.mainloop()
