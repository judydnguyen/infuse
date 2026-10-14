#!/usr/bin/env bash
set -e

cd /app/my-python-tool

echo "[*] Running README generation tests..."

# Check if README.md exists
if [ ! -f "README.md" ]; then
    echo "[✗] ERROR: README.md not found"
    exit 1
fi

echo "[✓] Found README.md"

# Check if README.md is not empty
if [ ! -s "README.md" ]; then
    echo "[✗] ERROR: README.md is empty"
    exit 1
fi

echo "[✓] README.md is not empty"

# Check for required sections
echo "[*] Checking for required sections in README.md..."

REQUIRED_SECTIONS=("description" "installation" "usage" "example")

FOUND_SECTIONS=0
README_CONTENT=$(cat README.md | tr '[:upper:]' '[:lower:]')

for section in "${REQUIRED_SECTIONS[@]}"; do
    if echo "$README_CONTENT" | grep -qi "$section"; then
        echo "[✓] Found section related to: $section"
        FOUND_SECTIONS=$((FOUND_SECTIONS + 1))
    else
        echo "[!] WARNING: Section related to '$section' not found"
    fi
done

if [ "$FOUND_SECTIONS" -lt 2 ]; then
    echo "[✗] ERROR: README.md is missing required sections"
    echo "    Expected at least: description, installation, usage, examples"
    exit 1
fi

echo "[✓] Found $FOUND_SECTIONS required sections"

# Check for project description
echo "[*] Checking for project description..."

if echo "$README_CONTENT" | grep -qi "python.*tool\|data.*process\|data.*valid"; then
    echo "[✓] Project description found"
else
    echo "[!] WARNING: Project description may be missing or incomplete"
fi

# Check for installation instructions
echo "[*] Checking for installation instructions..."

if echo "$README_CONTENT" | grep -qi "install\|pip\|setup\|requirements"; then
    echo "[✓] Installation instructions found"
else
    echo "[!] WARNING: Installation instructions may be missing"
fi

# Check for usage examples
echo "[*] Checking for usage examples..."

if echo "$README_CONTENT" | grep -qi "usage\|example\|command\|--input\|--output"; then
    echo "[✓] Usage examples found"
else
    echo "[!] WARNING: Usage examples may be missing"
fi

# Check if README mentions main modules
echo "[*] Checking if README mentions project structure..."

MODULES=("core" "utils" "cli" "processor" "validator")

MODULES_MENTIONED=0
for module in "${MODULES[@]}"; do
    if echo "$README_CONTENT" | grep -qi "$module"; then
        MODULES_MENTIONED=$((MODULES_MENTIONED + 1))
    fi
done

if [ "$MODULES_MENTIONED" -gt 0 ]; then
    echo "[✓] README mentions $MODULES_MENTIONED project modules/components"
else
    echo "[!] WARNING: README may not describe project structure"
fi

# Check for code examples or command examples
echo "[*] Checking for code/command examples..."

if grep -qE "```|python|bash|command|example" README.md; then
    echo "[✓] Code or command examples found"
else
    echo "[!] WARNING: Code examples may be missing"
fi

# Validate README is well-formatted (basic checks)
echo "[*] Validating README format..."

# Check if it starts with a title (usually #)
if head -1 README.md | grep -q "^#"; then
    echo "[✓] README starts with a title"
else
    echo "[!] WARNING: README may not start with a proper title"
fi

# Check minimum length (should be substantial)
LINE_COUNT=$(wc -l < README.md)
if [ "$LINE_COUNT" -lt 10 ]; then
    echo "[!] WARNING: README seems very short ($LINE_COUNT lines)"
else
    echo "[✓] README has sufficient content ($LINE_COUNT lines)"
fi

# Check if README is readable (not just code dumps)
WORD_COUNT=$(wc -w < README.md)
if [ "$WORD_COUNT" -lt 50 ]; then
    echo "[!] WARNING: README seems too short ($WORD_COUNT words)"
else
    echo "[✓] README has sufficient text content ($WORD_COUNT words)"
fi

# Summary
echo "[*] Summary:"
echo "    Required sections found: $FOUND_SECTIONS/4"
echo "    Modules mentioned: $MODULES_MENTIONED"
echo "    Total lines: $LINE_COUNT"
echo "    Total words: $WORD_COUNT"

if [ "$FOUND_SECTIONS" -ge 2 ] && [ "$LINE_COUNT" -ge 10 ] && [ "$WORD_COUNT" -ge 50 ]; then
    echo "[✓] All tests passed! README.md appears to be complete."
    exit 0
else
    echo "[✗] ERROR: README.md may be incomplete or missing required content"
    exit 1
fi
