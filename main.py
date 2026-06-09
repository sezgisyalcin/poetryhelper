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

# --- THEMES & PALETTES ---
THEMES = {
    "MSN Classic": {"bg": "#E5E5E5", "text_bg": "#FFFFFF", "fg": "#000000", "accent": "#767676"},
    "Matrix": {"bg": "#000000", "text_bg": "#000000", "fg": "#00FF00", "accent": "#00FF00"},
    "Cyber Sunset": {"bg": "#1A0B2E", "text_bg": "#2D1B4E", "fg": "#FF71CE", "accent": "#01CDFE"},
    "Paper Pastel": {"bg": "#FDF6E3", "text_bg": "#FEFBF0", "fg": "#5B4636", "accent": "#B58900"}
}

PANTONE_COLORS = {"Black": "#000000", "Blue": "#0F4C81", "Coral": "#FF6F61", "Violet": "#5F4B8B", "Emerald": "#009473"}
COLORBLIND_SAFE_COLORS = {"Black": "#000000", "Orange": "#E69F00", "Sky Blue": "#56B4E9", "Vermilion": "#D55E00"}

class PoetryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Poetry Studio Evolution")
        self.root.geometry("1300x850")
        self.root.option_add('*Font', 'Calibri 12')
        
        self.theme = THEMES["MSN Classic"]
        self.is_dark_mode = False
        self.mandala_mode = False
        self.bio_feedback = False
        self.strokes = []
        self.redo_stack = []
        self.version_history = []
        self.favorites = []
        
        try: self.tts_engine = pyttsx3.init()
        except: self.tts_engine = None
        
        self.setup_ui()
        self.setup_drawing()
        self.track_wpm_loop()
        self.night_cycle_loop()

    def setup_ui(self):
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.theme["bg"])
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # LEFT PANEL
        self.left_frame = tk.Frame(self.main_paned, bg=self.theme["bg"])
        self.main_paned.add(self.left_frame, minsize=600)

        # Dictionary & Tools
        self.dict_frame = tk.LabelFrame(self.left_frame, text="Tools & Dictionaries", bg=self.theme["bg"])
        self.dict_frame.pack(fill=tk.X, padx=5)
        
        self.word_entry = ttk.Entry(self.dict_frame, width=15)
        self.word_entry.pack(side=tk.LEFT, padx=5)
        for d in ["Oxford", "Cambridge", "Merriam-Webster"]:
            tk.Button(self.dict_frame, text=d, command=lambda n=d: self.open_dict(n)).pack(side=tk.LEFT)
        
        tk.Button(self.dict_frame, text="Highlight Alliteration", command=self.highlight_alliteration).pack(side=tk.LEFT, padx=5)
        tk.Button(self.dict_frame, text="Theme Switcher", command=self.switch_theme).pack(side=tk.LEFT)

        # Text Area
        self.text_area = tk.Text(self.left_frame, font=("Calibri", 14), undo=True, bg=self.theme["text_bg"], fg=self.theme["fg"])
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # RIGHT PANEL
        self.right_frame = tk.Frame(self.main_paned, bg=self.theme["bg"])
        self.main_paned.add(self.right_frame, minsize=450)
        
        tk.Label(self.right_frame, text="Sketch Canvas", bg=self.theme["bg"]).pack()
        self.canvas = tk.Canvas(self.right_frame, bg="white", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Menu Bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export PDF", command=self.export_pdf)
        file_menu.add_command(label="Show History", command=self.show_versions)

    def switch_theme(self):
        theme_names = list(THEMES.keys())
        current = theme_names.index(next(k for k, v in THEMES.items() if v == self.theme))
        self.theme = THEMES[theme_names[(current + 1) % len(theme_names)]]
        self.left_frame.config(bg=self.theme["bg"])
        self.text_area.config(bg=self.theme["text_bg"], fg=self.theme["fg"])

    def night_cycle_loop(self):
        hour = datetime.datetime.now().hour
        if hour >= 20 or hour <= 6: self.text_area.config(bg="#1a1a1a", fg="#cccccc")
        self.root.after(3600000, self.night_cycle_loop)

    def highlight_alliteration(self):
        self.text_area.tag_config("alliteration", background="#FFF2A8")
        # Aliterasyon mantığı...

    def open_dict(self, name):
        word = self.word_entry.get().strip()
        urls = {"Oxford": f"https://www.oxfordlearnersdictionaries.com/definition/english/{word}", 
                "Cambridge": f"https://dictionary.cambridge.org/dictionary/english/{word}",
                "Merriam-Webster": f"https://www.merriam-webster.com/dictionary/{word}"}
        if word: webbrowser.open(urls[name])

    def setup_drawing(self):
        self.canvas.bind('<B1-Motion>', self.draw)

    def draw(self, event):
        self.canvas.create_oval(event.x, event.y, event.x+2, event.y+2, fill="black")

    def export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if path:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, self.text_area.get(1.0, tk.END).encode('latin-1', 'replace').decode('latin-1'))
            pdf.output(path)

    def show_versions(self):
        messagebox.showinfo("History", "Version history logged.")

    def track_wpm_loop(self):
        self.root.after(10000, self.track_wpm_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = PoetryApp(root)
    root.mainloop()
