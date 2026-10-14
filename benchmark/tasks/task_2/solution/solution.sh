#!/usr/bin/env bash
set -euo pipefail

echo "[*] Task: List and extract all archives in current directory (/app)"
echo "[*] Step 1: Listing all archive files..."

# List all archive files in current directory (/app)
find . -maxdepth 1 -type f \( -name "*.zip" -o -name "*.tar" -o -name "*.tar.gz" -o -name "*.tgz" \) | sort

echo ""
echo "[*] Step 2: Extracting each archive..."

# Extract each archive found (use read to handle paths safely)
while IFS= read -r archive; do
    echo ""
    echo "[*] Extracting: $archive"
    
    # Get the base name without extension
    base_name=$(basename "$archive" .zip)
    base_name=$(basename "$base_name" .tar.gz)
    base_name=$(basename "$base_name" .tgz)
    base_name=$(basename "$base_name" .tar)
    
    # Create extraction directory
    extract_dir="${base_name}_extracted"
    mkdir -p "$extract_dir"
    
    # Extract based on file type
    if [[ "$archive" == *.zip ]]; then
        unzip -q "$archive" -d "$extract_dir"
        echo "  ✓ Extracted ZIP archive to $extract_dir"
    elif [[ "$archive" == *.tar.gz ]] || [[ "$archive" == *.tgz ]]; then
        tar -xzf "$archive" -C "$extract_dir"
        echo "  ✓ Extracted TAR.GZ archive to $extract_dir"
    elif [[ "$archive" == *.tar ]]; then
        tar -xf "$archive" -C "$extract_dir"
        echo "  ✓ Extracted TAR archive to $extract_dir"
    fi
    
    # List extracted contents
    echo "  Contents:"
    find "$extract_dir" -type f | head -10 | sed 's/^/    /'
    if [ "$(find "$extract_dir" -type f | wc -l)" -gt 10 ]; then
        echo "    ... (and more)"
    fi
done < <(find . -maxdepth 1 -type f \( -name "*.zip" -o -name "*.tar" -o -name "*.tar.gz" -o -name "*.tgz" \) | sort)

echo ""
echo "[✓] All archives have been listed and extracted successfully."
