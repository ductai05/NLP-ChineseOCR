import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
import json

class BBoxAdjuster(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BBox Adjuster")
        self.geometry("1200x800")

        self.current_dir = ""
        self.image_files = []
        self.current_image_index = -1
        self.labels = {}  # Dictionary to store labels: {filename: [boxes]}
        self.current_image_path = ""
        self.tk_image = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # State for drawing/editing
        self.boxes = [] # List of box dicts for current image
        self.selected_box_index = -1
        self.hovered_box_index = -1
        self.is_drawing = False
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None

        self._init_ui()

    def _init_ui(self):
        # Top Toolbar
        self.toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.btn_open = tk.Button(self.toolbar, text="Open Directory", command=self.open_directory)
        self.btn_open.pack(side=tk.LEFT, padx=5, pady=5)

        self.btn_check = tk.Button(self.toolbar, text="Check", command=self.toggle_check_status, state=tk.DISABLED)
        self.btn_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.lbl_status = tk.Label(self.toolbar, text="No directory loaded")
        self.lbl_status.pack(side=tk.RIGHT, padx=5, pady=5)

        # Main Layout
        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Sidebar (File List)
        self.sidebar_frame = tk.Frame(self.paned_window, width=200)
        self.paned_window.add(self.sidebar_frame)

        self.listbox = tk.Listbox(self.sidebar_frame)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_file_select)

        # Canvas Area
        self.canvas_frame = tk.Frame(self.paned_window, bg="grey")
        self.paned_window.add(self.canvas_frame)

        self.v_scroll = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        self.h_scroll = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white", cursor="cross",
                                xscrollcommand=self.h_scroll.set,
                                yscrollcommand=self.v_scroll.set)
        
        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.config(command=self.canvas.xview)

        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Events
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.bind("<Delete>", self.delete_selected_box)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)

    def open_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.load_directory(dir_path)

    def load_directory(self, dir_path):
        self.current_dir = dir_path
        self.image_files = [f for f in os.listdir(dir_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        self.image_files.sort()
        
        self.listbox.delete(0, tk.END)
        for f in self.image_files:
            self.listbox.insert(tk.END, f)
            
        self.load_labels()
        self.load_file_state()
        self.lbl_status.config(text=f"Loaded {len(self.image_files)} images from {dir_path}")
        self.btn_check.config(state=tk.NORMAL)

    def load_labels(self):
        label_path = os.path.join(self.current_dir, "Label.txt")
        self.labels = {}
        if os.path.exists(label_path):
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 2:
                            path_key = parts[0]
                            try:
                                data = json.loads(parts[1])
                                self.labels[path_key] = data
                            except json.JSONDecodeError:
                                print(f"Error decoding JSON for line: {line}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load Label.txt: {e}")

    def load_file_state(self):
        self.checked_files = set()
        state_path = os.path.join(self.current_dir, "fileState.txt")
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        self.checked_files.add(line.strip())
            except Exception as e:
                print(f"Failed to load fileState.txt: {e}")
        self.update_listbox_colors()

    def update_listbox_colors(self):
        for i, filename in enumerate(self.image_files):
            if filename in self.checked_files:
                self.listbox.itemconfig(i, {'bg': '#e0ffe0'}) # Light green for checked
            else:
                self.listbox.itemconfig(i, {'bg': 'white'})

    def on_file_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            self.current_image_index = index
            self.load_image(self.image_files[index])
            self.update_check_button()

    def update_check_button(self):
        if self.current_image_index != -1:
            filename = self.image_files[self.current_image_index]
            if filename in self.checked_files:
                self.btn_check.config(text="Uncheck", bg="#e0ffe0")
            else:
                self.btn_check.config(text="Check", bg="SystemButtonFace")

    def load_image(self, filename):
        self.current_image_path = os.path.join(self.current_dir, filename)
        try:
            image = Image.open(self.current_image_path)
            self.original_image = image
            
            # Calculate scale to fit
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img_width, img_height = image.size
                scale_w = canvas_width / img_width
                scale_h = canvas_height / img_height
                self.scale = min(scale_w, scale_h) * 0.95 # 0.95 for a little padding
            else:
                self.scale = 1.0
                
            self.update_image_display()
            self.load_boxes_for_current_image(filename)
            self.draw_boxes()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")

    def update_image_display(self):
        if not hasattr(self, 'original_image'):
            return
            
        width, height = self.original_image.size
        new_width = int(width * self.scale)
        new_height = int(height * self.scale)
        
        resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_image)
        
        self.canvas.config(scrollregion=(0, 0, new_width, new_height))
        self.canvas.delete("image")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image, tags="image")
        self.canvas.tag_lower("image") # Ensure image is behind boxes

    def on_zoom(self, event):
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        
        self.update_image_display()
        self.draw_boxes()

    def load_boxes_for_current_image(self, filename):
        self.boxes = []
        found_key = None
        
        if filename in self.labels:
            found_key = filename
        else:
            for key in self.labels:
                if key.endswith(f"/{filename}") or key == filename:
                    found_key = key
                    break
        
        if found_key:
            self.boxes = self.labels[found_key]
        else:
            self.boxes = []

    def draw_boxes(self):
        self.canvas.delete("box")
        for i, box in enumerate(self.boxes):
            points = box['points']
            # Scale points
            scaled_points = []
            for point in points:
                scaled_points.append(point[0] * self.scale)
                scaled_points.append(point[1] * self.scale)
            
            color = "green"
            width = 2
            
            if i == self.selected_box_index:
                color = "blue"
                width = 3
            elif i == self.hovered_box_index:
                color = "red"
                width = 4 # Bold red
                
            self.canvas.create_polygon(scaled_points, outline=color, fill="", width=width, tags="box")

    def on_mouse_move(self, event):
        x = self.canvas.canvasx(event.x) / self.scale
        y = self.canvas.canvasy(event.y) / self.scale
        
        old_hover = self.hovered_box_index
        self.hovered_box_index = -1
        
        for i, box in enumerate(self.boxes):
            points = box['points']
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            if min_x <= x <= max_x and min_y <= y <= max_y:
                self.hovered_box_index = i
                break
        
        if old_hover != self.hovered_box_index:
            self.draw_boxes()

    def on_mouse_down(self, event):
        x = self.canvas.canvasx(event.x) / self.scale
        y = self.canvas.canvasy(event.y) / self.scale
        
        if self.hovered_box_index != -1:
            self.selected_box_index = self.hovered_box_index
            self.draw_boxes()
        else:
            self.is_drawing = True
            self.start_x = x
            self.start_y = y
            self.selected_box_index = -1
            self.draw_boxes()

    def on_mouse_drag(self, event):
        x = self.canvas.canvasx(event.x) / self.scale
        y = self.canvas.canvasy(event.y) / self.scale
        
        if self.is_drawing:
            if self.current_rect:
                self.canvas.delete(self.current_rect)
            
            # Draw rect needs scaled coordinates
            sx = self.start_x * self.scale
            sy = self.start_y * self.scale
            ex = x * self.scale
            ey = y * self.scale
            
            self.current_rect = self.canvas.create_rectangle(sx, sy, ex, ey, outline="blue", width=2)

    def on_mouse_up(self, event):
        x = self.canvas.canvasx(event.x) / self.scale
        y = self.canvas.canvasy(event.y) / self.scale
        
        if self.is_drawing:
            self.is_drawing = False
            if self.current_rect:
                self.canvas.delete(self.current_rect)
                self.current_rect = None
                
                x1, y1 = self.start_x, self.start_y
                x2, y2 = x, y
                
                min_x, max_x = sorted([x1, x2])
                min_y, max_y = sorted([y1, y2])
                
                if (max_x - min_x) < 5 or (max_y - min_y) < 5:
                    return

                new_points = [[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y]]
                new_box = {
                    "transcription": "TEMPORARY",
                    "points": new_points,
                    "difficult": False
                }
                self.boxes.append(new_box)
                self.save_current_image_boxes()
                self.draw_boxes()

    def delete_selected_box(self, event):
        if self.selected_box_index != -1:
            del self.boxes[self.selected_box_index]
            self.selected_box_index = -1
            self.save_current_image_boxes()
            self.draw_boxes()

    def save_current_image_boxes(self):
        filename = self.image_files[self.current_image_index]
        dirname = os.path.basename(self.current_dir)
        
        found_key = None
        for key in self.labels:
            if key.endswith(f"/{filename}") or key == filename:
                found_key = key
                break
        
        if not found_key:
            found_key = f"{dirname}/{filename}"
            
        self.labels[found_key] = self.boxes
        self.save_labels_to_file()

    def save_labels_to_file(self):
        label_path = os.path.join(self.current_dir, "Label.txt")
        try:
            with open(label_path, 'w', encoding='utf-8') as f:
                for key, boxes in self.labels.items():
                    json_str = json.dumps(boxes, ensure_ascii=False)
                    f.write(f"{key}\t{json_str}\n")
            print("Auto-saved Label.txt")
        except Exception as e:
            print(f"Failed to save Label.txt: {e}")

    def toggle_check_status(self):
        if self.current_image_index == -1:
            return
            
        filename = self.image_files[self.current_image_index]
        if filename in self.checked_files:
            self.checked_files.remove(filename)
        else:
            self.checked_files.add(filename)
            
        self.save_file_state()
        self.update_listbox_colors()
        self.update_check_button()

    def save_file_state(self):
        state_path = os.path.join(self.current_dir, "fileState.txt")
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                for filename in sorted(list(self.checked_files)):
                    f.write(f"{filename}\n")
        except Exception as e:
            print(f"Failed to save fileState.txt: {e}")

if __name__ == "__main__":
    app = BBoxAdjuster()
    app.mainloop()
