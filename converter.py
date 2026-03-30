import os, subprocess, time, schedule, sys, argparse, zipfile, re, shutil
from pathlib import Path
from epubcheck import EpubCheck

# Configuration from Docker Compose
LIBRARY_PATH = "/books"
EXTENSIONS_TO_CONVERT = {".azw3", ".mobi", ".azw"}
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
SKIP_CONVERSION = os.getenv("SKIP_CONVERSION", "false").lower() == "true"
SKIP_VALIDATION = os.getenv("SKIP_VALIDATION", "false").lower() == "true"
GENERATE_AZW3 = os.getenv("GENERATE_AZW3", "false").lower() == "true"
EPUB_VERSION = os.getenv("EPUB_VERSION", None)
CONVERT_TIME = os.getenv("CONVERT_TIME", "02:00")
VALIDATE_TIME = os.getenv("VALIDATE_TIME", "04:00")

def sanitize_epub(epub_path):
    print(f"🧹 Sanitizing EPUB to remove Kindle-breaking HTML tags: {epub_path}")
    temp_zip = str(epub_path) + ".tmp.zip"

    with zipfile.ZipFile(epub_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename.lower().endswith(('.html', '.xhtml', '.xml', '.opf', '.ncx')):
                text = content.decode('utf-8', errors='ignore')

                # Strip <wbr> / <wbr/>
                text = re.sub(r'<wbr\s*/?>', '', text)

                # Strip Amazon-specific removed attributes
                text = re.sub(r'\sdata-AmznRemoved(?:-M8)?="[^"]*"', '', text)

                # Strip other epub validation errors
                text = re.sub(r'\srole="[^"]*"', '', text)
                # Ensure we don't blanket strip epub:prefix/type because EPUB 3 requires epub:type="toc"

                # Fix colons in target XML IDs
                def fix_id(match):
                    return ' id="' + match.group(1).replace(':', '_') + '"'
                text = re.sub(r'\sid="([^"]+:[^"]+)"', fix_id, text)

                zout.writestr(item, text.encode('utf-8'))
            else:
                zout.writestr(item, content)

    shutil.move(temp_zip, epub_path)
    print(f"✅ EPUB Sanitization complete.")

def auto_fix_epub(file_path):
    print(f"🛠️ Attempting auto-fix on {file_path}...")

    # Define paths
    original_backup = str(file_path).replace(".epub", ".original.epub")
    temp_fix = str(file_path).replace(".epub", ".fix.epub")

    # 1. Skip if we've already backed up (prevents infinite loops/double processing)
    if os.path.exists(original_backup):
        print(f"⭐ Skipping: Original backup already exists for {file_path}")
        return

    # 2. Run the conversion with Kindle-optimized profile
    cmd = ['ebook-convert', file_path, temp_fix, '--output-profile', 'kindle']
    if EPUB_VERSION:
        cmd.extend(['--epub-version', EPUB_VERSION])

    try:
        subprocess.run(cmd, check=True)

        sanitize_epub(temp_fix)

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
                    # Skip files that are already backups (contain .original)
                    if ".original" in file.lower():
                        print(f"⭐ Skipping: File appears to be an original/backup: {file}")
                        continue
                    path = os.path.join(root, file)
                    try:
                        result = EpubCheck(path)
                        if not result.valid:
                            print(f"🚩 Broken EPUB found: {file}")
                            if not DRY_RUN:
                                auto_fix_epub(path)

                        if GENERATE_AZW3 and not DRY_RUN:
                            azw3_path = str(path).replace(".epub", ".azw3")
                            if not os.path.exists(azw3_path):
                                print(f"📱 Generating AZW3 format: {azw3_path}...")
                                try:
                                    subprocess.run(['ebook-convert', path, azw3_path, '--output-profile', 'kindle'], check=True)
                                    print(f"✅ Generated AZW3 successfully: {azw3_path}")
                                except Exception as e:
                                    print(f"❌ AZW3 generation failed: {e}")
                                    if os.path.exists(azw3_path):
                                        os.remove(azw3_path)
                    except Exception as e:
                        print(f"❌ Error checking {file}: {e}")

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
                        cmd = ['ebook-convert', in_p, out_p]
                        if EPUB_VERSION:
                            cmd.extend(['--epub-version', EPUB_VERSION])
                        try:
                            subprocess.run(cmd, check=True)
                            print(f"✅ Created: {out_p}")
                        except Exception as e: print(f"❌ Error: {e}")
                    break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Book-Utils Converter")
    parser.add_argument("folder", nargs="?", help="Optional specific folder to scan and fix immediately")
    parser.add_argument("--epub-version", type=str, choices=["2", "3", "4"], help="Set the generated EPUB version")    
    parser.add_argument("--generate-azw3", action="store_true", help="Generate a .azw3 file alongside the fixed .epub")
    args = parser.parse_args()

    if args.generate_azw3:
        GENERATE_AZW3 = True

    if args.epub_version:
        EPUB_VERSION = args.epub_version

    if args.folder:
        if os.path.exists(args.folder):
            LIBRARY_PATH = args.folder
            print(f"🎯 Running one-time scan on specific folder: {LIBRARY_PATH}")
            scan_and_convert()
            run_integrity_check()
        else:
            print(f"❌ Error: Folder not found: {args.folder}")
            sys.exit(1)
    else:
        schedule.every().day.at(CONVERT_TIME).do(scan_and_convert)
        schedule.every().day.at(VALIDATE_TIME).do(run_integrity_check)

        # Run once at startup for immediate feedback
        scan_and_convert()
        run_integrity_check()

        while True:
            schedule.run_pending()
            time.sleep(60)
