# Code này dùng để sao chép toàn bộ ảnh từ thư mục data sang thư mục images 
import os
import shutil

def collect_images(source_dir, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Đã tạo thư mục: {target_dir}")
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    count = 0
    
    print(f"Đang tìm kiếm ảnh trong '{source_dir}'...")
    
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                source_path = os.path.join(root, file)
                target_path = os.path.join(target_dir, file)
                
                if os.path.exists(target_path):
                    base, extension = os.path.splitext(file)
                    idx = 1
                    while os.path.exists(target_path):
                        new_name = f"{base}_{idx}{extension}"
                        target_path = os.path.join(target_dir, new_name)
                        idx += 1
                
                shutil.copy2(source_path, target_path)
                count += 1
                
    print(f"Hoàn tất! Tổng số ảnh đã sao chép: {count}")


def merge_json_files(source_dir, output_file):
    import json
    print(f"Đang gộp các file JSON từ '{source_dir}'...")
    all_books = []
    
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('_images.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        all_books.append(data)
                except Exception as e:
                    print(f"Lỗi khi đọc file {file_path}: {e}")
    
    # Sắp xếp theo book_id
    all_books.sort(key=lambda x: x.get('book_id', ''))
                    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_books, f, ensure_ascii=False, indent=2)
        
    print(f"Đã gộp {len(all_books)} file vào '{output_file}'")

if __name__ == "__main__":
    source = "Data"
    target = "images"
    collect_images(source, target)
    merge_json_files(source, os.path.join(target, "metadata.json"))
