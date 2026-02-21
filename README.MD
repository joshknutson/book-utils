# Book-Utils: Automated E-Book Converter & Fixer

A lightweight, Dockerized Python utility designed to maintain a healthy e-book library. It bridges the gap between different formats (AZW3/MOBI to EPUB) and automatically repairs malformed EPUBs that fail to open on devices like Amazon Kindle.

## 🌟 Features

* **State-Aware Gap Filling:** Scans your library for folders containing `.azw3` or `.mobi` files that lack a corresponding `.epub`.
* **Kindle Integrity Validation:** Uses `epubcheck` to verify that EPUB files meet industry standards.
* **Auto-Fix Logic:** Automatically "re-bakes" broken EPUBs using Calibre's conversion engine with a Kindle-optimized output profile.
* **Safety First:** Creates `.original.epub` backups before attempting any repairs to ensure non-destructive automation.
* **Scheduled Maintenance:** Run conversion and validation on separate daily schedules.

## 🚀 Quick Start

### Docker Compose (Recommended)

```yaml
services:
  book-utils:
    image: ghcr.io/joshknutson/book-utils:latest
    container_name: book-utils
    environment:
      - TZ=America/Chicago
      - DRY_RUN=false
      - CONVERT_TIME=02:00      # Time for gap-fill scan (24hr)
      - VALIDATE_TIME=04:00     # Time for integrity/fix scan (24hr)
      - SKIP_CONVERSION=false
      - SKIP_VALIDATION=false
    volumes:
      - /data/media/books:/books
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
```

### ⚙️ Configuration (Environment Variables)

Variable,Default,Description
DRY_RUN,true,"If true, logs actions without modifying files."
CONVERT_TIME,02:00,24hr time for the AZW3/MOBI to EPUB conversion scan.
VALIDATE_TIME,04:00,24hr time for the EPUB integrity check and auto-fix.
SKIP_CONVERSION,false,Disable the gap-filling conversion logic.
SKIP_VALIDATION,false,Disable the EPUBCheck and auto-fix logic.

### 🛠️ How it Works
1. The Conversion Engine
The tool uses the Calibre CLI (ebook-convert) to perform high-quality conversions. When a gap is found, it generates an EPUB from the highest-quality source available in the folder.

2. The Validation Engine
Using EPUBCheck (Java-based), the script scans existing EPUBs. If a file is found to be malformed (missing manifests, CSS errors, etc.), it triggers the Auto-Fix routine.

3. The Auto-Fix Routine
To ensure Kindle compatibility, the script:

Copies the file to a local temporary workspace on the container's SSD.

Renames the original on the host to .original.epub.

Re-processes the file using the --output-profile kindle flag.

Pushes the sanitized EPUB back to the library.