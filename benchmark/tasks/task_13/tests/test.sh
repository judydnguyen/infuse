#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running file organization tests..."

DOWNLOADS_DIR="Downloads"

# Check if Downloads directory exists
if [ ! -d "$DOWNLOADS_DIR" ]; then
    echo "[✗] ERROR: Downloads directory not found"
    exit 1
fi

echo "[✓] Found Downloads directory"

# Check if files have been organized into folders by type
echo "[*] Checking if files are organized by type..."

EXPECTED_FOLDERS=("Images" "Documents" "Videos" "Audio" "Applications" "Archives" "Other")

FOLDERS_FOUND=0
for folder in "${EXPECTED_FOLDERS[@]}"; do
    if [ -d "$DOWNLOADS_DIR/$folder" ]; then
        echo "[✓] Found folder: $folder"
        FOLDERS_FOUND=$((FOLDERS_FOUND + 1))
    fi
done

if [ "$FOLDERS_FOUND" -eq 0 ]; then
    echo "[✗] ERROR: No organization folders found"
    echo "    Expected folders like: Images, Documents, Videos, Audio, Applications"
    exit 1
fi

echo "[✓] Found $FOLDERS_FOUND organization folders"

# Check if files are in appropriate folders
echo "[*] Checking file organization..."

# Check images
if [ -d "$DOWNLOADS_DIR/Images" ]; then
    IMAGE_FILES=$(find "$DOWNLOADS_DIR/Images" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" -o -name "*.bmp" \) 2>/dev/null | wc -l)
    if [ "$IMAGE_FILES" -gt 0 ]; then
        echo "[✓] Found $IMAGE_FILES image files in Images folder"
    fi
fi

# Check documents
if [ -d "$DOWNLOADS_DIR/Documents" ]; then
    DOC_FILES=$(find "$DOWNLOADS_DIR/Documents" -type f \( -name "*.pdf" -o -name "*.doc" -o -name "*.docx" -o -name "*.txt" -o -name "*.md" \) 2>/dev/null | wc -l)
    if [ "$DOC_FILES" -gt 0 ]; then
        echo "[✓] Found $DOC_FILES document files in Documents folder"
    fi
fi

# Check videos
if [ -d "$DOWNLOADS_DIR/Videos" ]; then
    VIDEO_FILES=$(find "$DOWNLOADS_DIR/Videos" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mov" -o -name "*.mkv" \) 2>/dev/null | wc -l)
    if [ "$VIDEO_FILES" -gt 0 ]; then
        echo "[✓] Found $VIDEO_FILES video files in Videos folder"
    fi
fi

# Check audio
if [ -d "$DOWNLOADS_DIR/Audio" ]; then
    AUDIO_FILES=$(find "$DOWNLOADS_DIR/Audio" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.flac" -o -name "*.ogg" \) 2>/dev/null | wc -l)
    if [ "$AUDIO_FILES" -gt 0 ]; then
        echo "[✓] Found $AUDIO_FILES audio files in Audio folder"
    fi
fi

# Check applications
if [ -d "$DOWNLOADS_DIR/Applications" ]; then
    APP_FILES=$(find "$DOWNLOADS_DIR/Applications" -type f \( -name "*.exe" -o -name "*.dmg" -o -name "*.deb" -o -name "*.rpm" \) 2>/dev/null | wc -l)
    if [ "$APP_FILES" -gt 0 ]; then
        echo "[✓] Found $APP_FILES application files in Applications folder"
    fi
fi

# Check for duplicates - verify that duplicates have been removed
echo "[*] Checking for duplicate files..."

# Known duplicates in the original Downloads folder:
# - photo1.jpg and photo1_1.jpg (likely duplicates)
# - report.pdf and report_copy.pdf (likely duplicates)
# - screenshot.png and Screen Shot 2024-01-15 at 3.45.23 PM.png (might be duplicates)

DUPLICATES_FOUND=0

# Check if both photo1.jpg and photo1_1.jpg exist
if [ -f "$DOWNLOADS_DIR/Images/photo1.jpg" ] && [ -f "$DOWNLOADS_DIR/Images/photo1_1.jpg" ]; then
    echo "[!] WARNING: Both photo1.jpg and photo1_1.jpg found - may be duplicates"
    DUPLICATES_FOUND=$((DUPLICATES_FOUND + 1))
fi

# Check if both report.pdf and report_copy.pdf exist
if [ -f "$DOWNLOADS_DIR/Documents/report.pdf" ] && [ -f "$DOWNLOADS_DIR/Documents/report_copy.pdf" ]; then
    echo "[!] WARNING: Both report.pdf and report_copy.pdf found - may be duplicates"
    DUPLICATES_FOUND=$((DUPLICATES_FOUND + 1))
fi

# Count files in root Downloads directory (should be minimal or empty after organization)
ROOT_FILES=$(find "$DOWNLOADS_DIR" -maxdepth 1 -type f 2>/dev/null | wc -l)
if [ "$ROOT_FILES" -gt 0 ]; then
    echo "[!] WARNING: $ROOT_FILES files still in root Downloads directory"
    echo "    Files should be organized into subfolders"
fi

# Check that original files are no longer in root (they should be in organized folders)
ORIGINAL_FILES=("contract.pdf" "invoice.pdf" "notes.txt" "photo1.jpg" "photo2.png" "report.pdf" "tutorial.mp4" "song.mp3" "setup.exe" "installer.dmg")
FILES_IN_ROOT=0
for file in "${ORIGINAL_FILES[@]}"; do
    if [ -f "$DOWNLOADS_DIR/$file" ]; then
        echo "[!] WARNING: $file still in root Downloads directory"
        FILES_IN_ROOT=$((FILES_IN_ROOT + 1))
    fi
done

if [ "$FILES_IN_ROOT" -gt 0 ]; then
    echo "[✗] ERROR: $FILES_IN_ROOT original files still in root Downloads directory"
    echo "    All files should be organized into appropriate subfolders"
    exit 1
fi

echo "[✓] No original files remaining in root Downloads directory"

# Verify that files exist in organized folders
FILES_IN_FOLDERS=0
for folder in "${EXPECTED_FOLDERS[@]}"; do
    if [ -d "$DOWNLOADS_DIR/$folder" ]; then
        COUNT=$(find "$DOWNLOADS_DIR/$folder" -type f 2>/dev/null | wc -l)
        if [ "$COUNT" -gt 0 ]; then
            FILES_IN_FOLDERS=$((FILES_IN_FOLDERS + COUNT))
            echo "[✓] $folder contains $COUNT files"
        fi
    fi
done

if [ "$FILES_IN_FOLDERS" -eq 0 ]; then
    echo "[✗] ERROR: No files found in organized folders"
    exit 1
fi

echo "[✓] Found $FILES_IN_FOLDERS files in organized folders"

# Summary
echo "[*] Summary:"
echo "    Organization folders: $FOLDERS_FOUND"
echo "    Files organized: $FILES_IN_FOLDERS"
echo "    Files in root: $ROOT_FILES"
echo "    Potential duplicates: $DUPLICATES_FOUND"

if [ "$FILES_IN_ROOT" -eq 0 ] && [ "$FILES_IN_FOLDERS" -gt 0 ]; then
    echo "[✓] All tests passed! Files have been organized successfully."
    exit 0
else
    echo "[✗] ERROR: File organization incomplete"
    exit 1
fi
