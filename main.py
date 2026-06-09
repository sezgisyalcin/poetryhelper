import tkinter as tk
from tkinter import messagebox, filedialog, ttk, font, simpledialog
import requests
import re
import os
import datetime
import math
import time
import random
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

class PoetryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Poetry & Sketch Studio - Pro Edition")
        self.root.geometry("1200x850")
        
        # --- GLOBAL UI FONT SETTING ---
        self.root.option_add('*Font', 'Calibri 12')
        
        # --- STATE VARIABLES ---
        self.is_dark_mode = False
        self.current_brush_color = "#000000"
        self.current_bg_color = "#FFFFFF"
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
        
        try:
            self.tts_engine = pyttsx3.init()
        except:
            self.tts_engine = None

        self.setup_ui()
        self.setup_drawing()
        self.track_wpm_loop()
        self.auto_save()

    def setup_ui(self):
        # --- MAIN LAYOUT ---
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ==========================================
        # --- LEFT PANEL (WRITING & TOOLS) ---
        # ==========================================
        self.left_frame = tk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, minsize=550)

        # 1. DICTIONARY & REFERENCE BOX
        self.dict_frame = tk.LabelFrame(self.left_frame, text="Dictionary & Reference (Oxford/Wiktionary Data)", font=("Calibri", 12, "bold"))
        self.dict_frame.pack(fill=tk.X, pady=(0, 10), ipady=5, padx=5)
        
        self.dict_search_frame = tk.Frame(self.dict_frame)
        self.dict_search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.word_entry = ttk.Entry(self.dict_search_frame, width=25, font=("Calibri", 12))
        self.word_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(self.dict_search_frame, text="Search Definition", command=self.search_word, bg="#E6D8C3", font=("Calibri", 11)).pack(side=tk.LEFT)
        
        # Result Box for Dictionary
        self.dict_result_box = tk.Text(self.dict_frame, height=5, wrap=tk.WORD, font=("Calibri", 12), bg="#F8F9FA", state=tk.DISABLED)
        self.dict_result_box.pack(fill=tk.X, padx=10, pady=(5, 5))

        # 2. WRITING TOOLBAR
        self.text_toolbar = tk.Frame(self.left_frame)
        self.text_toolbar.pack(fill=tk.X, pady=2, padx=5)

        tk.Button(self.text_toolbar, text="Read Aloud", command=self.read_aloud).pack(side=tk.LEFT, padx=2)
        tk.Button(self.text_toolbar, text="Show WPM Graph", command=self.show_wpm_graph).pack(side=tk.LEFT, padx=2)
        
        self.font_family = tk.StringVar(value="Calibri")
        font_combo = ttk.Combobox(self.text_toolbar, textvariable=self.font_family, values=list(font.families()), width=15)
        font_combo.pack(side=tk.LEFT, padx=5)
        font_combo.bind("<<ComboboxSelected>>", self.update_font)
        
        self.font_size = tk.IntVar(value=14)
        size_spin = ttk.Spinbox(self.text_toolbar, from_=8, to=72, textvariable=self.font_size, width=4, command=self.update_font)
        size_spin.pack(side=tk.LEFT, padx=2)

        # 3. STYLE & SENSORY TOOLBAR
        self.style_toolbar = tk.Frame(self.left_frame)
        self.style_toolbar.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(self.style_toolbar, text="Paper Color:").pack(side=tk.LEFT)
        self.paper_var = tk.StringVar(value="Classic White")
        paper_combo = ttk.Combobox(self.style_toolbar, textvariable=self.paper_var, values=list(PAPER_COLORS.keys()), width=12)
        paper_combo.pack(side=tk.LEFT, padx=5)
        paper_combo.bind("<<ComboboxSelected>>", self.change_paper_color)

        self.btn_dark = tk.Button(self.style_toolbar, text="Dark Mode", command=self.toggle_dark_mode, bg="#333333", fg="white")
        self.btn_dark.pack(side=tk.LEFT, padx=5)
        
        self.btn_metronome = tk.Button(self.style_toolbar, text="Metronome: OFF", command=self.toggle_metronome)
        self.btn_metronome.pack(side=tk.LEFT, padx=5)

        # 4. MAIN TEXT AREA
        self.font_weight = "normal"
        self.text_area = tk.Text(self.left_frame, wrap=tk.WORD, font=(self.font_family.get(), self.font_size.get(), self.font_weight), undo=True, bg=self.current_paper_color)
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        self.text_area.bind("<KeyRelease>", self.on_key_release)

        # 5. STATUS BAR
        self.status_var = tk.StringVar()
        self.status_var.set("Words: 0 | WPM: 0 | Auto-Save: ON")
        self.status_bar = tk.Label(self.left_frame, textvariable=self.status_var, anchor=tk.W, font=("Calibri", 11))
        self.status_bar.pack(fill=tk.X, padx=5)

        # ==========================================
        # --- RIGHT PANEL (SKETCH CANVAS) ---
        # ==========================================
        self.right_frame = tk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, minsize=450)

        tk.Label(self.right_frame, text="Sketch Canvas", font=("Calibri", 16, "bold"), fg="#5F4B8B").pack(pady=(0, 5))

        self.draw_toolbar = tk.Frame(self.right_frame)
        self.draw_toolbar.pack(fill=tk.X, pady=2)

        tk.Button(self.draw_toolbar, text="Undo", command=self.undo_stroke).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Eraser", command=self.toggle_eraser).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Clear", command=self.clear_canvas).pack(side=tk.LEFT, padx=2)

        tk.Label(self.draw_toolbar, text="Size:").pack(side=tk.LEFT, padx=(5,0))
        self.brush_slider = ttk.Scale(self.draw_toolbar, from_=1, to=10, orient=tk.HORIZONTAL, length=80, command=self.change_brush_size)
        self.brush_slider.set(2)
        self.brush_slider.pack(side=tk.LEFT, padx=2)

        self.color_var = tk.StringVar(value="Black (Standard)")
        self.color_combo = ttk.Combobox(self.draw_toolbar, textvariable=self.color_var, values=list(PANTONE_COLORS.keys()), width=15)
        self.color_combo.pack(side=tk.LEFT, padx=5)
        self.color_combo.bind("<<ComboboxSelected>>", self.change_color)
        
        self.canvas = tk.Canvas(self.right_frame, bg="#FFFFFF", cursor="cross", highlightbackground="gray", highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.image = Image.new("RGB", (800, 800), "#FFFFFF")
        self.draw_img = ImageDraw.Draw(self.image)

        self.setup_top_menu()

    def setup_top_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Text (TXT)", command=self.save_txt)
        file_menu.add_command(label="Export Text (PDF)", command=self.export_pdf)
        file_menu.add_command(label="Export Canvas (PNG)", command=self.save_sketch)

    # --- DICTIONARY FETCH METHOD ---
    def search_word(self):
        word = self.word_entry.get().strip()
        if not word: return
        
        self.dict_result_box.config(state=tk.NORMAL)
        self.dict_result_box.delete(1.0, tk.END)
        self.dict_result_box.insert(tk.END, "Searching...\n")
        self.dict_result_box.config(state=tk.DISABLED)
        self.root.update()

        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url)
            
            self.dict_result_box.config(state=tk.NORMAL)
            self.dict_result_box.delete(1.0, tk.END)
            
            if response.status_code == 200:
                data = response.json()
                definition = data[0]['meanings'][0]['definitions'][0]['definition']
                phonetic = data[0].get('phonetic', '')
                
                result_text = f"Word: {word.capitalize()}  {phonetic}\nDefinition: {definition}"
                self.dict_result_box.insert(tk.END, result_text)
            else:
                self.dict_result_box.insert(tk.END, f"Could not find definition for '{word}'.")
                
            self.dict_result_box.config(state=tk.DISABLED)
        except Exception as e:
            self.dict_result_box.config(state=tk.NORMAL)
            self.dict_result_box.delete(1.0, tk.END)
            self.dict_result_box.insert(tk.END, "Error connecting to the dictionary server.")
            self.dict_result_box.config(state=tk.DISABLED)

    # --- UI & STYLE METHODS ---
    def update_font(self, event=None):
        my_font = font.Font(family=self.font_family.get(), size=self.font_size.get(), weight=self.font_weight)
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
            bg_color, fg_color = "#1E1E1E", "#FFFFFF"
            self.btn_dark.config(text="Light Mode", bg="#f4f1ea", fg="black")
        else:
            bg_color, fg_color = self.current_paper_color, "#000000"
            self.btn_dark.config(text="Dark Mode", bg="#333333", fg="white")
            
        self.text_area.config(bg=bg_color, fg=fg_color, insertbackground=fg_color)
        
    def toggle_metronome(self):
        self.is_metronome_on = not self.is_metronome_on
        if self.is_metronome_on:
            self.bpm = simpledialog.askinteger("Metronome", "Enter BPM (e.g. 60):", initialvalue=60, minvalue=30, maxvalue=240)
            if self.bpm: 
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
            self.root.after(int((60/self.bpm)*1000), self.tick_metronome)

    def read_aloud(self):
        if not self.tts_engine: return
        text = self.text_area.get(1.0, tk.END)
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    # --- TRACKING METHODS ---
    def on_key_release(self, event):
        if not self.start_time: self.start_time = time.time()
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
        self.root.after(10000, self.track_wpm_loop)

    def show_wpm_graph(self):
        if not self.wpm_history:
            messagebox.showinfo("Graph", "Keep writing to generate data!")
            return
        win = tk.Toplevel(self.root)
        win.title("WPM Graph")
        win.geometry("500x300")
        g_canvas = tk.Canvas(win, bg="white")
        g_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        w, h, max_wpm, pts = 480, 280, max(max(self.wpm_history), 50), len(self.wpm_history)
        for i in range(pts - 1):
            x1, y1 = (i/pts)*w, h - (self.wpm_history[i]/max_wpm)*h
            x2, y2 = ((i+1)/pts)*w, h - (self.wpm_history[i+1]/max_wpm)*h
            g_canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)
            g_canvas.create_oval(x2-3, y2-3, x2+3, y2+3, fill="red")

    # --- DRAWING METHODS ---
    def setup_drawing(self):
        self.old_x, self.old_y = None, None
        self.canvas.bind('<Button-1>', self.start_draw)
        self.canvas.bind('<B1-Motion>', self.draw)
        self.canvas.bind('<ButtonRelease-1>', self.stop_draw)

    def change_brush_size(self, val): self.brush_size = int(float(val))
    def toggle_eraser(self): self.is_eraser = True

    def change_color(self, event=None):
        self.current_brush_color = PANTONE_COLORS.get(self.color_var.get(), "#000000")
        self.is_eraser = False

    def start_draw(self, event):
        self.old_x, self.old_y = event.x, event.y
        self.current_stroke = []

    def draw(self, event):
        if self.old_x and self.old_y:
            color = "#FFFFFF" if self.is_eraser else self.current_brush_color
            line_id = self.canvas.create_line(self.old_x, self.old_y, event.x, event.y, width=self.brush_size, fill=color, capstyle=tk.ROUND)
            self.current_stroke.append(line_id)
            self.draw_img.line([self.old_x, self.old_y, event.x, event.y], fill=color, width=self.brush_size)
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
            for line_id in stroke: self.canvas.itemconfig(line_id, state='hidden')

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (800, 800), "#FFFFFF")
        self.draw_img = ImageDraw.Draw(self.image)

    # --- UTILITY & FILE METHODS ---
    def auto_save(self):
        try:
            with open("autosave_backup.txt", "w", encoding="utf-8") as f:
                f.write(self.text_area.get(1.0, tk.END))
        except: pass
        self.root.after(60000, self.auto_save)

    def save_txt(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w", encoding="utf-8") as f: f.write(self.text_area.get(1.0, tk.END))

    def save_sketch(self):
        path = filedialog.asksaveasfilename(defaultextension=".png")
        if path: self.image.save(path)

    def export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            text = self.text_area.get(1.0, tk.END).encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, text)
            pdf.output(path)
            messagebox.showinfo("Success", "Exported to PDF!")

if __name__ == "__main__":
    root = tk.Tk()
    app = PoetryApp(root)
    root.mainloop()
