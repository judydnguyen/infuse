#!/bin/bash
# Solution for fixing file permissions

set -e

echo "[*] Scanning for insecure file permissions..."

scanned_files=()
fixed_files=()
remaining_issues=()

# Scan all files in current directory
for file in *; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    scanned_files+=("$file")
    
    perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%OLp" "$file" 2>/dev/null || echo "unknown")
    
    # Check for world-writable files (source code)
    if [[ "$file" =~ \.(py|js|java|cpp|c|h)$ ]] || [[ "$file" =~ ^[^.]*$ ]] && [[ ! "$file" =~ \.(sh|json|env)$ ]]; then
        if [[ "$perms" =~ ^[0-9]*[26][0-9]*$ ]] || [[ "$perms" =~ ^[0-9]*[37][0-9]*$ ]]; then
            echo "  Fixing world-writable: $file (was $perms)"
            chmod 644 "$file"
            fixed_files+=("$file")
        fi
    fi
    
    # Check for config/secret files (should be 600)
    if [[ "$file" =~ \.(json|env|conf|config)$ ]] || [[ "$file" =~ ^(secrets|config|\.env) ]]; then
        if [[ ! "$perms" =~ ^600$ ]]; then
            echo "  Fixing config/secret file: $file (was $perms)"
            chmod 600 "$file"
            fixed_files+=("$file")
        fi
    fi
    
    # Check for executable scripts (should be 750, but 755 is acceptable)
    if [[ "$file" =~ \.(sh|py)$ ]] && [ -x "$file" ]; then
        if [[ ! "$perms" =~ ^(750|755)$ ]]; then
            echo "  Fixing executable script: $file (was $perms)"
            chmod 750 "$file"
            fixed_files+=("$file")
        fi
    fi
done

# Generate report
cat > security_report.json << EOF
{
  "scanned_files": $(printf '%s\n' "${scanned_files[@]}" | jq -R . | jq -s .),
  "fixed_files": $(printf '%s\n' "${fixed_files[@]}" | jq -R . | jq -s .),
  "remaining_issues": []
}
EOF

echo "[✓] Generated security_report.json"
echo "  Scanned: ${#scanned_files[@]} files"
echo "  Fixed: ${#fixed_files[@]} files"
