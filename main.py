import tkinter as tk
from tkinter import messagebox, filedialog, ttk, font, simpledialog
import requests
import re
import os
import datetime
import math
import time
import random
import webbrowser
from PIL import Image, ImageDraw
import pyttsx3
from fpdf import FPDF

# --- COLOR PALETTES ---
PANTONE_COLORS = {
    "Black (Standard)": "#000000",
    "Classic Blue": "#0F4C81",
    "Living Coral": "#FF6F61",
    "Ultra Violet": "#5F4B8B",
    "Emerald": "#009473",
    "Marsala": "#955251",
    "White (Standard)": "#FFFFFF"
}

PAPER_COLORS = {
    "Classic White": "#FFFFFF",
    "Baby Blue": "#89CFF0",
    "Baby Pink": "#F4C2C2",
    "Pastel Yellow": "#FDFD96",
    "Earth Green": "#8F9779",
    "Soft Sand": "#E6D8C3"
}

# --- THEMES (from second version) ---
THEMES = {
    "Default": {"bg": "#F0EDE8", "text_bg": "#FFFFFF", "fg": "#000000", "accent": "#5F4B8B"},
    "MSN Classic": {"bg": "#E5E5E5", "text_bg": "#FFFFFF", "fg": "#000000", "accent": "#767676"},
    "Matrix": {"bg": "#000000", "text_bg": "#0A0A0A", "fg": "#00FF00", "accent": "#00FF00"},
    "Cyber Sunset": {"bg": "#1A0B2E", "text_bg": "#2D1B4E", "fg": "#FF71CE", "accent": "#01CDFE"}
}

# --- PIXEL ART & RETRO THEME ---
PIXEL_THEME_CONFIG = {
    "font": "Courier",
    "font_size": 12,
    "bg": "#000000",
    "fg": "#33FF33",
    "accent": "#00FF00",
    "canvas_bg": "#0A0A0A",
    "pixel_grid": 8        # grid cell size in pixels for snapped drawing
}


class PoetryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Poetry & Sketch Studio — Ultimate Edition")
        self.root.geometry("1300x860")
        self.root.option_add('*Font', 'Calibri 12')

        # --- STATE VARIABLES ---
        self.is_dark_mode = False
        self.current_theme_name = "Default"
        self.current_brush_color = "#000000"
        self.current_paper_color = "#FFFFFF"
        self.brush_size = 2
        self.is_eraser = False
        self.strokes = []
        self.redo_stack = []
        self.current_stroke = []

        self.version_history = []
        self.is_metronome_on = False
        self.bpm = 60
        self.start_time = None
        self.wpm_history = []

        self.mandala_mode = False
        self.is_pixel_mode = False
        self.is_pixel_brush = False

        try:
            self.tts_engine = pyttsx3.init()
        except Exception:
            self.tts_engine = None

        self.setup_ui()
        self.setup_drawing()
        self.track_wpm_loop()
        self.auto_save()
        self.night_cycle_loop()

    # =========================================================
    # UI SETUP
    # =========================================================

    def setup_ui(self):
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=THEMES[self.current_theme_name]["bg"])
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_left_panel()
        self._build_right_panel()
        self.setup_top_menu()

    def _build_left_panel(self):
        theme = THEMES[self.current_theme_name]
        self.left_frame = tk.Frame(self.main_paned, bg=theme["bg"])
        self.main_paned.add(self.left_frame, minsize=580)

        # 1. DICTIONARY & REFERENCE
        self.dict_frame = tk.LabelFrame(
            self.left_frame, text="Dictionary & Reference (Free API)",
            font=("Calibri", 12, "bold"), bg=theme["bg"]
        )
        self.dict_frame.pack(fill=tk.X, pady=(0, 6), ipady=4, padx=5)

        self.dict_search_frame = tk.Frame(self.dict_frame, bg=theme["bg"])
        self.dict_search_frame.pack(fill=tk.X, padx=10, pady=5)

        self.word_entry = ttk.Entry(self.dict_search_frame, width=22, font=("Calibri", 12))
        self.word_entry.pack(side=tk.LEFT, padx=(0, 8))
        self.word_entry.bind("<Return>", lambda e: self.search_word())

        tk.Button(self.dict_search_frame, text="Search Definition",
                  command=self.search_word, bg="#E6D8C3", font=("Calibri", 11)).pack(side=tk.LEFT, padx=2)

        # Dictionary links
        for d in ["Oxford", "Cambridge", "Merriam-Webster"]:
            tk.Button(self.dict_search_frame, text=d,
                      command=lambda n=d: self.open_dict(n),
                      font=("Calibri", 10)).pack(side=tk.LEFT, padx=2)

        self.dict_result_box = tk.Text(
            self.dict_frame, height=4, wrap=tk.WORD,
            font=("Calibri", 12), bg="#F8F9FA", state=tk.DISABLED
        )
        self.dict_result_box.pack(fill=tk.X, padx=10, pady=(4, 5))

        # 2. WRITING TOOLBAR
        self.text_toolbar = tk.Frame(self.left_frame, bg=theme["bg"])
        self.text_toolbar.pack(fill=tk.X, pady=2, padx=5)

        tk.Button(self.text_toolbar, text="▶ Read Aloud", command=self.read_aloud).pack(side=tk.LEFT, padx=2)
        tk.Button(self.text_toolbar, text="WPM Graph", command=self.show_wpm_graph).pack(side=tk.LEFT, padx=2)
        tk.Button(self.text_toolbar, text="Alliteration", command=self.highlight_alliteration).pack(side=tk.LEFT, padx=2)
        tk.Button(self.text_toolbar, text="Readability", command=self.calculate_readability).pack(side=tk.LEFT, padx=2)
        tk.Button(self.text_toolbar, text="Save Version", command=self.save_version).pack(side=tk.LEFT, padx=2)
        tk.Button(self.text_toolbar, text="History", command=self.show_version_history).pack(side=tk.LEFT, padx=2)

        self.font_family = tk.StringVar(value="Calibri")
        font_combo = ttk.Combobox(self.text_toolbar, textvariable=self.font_family,
                                  values=list(font.families()), width=14)
        font_combo.pack(side=tk.LEFT, padx=5)
        font_combo.bind("<<ComboboxSelected>>", self.update_font)

        self.font_size = tk.IntVar(value=14)
        size_spin = ttk.Spinbox(self.text_toolbar, from_=8, to=72,
                                textvariable=self.font_size, width=4, command=self.update_font)
        size_spin.pack(side=tk.LEFT, padx=2)

        # 3. STYLE & SENSORY TOOLBAR
        self.style_toolbar = tk.Frame(self.left_frame, bg=theme["bg"])
        self.style_toolbar.pack(fill=tk.X, pady=4, padx=5)

        tk.Label(self.style_toolbar, text="Paper:", bg=theme["bg"]).pack(side=tk.LEFT)
        self.paper_var = tk.StringVar(value="Classic White")
        paper_combo = ttk.Combobox(self.style_toolbar, textvariable=self.paper_var,
                                   values=list(PAPER_COLORS.keys()), width=12)
        paper_combo.pack(side=tk.LEFT, padx=4)
        paper_combo.bind("<<ComboboxSelected>>", self.change_paper_color)

        self.btn_dark = tk.Button(self.style_toolbar, text="Dark Mode",
                                  command=self.toggle_dark_mode, bg="#333333", fg="white")
        self.btn_dark.pack(side=tk.LEFT, padx=4)

        self.btn_metronome = tk.Button(self.style_toolbar, text="Metronome: OFF",
                                       command=self.toggle_metronome)
        self.btn_metronome.pack(side=tk.LEFT, padx=4)

        tk.Label(self.style_toolbar, text="Theme:", bg=theme["bg"]).pack(side=tk.LEFT, padx=(8, 0))
        self.theme_var = tk.StringVar(value="Default")
        theme_combo = ttk.Combobox(self.style_toolbar, textvariable=self.theme_var,
                                   values=list(THEMES.keys()), width=12)
        theme_combo.pack(side=tk.LEFT, padx=4)
        theme_combo.bind("<<ComboboxSelected>>", self.switch_theme)

        self.mandala_btn = tk.Button(self.style_toolbar, text="Mandala: OFF",
                                     command=self.toggle_mandala, bg="#009473", fg="white")
        self.mandala_btn.pack(side=tk.LEFT, padx=4)

        self.pixel_mode_btn = tk.Button(self.style_toolbar, text="Pixel Mode: OFF",
                                        command=self.toggle_pixel_mode, bg="#555555", fg="#33FF33",
                                        font=("Courier", 10, "bold"))
        self.pixel_mode_btn.pack(side=tk.LEFT, padx=4)

        # 4. MAIN TEXT AREA
        self.font_weight = "normal"
        self.text_area = tk.Text(
            self.left_frame, wrap=tk.WORD,
            font=(self.font_family.get(), self.font_size.get(), self.font_weight),
            undo=True, bg=self.current_paper_color, fg="#000000"
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=4, padx=5)
        self.text_area.bind("<KeyRelease>", self.on_key_release)

        # 5. STATUS BAR
        self.status_var = tk.StringVar(value="Words: 0 | WPM: 0 | Auto-Save: ON")
        self.status_bar = tk.Label(self.left_frame, textvariable=self.status_var,
                                   anchor=tk.W, font=("Calibri", 11), bg=theme["bg"])
        self.status_bar.pack(fill=tk.X, padx=5, pady=(0, 2))

    def _build_right_panel(self):
        theme = THEMES[self.current_theme_name]
        self.right_frame = tk.Frame(self.main_paned, bg=theme["bg"])
        self.main_paned.add(self.right_frame, minsize=450)

        tk.Label(self.right_frame, text="Sketch Canvas",
                 font=("Calibri", 16, "bold"), fg="#5F4B8B", bg=theme["bg"]).pack(pady=(0, 4))

        self.draw_toolbar = tk.Frame(self.right_frame, bg=theme["bg"])
        self.draw_toolbar.pack(fill=tk.X, pady=2)

        tk.Button(self.draw_toolbar, text="Undo", command=self.undo_stroke).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Eraser", command=self.toggle_eraser).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Clear", command=self.clear_canvas).pack(side=tk.LEFT, padx=2)
        self.pixel_brush_btn = tk.Button(self.draw_toolbar, text="Pixel Brush: OFF",
                                         command=self.toggle_pixel_brush,
                                         bg="#222222", fg="#33FF33", font=("Courier", 9))
        self.pixel_brush_btn.pack(side=tk.LEFT, padx=2)

        tk.Label(self.draw_toolbar, text="Size:", bg=theme["bg"]).pack(side=tk.LEFT, padx=(5, 0))
        self.brush_slider = ttk.Scale(self.draw_toolbar, from_=1, to=20,
                                      orient=tk.HORIZONTAL, length=80, command=self.change_brush_size)
        self.brush_slider.set(2)
        self.brush_slider.pack(side=tk.LEFT, padx=2)

        self.color_var = tk.StringVar(value="Black (Standard)")
        self.color_combo = ttk.Combobox(self.draw_toolbar, textvariable=self.color_var,
                                        values=list(PANTONE_COLORS.keys()), width=16)
        self.color_combo.pack(side=tk.LEFT, padx=5)
        self.color_combo.bind("<<ComboboxSelected>>", self.change_color)

        self.canvas = tk.Canvas(self.right_frame, bg="#FFFFFF", cursor="cross",
                                highlightbackground="gray", highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=4)

        self.image = Image.new("RGB", (900, 900), "#FFFFFF")
        self.draw_img = ImageDraw.Draw(self.image)

    def setup_top_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Text (.txt)", command=self.save_txt)
        file_menu.add_command(label="Export Text (.pdf)", command=self.export_pdf)
        file_menu.add_command(label="Export Canvas (.png)", command=self.save_sketch)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Highlight Alliteration", command=self.highlight_alliteration)
        tools_menu.add_command(label="Readability Score", command=self.calculate_readability)
        tools_menu.add_command(label="WPM Graph", command=self.show_wpm_graph)
        tools_menu.add_command(label="Version History", command=self.show_version_history)
        tools_menu.add_separator()
        tools_menu.add_command(label="Toggle Pixel Mode", command=self.toggle_pixel_mode)
        tools_menu.add_command(label="Toggle Pixel Brush", command=self.toggle_pixel_brush)

    # =========================================================
    # DICTIONARY
    # =========================================================

    def search_word(self):
        word = self.word_entry.get().strip()
        if not word:
            return

        self.dict_result_box.config(state=tk.NORMAL)
        self.dict_result_box.delete(1.0, tk.END)
        self.dict_result_box.insert(tk.END, "Searching…\n")
        self.dict_result_box.config(state=tk.DISABLED)
        self.root.update()

        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url, timeout=5)

            self.dict_result_box.config(state=tk.NORMAL)
            self.dict_result_box.delete(1.0, tk.END)

            if response.status_code == 200:
                data = response.json()
                entry = data[0]
                phonetic = entry.get("phonetic", "")
                meanings = entry.get("meanings", [])
                lines = [f"Word: {word.capitalize()}  {phonetic}"]
                for m in meanings[:2]:
                    pos = m.get("partOfSpeech", "")
                    defs = m.get("definitions", [])
                    if defs:
                        lines.append(f"[{pos}] {defs[0]['definition']}")
                        if defs[0].get("example"):
                            lines.append(f"  e.g. \u201c{defs[0]['example']}\u201d")
                self.dict_result_box.insert(tk.END, "\n".join(lines))
            else:
                self.dict_result_box.insert(tk.END, f"No definition found for '{word}'.")

            self.dict_result_box.config(state=tk.DISABLED)

        except Exception:
            self.dict_result_box.config(state=tk.NORMAL)
            self.dict_result_box.delete(1.0, tk.END)
            self.dict_result_box.insert(tk.END, "Error: Could not connect to dictionary server.")
            self.dict_result_box.config(state=tk.DISABLED)

    def open_dict(self, name):
        word = self.word_entry.get().strip()
        if not word:
            messagebox.showwarning("Dictionary", "Enter a word first.")
            return
        urls = {
            "Oxford": f"https://www.oxfordlearnersdictionaries.com/definition/english/{word}",
            "Cambridge": f"https://dictionary.cambridge.org/dictionary/english/{word}",
            "Merriam-Webster": f"https://www.merriam-webster.com/dictionary/{word}"
        }
        webbrowser.open(urls[name])

    # =========================================================
    # THEME & APPEARANCE
    # =========================================================

    def switch_theme(self, event=None):
        self.current_theme_name = self.theme_var.get()
        theme = THEMES[self.current_theme_name]
        self.text_area.config(bg=theme["text_bg"], fg=theme["fg"], insertbackground=theme["fg"])
        self.left_frame.config(bg=theme["bg"])
        self.right_frame.config(bg=theme["bg"])
        self.style_toolbar.config(bg=theme["bg"])
        self.text_toolbar.config(bg=theme["bg"])
        self.draw_toolbar.config(bg=theme["bg"])
        self.status_bar.config(bg=theme["bg"])
        # Update paper color accordingly unless Matrix/Cyber
        if self.current_theme_name not in ("Matrix", "Cyber Sunset"):
            self.current_paper_color = theme["text_bg"]

    def update_font(self, event=None):
        my_font = font.Font(family=self.font_family.get(),
                            size=self.font_size.get(), weight=self.font_weight)
        self.text_area.configure(font=my_font)

    def change_paper_color(self, event=None):
        if self.is_dark_mode:
            return
        color_hex = PAPER_COLORS.get(self.paper_var.get(), "#FFFFFF")
        self.current_paper_color = color_hex
        self.text_area.config(bg=self.current_paper_color)

    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.text_area.config(bg="#1E1E1E", fg="#FFFFFF", insertbackground="#FFFFFF")
            self.btn_dark.config(text="Light Mode", bg="#f4f1ea", fg="black")
        else:
            self.text_area.config(bg=self.current_paper_color, fg="#000000", insertbackground="#000000")
            self.btn_dark.config(text="Dark Mode", bg="#333333", fg="white")

    def toggle_mandala(self):
        self.mandala_mode = not self.mandala_mode
        state = "ON" if self.mandala_mode else "OFF"
        self.mandala_btn.config(text=f"Mandala: {state}",
                                bg="#FF6F61" if self.mandala_mode else "#009473")

    def toggle_pixel_mode(self):
        """Apply full retro pixel aesthetic to text area, canvas and status bar."""
        self.is_pixel_mode = not self.is_pixel_mode
        if self.is_pixel_mode:
            cfg = PIXEL_THEME_CONFIG
            self.root.option_add('*Font', f"{cfg['font']} {cfg['font_size']}")
            self.text_area.config(
                bg=cfg["bg"], fg=cfg["fg"],
                insertbackground=cfg["accent"],
                font=(cfg["font"], cfg["font_size"])
            )
            self.canvas.config(bg=cfg["canvas_bg"])
            self.status_bar.config(bg=cfg["bg"], fg=cfg["fg"])
            self.pixel_mode_btn.config(text="Pixel Mode: ON", bg="#33FF33", fg="#000000")
        else:
            # Restore defaults
            self.root.option_add('*Font', 'Calibri 12')
            self.text_area.config(
                bg=self.current_paper_color, fg="#000000",
                insertbackground="#000000",
                font=(self.font_family.get(), self.font_size.get())
            )
            self.canvas.config(bg="#FFFFFF")
            theme = THEMES[self.current_theme_name]
            self.status_bar.config(bg=theme["bg"], fg=theme["fg"] if theme["fg"] != "#FFFFFF" else "#000000")
            self.pixel_mode_btn.config(text="Pixel Mode: OFF", bg="#555555", fg="#33FF33")

    def toggle_pixel_brush(self):
        """Toggle grid-snapped pixel drawing on the canvas."""
        self.is_pixel_brush = not self.is_pixel_brush
        if self.is_pixel_brush:
            self.is_eraser = False  # pixel brush overrides eraser
            self.pixel_brush_btn.config(text="Pixel Brush: ON", bg="#33FF33", fg="#000000")
        else:
            self.pixel_brush_btn.config(text="Pixel Brush: OFF", bg="#222222", fg="#33FF33")

    def night_cycle_loop(self):
        """Auto dim text area at night."""
        hour = datetime.datetime.now().hour
        if 21 <= hour or hour < 6:
            if not self.is_dark_mode:
                self.text_area.config(bg="#1a1a2e", fg="#e0e0e0", insertbackground="#e0e0e0")
        else:
            if not self.is_dark_mode:
                self.text_area.config(bg=self.current_paper_color, fg="#000000",
                                      insertbackground="#000000")
        self.root.after(3_600_000, self.night_cycle_loop)

    # =========================================================
    # METRONOME
    # =========================================================

    def toggle_metronome(self):
        self.is_metronome_on = not self.is_metronome_on
        if self.is_metronome_on:
            bpm = simpledialog.askinteger("Metronome", "Enter BPM (30–240):",
                                          initialvalue=60, minvalue=30, maxvalue=240)
            if bpm:
                self.bpm = bpm
                self.btn_metronome.config(text=f"Metronome: {self.bpm} BPM", bg="#FF6F61")
                self.tick_metronome()
            else:
                self.is_metronome_on = False
                self.btn_metronome.config(text="Metronome: OFF", bg="SystemButtonFace")
        else:
            self.btn_metronome.config(text="Metronome: OFF", bg="SystemButtonFace")

    def tick_metronome(self):
        if self.is_metronome_on:
            self.root.bell()
            self.root.after(int((60 / self.bpm) * 1000), self.tick_metronome)

    # =========================================================
    # WRITING ANALYSIS TOOLS
    # =========================================================

    def read_aloud(self):
        if not self.tts_engine:
            messagebox.showwarning("TTS", "Text-to-speech engine not available.")
            return
        text = self.text_area.get(1.0, tk.END).strip()
        if not text:
            return
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def highlight_alliteration(self):
        """Highlight consecutive words starting with the same letter."""
        self.text_area.tag_config("alliteration", background="#FFF2A8", foreground="#000000")
        self.text_area.tag_remove("alliteration", "1.0", tk.END)

        full_text = self.text_area.get(1.0, tk.END)
        words = list(re.finditer(r'\b([a-zA-Z]\w*)', full_text))

        i = 0
        while i < len(words) - 1:
            if words[i].group(1)[0].lower() == words[i + 1].group(1)[0].lower():
                start = f"1.0+{words[i].start()}c"
                end = f"1.0+{words[i + 1].end()}c"
                self.text_area.tag_add("alliteration", start, end)
            i += 1

    def calculate_readability(self):
        """Flesch Reading Ease score."""
        text = self.text_area.get(1.0, tk.END).strip()
        if not text:
            messagebox.showinfo("Readability", "Nothing to analyse yet.")
            return

        sentences = max(len(re.findall(r'[.!?]+', text)), 1)
        words_list = re.findall(r'\b\w+\b', text)
        words = max(len(words_list), 1)
        # Syllable approximation
        syllables = sum(
            max(1, len(re.findall(r'[aeiouAEIOU]', w)) - (1 if w.endswith('e') else 0))
            for w in words_list
        )

        fre = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        fre = max(0.0, min(100.0, fre))

        if fre >= 70:
            label = "Easy to read"
        elif fre >= 50:
            label = "Fairly difficult"
        else:
            label = "Difficult / academic"

        messagebox.showinfo(
            "Readability — Flesch Reading Ease",
            f"Score: {fre:.1f} / 100\n{label}\n\n"
            f"Words: {words}  |  Sentences: {sentences}  |  Syllables: {syllables}"
        )

    def save_version(self):
        snapshot = self.text_area.get(1.0, tk.END).strip()
        if snapshot:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.version_history.append((ts, snapshot))
            messagebox.showinfo("Version Saved", f"Version saved at {ts}.")

    def show_version_history(self):
        if not self.version_history:
            messagebox.showinfo("History", "No saved versions yet.\nUse 'Save Version' to snapshot your work.")
            return
        win = tk.Toplevel(self.root)
        win.title("Version History")
        win.geometry("600x400")
        listbox = tk.Listbox(win, font=("Calibri", 12), width=20)
        listbox.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        preview = tk.Text(win, wrap=tk.WORD, font=("Calibri", 12), state=tk.DISABLED)
        preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        for ts, _ in self.version_history:
            listbox.insert(tk.END, ts)

        def on_select(event):
            idx = listbox.curselection()
            if idx:
                _, text = self.version_history[idx[0]]
                preview.config(state=tk.NORMAL)
                preview.delete(1.0, tk.END)
                preview.insert(tk.END, text)
                preview.config(state=tk.DISABLED)

        def restore_version():
            idx = listbox.curselection()
            if idx:
                _, text = self.version_history[idx[0]]
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(1.0, text)
                win.destroy()

        listbox.bind("<<ListboxSelect>>", on_select)
        tk.Button(win, text="Restore Selected", command=restore_version,
                  bg="#5F4B8B", fg="white", font=("Calibri", 11)).pack(side=tk.BOTTOM, pady=5)

    # =========================================================
    # WPM TRACKING
    # =========================================================

    def on_key_release(self, event):
        if not self.start_time:
            self.start_time = time.time()
        text = self.text_area.get(1.0, tk.END).strip()
        words = len(text.split()) if text else 0
        elapsed_minutes = (time.time() - self.start_time) / 60.0 if self.start_time else 0.01
        current_wpm = int(words / elapsed_minutes) if elapsed_minutes > 0 else 0
        self.status_var.set(f"Words: {words} | WPM: {current_wpm} | Auto-Save: ON")

    def track_wpm_loop(self):
        if self.start_time:
            text = self.text_area.get(1.0, tk.END).strip()
            words = len(text.split())
            elapsed_minutes = (time.time() - self.start_time) / 60.0
            current_wpm = int(words / elapsed_minutes) if elapsed_minutes > 0.1 else 0
            self.wpm_history.append(current_wpm)
        self.root.after(10_000, self.track_wpm_loop)

    def show_wpm_graph(self):
        if not self.wpm_history:
            messagebox.showinfo("WPM Graph", "Keep writing to generate data!")
            return
        win = tk.Toplevel(self.root)
        win.title("WPM Over Time")
        win.geometry("520x320")
        g_canvas = tk.Canvas(win, bg="white")
        g_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        w, h = 500, 280
        max_wpm = max(max(self.wpm_history), 50)
        pts = len(self.wpm_history)

        g_canvas.create_line(30, 0, 30, h, fill="#cccccc")
        g_canvas.create_line(30, h, w, h, fill="#cccccc")

        for i in range(pts - 1):
            x1 = 30 + (i / pts) * (w - 30)
            y1 = h - (self.wpm_history[i] / max_wpm) * (h - 20)
            x2 = 30 + ((i + 1) / pts) * (w - 30)
            y2 = h - (self.wpm_history[i + 1] / max_wpm) * (h - 20)
            g_canvas.create_line(x1, y1, x2, y2, fill="#5F4B8B", width=2)
            g_canvas.create_oval(x2 - 4, y2 - 4, x2 + 4, y2 + 4, fill="#FF6F61", outline="")

    # =========================================================
    # DRAWING
    # =========================================================

    def setup_drawing(self):
        self.old_x, self.old_y = None, None
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)

    def change_brush_size(self, val):
        self.brush_size = int(float(val))

    def toggle_eraser(self):
        self.is_eraser = True

    def change_color(self, event=None):
        self.current_brush_color = PANTONE_COLORS.get(self.color_var.get(), "#000000")
        self.is_eraser = False

    def start_draw(self, event):
        self.old_x, self.old_y = event.x, event.y
        self.current_stroke = []

    def draw(self, event):
        if self.old_x is None or self.old_y is None:
            return
        color = "#FFFFFF" if self.is_eraser else self.current_brush_color

        # Snap coordinates to pixel grid if pixel brush is active
        ex, ey = event.x, event.y
        ox, oy = self.old_x, self.old_y
        if self.is_pixel_brush:
            g = PIXEL_THEME_CONFIG["pixel_grid"]
            ex = (ex // g) * g
            ey = (ey // g) * g
            ox = (ox // g) * g
            oy = (oy // g) * g
            # Draw a filled square at the snapped position
            size = max(g, self.brush_size)
            rect_id = self.canvas.create_rectangle(
                ex, ey, ex + size, ey + size,
                fill=color, outline=""
            )
            self.current_stroke.append(rect_id)
            self.draw_img.rectangle([ex, ey, ex + size, ey + size], fill=color)
            self.old_x, self.old_y = ex, ey
            return

        if self.mandala_mode:
            cx = self.canvas.winfo_width() // 2
            cy = self.canvas.winfo_height() // 2
            dx, dy = event.x - cx, event.y - cy
            for i in range(8):
                angle = math.radians(i * 45)
                rx = cx + dx * math.cos(angle) - dy * math.sin(angle)
                ry = cy + dx * math.sin(angle) + dy * math.cos(angle)
                ox = cx + (self.old_x - cx) * math.cos(angle) - (self.old_y - cy) * math.sin(angle)
                oy = cy + (self.old_x - cx) * math.sin(angle) + (self.old_y - cy) * math.cos(angle)
                lid = self.canvas.create_line(ox, oy, rx, ry, width=self.brush_size,
                                              fill=color, capstyle=tk.ROUND)
                self.current_stroke.append(lid)
                self.draw_img.line([ox, oy, rx, ry], fill=color, width=self.brush_size)
        else:
            lid = self.canvas.create_line(self.old_x, self.old_y, event.x, event.y,
                                          width=self.brush_size, fill=color, capstyle=tk.ROUND)
            self.current_stroke.append(lid)
            self.draw_img.line([self.old_x, self.old_y, event.x, event.y],
                               fill=color, width=self.brush_size)

        self.old_x, self.old_y = event.x, event.y

    def stop_draw(self, event):
        if self.current_stroke:
            self.strokes.append(self.current_stroke)
            self.redo_stack.clear()
        self.old_x, self.old_y = None, None

    def undo_stroke(self):
        if self.strokes:
            stroke = self.strokes.pop()
            self.redo_stack.append(stroke)
            for line_id in stroke:
                self.canvas.itemconfig(line_id, state="hidden")

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (900, 900), "#FFFFFF")
        self.draw_img = ImageDraw.Draw(self.image)

    # =========================================================
    # FILE & EXPORT
    # =========================================================

    def auto_save(self):
        try:
            with open("autosave_backup.txt", "w", encoding="utf-8") as f:
                f.write(self.text_area.get(1.0, tk.END))
        except Exception:
            pass
        self.root.after(60_000, self.auto_save)

    def save_txt(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text_area.get(1.0, tk.END))
            messagebox.showinfo("Saved", f"Text saved to:\n{path}")

    def save_sketch(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG Image", "*.png"), ("All files", "*.*")]
        )
        if path:
            self.image.save(path)
            messagebox.showinfo("Saved", f"Canvas saved to:\n{path}")

    def export_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            raw_text = self.text_area.get(1.0, tk.END)
            # Safe encode for latin-1 based FPDF
            text = raw_text.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 10, text)
            pdf.output(path)
            messagebox.showinfo("Exported", f"PDF saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = PoetryApp(root)
    root.mainloop()
