
import os
import json
import shutil
import random

FINAL_DATASET_DIR = r"d:\My files\HK5\Natural Language processing\Final\CWKB"
NOMNAOCR_DIR = r"d:\My files\HK5\Natural Language processing\Final\NomNaOCR"
OUTPUT_DIR = r"d:\My files\HK5\Natural Language processing\Final\Dataset"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

all_entries = []

if os.path.exists(FINAL_DATASET_DIR):
    for sub_dir_name in os.listdir(FINAL_DATASET_DIR):
        sub_dir_path = os.path.join(FINAL_DATASET_DIR, sub_dir_name)
        if not os.path.isdir(sub_dir_path):
            continue
        
        gt_file_path = os.path.join(sub_dir_path, "det_gt.txt")
        if not os.path.exists(gt_file_path):
            continue

        with open(gt_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    parts = line.split('\t', 1)
                    if len(parts) != 2: continue
                    rel_path_in_gt, label = parts
                    
                    abs_src_path = os.path.join(FINAL_DATASET_DIR, rel_path_in_gt)
                    
                    if not os.path.exists(abs_src_path):
                        img_name = os.path.basename(rel_path_in_gt)
                        potential_path = os.path.join(sub_dir_path, "images", img_name)
                        if os.path.exists(potential_path):
                            abs_src_path = potential_path
                        else:
                            continue
                            
                    all_entries.append({
                        'src_path': abs_src_path,
                        'label': label,
                        'book_name': sub_dir_name,
                        'is_test': False
                    })
                except:
                    continue

nomna_pages_dir = os.path.join(NOMNAOCR_DIR, "Pages")
validate_txt_path = os.path.join(nomna_pages_dir, "Validate.txt")
test_files_set = set()

if os.path.exists(validate_txt_path):
    with open(validate_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if parts:
                path_key = parts[0].replace('\\', '/')
                test_files_set.add(path_key)

if os.path.exists(nomna_pages_dir):
    for book_name in os.listdir(nomna_pages_dir):
        book_dir = os.path.join(nomna_pages_dir, book_name)
        if not os.path.isdir(book_dir): continue
        
        imgs_dir = os.path.join(book_dir, "imgs")
        gts_dir = os.path.join(book_dir, "gts")
        
        if not os.path.exists(imgs_dir) or not os.path.exists(gts_dir):
            continue
            
        for img_file in os.listdir(imgs_dir):
            if not img_file.lower().endswith(('.jpg', '.png', '.jpeg')):
                continue
            
            src_img_path = os.path.join(imgs_dir, img_file)
            gt_filename = os.path.splitext(img_file)[0] + ".txt"
            gt_path = os.path.join(gts_dir, gt_filename)
            
            if not os.path.exists(gt_path):
                continue
                
            labels_list = []
            try:
                with open(gt_path, 'r', encoding='utf-8') as gf:
                    for cline in gf:
                        cline = cline.strip()
                        if not cline: continue
                        cparts = cline.split(',', 8)
                        if len(cparts) >= 9:
                            points = [
                                [float(cparts[0]), float(cparts[1])],
                                [float(cparts[2]), float(cparts[3])],
                                [float(cparts[4]), float(cparts[5])],
                                [float(cparts[6]), float(cparts[7])]
                            ]
                            transcription = cparts[8]
                            labels_list.append({'transcription': transcription, 'points': points})
            except:
                continue
                
            if not labels_list:
                continue
            
            rel_key = f"{book_name}/imgs/{img_file}".replace('\\', '/')
            is_test = rel_key in test_files_set
            
            all_entries.append({
                'src_path': src_img_path,
                'label': json.dumps(labels_list, ensure_ascii=False),
                'book_name': book_name,
                'is_test': is_test
            })

test_entries = [e for e in all_entries if e['is_test']]
pool_entries = [e for e in all_entries if not e['is_test']]

random.seed(42)
random.shuffle(pool_entries)
split_idx = int(len(pool_entries) * 0.8)
train_entries = pool_entries[:split_idx]
val_entries = pool_entries[split_idx:]

def process_subset(entries, subset_name):
    print(f"Processing {subset_name} ({len(entries)} files)...")
    subset_dir = os.path.join(OUTPUT_DIR, subset_name)
    images_dir = os.path.join(subset_dir, "images")
    gt_path = os.path.join(subset_dir, "det_gt.txt")
    
    ensure_dir(images_dir)
    
    with open(gt_path, 'w', encoding='utf-8') as f_gt:
        for entry in entries:
            orig_filename = os.path.basename(entry['src_path'])
            
            # Đổi thành <tên sách>_<tên ảnh>.<ext>
            new_filename = f"{entry['book_name']}_{orig_filename}"
            
            dest_path = os.path.join(images_dir, new_filename)
            
            # Copy file
            if not os.path.exists(dest_path):
                shutil.copy2(entry['src_path'], dest_path)
            
            # Write to GT
            gt_rel_path = f"images/{new_filename}"
            f_gt.write(f"{gt_rel_path}\t{entry['label']}\n")

process_subset(train_entries, "Train")
process_subset(val_entries, "Val")
process_subset(test_entries, "Test")
