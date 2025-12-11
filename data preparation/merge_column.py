# Code này dùng để gộp các box cùng cột vào cùng một box
# để giảm thiểu số box phải chỉnh sửa tay
import os
import json
import shutil

def get_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)

def is_same_column(box1, box2):
    min_x1, max_x1, _, _ = box1
    min_x2, max_x2, _, _ = box2
    
    center_x1 = (min_x1 + max_x1) / 2
    center_x2 = (min_x2 + max_x2) / 2
    
    cond1 = min_x2 <= center_x1 <= max_x2
    cond2 = min_x1 <= center_x2 <= max_x1
    
    return cond1 or cond2

def merge_boxes(boxes_data):
    if not boxes_data:
        return []

    n = len(boxes_data)
    adj = [[] for _ in range(n)]
    
    # Precompute bounding boxes
    bboxes = [get_bbox(item['points']) for item in boxes_data]
    
    for i in range(n):
        for j in range(i + 1, n):
            if is_same_column(bboxes[i], bboxes[j]):
                adj[i].append(j)
                adj[j].append(i)
    
    visited = [False] * n
    merged_data = []
    
    for i in range(n):
        if not visited[i]:
            component = []
            stack = [i]
            visited[i] = True
            while stack:
                u = stack.pop()
                component.append(u)
                for v in adj[u]:
                    if not visited[v]:
                        visited[v] = True
                        stack.append(v)
            
            if len(component) == 1:
                merged_data.append(boxes_data[component[0]])
            else:
                component.sort(key=lambda idx: bboxes[idx][2]) 
                
                all_points = []
                transcriptions = []
                difficult = False
                
                for idx in component:
                    all_points.extend(boxes_data[idx]['points'])
                    transcriptions.append(boxes_data[idx]['transcription'])
                    if boxes_data[idx]['difficult']:
                        difficult = True
                
                min_x = min(p[0] for p in all_points)
                max_x = max(p[0] for p in all_points)
                min_y = min(p[1] for p in all_points)
                max_y = max(p[1] for p in all_points)
                
                new_points = [[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y]]
                new_transcription = " ".join(transcriptions)
                
                merged_data.append({
                    "transcription": new_transcription,
                    "points": new_points,
                    "difficult": difficult
                })
                
    return merged_data

def process_folder(folder_path):
    label_path = os.path.join(folder_path, "Label.txt")
    if not os.path.exists(label_path):
        print(f"Label.txt not found in {folder_path}")
        return

    print(f"Processing {label_path}...")
    
    with open(label_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        parts = line.split('\t')
        if len(parts) < 2:
            new_lines.append(line)
            continue
            
        filename = parts[0]
        try:
            json_str = parts[1]
            boxes_data = json.loads(json_str)
            merged_boxes = merge_boxes(boxes_data)
            new_json_str = json.dumps(merged_boxes, ensure_ascii=False)
            new_lines.append(f"{filename}\t{new_json_str}")
        except Exception as e:
            print(f"Error processing line for {filename}: {e}")
            new_lines.append(line)
            
    old_label_path = os.path.join(folder_path, "old_label.txt")
    shutil.move(label_path, old_label_path)
    print(f"Renamed {label_path} to {old_label_path}")
    
    with open(label_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')
    print(f"Written new {label_path}")

def main():
    folders = ['images']
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for folder in folders:
        folder_path = os.path.join(base_dir, folder)
        if os.path.exists(folder_path):
            process_folder(folder_path)
        else:
            print(f"Folder {folder} not found.")

if __name__ == "__main__":
    main()
