import os, subprocess, time, schedule
from pathlib import Path
from epubcheck import EpubCheck

# Configuration from Docker Compose
LIBRARY_PATH = "/books"
EXTENSIONS_TO_CONVERT = {".azw3", ".mobi", ".azw"}
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
SKIP_CONVERSION = os.getenv("SKIP_CONVERSION", "false").lower() == "true"
SKIP_VALIDATION = os.getenv("SKIP_VALIDATION", "false").lower() == "true"
CONVERT_TIME = os.getenv("CONVERT_TIME", "02:00")
VALIDATE_TIME = os.getenv("VALIDATE_TIME", "04:00")

def auto_fix_epub(file_path):
    print(f"🛠️ Attempting auto-fix on {file_path}...")
    
    # Define paths
    original_backup = str(file_path).replace(".epub", ".original.epub")
    temp_fix = str(file_path).replace(".epub", ".fix.epub")
    
    # 1. Skip if we've already backed up (prevents infinite loops/double processing)
    if os.path.exists(original_backup):
        print(f"⏭️ Skipping: Original backup already exists for {file_path}")
        return

    # 2. Run the conversion with Kindle-optimized profile
    cmd = ['ebook-convert', file_path, temp_fix, '--output-profile', 'kindle']
    
    try:
        subprocess.run(cmd, check=True)
        
        # 3. Rename current file to .original.epub
        os.rename(file_path, original_backup)
        
        # 4. Move the fixed version to the primary .epub name
        os.rename(temp_fix, file_path)
        
        print(f"✅ Auto-fixed and backed up original: {original_backup}")
        
    except Exception as e:
        print(f"❌ Auto-fix failed: {e}")
        if os.path.exists(temp_fix):
            os.remove(temp_fix)

def run_integrity_check():
    if SKIP_VALIDATION: return
    print(f"--- Starting Integrity Scan: {time.strftime('%H:%M:%S')} ---")
    for root, _, files in os.walk(LIBRARY_PATH):
        for file in files:
            if file.lower().endswith(".epub"):
                path = os.path.join(root, file)
                result = EpubCheck(path)
                if not result.valid:
                    print(f"🚩 Broken EPUB found: {file}")
                    if not DRY_RUN:
                        auto_fix_epub(path)

def scan_and_convert():
    if SKIP_CONVERSION: return
    print(f"--- Starting Conversion Scan: {time.strftime('%H:%M:%S')} ---")
    for root, _, files in os.walk(LIBRARY_PATH):
        files_in_folder = {Path(f).suffix.lower() for f in files}
        if ".epub" not in files_in_folder:
            for file in files:
                time.sleep(5)
                if Path(file).suffix.lower() in EXTENSIONS_TO_CONVERT:
                    in_p = os.path.join(root, file)
                    out_p = os.path.join(root, Path(file).stem + ".epub")
                    if DRY_RUN:
                        print(f"[DRY RUN] Would convert: {file}")
                    else:
                        try:
                            subprocess.run(['ebook-convert', in_p, out_p], check=True)
                            print(f"✅ Created: {out_p}")
                        except Exception as e: print(f"❌ Error: {e}")
                    break

if __name__ == "__main__":
    schedule.every().day.at(CONVERT_TIME).do(scan_and_convert)
    schedule.every().day.at(VALIDATE_TIME).do(run_integrity_check)
    
    # Run once at startup for immediate feedback
    scan_and_convert()
    run_integrity_check()

    while True:
        schedule.run_pending()
        time.sleep(60)