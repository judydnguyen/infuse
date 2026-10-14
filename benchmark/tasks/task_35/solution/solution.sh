#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fix to git_helper.py..."

cat > git_helper.py << 'PYEOF'
"""Git helper module for parsing commit logs."""
import os


def parse_commit(line):
    # FIXED: handle malformed commit line with proper message
    parts = line.strip().split("|")
    if len(parts) != 4:
        raise ValueError(f"Malformed commit line: {line}")
    return {
        "hash": parts[0].strip(),
        "author": parts[1].strip(),
        "date": parts[2].strip(),
        "message": parts[3].strip(),
    }


def load_commit_log(path):
    if not os.path.exists(path):
        raise ValueError(f"Commit log not found: {path}")
    with open(path, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    return [parse_commit(line) for line in lines]


def get_author_commits(commits, author):
    # FIXED: handle empty commits list
    if not commits:
        return []
    author_commits = [c for c in commits if c["author"] == author]
    return author_commits


def get_commit_count(commits):
    return len(commits)


def get_unique_authors(commits):
    return list(set(c["author"] for c in commits))


if __name__ == "__main__":
    commits = load_commit_log("COMMIT_LOG.txt")
    print(get_unique_authors(commits))
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
