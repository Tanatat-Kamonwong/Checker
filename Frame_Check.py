import csv, re
from collections import defaultdict
import statistics

print("--- เริ่มการค้นหาเฟรมตัวอย่าง... ---")

# 1. อ่านข้อมูลจาก D2
shot_data = defaultdict(lambda: defaultdict(dict))
try:
    with open('D2_delivery_manifest.csv', 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            parts = row['relative_path'].split('/')
            if len(parts) >= 3:
                shot, ver, fname = parts[0], parts[-2], parts[-1]
                mv = re.match(r'^v(\d+)$', ver, re.IGNORECASE)
                mf = re.search(r'\.(\d+)\.[^.]+$', fname)
                if mv and mf:
                    shot_data[shot][int(mv.group(1))][int(mf.group(1))] = int(row['size_bytes'])
    print("อ่านข้อมูล D2 สำเร็จ กำลังเทียบกับ D3...")
except FileNotFoundError:
    print("Error: หาไฟล์ D2_delivery_manifest.csv ไม่เจอ")

# 2. อ่าน D3 หาจุดที่ R6 พลาด แต่ R9 จับได้
found = False
try:
    with open('D3_labelled_sample.csv', 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if int(row['is_corrupt']) == 1:
                parts = row['relative_path'].split('/')
                shot, fname = parts[0], parts[-1]
                mf = re.search(r'\.(\d+)\.[^.]+$', fname)
                
                if mf and shot in shot_data:
                    f_num = int(mf.group(1))
                    latest_v = max(shot_data[shot].keys())
                    files = shot_data[shot][latest_v]
                    
                    if f_num in files:
                        size = files[f_num]
                        med_r6 = statistics.median(files.values())
                        
                        # ถ้ารอด R6 (ขนาดใหญ่กว่า 10% ของทั้งช็อต)
                        if size >= 0.10 * med_r6:
                            neighbours = [f_num-3, f_num-2, f_num-1, f_num+1, f_num+2, f_num+3]
                            n_sizes = [files[nf] for nf in neighbours if nf in files]
                            
                            if n_sizes:
                                med_r9 = statistics.median(n_sizes)
                                # แต่โดน R9 จับได้ (เล็กกว่า 50% ของเพื่อนบ้าน)
                                if size < 0.5 * med_r9:
                                    print(f"\n🎯 เจอเฟรมตัวอย่างแล้ว! นำข้อมูลนี้ไปอ้างอิงได้เลย:")
                                    print(f"Shot: {shot} | Frame: {f_num}")
                                    print(f"ขนาดไฟล์จริง: {size:,.0f} Bytes")
                                    print(f"เกณฑ์ผ่าน R6 (10% ของทั้งช็อต): {0.10*med_r6:,.0f} Bytes -> รอดการตรวจจับ")
                                    print(f"เกณฑ์ผ่าน R9 (50% ของเพื่อนบ้าน): {0.5*med_r9:,.0f} Bytes -> ตรวจพบว่าเสีย")
                                    found = True
                                    break
        if not found:
            print("\nไม่พบเฟรมที่ตรงตามเงื่อนไข ลองตรวจสอบข้อมูลดูอีกครั้ง")
except FileNotFoundError:
    print("Error: หาไฟล์ D3_labelled_sample.csv ไม่เจอ")

print("--- จบการทำงาน ---")