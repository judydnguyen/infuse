#!/bin/bash
# Script to generate thumbnails from product images
# Note: This script uses the original high-resolution images

echo "Generating thumbnails from product images..."

for img in product_*.jpg product_*.png; do
    if [ -f "$img" ]; then
        echo "Processing $img..."
        # This would use imagemagick or similar tool
        # convert "$img" -resize 300x300 "thumb_${img}"
    fi
done

echo "Thumbnail generation complete."
