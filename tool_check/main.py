"""
Dataset Validation Tool with UI for NLP Final Project
Kiểm tra độ chính xác của det_gt.txt, rec_gt.txt, patches, puncs, images với giao diện đồ họa
"""

import os
import json
import cv2
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from datetime import datetime
import threading


class DatasetValidator:
    """Công cụ kiểm tra tính chính xác của dataset"""
    
    def __init__(self, root_dir: str, log_callback=None):
        self.root_dir = Path(root_dir)
        self.final_dataset = self.root_dir / "Final_Dataset"
        self.errors = []
        self.warnings = []
        self.stats = defaultdict(int)
        self.log_callback = log_callback
        
    def log_error(self, message: str):
        """Ghi lỗi"""
        self.errors.append(message)
        if self.log_callback:
            self.log_callback(f"❌ ERROR: {message}\n", "error")
        
    def log_warning(self, message: str):
        """Ghi cảnh báo"""
        self.warnings.append(message)
        if self.log_callback:
            self.log_callback(f"⚠️  WARNING: {message}\n", "warning")
        
    def log_info(self, message: str):
        """Ghi thông tin"""
        if self.log_callback:
            self.log_callback(f"{message}\n", "info")
    
    def log_success(self, message: str):
        """Ghi thành công"""
        if self.log_callback:
            self.log_callback(f"✓ {message}\n", "success")
            
    def validate_images(self) -> Dict[str, Set[str]]:
        """
        Kiểm tra folder images
        Returns: Dict[dataset_name, Set[image_names]]
        """
        self.log_info("=" * 80)
        self.log_info("1. KIỂM TRA FOLDER IMAGES")
        self.log_info("=" * 80)
        
        dataset_images = {}
        
        for dataset_folder in sorted(self.final_dataset.iterdir()):
            if not dataset_folder.is_dir():
                continue
                
            images_folder = dataset_folder / "images"
            if not images_folder.exists():
                self.log_warning(f"[{dataset_folder.name}] Không tìm thấy folder images")
                continue
                
            image_files = set()
            for image_file in sorted(images_folder.glob("*.jpg")):
                try:
                    # Read image with absolute path
                    img = cv2.imread(str(image_file.absolute()))
                    if img is None:
                        self.log_error(f"[{dataset_folder.name}] Không thể đọc ảnh: {image_file.name} (Path: {image_file})")
                    else:
                        h, w = img.shape[:2]
                        if h == 0 or w == 0:
                            self.log_error(f"[{dataset_folder.name}] Ảnh có kích thước không hợp lệ: {image_file.name}")
                        else:
                            image_files.add(image_file.name)
                            self.stats['total_images'] += 1
                except Exception as e:
                    self.log_error(f"[{dataset_folder.name}] Lỗi khi đọc ảnh {image_file.name}: {str(e)}")
                    
            dataset_images[dataset_folder.name] = image_files
            self.log_info(f"  [{dataset_folder.name}] Tìm thấy {len(image_files)} ảnh hợp lệ")
            
        self.log_success(f"Tổng số ảnh hợp lệ: {self.stats['total_images']}")
        return dataset_images
        
    def validate_det_gt(self, dataset_images: Dict[str, Set[str]]) -> Dict[str, Dict]:
        """
        Kiểm tra det_gt.txt (detection ground truth)
        Returns: Dict[dataset_name, Dict[image_name, annotations]]
        """
        self.log_info("\n" + "=" * 80)
        self.log_info("2. KIỂM TRA DET_GT.TXT")
        self.log_info("=" * 80)
        
        det_data = {}
        
        for dataset_folder in sorted(self.final_dataset.iterdir()):
            if not dataset_folder.is_dir():
                continue
                
            det_gt_file = dataset_folder / "det_gt.txt"
            if not det_gt_file.exists():
                self.log_error(f"[{dataset_folder.name}] Không tìm thấy det_gt.txt")
                continue
                
            det_images = {}
            try:
                with open(det_gt_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            parts = line.split('\t', 1)
                            if len(parts) != 2:
                                self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}: Format không đúng (thiếu tab)")
                                continue
                                
                            image_path, json_str = parts
                            
                            # Extract image filename from path (format: dataset/images/filename.jpg)
                            # Example: 三彌勒經疏_H0032/images/H0032_002_0077_c.jpg -> H0032_002_0077_c.jpg
                            image_name = Path(image_path).name
                            
                            # Parse JSON
                            try:
                                annotations = json.loads(json_str)
                            except json.JSONDecodeError as e:
                                self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}: JSON không hợp lệ - {str(e)}")
                                continue
                            
                            if not isinstance(annotations, list):
                                self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}: Annotations phải là list")
                                continue
                            
                            # Validate annotations structure
                            valid_anns = []
                            for idx, ann in enumerate(annotations):
                                if not isinstance(ann, dict):
                                    self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}, ann {idx}: Phải là dictionary")
                                    continue
                                
                                # Check required fields
                                if 'transcription' not in ann or 'points' not in ann:
                                    self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}, ann {idx}: Thiếu 'transcription' hoặc 'points'")
                                    continue
                                
                                # Validate points
                                points = ann['points']
                                if not isinstance(points, list) or len(points) != 4:
                                    self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}, ann {idx}: 'points' phải có 4 điểm")
                                    continue
                                
                                valid_points = True
                                for pt_idx, pt in enumerate(points):
                                    if not isinstance(pt, list) or len(pt) != 2:
                                        self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}, ann {idx}, point {pt_idx}: Phải là [x, y]")
                                        valid_points = False
                                        break
                                
                                if valid_points:
                                    valid_anns.append(ann)
                            
                            det_images[image_name] = valid_anns
                            self.stats['total_det_entries'] += 1
                            self.stats['total_det_annotations'] += len(valid_anns)
                            
                            # Check if image file exists physically
                            image_file_path = dataset_folder / "images" / image_name
                            if not image_file_path.exists():
                                self.log_warning(f"[{dataset_folder.name}] det_gt.txt có {image_name} nhưng file ảnh không tồn tại")
                            elif dataset_folder.name in dataset_images:
                                if image_name not in dataset_images[dataset_folder.name]:
                                    self.log_warning(f"[{dataset_folder.name}] det_gt.txt có {image_name} nhưng ảnh không đọc được")
                            
                        except Exception as e:
                            self.log_error(f"[{dataset_folder.name}] det_gt.txt dòng {line_num}: Lỗi - {str(e)}")
                            
            except Exception as e:
                self.log_error(f"[{dataset_folder.name}] Không thể đọc det_gt.txt: {str(e)}")
                
            det_data[dataset_folder.name] = det_images
            self.log_info(f"  [{dataset_folder.name}] Tìm thấy {len(det_images)} entries với {sum(len(anns) for anns in det_images.values())} annotations")
            
        self.log_success(f"Tổng số entries trong det_gt: {self.stats['total_det_entries']}")
        self.log_success(f"Tổng số annotations trong det_gt: {self.stats['total_det_annotations']}")
        return det_data
        
    def validate_patches(self, det_data: Dict[str, Dict]) -> Dict:
        """
        Kiểm tra patches (ảnh cắt từng text box)
        """
        self.log_info("\n" + "=" * 80)
        self.log_info("3. KIỂM TRA FOLDER PATCHES")
        self.log_info("=" * 80)
        
        patch_data = {}
        
        for dataset_folder in sorted(self.final_dataset.iterdir()):
            if not dataset_folder.is_dir():
                continue
                
            patches_folder = dataset_folder / "patches"
            if not patches_folder.exists():
                self.log_error(f"[{dataset_folder.name}] Không tìm thấy folder patches")
                continue
                
            dataset_patches = {}
            for image_folder in sorted(patches_folder.iterdir()):
                if not image_folder.is_dir():
                    continue
                    
                image_name = image_folder.name
                patch_files = sorted(list(image_folder.glob("*.jpg")))
                
                # Check if image has det_gt annotations
                if dataset_folder.name in det_data and image_name in det_data[dataset_folder.name]:
                    expected_count = len(det_data[dataset_folder.name][image_name])
                    actual_count = len(patch_files)
                    
                    if expected_count != actual_count:
                        self.log_error(
                            f"[{dataset_folder.name}] Patches cho {image_name}: "
                            f"Expected {expected_count}, Found {actual_count}"
                        )
                    else:
                        self.stats['matched_patches_folders'] += 1
                else:
                    self.log_warning(f"[{dataset_folder.name}] Patches cho {image_name} nhưng không có trong det_gt.txt")
                
                # Validate each patch
                valid_patches = []
                for patch_file in patch_files:
                    try:
                        # Read patch with absolute path
                        img = cv2.imread(str(patch_file.absolute()))
                        if img is None:
                            self.log_error(f"[{dataset_folder.name}] Không thể đọc patch: {image_name}/{patch_file.name}")
                        else:
                            valid_patches.append(patch_file.name)
                            self.stats['total_patches'] += 1
                    except Exception as e:
                        self.log_error(f"[{dataset_folder.name}] Lỗi khi đọc patch {image_name}/{patch_file.name}: {str(e)}")
                
                dataset_patches[image_name] = valid_patches
                
            patch_data[dataset_folder.name] = dataset_patches
            total_patches = sum(len(patches) for patches in dataset_patches.values())
            self.log_info(f"  [{dataset_folder.name}] Tìm thấy {total_patches} patches hợp lệ trong {len(dataset_patches)} folders")
            
        self.log_success(f"Số folders patches khớp với det_gt: {self.stats['matched_patches_folders']}")
        self.log_success(f"Tổng số patches hợp lệ: {self.stats['total_patches']}")
        return patch_data
        
    def validate_rec_gt(self, patch_data: Dict) -> Dict:
        """
        Kiểm tra rec_gt.txt (recognition ground truth)
        """
        self.log_info("\n" + "=" * 80)
        self.log_info("4. KIỂM TRA REC_GT.TXT")
        self.log_info("=" * 80)
        
        rec_data = {}
        
        for dataset_folder in sorted(self.final_dataset.iterdir()):
            if not dataset_folder.is_dir():
                continue
                
            rec_gt_file = dataset_folder / "rec_gt.txt"
            if not rec_gt_file.exists():
                self.log_error(f"[{dataset_folder.name}] Không tìm thấy rec_gt.txt")
                continue
                
            rec_entries = {}
            try:
                with open(rec_gt_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            parts = line.split('\t', 1)
                            if len(parts) != 2:
                                self.log_error(f"[{dataset_folder.name}] rec_gt.txt dòng {line_num}: Format không đúng (thiếu tab)")
                                continue
                                
                            patch_path, transcription = parts
                            
                            if transcription.strip() == "":
                                self.log_warning(f"[{dataset_folder.name}] rec_gt.txt dòng {line_num}: Transcription rỗng")
                            
                            # Check if patch file exists
                            patch_full_path = dataset_folder / "patches" / patch_path
                            if not patch_full_path.exists():
                                self.log_error(f"[{dataset_folder.name}] Patch không tồn tại: {patch_path}")
                            else:
                                self.stats['matched_rec_entries'] += 1
                            
                            rec_entries[patch_path] = transcription
                            self.stats['total_rec_entries'] += 1
                            
                        except Exception as e:
                            self.log_error(f"[{dataset_folder.name}] rec_gt.txt dòng {line_num}: Lỗi - {str(e)}")
                            
            except Exception as e:
                self.log_error(f"[{dataset_folder.name}] Không thể đọc rec_gt.txt: {str(e)}")
            
            rec_data[dataset_folder.name] = rec_entries
            self.log_info(f"  [{dataset_folder.name}] Tìm thấy {len(rec_entries)} entries")
            
        self.log_success(f"Tổng số entries trong rec_gt: {self.stats['total_rec_entries']}")
        self.log_success(f"Số entries có patch file hợp lệ: {self.stats['matched_rec_entries']}")
        return rec_data
        
    def validate_puncs(self) -> Dict:
        """
        Kiểm tra folder puncs (dấu câu)
        """
        self.log_info("\n" + "=" * 80)
        self.log_info("5. KIỂM TRA FOLDER PUNCS")
        self.log_info("=" * 80)
        
        puncs_data = {}
        
        for dataset_folder in sorted(self.final_dataset.iterdir()):
            if not dataset_folder.is_dir():
                continue
                
            puncs_folder = dataset_folder / "puncs"
            if not puncs_folder.exists():
                self.log_error(f"[{dataset_folder.name}] Không tìm thấy folder puncs")
                continue
            
            punc_files = {}
            for punc_file in sorted(puncs_folder.glob("*.txt")):
                try:
                    with open(punc_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            punc_files[punc_file.name] = len(content.strip())
                            self.stats['total_puncs'] += 1
                        else:
                            self.log_warning(f"[{dataset_folder.name}] File puncs rỗng: {punc_file.name}")
                except Exception as e:
                    self.log_error(f"[{dataset_folder.name}] Lỗi khi đọc punc {punc_file.name}: {str(e)}")
            
            puncs_data[dataset_folder.name] = punc_files
            self.log_info(f"  [{dataset_folder.name}] Tìm thấy {len(punc_files)} puncs hợp lệ")
                        
        self.log_success(f"Tổng số puncs hợp lệ: {self.stats['total_puncs']}")
        return puncs_data
        
    def check_cross_consistency(self, dataset_images: Dict, det_data: Dict, patch_data: Dict, rec_data: Dict):
        """
        Kiểm tra tính nhất quán giữa các file
        """
        self.log_info("\n" + "=" * 80)
        self.log_info("6. KIỂM TRA TÍNH NHẤT QUÁN GIỮA CÁC FILE")
        self.log_info("=" * 80)
        
        for dataset_name in sorted(set(dataset_images.keys()) | set(det_data.keys())):
            # Check images vs det_gt
            if dataset_name in dataset_images and dataset_name in det_data:
                image_files = dataset_images[dataset_name]
                det_images = set(det_data[dataset_name].keys())
                
                missing_in_det = image_files - det_images
                if missing_in_det:
                    self.log_warning(f"[{dataset_name}] {len(missing_in_det)} ảnh không có trong det_gt.txt")
                
                missing_in_folder = det_images - image_files
                if missing_in_folder:
                    self.log_warning(f"[{dataset_name}] {len(missing_in_folder)} ảnh trong det_gt.txt nhưng không có file")
            
            # Check det_gt vs patches
            if dataset_name in det_data and dataset_name in patch_data:
                det_images = set(det_data[dataset_name].keys())
                patch_folders = set(patch_data[dataset_name].keys())
                
                missing_patches = det_images - patch_folders
                if missing_patches:
                    self.log_warning(f"[{dataset_name}] {len(missing_patches)} ảnh trong det_gt.txt không có patches folder")
                
                extra_patches = patch_folders - det_images
                if extra_patches:
                    self.log_warning(f"[{dataset_name}] {len(extra_patches)} patches folder không có trong det_gt.txt")
            
            # Check patches vs rec_gt
            if dataset_name in patch_data and dataset_name in rec_data:
                # Count total patches
                total_patches = sum(len(patches) for patches in patch_data[dataset_name].values())
                total_rec_entries = len(rec_data[dataset_name])
                
                if total_patches != total_rec_entries:
                    self.log_warning(
                        f"[{dataset_name}] Số lượng patches ({total_patches}) "
                        f"khác số entries trong rec_gt.txt ({total_rec_entries})"
                    )
        
        self.log_success("Hoàn thành kiểm tra tính nhất quán")
        
    def run_full_validation(self):
        """
        Chạy toàn bộ quá trình validation
        """
        self.log_info("🚀 BẮT ĐẦU KIỂM TRA DATASET")
        self.log_info(f"📁 Thư mục gốc: {self.root_dir}")
        
        if not self.final_dataset.exists():
            self.log_error(f"CRITICAL: Không tìm thấy thư mục 'Final_Dataset' trong {self.root_dir}")
            self.log_error("Vui lòng chọn đúng thư mục chứa folder 'Final_Dataset'")
            return False

        self.log_info(f"📁 Dataset: {self.final_dataset}\n")
        
        # 1. Validate images
        dataset_images = self.validate_images()
        
        # 2. Validate det_gt.txt
        det_data = self.validate_det_gt(dataset_images)
        
        # 3. Validate patches
        patch_data = self.validate_patches(det_data)
        
        # 4. Validate rec_gt.txt
        rec_data = self.validate_rec_gt(patch_data)
        
        # 5. Validate puncs
        puncs_data = self.validate_puncs()
        
        # 6. Check cross consistency
        self.check_cross_consistency(dataset_images, det_data, patch_data, rec_data)
        
        # 7. Generate summary
        self.generate_summary()
        
        return len(self.errors) == 0
    
    def generate_summary(self):
        """
        Tạo báo cáo tổng hợp
        """
        self.log_info("\n" + "=" * 80)
        self.log_info("📊 BÁO CÁO TỔNG HỢP")
        self.log_info("=" * 80)
        
        self.log_info(f"\n📈 THỐNG KÊ:")
        for key, value in sorted(self.stats.items()):
            self.log_info(f"  • {key}: {value}")
        
        self.log_info(f"\n📋 KẾT QUẢ:")
        self.log_info(f"  • Tổng số lỗi: {len(self.errors)}")
        self.log_info(f"  • Tổng số cảnh báo: {len(self.warnings)}")
        
        if len(self.errors) == 0:
            self.log_success("\n✅ DATASET HỢP LỆ - Không có lỗi!")
        else:
            self.log_error(f"\n❌ DATASET CÓ {len(self.errors)} LỖI - Cần kiểm tra và sửa chữa!")
        
        # Save to file
        self.save_report()
    
    def save_report(self):
        """Lưu báo cáo ra file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.root_dir / f"validation_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("BÁO CÁO KIỂM TRA DATASET\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Thư mục: {self.root_dir}\n\n")
            
            f.write("THỐNG KÊ:\n")
            for key, value in sorted(self.stats.items()):
                f.write(f"  {key}: {value}\n")
            
            f.write(f"\nTổng số lỗi: {len(self.errors)}\n")
            f.write(f"Tổng số cảnh báo: {len(self.warnings)}\n\n")
            
            if self.errors:
                f.write("CHI TIẾT LỖI:\n")
                f.write("-" * 80 + "\n")
                for i, error in enumerate(self.errors, 1):
                    f.write(f"{i}. {error}\n")
                f.write("\n")
            
            if self.warnings:
                f.write("CHI TIẾT CẢNH BÁO:\n")
                f.write("-" * 80 + "\n")
                for i, warning in enumerate(self.warnings, 1):
                    f.write(f"{i}. {warning}\n")
        
        self.log_info(f"\n✓ Báo cáo đã lưu tại: {report_file.name}")


class ValidationUI:
    """Giao diện đồ họa cho công cụ validation"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Dataset Validation Tool - NLP Final Project")
        self.root.geometry("1000x700")
        
        # Configure colors
        self.colors = {
            'bg': '#f0f0f0',
            'frame_bg': '#ffffff',
            'error': '#ff4444',
            'warning': '#ffaa00',
            'success': '#00aa00',
            'info': '#333333'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        self.setup_ui()
        self.validator = None
        self.validation_running = False
        
    def setup_ui(self):
        """Thiết lập giao diện"""
        # Title
        title_frame = tk.Frame(self.root, bg=self.colors['bg'])
        title_frame.pack(pady=10, fill=tk.X)
        
        title_label = tk.Label(
            title_frame,
            text="🔍 DATASET VALIDATION TOOL",
            font=("Arial", 18, "bold"),
            bg=self.colors['bg'],
            fg='#2c3e50'
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Kiểm tra độ chính xác của det_gt.txt, rec_gt.txt, patches, puncs, images",
            font=("Arial", 10),
            bg=self.colors['bg'],
            fg='#7f8c8d'
        )
        subtitle_label.pack()
        
        # Control Frame
        control_frame = tk.Frame(self.root, bg=self.colors['frame_bg'], relief=tk.RAISED, borderwidth=2)
        control_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # Path selection
        path_frame = tk.Frame(control_frame, bg=self.colors['frame_bg'])
        path_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(
            path_frame, 
            text="📁 Thư mục gốc:", 
            bg=self.colors['frame_bg'],
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT)
        
        self.path_var = tk.StringVar(value=str(Path(__file__).resolve().parent))
        self.path_entry = tk.Entry(path_frame, textvariable=self.path_var, font=("Consolas", 10))
        self.path_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        tk.Button(
            path_frame, 
            text="Chọn thư mục...", 
            command=self.browse_folder,
            cursor="hand2"
        ).pack(side=tk.LEFT)
        
        # Buttons
        button_frame = tk.Frame(control_frame, bg=self.colors['frame_bg'])
        button_frame.pack(pady=10)
        
        self.start_button = tk.Button(
            button_frame,
            text="▶ BẮT ĐẦU KIỂM TRA",
            command=self.start_validation,
            bg='#27ae60',
            fg='white',
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
            cursor="hand2",
            relief=tk.RAISED
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(
            button_frame,
            text="🗑 XÓA LOG",
            command=self.clear_log,
            bg='#e74c3c',
            fg='white',
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
            cursor="hand2",
            relief=tk.RAISED
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            control_frame,
            mode='indeterminate',
            length=300
        )
        self.progress.pack(pady=5)
        
        # Stats Frame
        stats_frame = tk.Frame(self.root, bg=self.colors['frame_bg'], relief=tk.RAISED, borderwidth=2)
        stats_frame.pack(pady=5, padx=20, fill=tk.X)
        
        self.stats_label = tk.Label(
            stats_frame,
            text="📊 Chưa có dữ liệu thống kê",
            font=("Arial", 10),
            bg=self.colors['frame_bg'],
            fg='#34495e',
            justify=tk.LEFT
        )
        self.stats_label.pack(pady=10, padx=10)
        
        # Log Frame
        log_frame = tk.Frame(self.root, bg=self.colors['frame_bg'], relief=tk.SUNKEN, borderwidth=2)
        log_frame.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        log_title = tk.Label(
            log_frame,
            text="📝 LOG KIỂM TRA",
            font=("Arial", 11, "bold"),
            bg=self.colors['frame_bg'],
            fg='#2c3e50'
        )
        log_title.pack(pady=5)
        
        # Scrolled text for logs
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=100,
            height=25,
            font=("Consolas", 9),
            bg='#2c3e50',
            fg='#ecf0f1',
            insertbackground='white'
        )
        self.log_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # Configure text tags for colors
        self.log_text.tag_config("error", foreground=self.colors['error'])
        self.log_text.tag_config("warning", foreground=self.colors['warning'])
        self.log_text.tag_config("success", foreground=self.colors['success'])
        self.log_text.tag_config("info", foreground='#ecf0f1')
        
    def log_message(self, message: str, tag: str = "info"):
        """Ghi message vào log text"""
        self.log_text.insert(tk.END, message, tag)
        self.log_text.see(tk.END)
        self.root.update()
        
    def clear_log(self):
        """Xóa log"""
        self.log_text.delete(1.0, tk.END)
        self.stats_label.config(text="📊 Chưa có dữ liệu thống kê")
        
    def browse_folder(self):
        """Chọn thư mục"""
        folder_selected = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder_selected:
            self.path_var.set(folder_selected)
        
    def start_validation(self):
        """Bắt đầu validation trong thread riêng"""
        if self.validation_running:
            messagebox.showwarning("Cảnh báo", "Đang có quá trình kiểm tra đang chạy!")
            return
        
        self.validation_running = True
        self.start_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.progress.start(10)
        self.clear_log()
        
        # Run in separate thread
        thread = threading.Thread(target=self.run_validation)
        thread.daemon = True
        thread.start()
        
    def run_validation(self):
        """Chạy validation"""
        try:
            root_dir = self.path_var.get()
            if not root_dir:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn thư mục dataset!")
                self.validation_running = False
                self.progress.stop()
                self.start_button.config(state=tk.NORMAL)
                self.clear_button.config(state=tk.NORMAL)
                return

            self.validator = DatasetValidator(root_dir, log_callback=self.log_message)
            
            success = self.validator.run_full_validation()
            
            # Update stats
            stats_text = "📊 THỐNG KÊ:\n"
            for key, value in sorted(self.validator.stats.items()):
                stats_text += f"  • {key}: {value}\n"
            stats_text += f"\n❌ Lỗi: {len(self.validator.errors)}  |  ⚠️ Cảnh báo: {len(self.validator.warnings)}"
            
            self.stats_label.config(text=stats_text)
            
            # Show result dialog
            if success:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Thành công",
                    f"✅ Dataset hợp lệ!\n\n"
                    f"Tổng số kiểm tra:\n"
                    f"  • Images: {self.validator.stats.get('total_images', 0)}\n"
                    f"  • Patches: {self.validator.stats.get('total_patches', 0)}\n"
                    f"  • Puncs: {self.validator.stats.get('total_puncs', 0)}\n"
                    f"  • Det entries: {self.validator.stats.get('total_det_entries', 0)}\n"
                    f"  • Rec entries: {self.validator.stats.get('total_rec_entries', 0)}"
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror(
                    "Có lỗi",
                    f"❌ Phát hiện {len(self.validator.errors)} lỗi và {len(self.validator.warnings)} cảnh báo!\n\n"
                    f"Vui lòng xem log để biết chi tiết."
                ))
                
        except Exception as e:
            self.log_message(f"CRITICAL ERROR: {str(e)}\n", "error")
            self.root.after(0, lambda: messagebox.showerror("Lỗi nghiêm trọng", f"Có lỗi xảy ra:\n{str(e)}"))
        finally:
            self.validation_running = False
            self.progress.stop()
            self.start_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)


def main():
    """Main function"""
    root = tk.Tk()
    app = ValidationUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
