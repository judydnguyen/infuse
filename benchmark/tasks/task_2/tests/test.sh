#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running archive extraction tests..."

# Check for archive files in current directory (/app)
if [ ! -d "/app" ]; then
    echo "[✗] ERROR: /app directory not found"
    exit 1
fi

# Find all archive files in /app
archives=$(find /app -maxdepth 1 -type f \( -name "*.zip" -o -name "*.tar" -o -name "*.tar.gz" -o -name "*.tgz" \) 2>/dev/null || true)

if [ -z "$archives" ]; then
    echo "[✗] ERROR: No archive files found in /app"
    exit 1
fi

echo "[✓] Found archive files:"
echo "$archives" | sed 's/^/  /'

# Check if archives were extracted
extracted_count=0
for archive in $archives; do
    base_name=$(basename "$archive")
    base_name="${base_name%.zip}"
    base_name="${base_name%.tar.gz}"
    base_name="${base_name%.tgz}"
    base_name="${base_name%.tar}"
    
    extract_dir="/app/${base_name}_extracted"
    
    if [ -d "$extract_dir" ] && [ "$(ls -A $extract_dir 2>/dev/null)" ]; then
        echo "[✓] Archive $base_name extracted to $extract_dir"
        extracted_count=$((extracted_count + 1))
    else
        echo "[✗] WARNING: Archive $base_name not extracted or extraction directory is empty"
    fi
done

archive_count=$(echo "$archives" | wc -l)

if [ "$extracted_count" -eq "$archive_count" ]; then
    echo "[✓] All $archive_count archives have been extracted successfully"
    exit 0
else
    echo "[✗] ERROR: Only $extracted_count out of $archive_count archives were extracted"
    exit 1
fi
