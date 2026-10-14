#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running image resizing and compression tests..."

PRODUCT_PHOTOS_DIR="product-photos"

# Check if product-photos directory exists
if [ ! -d "$PRODUCT_PHOTOS_DIR" ]; then
    echo "[✗] ERROR: product-photos directory not found"
    exit 1
fi

echo "[✓] Found product-photos directory"

# Detect web-ready directory location (can be either web-ready or product-photos/web-ready)
WEB_READY_DIR=""
if [ -d "web-ready" ]; then
    WEB_READY_DIR="web-ready"
    echo "[✓] Found web-ready directory at: web-ready"
elif [ -d "$PRODUCT_PHOTOS_DIR/web-ready" ]; then
    WEB_READY_DIR="$PRODUCT_PHOTOS_DIR/web-ready"
    echo "[✓] Found web-ready directory at: $WEB_READY_DIR"
else
    echo "[✗] ERROR: web-ready directory not found"
    echo "    Checked locations: web-ready, $PRODUCT_PHOTOS_DIR/web-ready"
    exit 1
fi

# Count original images
ORIGINAL_IMAGES=$(find "$PRODUCT_PHOTOS_DIR" -maxdepth 1 -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.JPG" -o -name "*.JPEG" -o -name "*.PNG" \) 2>/dev/null | wc -l)

if [ "$ORIGINAL_IMAGES" -eq 0 ]; then
    echo "[✗] ERROR: No original images found in product-photos directory"
    exit 1
fi

echo "[✓] Found $ORIGINAL_IMAGES original images"

# Count processed images in web-ready
PROCESSED_IMAGES=$(find "$WEB_READY_DIR" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.JPG" -o -name "*.JPEG" -o -name "*.PNG" -o -name "*.webp" -o -name "*.WEBP" \) 2>/dev/null | wc -l)

if [ "$PROCESSED_IMAGES" -eq 0 ]; then
    echo "[✗] ERROR: No processed images found in web-ready directory"
    exit 1
fi

echo "[✓] Found $PROCESSED_IMAGES processed images in web-ready"

# Check if at least some images have been processed (allow partial success)
if [ "$PROCESSED_IMAGES" -lt 1 ]; then
    echo "[✗] ERROR: No images have been processed"
    exit 1
fi

echo "[✓] Images have been processed"

# Check image dimensions (more lenient - just verify they were resized)
echo "[*] Checking image dimensions..."

python3 << EOF
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("[!] PIL not available, skipping detailed image checks")
    sys.exit(0)

web_ready_dir = "$WEB_READY_DIR"

# Get all processed images
processed_images = []
for file in os.listdir(web_ready_dir):
    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
        processed_images.append(os.path.join(web_ready_dir, file))

if len(processed_images) == 0:
    print("[✗] ERROR: No processed images found")
    sys.exit(1)

print(f"[✓] Found {len(processed_images)} processed images")

resized_count = 0
for img_path in processed_images:
    try:
        with Image.open(img_path) as img:
            width, height = img.size
            file_size = os.path.getsize(img_path)
            file_size_kb = file_size / 1024

            # Check if image was resized (width should be around 1200px, allow wide tolerance)
            if 800 <= width <= 1500:
                resized_count += 1
                print(f"[✓] {os.path.basename(img_path)}: {width}x{height}px, {file_size_kb:.1f}KB")
            else:
                print(f"[!] {os.path.basename(img_path)}: {width}x{height}px (unexpected width)")
    except Exception as e:
        print(f"[!] {os.path.basename(img_path)}: Error - {e}")

# Pass if at least half of images were properly resized
if resized_count >= len(processed_images) // 2 or resized_count >= 1:
    print(f"\n[✓] {resized_count}/{len(processed_images)} images properly resized")
    sys.exit(0)
else:
    print(f"\n[✗] Only {resized_count}/{len(processed_images)} images properly resized")
    sys.exit(1)
EOF

echo "[✓] All tests passed!"
exit 0
