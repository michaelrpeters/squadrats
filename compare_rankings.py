import os
import glob
import csv
import shutil
from datetime import datetime

def parse_stat(val):
    if not isinstance(val, str) or val in ['N/A', '0', '', None]:
        return None
    if '×' in val:
        val = val.split('×')[0]
    elif 'x' in val.lower():
        val = val.lower().split('x')[0]
    cleaned = val.replace(',', '').strip()
    try:
        return int(float(cleaned))
    except ValueError:
        return None

def parse_number(val):
    if not isinstance(val, str) or val in ['N/A', '0', '', None]:
        return None
    cleaned = val.replace('#', '').replace(',', '').strip()
    try:
        return int(float(cleaned))
    except ValueError:
        return None

def compare_rankings():
    # --- 1. FIND THE TWO MOST RECENT FILES ---
    files = glob.glob("squadrats_rankings_*.csv")
    files.sort(reverse=True)
    
    if len(files) < 2:
        print("Not enough data! Run the scraper at least twice to compare.")
        return

    new_file = files[0]
    old_file = files[1]

    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_lines = []
    log_lines.append("==================================================")
    log_lines.append(f"Date: {run_timestamp}")
    log_lines.append(f"Comparing New: {new_file}")
    log_lines.append(f"Against Old:   {old_file}")
    log_lines.append("--------------------------------------------------")

    # --- 2. LOAD THE DATA ---
    old_data = {}
    with open(old_file, mode='r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            old_data[row['Region']] = row

    new_data = {}
    with open(new_file, mode='r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            new_data[row['Region']] = row

    # --- 3. COMPARE COUNTS AND RANKS ---
    categories = ['Squadrats', 'Squadratinhos', 'Übersquadrat', 'Übersquadratinho', 'Yard', 'Yardinho']
    improvements_found = False
    
    for region, new_row in new_data.items():
        if region in old_data:
            old_row = old_data[region]
            region_improvements = []
            
            for cat in categories:
                rank_key = f"{cat} Rank"
                count_key = f"{cat} Count"
                
                new_rank_str = new_row.get(rank_key, 'N/A')
                old_rank_str = old_row.get(rank_key, 'N/A')
                new_count_str = new_row.get(count_key, '0')
                old_count_str = old_row.get(count_key, '0')
                
                new_count_val = parse_stat(new_count_str)
                old_count_val = parse_stat(old_count_str)
                
                if new_count_val is not None and old_count_val is not None:
                    if new_count_val > old_count_val:
                        gained = new_count_val - old_count_val
                        if '×' in new_count_str or 'x' in new_count_str.lower():
                            region_improvements.append(f"  • {cat} Size: Grew by {gained}! (from {old_count_str} to {new_count_str})")
                        else:
                            region_improvements.append(f"  • {cat} Tiles: Collected {gained} new tiles! (from {old_count_str} to {new_count_str})")
                            
                new_rank_val = parse_number(new_rank_str)
                old_rank_val = parse_number(old_rank_str)
                
                if new_rank_val is not None and old_rank_val is not None:
                    if new_rank_val < old_rank_val:
                        climbed = old_rank_val - new_rank_val
                        region_improvements.append(f"  • {cat} Rank: Climbed {climbed} spot(s) (from {old_rank_str} to {new_rank_str})")
                elif new_rank_val is not None and old_rank_val is None:
                    region_improvements.append(f"  • {cat} Rank: NEW RANKING! You are now {new_rank_str}")

            if region_improvements:
                improvements_found = True
                log_lines.append(f"🏆 {region}")
                for imp in region_improvements:
                    log_lines.append(imp)
                log_lines.append("")

    if not improvements_found:
        log_lines.append("No ranking or tile improvements found between these two files.\n")

    final_output = "\n".join(log_lines) + "\n"
    print(final_output)
    
    log_file_path = "squadrats_progress_log.txt"
    with open(log_file_path, mode='a', encoding='utf-8') as f:
        f.write(final_output)
        
    print(f"(Progress successfully appended to {log_file_path})")

    # --- 4. CLEAN UP OLD FILES ---
    print("\nArchiving older CSV files...")
    os.makedirs("data", exist_ok=True)
    
    # files[2:] grabs everything EXCEPT the two newest files
    for old_csv in files[2:]:
        destination = os.path.join("data", old_csv)
        # Overwrite if it already exists in the archive
        if os.path.exists(destination):
            os.remove(destination)
        shutil.move(old_csv, destination)
        print(f"Moved {old_csv} to data/")

if __name__ == "__main__":
    compare_rankings()