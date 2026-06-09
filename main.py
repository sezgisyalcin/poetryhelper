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

COLORBLIND_SAFE_COLORS = {
    "Black": "#000000",
    "Orange": "#E69F00",
    "Sky Blue": "#56B4E9",
    "Bluish Green": "#009E73",
    "Yellow": "#F0E442",
    "Blue": "#0072B2",
    "Vermilion": "#D55E00",
    "Reddish Purple": "#CC79A7",
    "White": "#FFFFFF"
}

class PoetryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Poetry & Sketch Studio - The Ultimate Edition")
        self.root.geometry("1200x800")
        
        # --- STATE VARIABLES ---
        self.is_dark_mode = False
        self.current_brush_color = "#000000"
        self.current_bg_color = "#FFFFFF"
        self.brush_size = 2
        self.is_eraser = False
        self.strokes = []
        self.redo_stack = []
        self.current_stroke = []
        
        # Pro Features
        self.version_history = []
        self.favorites = []
        self.is_metronome_on = False
        self.bpm = 60
        
        # Sensory Features
        self.mandala_mode = False
        self.mandala_axes = 8
        self.colorblind_mode = False
        self.mech_sounds = False
        self.bio_feedback = False
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
        # --- MENU BAR ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save as TXT", command=self.save_txt)
        file_menu.add_command(label="Export to PDF", command=self.export_pdf)
        file_menu.add_command(label="Export Sketch (PNG)", command=self.save_sketch)
        file_menu.add_separator()
        file_menu.add_command(label="View Version History", command=self.show_versions)
        file_menu.add_command(label="Add to Favorites", command=self.add_favorite)
        
        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Writing Tools", menu=tool_menu)
        tool_menu.add_command(label="Read Aloud (TTS)", command=self.read_aloud)
        tool_menu.add_command(label="Toggle Metronome", command=self.toggle_metronome)
        tool_menu.add_command(label="Insert Date/Time Stamp", command=self.insert_timestamp)
        tool_menu.add_command(label="Toggle Dark Mode", command=self.toggle_dark_mode)

        sensory_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sensory & Graph", menu=sensory_menu)
        sensory_menu.add_command(label="Show WPM Graph", command=self.show_wpm_graph)
        sensory_menu.add_checkbutton(label="Mandala Mode (Symmetry)", command=self.toggle_mandala)
        sensory_menu.add_checkbutton(label="Colorblind Helper Palette", command=self.toggle_colorblind_palette)
        sensory_menu.add_checkbutton(label="Mech Keyboard Sounds", command=self.toggle_sounds)
        sensory_menu.add_checkbutton(label="Bio-feedback Sync (Simulated)", command=self.toggle_biofeedback)

        # --- MAIN LAYOUT ---
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- LEFT PANEL ---
        self.left_frame = tk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, minsize=500)

        self.text_toolbar = tk.Frame(self.left_frame)
        self.text_toolbar.pack(fill=tk.X, pady=2)

        tk.Button(self.text_toolbar, text="Highlight Alliteration", command=self.highlight_alliteration).pack(side=tk.LEFT, padx=2)
        tk.Button(self.text_toolbar, text="Readability Score", command=self.calculate_readability).pack(side=tk.LEFT, padx=2)

        self.font_family = tk.StringVar(value="Georgia")
        self.font_size = tk.IntVar(value=14)
        self.font_weight = "normal"
        
        font_combo = ttk.Combobox(self.text_toolbar, textvariable=self.font_family, values=list(font.families()), width=15)
        font_combo.pack(side=tk.LEFT, padx=2)
        font_combo.bind("<<ComboboxSelected>>", self.update_font)
        
        self.text_area = tk.Text(self.left_frame, wrap=tk.WORD, font=(self.font_family.get(), self.font_size.get(), self.font_weight), undo=True)
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=5)
        self.text_area.bind("<KeyRelease>", self.on_key_release)
        self.text_area.bind("<KeyPress>", self.on_key_press)

        self.status_var = tk.StringVar()
        self.status_var.set("Words: 0 | WPM: 0 | Auto-Save: ON")
        self.status_bar = tk.Label(self.left_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_bar.pack(fill=tk.X)

        # --- RIGHT PANEL ---
        self.right_frame = tk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, minsize=400)

        self.draw_toolbar = tk.Frame(self.right_frame)
        self.draw_toolbar.pack(fill=tk.X, pady=2)

        tk.Button(self.draw_toolbar, text="Undo", command=self.undo_stroke).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Redo", command=self.redo_stroke).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Eraser", command=self.toggle_eraser).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Clear", command=self.clear_canvas).pack(side=tk.LEFT, padx=2)

        self.brush_slider = tk.Scale(self.draw_toolbar, from_=1, to=10, orient=tk.HORIZONTAL, length=80, command=self.change_brush_size)
        self.brush_slider.set(2)
        self.brush_slider.pack(side=tk.LEFT, padx=2)

        self.color_var = tk.StringVar(value="Black (Standard)")
        self.color_combo = ttk.Combobox(self.draw_toolbar, textvariable=self.color_var, values=list(PANTONE_COLORS.keys()), width=15)
        self.color_combo.pack(side=tk.LEFT, padx=2)
        self.color_combo.bind("<<ComboboxSelected>>", self.change_color)
        
        self.canvas = tk.Canvas(self.right_frame, bg=self.current_bg_color, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.image = Image.new("RGB", (800, 800), self.current_bg_color)
        self.draw_img = ImageDraw.Draw(self.image)

    # --- TEXT & NLP METHODS ---
    def update_font(self, event=None):
        my_font = font.Font(family=self.font_family.get(), size=self.font_size.get(), weight=self.font_weight)
        self.text_area.configure(font=my_font)

    def highlight_alliteration(self):
        self.text_area.tag_remove("alliteration", "1.0", tk.END)
        self.text_area.tag_config("alliteration", background="#FFF2A8", foreground="black") 
        text = self.text_area.get(1.0, tk.END).lower()
        words = re.finditer(r'\b(\w+)\b', text)
        word_list = list(words)
        for i in range(len(word_list) - 1):
            w1, w2 = word_list[i], word_list[i+1]
            if w1.group(1)[0] == w2.group(1)[0]:
                self.text_area.tag_add("alliteration", f"1.0 + {w1.start()}c", f"1.0 + {w2.end()}c")

    def calculate_readability(self):
        text = self.text_area.get(1.0, tk.END).strip()
        if not text: return
        sentences = max(1, len(re.split(r'[.!?]+', text)) - 1)
        words = max(1, len(text.split()))
        syllables = sum([len(re.findall(r'[aeiouy]+', w.lower())) for w in text.split()])
        score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        messagebox.showinfo("Readability", f"Score: {score:.2f}\n(Higher is easier to read)")

    def read_aloud(self):
        if not self.tts_engine: return
        text = self.text_area.get(1.0, tk.END)
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def insert_timestamp(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.text_area.insert(tk.END, f"\n\n--- {now} ---\n")

    # --- SENSORY METHODS ---
    def on_key_press(self, event):
        if self.mech_sounds and event.char:
            self.root.bell() 

    def on_key_release(self, event):
        if not self.start_time: self.start_time = time.time()
        text = self.text_area.get(1.0, tk.END).strip()
        words = len(text.split()) if text else 0
        elapsed_minutes = (time.time() - self.start_time) / 60.0 if self.start_time else 0.01
        current_wpm = int(words / elapsed_minutes) if elapsed_minutes > 0 else 0
        
        mode = "Bio-Feedback" if self.bio_feedback else "Normal"
        self.status_var.set(f"Words: {words} | WPM: {current_wpm} | Mode: {mode}")

        if event.keysym in ['space', 'Return']:
            self.save_version_history()

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

    def toggle_sounds(self): self.mech_sounds = not self.mech_sounds
    
    def toggle_biofeedback(self):
        self.bio_feedback = not self.bio_feedback
        if self.bio_feedback: self.bio_feedback_pulse()
        else: self.font_weight = "normal"; self.update_font()

    def bio_feedback_pulse(self):
        if self.bio_feedback:
            self.font_weight = "bold"
            self.update_font()
            self.root.after(150, self.bio_feedback_relax)
            self.root.after(random.randint(1000, 3000), self.bio_feedback_pulse)

    def bio_feedback_relax(self):
        if self.bio_feedback:
            self.font_weight = "normal"
            self.update_font()

    def toggle_metronome(self):
        self.is_metronome_on = not self.is_metronome_on
        if self.is_metronome_on:
            self.bpm = simpledialog.askinteger("Metronome", "Enter BPM:", initialvalue=60, minvalue=30, maxvalue=240)
            if self.bpm: self.tick_metronome()
            else: self.is_metronome_on = False

    def tick_metronome(self):
        if self.is_metronome_on:
            self.root.bell()
            self.root.after(int((60/self.bpm)*1000), self.tick_metronome)

    # --- DRAWING METHODS ---
    def setup_drawing(self):
        self.old_x, self.old_y = None, None
        self.canvas.bind('<Button-1>', self.start_draw)
        self.canvas.bind('<B1-Motion>', self.draw)
        self.canvas.bind('<ButtonRelease-1>', self.stop_draw)

    def change_brush_size(self, val): self.brush_size = int(val)
    def toggle_eraser(self): self.is_eraser = True
    def toggle_mandala(self): self.mandala_mode = not self.mandala_mode
    
    def toggle_colorblind_palette(self):
        self.colorblind_mode = not self.colorblind_mode
        self.color_combo['values'] = list(COLORBLIND_SAFE_COLORS.keys() if self.colorblind_mode else PANTONE_COLORS.keys())
        self.color_combo.current(0)
        self.change_color()

    def change_color(self, event=None):
        pal = COLORBLIND_SAFE_COLORS if self.colorblind_mode else PANTONE_COLORS
        self.current_brush_color = pal.get(self.color_var.get(), "#000000")
        self.is_eraser = False

    def start_draw(self, event):
        self.old_x, self.old_y = event.x, event.y
        self.current_stroke = []

    def draw(self, event):
        if self.old_x and self.old_y:
            color = self.current_bg_color if self.is_eraser else self.current_brush_color
            cx, cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2

            if self.mandala_mode and not self.is_eraser:
                for i in range(self.mandala_axes):
                    angle = math.radians(i * (360 / self.mandala_axes))
                    nx1 = cx + (self.old_x - cx) * math.cos(angle) - (self.old_y - cy) * math.sin(angle)
                    ny1 = cy + (self.old_x - cx) * math.sin(angle) + (self.old_y - cy) * math.cos(angle)
                    nx2 = cx + (event.x - cx) * math.cos(angle) - (event.y - cy) * math.sin(angle)
                    ny2 = cy + (event.x - cx) * math.sin(angle) + (event.y - cy) * math.cos(angle)
                    
                    line_id = self.canvas.create_line(nx1, ny1, nx2, ny2, width=self.brush_size, fill=color, capstyle=tk.ROUND)
                    self.current_stroke.append(line_id)
                    self.draw_img.line([nx1, ny1, nx2, ny2], fill=color, width=self.brush_size)
            else:
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

    def redo_stroke(self):
        if self.redo_stack:
            stroke = self.redo_stack.pop()
            self.strokes.append(stroke)
            for line_id in stroke: self.canvas.itemconfig(line_id, state='normal')

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (800, 800), self.current_bg_color)
        self.draw_img = ImageDraw.Draw(self.image)

    # --- UTILITY & FILE METHODS ---
    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        bg_color, fg_color = ("#1E1E1E", "#FFFFFF") if self.is_dark_mode else ("#FFFFFF", "#000000")
        self.root.config(bg=bg_color)
        self.text_area.config(bg=bg_color, fg=fg_color, insertbackground=fg_color)
        self.canvas.config(bg=bg_color)
        self.current_bg_color = bg_color

    def auto_save(self):
        with open("autosave_backup.txt", "w", encoding="utf-8") as f:
            f.write(self.text_area.get(1.0, tk.END))
        self.root.after(60000, self.auto_save)

    def save_version_history(self):
        text = self.text_area.get(1.0, tk.END)
        if not self.version_history or self.version_history[-1] != text:
            self.version_history.append(text)
            if len(self.version_history) > 10: self.version_history.pop(0)

    def show_versions(self):
        if not self.version_history: return
        top = tk.Toplevel(self.root)
        top.title("Version History")
        listbox = tk.Listbox(top, width=50)
        listbox.pack(padx=10, pady=10)
        for i in range(len(self.version_history)): listbox.insert(tk.END, f"Version {i+1}")
        def restore():
            idx = listbox.curselection()
            if idx:
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(1.0, self.version_history[idx[0]])
                top.destroy()
        tk.Button(top, text="Restore", command=restore).pack(pady=5)

    def add_favorite(self):
        self.favorites.append(self.text_area.get(1.0, tk.END)[:50] + "...")
        messagebox.showinfo("Favorites", "Added to favorites!")

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
