#!/usr/bin/env python3
"""
Source code file with insecure permissions (world-writable).
This should be fixed to not be world-writable.
"""

def main():
    print("Hello from source code")

if __name__ == "__main__":
    main()
