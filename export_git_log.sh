#!/bin/bash
# export_git_log.sh
#
# Export git commit history as a JSON array for the Git Commit Statistics Dashboard.
# Each commit includes: hash, author_name, author_email, date, additions, deletions.
# additions/deletions are summed across all files changed in the commit.
#
# Usage:
#   ./export_git_log.sh [path/to/repo] > commits.json
#   ./export_git_log.sh ~/projects/my-project > commits.json
#
# If no path is given, uses the current directory.
#
# The script pipes git log output through a Python script to safely generate
# valid JSON — Python handles all character escaping properly.

REPO="${1:-.}"

if [ ! -d "$REPO/.git" ]; then
  echo "Error: '$REPO' is not a git repository." >&2
  exit 1
fi

cd "$REPO"

# Use git log with markers to delineate commits, piped to Python for safe JSON generation
git log --all --format=$'__COMMIT__\t%H\t%an\t%ae\t%ad' --date=short --numstat | python3 -c '
import sys
import json

commits = []
current = None

for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue

    if line.startswith("__COMMIT__"):
        # Flush previous commit
        if current:
            commits.append(current)

        # Parse: __COMMIT__\t<hash>\t<author_name>\t<author_email>\t<date>
        parts = line.split("\t")
        current = {
            "hash": parts[1] if len(parts) > 1 else "",
            "author_name": parts[2] if len(parts) > 2 else "",
            "author_email": parts[3] if len(parts) > 3 else "",
            "date": parts[4] if len(parts) > 4 else "",
            "additions": 0,
            "deletions": 0,
        }
    elif current is not None:
        # Numstat line: additions\tdelletions\tfilename
        parts = line.split("\t")
        if len(parts) >= 2:
            add = parts[0]
            delete = parts[1]
            if add.isdigit():
                current["additions"] += int(add)
            if delete.isdigit():
                current["deletions"] += int(delete)

# Flush last commit
if current:
    commits.append(current)

json.dump(commits, sys.stdout, ensure_ascii=False, indent=None)
'
