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

# Colorblind-safe palette (Wong palette)
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
        self.root.title("Poetry & Sketch Studio - Sensory Edition")
        self.root.geometry("1200x800")
        
        # --- APP STATE & VARIABLES ---
        self.is_dark_mode = False
        self.current_brush_color = "#000000"
        self.current_bg_color = "#FFFFFF"
        self.brush_size = 2
        self.is_eraser = False
        self.strokes = []
        self.redo_stack = []
        self.current_stroke = []
        
        # New Feature States
        self.mandala_mode = False
        self.mandala_axes = 8
        self.colorblind_mode = False
        self.mech_sounds = False
        self.bio_feedback = False
        self.start_time = None
        self.wpm_history = []
        
        self.setup_ui()
        self.setup_drawing()
        self.track_wpm_loop() # Start WPM tracking loop

    def setup_ui(self):
        # --- MENU BAR ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save as TXT", command=self.save_txt)
        file_menu.add_command(label="Export Sketch (PNG)", command=self.save_sketch)
        
        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools & Sensory", menu=tool_menu)
        tool_menu.add_command(label="Toggle Dark Mode", command=self.toggle_dark_mode)
        tool_menu.add_separator()
        tool_menu.add_command(label="Show WPM Graph", command=self.show_wpm_graph)
        tool_menu.add_checkbutton(label="Mandala Mode (Symmetry)", command=self.toggle_mandala)
        tool_menu.add_checkbutton(label="Colorblind Helper Palette", command=self.toggle_colorblind_palette)
        tool_menu.add_checkbutton(label="Mech Keyboard Sounds", command=self.toggle_sounds)
        tool_menu.add_checkbutton(label="Bio-feedback Sync (Simulated)", command=self.toggle_biofeedback)

        # --- MAIN LAYOUT ---
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- LEFT PANEL (Text) ---
        self.left_frame = tk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, minsize=500)

        # Toolbar
        self.text_toolbar = tk.Frame(self.left_frame)
        self.text_toolbar.pack(fill=tk.X, pady=2)

        self.font_family = tk.StringVar(value="Georgia")
        self.font_size = tk.IntVar(value=14)
        self.font_weight = "normal"
        
        font_combo = ttk.Combobox(self.text_toolbar, textvariable=self.font_family, values=list(font.families()), width=15)
        font_combo.pack(side=tk.LEFT, padx=2)
        font_combo.bind("<<ComboboxSelected>>", self.update_font)
        
        # Text Area
        self.text_area = tk.Text(self.left_frame, wrap=tk.WORD, font=(self.font_family.get(), self.font_size.get(), self.font_weight), undo=True)
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=5)
        self.text_area.bind("<KeyRelease>", self.on_key_release)
        self.text_area.bind("<KeyPress>", self.on_key_press)

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Words: 0 | WPM: 0 | Sensory: Normal")
        self.status_bar = tk.Label(self.left_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_bar.pack(fill=tk.X)

        # --- RIGHT PANEL (Drawing) ---
        self.right_frame = tk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, minsize=400)

        # Drawing Toolbar
        self.draw_toolbar = tk.Frame(self.right_frame)
        self.draw_toolbar.pack(fill=tk.X, pady=2)

        tk.Button(self.draw_toolbar, text="Clear", command=self.clear_canvas).pack(side=tk.LEFT, padx=2)
        tk.Button(self.draw_toolbar, text="Eraser", command=self.toggle_eraser).pack(side=tk.LEFT, padx=2)

        self.brush_slider = tk.Scale(self.draw_toolbar, from_=1, to=10, orient=tk.HORIZONTAL, length=80, command=self.change_brush_size)
        self.brush_slider.set(2)
        self.brush_slider.pack(side=tk.LEFT, padx=2)

        self.color_var = tk.StringVar(value="Black (Standard)")
        self.color_combo = ttk.Combobox(self.draw_toolbar, textvariable=self.color_var, values=list(PANTONE_COLORS.keys()), width=15)
        self.color_combo.pack(side=tk.LEFT, padx=2)
        self.color_combo.bind("<<ComboboxSelected>>", self.change_color)
        
        # Canvas
        self.canvas = tk.Canvas(self.right_frame, bg=self.current_bg_color, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.image = Image.new("RGB", (800, 800), self.current_bg_color)
        self.draw_img = ImageDraw.Draw(self.image)

    # --- TEXT & SENSORY FUNCTIONS ---
    def update_font(self, event=None):
        my_font = font.Font(family=self.font_family.get(), size=self.font_size.get(), weight=self.font_weight)
        self.text_area.configure(font=my_font)

    def on_key_press(self, event):
        # Mechanical keyboard sound simulation
        if self.mech_sounds and event.char:
            self.root.bell() # Placeholder for actual mechanical switch .wav files

    def on_key_release(self, event):
        if not self.start_time:
            self.start_time = time.time()
            
        text = self.text_area.get(1.0, tk.END).strip()
        words = len(text.split()) if text else 0
        
        elapsed_minutes = (time.time() - self.start_time) / 60.0 if self.start_time else 0.01
        current_wpm = int(words / elapsed_minutes) if elapsed_minutes > 0 else 0
        
        mode = "Normal"
        if self.bio_feedback: mode = "Bio-Feedback Active"
        self.status_var.set(f"Words: {words} | WPM: {current_wpm} | Mode: {mode}")

    def track_wpm_loop(self):
        # Records WPM every 10 seconds for the graph
        if self.start_time:
            text = self.text_area.get(1.0, tk.END).strip()
            words = len(text.split())
            elapsed_minutes = (time.time() - self.start_time) / 60.0
            current_wpm = int(words / elapsed_minutes) if elapsed_minutes > 0.1 else 0
            self.wpm_history.append(current_wpm)
        self.root.after(10000, self.track_wpm_loop)

    def show_wpm_graph(self):
        if not self.wpm_history:
            messagebox.showinfo("WPM Graph", "Not enough typing data yet. Keep writing!")
            return
            
        graph_win = tk.Toplevel(self.root)
        graph_win.title("Words Per Minute (WPM) Graph")
        graph_win.geometry("500x300")
        
        g_canvas = tk.Canvas(graph_win, bg="white")
        g_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Simple graph rendering logic
        width, height = 480, 280
        max_wpm = max(max(self.wpm_history), 50)
        points = len(self.wpm_history)
        
        for i in range(points - 1):
            x1 = (i / points) * width
            y1 = height - (self.wpm_history[i] / max_wpm) * height
            x2 = ((i + 1) / points) * width
            y2 = height - (self.wpm_history[i+1] / max_wpm) * height
            g_canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)
            g_canvas.create_oval(x2-3, y2-3, x2+3, y2+3, fill="red")

    def toggle_sounds(self):
        self.mech_sounds = not self.mech_sounds

    def toggle_biofeedback(self):
        self.bio_feedback = not self.bio_feedback
        if self.bio_feedback:
            self.bio_feedback_pulse()
        else:
            self.font_weight = "normal"
            self.update_font()

    def bio_feedback_pulse(self):
        # Simulates a heartbeat pulse by making the font heavily bold black temporarily
        if self.bio_feedback:
            self.font_weight = "bold"
            self.update_font()
            
            # Revert back to normal after a short pulse (150ms)
            self.root.after(150, self.bio_feedback_relax)
            
            # Next random heartbeat between 1 to 3 seconds
            next_pulse = random.randint(1000, 3000)
            self.root.after(next_pulse, self.bio_feedback_pulse)

    def bio_feedback_relax(self):
        if self.bio_feedback:
            self.font_weight = "normal"
            self.update_font()

    # --- DRAWING & CANVAS FUNCTIONS ---
    def setup_drawing(self):
        self.old_x, self.old_y = None, None
        self.canvas.bind('<Button-1>', self.start_draw)
        self.canvas.bind('<B1-Motion>', self.draw)
        self.canvas.bind('<ButtonRelease-1>', self.stop_draw)

    def change_brush_size(self, val):
        self.brush_size = int(val)

    def toggle_colorblind_palette(self):
        self.colorblind_mode = not self.colorblind_mode
        palette = COLORBLIND_SAFE_COLORS if self.colorblind_mode else PANTONE_COLORS
        self.color_combo['values'] = list(palette.keys())
        self.color_combo.current(0)
        self.change_color()

    def change_color(self, event=None):
        palette = COLORBLIND_SAFE_COLORS if self.colorblind_mode else PANTONE_COLORS
        color_name = self.color_var.get()
        # Fallback to black if not found
        self.current_brush_color = palette.get(color_name, "#000000")
        self.is_eraser = False

    def toggle_eraser(self):
        self.is_eraser = True

    def toggle_mandala(self):
        self.mandala_mode = not self.mandala_mode

    def start_draw(self, event):
        self.old_x, self.old_y = event.x, event.y

    def draw(self, event):
        if self.old_x and self.old_y:
            color = self.current_bg_color if self.is_eraser else self.current_brush_color
            
            # Center of the canvas for symmetry math
            self.canvas.update()
            cx, cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2

            if self.mandala_mode and not self.is_eraser:
                # Draw symmetrical lines around the center
                for i in range(self.mandala_axes):
                    angle = math.radians(i * (360 / self.mandala_axes))
                    
                    # Rotate old point
                    nx1 = cx + (self.old_x - cx) * math.cos(angle) - (self.old_y - cy) * math.sin(angle)
                    ny1 = cy + (self.old_x - cx) * math.sin(angle) + (self.old_y - cy) * math.cos(angle)
                    
                    # Rotate new point
                    nx2 = cx + (event.x - cx) * math.cos(angle) - (event.y - cy) * math.sin(angle)
                    ny2 = cy + (event.x - cx) * math.sin(angle) + (event.y - cy) * math.cos(angle)
                    
                    self.canvas.create_line(nx1, ny1, nx2, ny2, width=self.brush_size, fill=color, capstyle=tk.ROUND)
                    self.draw_img.line([nx1, ny1, nx2, ny2], fill=color, width=self.brush_size)
            else:
                # Normal drawing
                self.canvas.create_line(self.old_x, self.old_y, event.x, event.y, width=self.brush_size, fill=color, capstyle=tk.ROUND)
                self.draw_img.line([self.old_x, self.old_y, event.x, event.y], fill=color, width=self.brush_size)
            
            self.old_x, self.old_y = event.x, event.y

    def stop_draw(self, event):
        self.old_x, self.old_y = None, None

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (800, 800), self.current_bg_color)
        self.draw_img = ImageDraw.Draw(self.image)

    # --- UTILITY ---
    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        bg_color = "#1E1E1E" if self.is_dark_mode else "#FFFFFF"
        fg_color = "#FFFFFF" if self.is_dark_mode else "#000000"
        
        self.root.config(bg=bg_color)
        self.text_area.config(bg=bg_color, fg=fg_color, insertbackground=fg_color)
        self.canvas.config(bg=bg_color)
        self.current_bg_color = bg_color

    def save_txt(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.text_area.get(1.0, tk.END))

    def save_sketch(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png")
        if file_path:
            self.image.save(file_path)

if __name__ == "__main__":
    root = tk.Tk()
    app = PoetryApp(root)
    root.mainloop()
