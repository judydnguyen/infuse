#!/usr/bin/env python3
"""
Solution for fixing file permissions and generating security report.
"""

import os
import json
import stat
from pathlib import Path

def get_file_permissions(filepath):
    """Get file permissions as octal string."""
    try:
        return oct(os.stat(filepath).st_mode)[-3:]
    except OSError:
        return "unknown"

def is_world_writable(perms):
    """Check if permissions allow world write."""
    if len(perms) < 3:
        return False
    return perms[2] in ['2', '3', '6', '7']

def is_world_readable(perms):
    """Check if permissions allow world read."""
    if len(perms) < 3:
        return False
    return perms[2] in ['4', '5', '6', '7']

def fix_permissions():
    """Scan and fix file permissions."""
    scanned_files = []
    fixed_files = []
    remaining_issues = []
    
    # Scan all files in current directory
    for filepath in Path('.').iterdir():
        if not filepath.is_file():
            continue
        
        filename = filepath.name
        scanned_files.append(filename)
        
        current_perms = get_file_permissions(filename)
        
        # Check for source code files (should not be world-writable)
        if filename.endswith(('.py', '.js', '.java', '.cpp', '.c', '.h')) or \
           ('.' not in filename and not filename.endswith(('.sh', '.json', '.env'))):
            if is_world_writable(current_perms):
                print(f"  Fixing world-writable source: {filename} (was {current_perms})")
                os.chmod(filename, 0o644)
                fixed_files.append(filename)
        
        # Check for config/secret files (should be 600 - readable only by owner)
        if filename.endswith(('.json', '.env', '.conf', '.config')) or \
           filename.startswith(('secrets', 'config', '.env')):
            if current_perms != '600':
                print(f"  Fixing config/secret file: {filename} (was {current_perms})")
                os.chmod(filename, 0o600)
                fixed_files.append(filename)
        
        # Check for executable scripts (should be 750 - executable by owner/group)
        if filename.endswith(('.sh', '.py')) and os.access(filename, os.X_OK):
            if current_perms not in ('750', '755'):
                print(f"  Fixing executable script: {filename} (was {current_perms})")
                os.chmod(filename, 0o750)
                fixed_files.append(filename)
    
    # Generate report
    report = {
        "scanned_files": sorted(scanned_files),
        "fixed_files": sorted(fixed_files),
        "remaining_issues": remaining_issues
    }
    
    with open('security_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n[✓] Generated security_report.json")
    print(f"  Scanned: {len(scanned_files)} files")
    print(f"  Fixed: {len(fixed_files)} files")

if __name__ == '__main__':
    fix_permissions()
