import csv
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import statistics

def plot_shot_sizes_r6(d2_path, target_shot):
    valid_exts = {'exr', 'png', 'jpg', 'jpeg', 'dpx', 'tif', 'tiff'}
    shot_versions = defaultdict(dict)

    # 1. อ่านไฟล์และกรองข้อมูล
    with open(d2_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            parts = row['relative_path'].split('/')
            if len(parts) < 3: continue
            
            shot_code = parts[0]
            if shot_code != target_shot:
                continue
                
            version_folder, file_name = parts[-2], parts[-1]
            if file_name.startswith('.') or file_name.split('.')[-1].lower() not in valid_exts:
                continue
                
            match_v = re.match(r'^v(\d+)$', version_folder, re.IGNORECASE)
            match_f = re.search(r'\.(\d+)\.[^.]+$', file_name)
            
            if match_v and match_f:
                v_num, f_num = int(match_v.group(1)), int(match_f.group(1))
                shot_versions[v_num][f_num] = int(row['size_bytes'])

    if not shot_versions:
        print(f"Error: ไม่พบข้อมูลของ {target_shot}")
        return

    latest_version = max(shot_versions.keys())
    frame_data = shot_versions[latest_version]

    frames = sorted(frame_data.keys())
    sizes = [frame_data[f] for f in frames]
    
    # 2. คำนวณค่ามัธยฐานและเกณฑ์ 10% ของกฎ R6
    med_size = statistics.median(sizes)
    r6_threshold = 0.10 * med_size

    # 3. ตั้งค่าและแสดงผลกร๊าฟ
    plt.figure(figsize=(12, 6))
    plt.plot(frames, sizes, marker='.', linestyle='-', color='#2ca02c', label=f'{target_shot} (v{latest_version})')
    
    # วาดเส้นมัธยฐาน (สีส้ม) และเส้นเกณฑ์ R6 (สีแดงหนา)
    plt.axhline(y=med_size, color='orange', linestyle='--', linewidth=1.5, label=f'Median Size: {med_size:,.0f} Bytes')
    plt.axhline(y=r6_threshold, color='red', linestyle='-', linewidth=2.5, label=f'R6 Threshold (10%): {r6_threshold:,.0f} Bytes')
    
    plt.title(f"Frame Sizes vs R6 Rule - {target_shot}", fontsize=14, fontweight='bold')
    plt.xlabel("Frame Number", fontsize=12)
    plt.ylabel("File Size (Bytes)", fontsize=12)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.ticklabel_format(style='plain', axis='y')
    plt.legend()
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_shot_sizes_r6('D2_delivery_manifest.csv', 'SH030')