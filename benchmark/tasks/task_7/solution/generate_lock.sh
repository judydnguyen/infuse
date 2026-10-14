#!/usr/bin/env bash
# Solution for generating requirements.lock
# This uses pip-compile from pip-tools, but the agent might use other methods

set -e

echo "[*] Generating requirements.lock..."

# Method 1: Use pip freeze (if dependencies are already installed)
# pip freeze > requirements.lock

# Method 2: Use pip-tools (pip-compile)
# pip install pip-tools
# pip-compile requirements.txt

# Method 3: Use pip install with --dry-run and parse output
# This is more complex but doesn't require installing packages

# For this solution, we'll use a Python script that:
# 1. Reads requirements.txt
# 2. Installs each package in a virtual environment
# 3. Uses pip freeze to get exact versions
# 4. Sorts alphabetically

python3 << 'EOF'
import subprocess
import sys
import re
from pathlib import Path

def get_package_name(requirement):
    """Extract package name from requirement string."""
    # Remove version specifiers and comments
    requirement = requirement.split('#')[0].strip()
    if not requirement:
        return None
    # Extract name (everything before >=, ==, <, >, etc.)
    match = re.match(r'([a-zA-Z0-9_-]+)', requirement)
    return match.group(1).lower() if match else None

def generate_lock_file():
    """Generate requirements.lock from requirements.txt."""
    requirements_file = Path('requirements.txt')
    if not requirements_file.exists():
        print("ERROR: requirements.txt not found", file=sys.stderr)
        sys.exit(1)
    
    # Read requirements.txt
    packages = []
    with open(requirements_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            package_name = get_package_name(line)
            if package_name:
                packages.append(package_name)
    
    if not packages:
        print("ERROR: No packages found in requirements.txt", file=sys.stderr)
        sys.exit(1)
    
    # Install packages and get versions
    # Note: This requires packages to be installed
    # In a real scenario, you'd use pip-tools or pip install --dry-run
    try:
        result = subprocess.run(
            ['pip', 'freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Filter to only packages from requirements.txt
        lock_entries = []
        package_names_lower = [p.lower() for p in packages]
        
        for line in result.stdout.split('\n'):
            if not line or '==' not in line:
                continue
            package_name = line.split('==')[0].lower()
            if package_name in package_names_lower:
                lock_entries.append(line)
        
        # Sort alphabetically
        lock_entries.sort(key=str.lower)
        
        # Write to requirements.lock
        with open('requirements.lock', 'w') as f:
            for entry in lock_entries:
                f.write(entry + '\n')
        
        print(f"✓ Generated requirements.lock with {len(lock_entries)} packages")
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to run pip freeze: {e}", file=sys.stderr)
        print("Note: This solution requires packages to be installed first", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    generate_lock_file()
EOF

echo "[✓] Done!"
