#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running React performance optimization tests..."

# Check if node_modules exists (dependencies installed)
if [ ! -d "node_modules" ]; then
    echo "[✗] ERROR: node_modules not found - dependencies not installed"
    exit 1
fi

echo "[✓] Dependencies installed"

# Check if webpack config has been optimized
echo "[*] Checking webpack configuration optimizations..."

# Check for code splitting configuration
if ! grep -q "splitChunks" webpack.config.js 2>/dev/null; then
    echo "[!] WARNING: No code splitting configuration found in webpack.config.js"
    echo "    Consider adding splitChunks optimization"
fi

# Check for production mode or optimization settings
if grep -q "mode.*production" webpack.config.js 2>/dev/null || grep -q "optimization" webpack.config.js 2>/dev/null; then
    echo "[✓] Webpack optimization settings found"
else
    echo "[!] WARNING: Webpack may not be optimized for production"
fi

# Build the application
echo "[*] Building application..."
if npm run build 2>&1 | tee build.log; then
    echo "[✓] Build completed successfully"
else
    echo "[✗] ERROR: Build failed"
    exit 1
fi

# Check if dist directory exists and has files
if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    echo "[✗] ERROR: dist directory is empty or missing"
    exit 1
fi

echo "[✓] Build output exists"

# Check bundle size (should be reasonable after optimization)
echo "[*] Checking bundle size..."
BUNDLE_SIZE=$(du -sb dist 2>/dev/null | cut -f1)
BUNDLE_SIZE_MB=$((BUNDLE_SIZE / 1024 / 1024))

echo "    Bundle size: ${BUNDLE_SIZE_MB} MB"

# Warn if bundle is extremely large (over 5MB suggests no optimization)
if [ "$BUNDLE_SIZE_MB" -gt 5 ]; then
    echo "[!] WARNING: Bundle size is very large (${BUNDLE_SIZE_MB} MB)"
    echo "    Consider code splitting and tree shaking"
fi

# Check for multiple chunk files (code splitting required)
CHUNK_COUNT=$(find dist -name "*.js" -type f | wc -l)
echo "    JavaScript chunks: ${CHUNK_COUNT}"

if [ "$CHUNK_COUNT" -lt 2 ]; then
    echo "[✗] ERROR: Code splitting not implemented (only ${CHUNK_COUNT} JS file found)"
    echo "    Add splitChunks optimization to webpack.config.js"
    exit 1
fi
echo "[✓] Multiple chunks found (code splitting implemented)"

# Check largest bundle size (should be under 500KB after optimization)
echo "[*] Checking largest bundle size..."
LARGEST_BUNDLE=$(find dist -name "*.js" -type f -exec stat -c%s {} \; 2>/dev/null | sort -rn | head -1)

if [ -n "$LARGEST_BUNDLE" ]; then
    LARGEST_SIZE_KB=$((LARGEST_BUNDLE / 1024))
    echo "    Largest bundle size: ${LARGEST_SIZE_KB} KB"

    if [ "$LARGEST_SIZE_KB" -gt 700 ]; then
        echo "[✗] ERROR: Largest bundle is too large (${LARGEST_SIZE_KB} KB > 700 KB)"
        echo "    Consider more aggressive code splitting"
        exit 1
    fi
    echo "[✓] Bundle sizes are acceptable (< 700 KB)"
else
    echo "[✗] ERROR: Could not find any JS bundles"
    exit 1
fi

# Check if Dashboard component has been optimized
echo "[*] Checking component optimizations..."

if grep -q "React.memo\|useMemo\|useCallback" src/components/Dashboard.tsx 2>/dev/null; then
    echo "[✓] React optimization hooks found in Dashboard component"
else
    echo "[!] WARNING: No React optimization hooks (memo, useMemo, useCallback) found"
    echo "    Consider optimizing component re-renders"
fi

# Check if lodash and moment are being used efficiently
if grep -q "import.*lodash\|import.*moment" src/components/Dashboard.tsx 2>/dev/null; then
    echo "[!] WARNING: Full lodash/moment imports detected"
    echo "    Consider using tree-shakeable imports or alternatives"
fi

echo "[✓] All tests passed!"
exit 0
