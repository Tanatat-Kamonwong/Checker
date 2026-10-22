import csv
import re
from collections import defaultdict
import statistics

class DeliveryChecker:
    def __init__(self, d1_path, d2_path):
        self.expected_shots = {}
        self.shot_data = defaultdict(lambda: defaultdict(dict))
        self.valid_exts = {'exr', 'png', 'jpg', 'jpeg', 'dpx', 'tif', 'tiff'}
        
        self._load_d1(d1_path)
        self._load_d2(d2_path)

    def _load_d1(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                self.expected_shots[row['shot_code']] = (int(row['first_frame']), int(row['last_frame']))

    def _load_d2(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                parts = row['relative_path'].split('/')
                if len(parts) < 3: continue
                
                shot_code, version_folder, file_name = parts[0], parts[-2], parts[-1]
                
                if file_name.startswith('.') or file_name.split('.')[-1].lower() not in self.valid_exts:
                    continue
                    
                match_v = re.match(r'^v(\d+)$', version_folder, re.IGNORECASE)
                match_f = re.search(r'\.(\d+)\.[^.]+$', file_name)
                
                if match_v and match_f:
                    version_num = int(match_v.group(1))
                    frame_num = int(match_f.group(1))
                    self.shot_data[shot_code][version_num][frame_num] = int(row['size_bytes'])

    def get_total_missing_frames(self):
        total_missing = 0
        for shot, (first, last) in self.expected_shots.items():
            expected_frames = set(range(first, last + 1))
            if shot not in self.shot_data:
                total_missing += len(expected_frames)
                continue
                
            latest_version = max(self.shot_data[shot].keys())
            total_missing += len(expected_frames - self.shot_data[shot][latest_version].keys())
            
        return total_missing

    def _compress_ranges(self, nums):
        if not nums: return ""
        nums = sorted(list(nums))
        ranges = []
        start = prev = nums[0]
        
        for n in nums[1:]:
            if n == prev + 1:
                prev = n
            else:
                ranges.append(str(start) if start == prev else f"{start}-{prev}")
                start = prev = n
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        return ",".join(ranges)

    def get_missing_ranges(self, shot_code):
        if shot_code not in self.expected_shots:
            return f"Error: {shot_code} not found in D1 list."
            
        first, last = self.expected_shots[shot_code]
        expected_frames = set(range(first, last + 1))
        
        if shot_code not in self.shot_data:
            return self._compress_ranges(expected_frames)
            
        latest_version = max(self.shot_data[shot_code].keys())
        missing_frames = expected_frames - self.shot_data[shot_code][latest_version].keys()
        
        return self._compress_ranges(missing_frames)
    def get_total_corrupt_r6(self):
        total_corrupt = 0
        
        for shot, (first, last) in self.expected_shots.items():
            if shot not in self.shot_data:
                continue
                
            expected_frames = set(range(first, last + 1))
            latest_version = max(self.shot_data[shot].keys())
            latest_files = self.shot_data[shot][latest_version] #dict {เฟรม: ขนาดไฟล์}
            
            # 1. ดึงขนาดไฟล์เฉพาะ "เฟรมที่คาดหวัง" มาคำนวณ Median
            valid_sizes = []
            for f in expected_frames:
                if f in latest_files:
                    valid_sizes.append(latest_files[f])
            if not valid_sizes:
                continue
                
            # 2. หาค่ามัธยฐาน และตั้งเกณฑ์ 0.10
            med_size = statistics.median(valid_sizes)
            threshold = 0.10 * med_size
            
            # 3. เช็คหาเฟรมเสีย
            for f in expected_frames:
                if f in latest_files:
                    size = latest_files[f]
                    if size == 0 or size < threshold:
                        total_corrupt += 1              
        return total_corrupt
    def get_total_corrupt_r9(self):
        total_corrupt = 0
        
        for shot, (first, last) in self.expected_shots.items():
            if shot not in self.shot_data:
                continue
                
            expected_frames = set(range(first, last + 1))
            latest_version = max(self.shot_data[shot].keys())
            latest_files = self.shot_data[shot][latest_version]
            
            for f in expected_frames:
                if f in latest_files:
                    size = latest_files[f]
                    
                    if size == 0:
                        total_corrupt += 1
                        continue
                        
                    neighbour_frames = [f-3, f-2, f-1, f+1, f+2, f+3]
                    neighbour_sizes = []
                    
                    for nf in neighbour_frames:
                        if (nf in expected_frames) and (nf in latest_files):
                            neighbour_sizes.append(latest_files[nf])
                            
                    if neighbour_sizes:
                        med_size = statistics.median(neighbour_sizes)
                        if size < (0.5 * med_size):
                            total_corrupt += 1
        return total_corrupt
    def evaluate_rules(self, d3_path):
        # 1. ตั้งค่าตัวนับสถิติ (TP = ทายถูกว่าเสีย, FP = ทายผิดว่าเสีย, FN = เสียจริงแต่ทายว่าไม่เสีย)
        r6_tp = r6_fp = r6_fn = 0
        r9_tp = r9_fp = r9_fn = 0
        
        with open(d3_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                path = row['relative_path']
                truth_corrupt = int(row['is_corrupt']) # 1 = เสียจริง, 0 = ปกติ
                
                parts = path.split('/')
                shot_code = parts[0]
                version_folder = parts[-2]
                file_name = parts[-1]
                
                match_v = re.match(r'^v(\d+)$', version_folder, re.IGNORECASE)
                match_f = re.search(r'\.(\d+)\.[^.]+$', file_name)
                
                if not (match_v and match_f): continue
                    
                version_num = int(match_v.group(1))
                frame_num = int(match_f.group(1))
                
                if shot_code not in self.shot_data or version_num not in self.shot_data[shot_code]: continue
                    
                latest_files = self.shot_data[shot_code][version_num]
                if frame_num not in latest_files: continue
                    
                size = latest_files[frame_num]
                
                # --- ทดสอบทายด้วยกฎ R6 ---
                r6_pred = 0
                if shot_code in self.expected_shots:
                    first, last = self.expected_shots[shot_code]
                    expected_frames = set(range(first, last + 1))
                    valid_sizes = [latest_files[f] for f in expected_frames if f in latest_files]
                    
                    if valid_sizes:
                        med_r6 = statistics.median(valid_sizes)
                        if size == 0 or size < (0.10 * med_r6):
                            r6_pred = 1 # ทายว่าเสีย
                
                # --- ทดสอบทายด้วยกฎ R9 ---
                r9_pred = 0
                if size == 0:
                    r9_pred = 1 # ขนาด 0 เสียเสมอ
                elif shot_code in self.expected_shots:
                    first, last = self.expected_shots[shot_code]
                    expected_frames = set(range(first, last + 1))
                    
                    # เช็คเพื่อนบ้าน f-3 ถึง f+3
                    neighbour_frames = [frame_num-3, frame_num-2, frame_num-1, frame_num+1, frame_num+2, frame_num+3]
                    n_sizes = [latest_files[nf] for nf in neighbour_frames if nf in expected_frames and nf in latest_files]
                    
                    if n_sizes:
                        med_r9 = statistics.median(n_sizes)
                        if size < (0.5 * med_r9):
                            r9_pred = 1 # ทายว่าเสีย
                                
                # --- ตรวจคำตอบเทียบกับเฉลย (Ground Truth) ---
                # เช็คคะแนน R6
                if r6_pred == 1 and truth_corrupt == 1: r6_tp += 1
                elif r6_pred == 1 and truth_corrupt == 0: r6_fp += 1
                elif r6_pred == 0 and truth_corrupt == 1: r6_fn += 1
                
                # เช็คคะแนน R9
                if r9_pred == 1 and truth_corrupt == 1: r9_tp += 1
                elif r9_pred == 1 and truth_corrupt == 0: r9_fp += 1
                elif r9_pred == 0 and truth_corrupt == 1: r9_fn += 1

                #print(f"R6 - TP: {r6_tp}, FP: {r6_fp}, FN: {r6_fn}")
                #print(f"R9 - TP: {r9_tp}, FP: {r9_fp}, FN: {r9_fn}")
                
        # 2. ฟังก์ชันคำนวณ F1 Score ตามสูตร
        def calc_f1(tp, fp, fn):
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            if precision + recall == 0: return 0
            return 2 * precision * recall / (precision + recall)
            
        r6_f1 = calc_f1(r6_tp, r6_fp, r6_fn)
        r9_f1 = calc_f1(r9_tp, r9_fp, r9_fn)
        
        # คืนค่าเป็น String ปัดเศษคูณ 100 คั่นด้วย /
        return f"{round(r6_f1 * 100)}/{round(r9_f1 * 100)}"
    def export_json_report(self, output_filename="report.json"):
        import json
        report_data = {
            "total_missing": self.get_total_missing_frames(),
            "total_corrupt_r6": self.get_total_corrupt_r6(),
            "total_corrupt_r9": self.get_total_corrupt_r9(),
            "status": "FAILED" if self.get_total_missing_frames() > 0 or self.get_total_corrupt_r9() > 0 else "PASSED"
        }
        with open(output_filename, 'w') as f:
            json.dump(report_data, f, indent=4)
        print(f"JSON Report exported to {output_filename}")

if __name__ == "__main__":
    checker = DeliveryChecker('D1_shot_list.csv', 'D2_delivery_manifest.csv')
    
    #Create Object
    checker = DeliveryChecker('D1_shot_list.csv', 'D2_delivery_manifest.csv')
    
    #Lock D1
    print(f"Lock D1 (Total Missing): {checker.get_total_missing_frames()}")
    
    #Lock D2
    target_shot = 'SH040' #Reusable ขอแค่เปลี่ยนShotตรงนี้
    print(f"Lock D2 ({target_shot} Missing): {checker.get_missing_ranges(target_shot)}")
    
    #Lock D3
    print(f"Lock D3 (Total Corrupt R6): {checker.get_total_corrupt_r6()}")

    #R9
    print(f"Total Corrupt (R9): {checker.get_total_corrupt_r9()}")

    #Lock D4 (F1 Score R6/R9)
    print(f"Lock D4 (F1 Score R6/R9): {checker.evaluate_rules('D3_labelled_sample.csv')}")

    checker.export_json_report()

    