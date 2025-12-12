import os
import json
import cv2
import shutil
import numpy as np
import pandas as pd

# Cấu hình
IMAGE_DIR = "images"
LABEL_FILE = "images/Label.txt"
METADATA_FILE = "images/metadata.json"
OUTPUT_ROOT = "Final_Dataset"
ERROR_FILE = "error.txt"

# các hàm hỗ trợ IO
def read_image_unicode(path):
    try:
        stream = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(stream, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error reading image {path}: {e}")
        return None

def write_image_unicode(path, img):
    try:
        is_success, im_buf = cv2.imencode(".jpg", img)
        if is_success:
            im_buf.tofile(path)
            return True
        return False
    except Exception as e:
        print(f"Error writing image {path}: {e}")
        return False

# Các hàm xư lý hình ảnh
def order_points(pts):
    """
    Sắp xếp 4 điểm theo thứ tự: Top-Left, Top-Right, Bottom-Right, Bottom-Left
    """
    rect = np.zeros((4, 2), dtype="float32")
    
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def crop_perspective_and_rotate(img, box_points):
    pts = np.array(box_points, dtype="float32")
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    if maxWidth <= 0 or maxHeight <= 0:
        return None

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))

    img_rotated = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    
    return img_rotated

# Các hàm xử lý chính
def load_metadata(meta_path):
    with open(meta_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    meta_map = {}
    for book in data:
        book_id = book.get('book_id', 'Unknown')
        book_name = book.get('book_name', 'Unknown')
        folder_name = f"{book_name}_{book_id}"
        
        for img in book.get('images', []):
            image_id = img.get('image_id', '')
            filename = f"{book_id}_{image_id}.jpg"
            
            # clean_text dùng để khớp với box và gán nhãn từng patch
            clean_text = img.get('clean_text', '')
            lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            
            # Dùng cho file puncs (giữ nguyên gốc, chỉ chuẩn hóa dòng)
            original_text = img.get('original_text', '')
            # strip khoảng trắng 2 đầu dòng và loại bỏ dòng rỗng
            original_lines = [line.strip() for line in original_text.split('\n') if line.strip()]
            
            meta_map[filename] = {
                "lines": lines,               # Dùng cho patches/rec_gt
                "original_lines": original_lines, # Dùng cho puncs
                "folder_name": folder_name
            }
    return meta_map

def parse_label_file(label_path):
    labels = []
    with open(label_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('\t')
            if len(parts) < 2: continue
            
            img_path = parts[0]
            json_str = parts[1]
            try:
                boxes = json.loads(json_str)
                labels.append((img_path, boxes))
            except:
                print(f"Lỗi parse JSON: {img_path}")
    return labels

def sort_boxes_right_to_left(boxes):
    def get_center_x(box):
        points = np.array(box['points'])
        return np.mean(points[:, 0])
    return sorted(boxes, key=get_center_x, reverse=True)

def main():
    if os.path.exists(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT)
    os.makedirs(OUTPUT_ROOT)
    
    meta_map = load_metadata(METADATA_FILE)
    labels = parse_label_file(LABEL_FILE)
    
    error_list = []
    processed_count = 0
    total_boxes = 0
    book_results = {}

    for img_rel_path, boxes in labels:
        filename = os.path.basename(img_rel_path.replace('\\', '/'))
        
        if filename not in meta_map:
            print(f"Skipping (No Metadata): {filename}")
            continue
            
        meta_info = meta_map[filename]
        ground_truth_lines = meta_info['lines']      # Clean text cho boxes
        original_lines = meta_info['original_lines'] # Original text cho puncs
        folder_name = meta_info['folder_name']
        
        # Kiểm tra khớp số lượng box
        if len(boxes) != len(ground_truth_lines):
            err = f"{filename}\tBoxes: {len(boxes)} != Lines: {len(ground_truth_lines)}"
            error_list.append(err)
            print(f"[SKIP] {filename}: Box count mismatch")
            continue
            
        book_dir = os.path.join(OUTPUT_ROOT, folder_name)
        img_out_dir = os.path.join(book_dir, "images")
        patch_out_dir = os.path.join(book_dir, "patches")
        punc_out_dir = os.path.join(book_dir, "puncs")
        
        for d in [img_out_dir, patch_out_dir, punc_out_dir]:
            os.makedirs(d, exist_ok=True)
        
        src_img_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(src_img_path):
             src_img_path = img_rel_path
        
        img = read_image_unicode(src_img_path)
        if img is None:
            continue
            
        shutil.copy(src_img_path, os.path.join(img_out_dir, filename))

        sorted_boxes = sort_boxes_right_to_left(boxes)
        rec_gt_lines = []
        det_json_list = []
        
        # Xử lý patches
        for idx, (box, text_content) in enumerate(zip(sorted_boxes, ground_truth_lines)):
            patch_filename = f"{os.path.splitext(filename)[0]}.{idx+1:03d}.jpg"
            patch_path = os.path.join(patch_out_dir, patch_filename)
            
            final_patch = crop_perspective_and_rotate(img, box['points'])
            
            if final_patch is not None:
                write_image_unicode(patch_path, final_patch)
                
                rel_patch_path = f"{folder_name}/patches/{patch_filename}"
                rec_gt_lines.append(f"{rel_patch_path}\t{text_content}")
                
                det_json_list.append({
                    "transcription": text_content,
                    "points": box['points']
                })
                
                if folder_name not in book_results:
                    book_results[folder_name] = []
                book_results[folder_name].append({
                    "Image ID": filename,
                    "Patch ID": patch_filename,
                    "Bounding Box": str(box['points']),
                    "Sino-Nom OCR": text_content
                })
            else:
                print(f"Error cropping: {patch_filename}")

        # Ghi file puncs
        with open(os.path.join(punc_out_dir, f"{os.path.splitext(filename)[0]}.txt"), 'w', encoding='utf-8') as f:
            f.write("\n".join(original_lines))

        with open(os.path.join(book_dir, "rec_gt.txt"), 'a', encoding='utf-8') as f:
            for line in rec_gt_lines:
                f.write(line + "\n")
        
        rel_img_path = f"{folder_name}/images/{filename}"
        with open(os.path.join(book_dir, "det_gt.txt"), 'a', encoding='utf-8') as f:
            f.write(f"{rel_img_path}\t{json.dumps(det_json_list, ensure_ascii=False)}\n")
        
        processed_count += 1
        total_boxes += len(boxes)
        print(f"Processed: {filename} ({len(boxes)} boxes)")

    if error_list:
        with open(ERROR_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(error_list))
    
    for folder_name, results in book_results.items():
        if results:
            df = pd.DataFrame(results)
            book_dir = os.path.join(OUTPUT_ROOT, folder_name)
            df.to_excel(os.path.join(book_dir, "results.xlsx"), index=False, columns=["Image ID", "Patch ID", "Bounding Box", "Sino-Nom OCR"])

    print(f"\n\nSố ảnh: {processed_count} / {len(labels)}")
    print(f"Số boxes: {total_boxes}")

if __name__ == "__main__":
    main()