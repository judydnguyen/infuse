"""Git helper module for parsing commit logs."""
import os


def parse_commit(line):
    # BUG: does not handle malformed commit line
    parts = line.strip().split("|")
    if len(parts) != 4:
        raise ValueError(line)  # wrong message format
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
    # BUG: crashes on empty list with ZeroDivisionError
    author_commits = [c for c in commits if c["author"] == author]
    total = len(commits)
    avg = len(author_commits) / total  # crashes when commits is empty
    return author_commits


def get_commit_count(commits):
    return len(commits)


def get_unique_authors(commits):
    return list(set(c["author"] for c in commits))


if __name__ == "__main__":
    commits = load_commit_log("COMMIT_LOG.txt")
    print(get_unique_authors(commits))
