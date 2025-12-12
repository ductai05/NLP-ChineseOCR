"""
Manual Dataset Checker with UI
Công cụ kiểm tra thủ công dataset với giao diện đồ họa
"""

import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os


class ManualDatasetChecker:
    """Giao diện kiểm tra thủ công dataset"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Manual Dataset Checker - NLP Final Project")
        self.root.geometry("1400x900")
        
        self.dataset_root = Path(__file__).resolve().parent / "Final_Dataset"
        self.current_dataset = None
        self.current_image = None
        self.current_image_data = None
        self.det_data = {}
        self.rec_data = {}
        self.patch_files = []
        self.current_patch_index = 0
        
        self.setup_ui()
        self.load_datasets()
        
    def setup_ui(self):
        """Thiết lập giao diện"""
        # Title
        title_frame = tk.Frame(self.root, bg='#2c3e50')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            title_frame,
            text="🔍 MANUAL DATASET CHECKER",
            font=("Arial", 18, "bold"),
            bg='#2c3e50',
            fg='white',
            pady=10
        ).pack()
        
        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left panel - Dataset & Image selection
        left_panel = tk.Frame(main_container, width=300, bg='#ecf0f1')
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Dataset selection
        tk.Label(left_panel, text="📚 Chọn Dataset:", font=("Arial", 11, "bold"), bg='#ecf0f1').pack(pady=(10, 5))
        self.dataset_listbox = tk.Listbox(left_panel, font=("Consolas", 9), height=8)
        self.dataset_listbox.pack(fill=tk.X, padx=10, pady=5)
        self.dataset_listbox.bind('<<ListboxSelect>>', self.on_dataset_select)
        
        # Image selection
        tk.Label(left_panel, text="🖼 Chọn Ảnh:", font=("Arial", 11, "bold"), bg='#ecf0f1').pack(pady=(10, 5))
        
        # Search box
        search_frame = tk.Frame(left_panel, bg='#ecf0f1')
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="🔍", bg='#ecf0f1').pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *args: self.filter_images())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Consolas", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.image_listbox = tk.Listbox(left_panel, font=("Consolas", 9))
        self.image_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
        # Stats
        self.stats_label = tk.Label(left_panel, text="", font=("Arial", 8), bg='#ecf0f1', justify=tk.LEFT)
        self.stats_label.pack(fill=tk.X, padx=10, pady=10)
        
        # Right panel - Content viewer
        right_panel = tk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Image with annotations
        self.image_tab = tk.Frame(self.notebook)
        self.notebook.add(self.image_tab, text="📷 Ảnh Gốc & Annotations")
        self.setup_image_tab()
        
        # Tab 2: Patches viewer
        self.patches_tab = tk.Frame(self.notebook)
        self.notebook.add(self.patches_tab, text="🔲 Patches")
        self.setup_patches_tab()
        
        # Tab 3: Text data
        self.text_tab = tk.Frame(self.notebook)
        self.notebook.add(self.text_tab, text="📝 Text Data")
        self.setup_text_tab()
        
        # Tab 4: Puncs
        self.puncs_tab = tk.Frame(self.notebook)
        self.notebook.add(self.puncs_tab, text="📌 Dấu Câu")
        self.setup_puncs_tab()
        
    def setup_image_tab(self):
        """Setup tab hiển thị ảnh gốc"""
        # Control panel
        control_frame = tk.Frame(self.image_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.show_boxes_var = tk.BooleanVar(value=True)
        tk.Checkbutton(control_frame, text="Hiển thị bounding boxes", variable=self.show_boxes_var, 
                      command=self.display_image).pack(side=tk.LEFT, padx=5)
        
        self.show_text_var = tk.BooleanVar(value=True)
        tk.Checkbutton(control_frame, text="Hiển thị text", variable=self.show_text_var,
                      command=self.display_image).pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="🔄 Refresh", command=self.display_image).pack(side=tk.LEFT, padx=5)
        
        # Image canvas with scrollbar
        canvas_frame = tk.Frame(self.image_tab)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.image_canvas = tk.Canvas(canvas_frame, bg='#2c3e50')
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.image_canvas.xview)
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.image_canvas.yview)
        
        self.image_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.image_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Info label
        self.image_info_label = tk.Label(self.image_tab, text="", font=("Consolas", 9), bg='#ecf0f1')
        self.image_info_label.pack(fill=tk.X, padx=10, pady=5)
        
    def setup_patches_tab(self):
        """Setup tab hiển thị patches"""
        # Navigation
        nav_frame = tk.Frame(self.patches_tab)
        nav_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(nav_frame, text="⏮ First", command=lambda: self.goto_patch(0)).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="◀ Prev", command=self.prev_patch).pack(side=tk.LEFT, padx=2)
        
        self.patch_index_label = tk.Label(nav_frame, text="0 / 0", font=("Arial", 11, "bold"))
        self.patch_index_label.pack(side=tk.LEFT, padx=20)
        
        tk.Button(nav_frame, text="Next ▶", command=self.next_patch).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Last ⏭", command=lambda: self.goto_patch(-1)).pack(side=tk.LEFT, padx=2)
        
        # Patch display
        self.patch_canvas = tk.Canvas(self.patches_tab, bg='#2c3e50', height=400)
        self.patch_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Patch info
        info_frame = tk.Frame(self.patches_tab, bg='#ecf0f1')
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Left side: horizontal text display
        text_frame = tk.Frame(info_frame, bg='white', relief=tk.SUNKEN, bd=2)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(text_frame, text="📝 Transcription:", font=("Arial", 9, "bold"), bg='white').pack(anchor=tk.W, padx=5, pady=2)
        
        # Horizontal text display with scrollbar
        text_container = tk.Frame(text_frame, bg='white')
        text_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        v_scroll = tk.Scrollbar(text_container, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.patch_text_widget = tk.Text(text_container, bg='#fffef0', height=8, wrap=tk.WORD,
                                         yscrollcommand=v_scroll.set, font=('SimSun', 12))
        self.patch_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.config(command=self.patch_text_widget.yview)
        
        # Right side: info
        self.patch_info_label = tk.Label(info_frame, text="", font=("Consolas", 9), bg='#ecf0f1', justify=tk.LEFT)
        self.patch_info_label.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        
    def setup_text_tab(self):
        """Setup tab hiển thị dữ liệu text"""
        # det_gt.txt section
        tk.Label(self.text_tab, text="📋 det_gt.txt (Detection Ground Truth)", 
                font=("Arial", 11, "bold")).pack(pady=(10, 5))
        
        det_frame = tk.Frame(self.text_tab)
        det_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        det_scroll = tk.Scrollbar(det_frame)
        det_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.det_text = tk.Text(det_frame, font=("Consolas", 9), wrap=tk.WORD, 
                               yscrollcommand=det_scroll.set, height=15)
        self.det_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        det_scroll.config(command=self.det_text.yview)
        
        # rec_gt.txt section
        tk.Label(self.text_tab, text="📋 rec_gt.txt (Recognition Ground Truth)", 
                font=("Arial", 11, "bold")).pack(pady=(10, 5))
        
        rec_frame = tk.Frame(self.text_tab)
        rec_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        rec_scroll = tk.Scrollbar(rec_frame)
        rec_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.rec_text = tk.Text(rec_frame, font=("Consolas", 9), wrap=tk.WORD,
                               yscrollcommand=rec_scroll.set, height=15)
        self.rec_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rec_scroll.config(command=self.rec_text.yview)
        
    def setup_puncs_tab(self):
        """Setup tab hiển thị dấu câu"""
        tk.Label(self.puncs_tab, text="📌 Nội dung file dấu câu (chữ dọc)", 
                font=("Arial", 11, "bold")).pack(pady=(10, 5))
        
        puncs_frame = tk.Frame(self.puncs_tab)
        puncs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Canvas for vertical text with scrollbar
        canvas_frame = tk.Frame(puncs_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.puncs_canvas = tk.Canvas(canvas_frame, bg='white',
                                      xscrollcommand=h_scrollbar.set,
                                      yscrollcommand=v_scrollbar.set)
        self.puncs_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        h_scrollbar.config(command=self.puncs_canvas.xview)
        v_scrollbar.config(command=self.puncs_canvas.yview)
        
    def load_datasets(self):
        """Load danh sách datasets"""
        if not self.dataset_root.exists():
            messagebox.showerror("Lỗi", f"Không tìm thấy thư mục Final_Dataset tại:\n{self.dataset_root}")
            return
        
        datasets = [d.name for d in sorted(self.dataset_root.iterdir()) if d.is_dir()]
        
        for dataset in datasets:
            self.dataset_listbox.insert(tk.END, dataset)
        
        if datasets:
            self.dataset_listbox.selection_set(0)
            self.on_dataset_select(None)
            
    def on_dataset_select(self, event):
        """Khi chọn dataset"""
        selection = self.dataset_listbox.curselection()
        if not selection:
            return
        
        dataset_name = self.dataset_listbox.get(selection[0])
        self.current_dataset = self.dataset_root / dataset_name
        
        # Load det_gt.txt
        det_gt_file = self.current_dataset / "det_gt.txt"
        self.det_data = {}
        if det_gt_file.exists():
            with open(det_gt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split('\t', 1)
                        if len(parts) == 2:
                            img_path = Path(parts[0]).name
                            self.det_data[img_path] = json.loads(parts[1])
        
        # Load rec_gt.txt
        rec_gt_file = self.current_dataset / "rec_gt.txt"
        self.rec_data = {}
        if rec_gt_file.exists():
            with open(rec_gt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split('\t', 1)
                        if len(parts) == 2:
                            patch_name = Path(parts[0]).name
                            self.rec_data[patch_name] = parts[1]
        
        # Load image list
        self.load_images()
        
        # Update stats
        self.update_stats()
        
    def load_images(self):
        """Load danh sách ảnh"""
        self.image_listbox.delete(0, tk.END)
        
        images_folder = self.current_dataset / "images"
        if not images_folder.exists():
            return
        
        self.all_images = sorted([img.name for img in images_folder.glob("*.jpg")])
        
        for img_name in self.all_images:
            self.image_listbox.insert(tk.END, img_name)
        
        if self.all_images:
            self.image_listbox.selection_set(0)
            self.on_image_select(None)
            
    def filter_images(self, *args):
        """Filter danh sách ảnh"""
        search_text = self.search_var.get().lower()
        
        self.image_listbox.delete(0, tk.END)
        
        for img_name in self.all_images:
            if search_text in img_name.lower():
                self.image_listbox.insert(tk.END, img_name)
                
    def on_image_select(self, event):
        """Khi chọn ảnh"""
        selection = self.image_listbox.curselection()
        if not selection:
            return
        
        self.current_image = self.image_listbox.get(selection[0])
        self.current_image_data = self.det_data.get(self.current_image, [])
        
        # Load patches for this image
        self.load_patches()
        
        # Display
        self.display_image()
        self.display_text_data()
        self.display_puncs()
        self.goto_patch(0)
        
    def load_patches(self):
        """Load patches của ảnh hiện tại"""
        self.patch_files = []
        self.current_patch_index = 0
        
        if not self.current_image:
            return
        
        patches_folder = self.current_dataset / "patches"
        if not patches_folder.exists():
            return
        
        # Get base image name without extension
        base_name = self.current_image.rsplit('.', 1)[0]
        
        # Find all patches for this image
        self.patch_files = sorted([
            p for p in patches_folder.glob("*.jpg") 
            if p.name.startswith(base_name + ".")
        ])
        
        self.patch_index_label.config(text=f"0 / {len(self.patch_files)}")
        
    def display_image(self):
        """Hiển thị ảnh với annotations"""
        if not self.current_image or not self.current_dataset:
            return
        
        image_path = self.current_dataset / "images" / self.current_image
        
        # Read image with Unicode support
        with open(image_path, 'rb') as f:
            img_array = np.frombuffer(f.read(), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            return
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL for better text rendering
        img_pil = Image.fromarray(img)
        draw = ImageDraw.Draw(img_pil)
        
        # Try to load Chinese font
        try:
            font = ImageFont.truetype(r'C:\Windows\Fonts\simsun.ttc', 16)
        except:
            try:
                font = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 16)
            except:
                font = ImageFont.load_default()
        
        # Draw annotations
        if self.show_boxes_var.get() and self.current_image_data:
            for idx, ann in enumerate(self.current_image_data):
                points = np.array(ann['points'], dtype=np.int32)
                
                # Draw box using PIL
                draw.line([tuple(points[0]), tuple(points[1]), tuple(points[2]), 
                          tuple(points[3]), tuple(points[0])], fill=(0, 255, 0), width=2)
                
                # Draw index
                draw.text(tuple(points[0]), str(idx + 1), fill=(255, 0, 0), font=font)
                
                # Draw text next to box (vertical)
                if self.show_text_var.get():
                    text = ann.get('transcription', '')
                    if text:
                        # Position text to the right of the box
                        text_x = points[1][0] + 10
                        text_y = points[0][1]
                        
                        # Draw each character vertically
                        char_height = font.size + 4
                        for i, char in enumerate(text):
                            char_y = text_y + (i * char_height)
                            
                            # Draw background for each character
                            bbox = draw.textbbox((text_x, char_y), char, font=font)
                            draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill=(255, 255, 255))
                            
                            # Draw character
                            draw.text((text_x, char_y), char, fill=(0, 0, 0), font=font)
        
        # Convert back to array
        img = np.array(img_pil)
        
        # Convert to PhotoImage
        img_tk = ImageTk.PhotoImage(Image.fromarray(img))
        
        # Update canvas
        self.image_canvas.delete("all")
        self.image_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        self.image_canvas.image = img_tk  # Keep reference
        
        # Update scroll region
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
        
        # Update info
        h, w = img.shape[:2]
        num_annotations = len(self.current_image_data)
        self.image_info_label.config(
            text=f"📊 Kích thước: {w}x{h} | Số annotations: {num_annotations}"
        )
        
    def display_text_data(self):
        """Hiển thị dữ liệu text"""
        # Clear
        self.det_text.delete(1.0, tk.END)
        self.rec_text.delete(1.0, tk.END)
        
        if not self.current_image:
            return
        
        # Display det_gt
        if self.current_image in self.det_data:
            self.det_text.insert(tk.END, json.dumps(self.det_data[self.current_image], 
                                                    indent=2, ensure_ascii=False))
        else:
            self.det_text.insert(tk.END, "Không có dữ liệu det_gt cho ảnh này")
        
        # Display rec_gt for current image patches
        base_name = self.current_image.rsplit('.', 1)[0]
        rec_entries = {k: v for k, v in self.rec_data.items() if k.startswith(base_name + ".")}
        
        if rec_entries:
            for patch_name, text in sorted(rec_entries.items()):
                self.rec_text.insert(tk.END, f"{patch_name}\t{text}\n")
        else:
            self.rec_text.insert(tk.END, "Không có dữ liệu rec_gt cho ảnh này")
            
    def display_puncs(self):
        """Hiển thị nội dung file dấu câu dạng dọc"""
        if not self.current_image:
            self.puncs_canvas.delete("all")
            return
        
        # Tìm file puncs tương ứng
        punc_name = self.current_image.rsplit('.', 1)[0] + ".txt"
        punc_file = self.current_dataset / "puncs" / punc_name
        
        if punc_file.exists():
            with open(punc_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Font lớn hơn cho puncs để dễ đọc (18 pt)
                self.draw_vertical_text(self.puncs_canvas, content, font_size=18, start_x=50)
        else:
            self.puncs_canvas.delete("all")
            self.puncs_canvas.create_text(50, 50, text=f"Không tìm thấy file: {punc_name}",
                                         font=('Arial', 10), anchor=tk.NW)
            
    def goto_patch(self, index):
        """Đi tới patch cụ thể"""
        if not self.patch_files:
            return
        
        if index == -1:
            index = len(self.patch_files) - 1
        
        if 0 <= index < len(self.patch_files):
            self.current_patch_index = index
            self.display_patch()
            
    def prev_patch(self):
        """Patch trước"""
        if self.current_patch_index > 0:
            self.current_patch_index -= 1
            self.display_patch()
            
    def next_patch(self):
        """Patch tiếp theo"""
        if self.current_patch_index < len(self.patch_files) - 1:
            self.current_patch_index += 1
            self.display_patch()
            
    def display_patch(self):
        """Hiển thị patch hiện tại"""
        if not self.patch_files or self.current_patch_index >= len(self.patch_files):
            self.patch_canvas.delete("all")
            self.patch_text_widget.delete(1.0, tk.END)
            self.patch_text_widget.insert(tk.END, "Không có patches")
            self.patch_info_label.config(text="")
            return
        
        patch_file = self.patch_files[self.current_patch_index]
        
        # Read patch image
        with open(patch_file, 'rb') as f:
            img_array = np.frombuffer(f.read(), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            return
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Scale to fit canvas
        scale = min(800 / img.shape[1], 400 / img.shape[0], 3.0)
        new_w = int(img.shape[1] * scale)
        new_h = int(img.shape[0] * scale)
        img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Convert to PhotoImage
        img_pil = Image.fromarray(img_resized)
        img_tk = ImageTk.PhotoImage(img_pil)
        
        # Update canvas
        self.patch_canvas.delete("all")
        canvas_w = self.patch_canvas.winfo_width()
        canvas_h = self.patch_canvas.winfo_height()
        x = max(10, (canvas_w - new_w) // 2)
        y = max(10, (canvas_h - new_h) // 2)
        self.patch_canvas.create_image(x, y, anchor=tk.NW, image=img_tk)
        self.patch_canvas.image = img_tk
        
        # Update text - display horizontal
        patch_name = patch_file.name
        transcription = self.rec_data.get(patch_name, "Không có dữ liệu")
        
        self.patch_text_widget.delete(1.0, tk.END)
        self.patch_text_widget.insert(tk.END, transcription)
        
        # Update info
        h, w = img.shape[:2]
        file_size = patch_file.stat().st_size / 1024  # KB
        self.patch_index_label.config(text=f"{self.current_patch_index + 1} / {len(self.patch_files)}")
        self.patch_info_label.config(
            text=f"📄 {patch_name}\n"
                 f"📊 Kích thước: {w}x{h} | Dung lượng: {file_size:.1f} KB\n"
                 f"🔍 Scale: {scale:.2f}x"
        )
        
    def draw_vertical_text(self, canvas, text, font_size=10, start_x=50):
        """Vẽ text dọc (từ trên xuống, phải sang trái) kiểu chữ Trung Quốc cổ điển bằng PIL"""
        if not text or text == "Không có dữ liệu":
            canvas.create_text(20, 20, text=text, font=('Arial', font_size), anchor=tk.NW)
            canvas.configure(scrollregion=canvas.bbox("all"))
            return
        
        # Tìm font file trên Windows
        font_paths = [
            r'C:\Windows\Fonts\simsun.ttc',     # SimSun
            r'C:\Windows\Fonts\msyh.ttc',       # Microsoft YaHei
            r'C:\Windows\Fonts\mingliu.ttc',    # MingLiU
            r'C:\Windows\Fonts\kaiu.ttf',       # KaiTi
            r'C:\Windows\Fonts\simhei.ttf',     # SimHei
        ]
        
        # Tìm font file có sẵn
        pil_font = None
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    pil_font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        if pil_font is None:
            # Fallback to default
            try:
                pil_font = ImageFont.truetype("arial.ttf", font_size)
            except:
                pil_font = ImageFont.load_default()
        
        # Tính toán kích thước
        char_spacing = font_size + 6
        column_spacing = int(font_size * 1.8) + 10
        
        # Chia text thành các cột (mỗi dòng là 1 cột)
        lines = text.split('\n') if '\n' in text else [text]
        
        # Tính kích thước canvas cần thiết
        max_chars = max(len(line) for line in lines) if lines else 0
        img_width = start_x + (len(lines) * column_spacing) + 50
        img_height = max_chars * char_spacing + 50
        
        # Tạo ảnh PIL
        img = Image.new('RGB', (img_width, img_height), color='#fffef0')
        draw = ImageDraw.Draw(img)
        
        # Vẽ text dọc (từ phải sang trái)
        current_col = len(lines) - 1
        
        for line in lines:
            x = start_x + (current_col * column_spacing)
            y = 20
            
            # Vẽ từng ký tự trong cột này (từ trên xuống)
            for char in line:
                if char.strip():  # Bỏ qua space
                    # Sử dụng textbbox để tính toán vị trí chính xác
                    bbox = draw.textbbox((x, y), char, font=pil_font)
                    # Center character
                    char_width = bbox[2] - bbox[0]
                    actual_x = x - char_width // 2
                    draw.text((actual_x, y), char, font=pil_font, fill='black')
                y += char_spacing
            
            current_col -= 1
        
        # Convert PIL image to PhotoImage
        photo = ImageTk.PhotoImage(img)
        
        # Clear canvas and display image
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.image = photo  # Keep reference
        
        # Update scroll region
        canvas.configure(scrollregion=(0, 0, img_width, img_height))
    
    def update_stats(self):
        """Cập nhật thống kê"""
        if not self.current_dataset:
            return
        
        images_count = len(list((self.current_dataset / "images").glob("*.jpg"))) if (self.current_dataset / "images").exists() else 0
        patches_count = len(list((self.current_dataset / "patches").glob("*.jpg"))) if (self.current_dataset / "patches").exists() else 0
        puncs_count = len(list((self.current_dataset / "puncs").glob("*.txt"))) if (self.current_dataset / "puncs").exists() else 0
        
        self.stats_label.config(
            text=f"📊 Thống kê:\n"
                 f"  • Images: {images_count}\n"
                 f"  • Patches: {patches_count}\n"
                 f"  • Puncs: {puncs_count}\n"
                 f"  • Det entries: {len(self.det_data)}\n"
                 f"  • Rec entries: {len(self.rec_data)}"
        )


def main():
    """Main function"""
    root = tk.Tk()
    app = ManualDatasetChecker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
