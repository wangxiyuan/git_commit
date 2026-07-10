#!/usr/bin/env python3
"""resolve_github_ids.py

Resolve git authors to real GitHub usernames.
Writes github_id_map.json for the frontend.

Usage:
  python3 resolve_github_ids.py /path/to/repo [github_token]
  # or set GITHUB_TOKEN env var

Token needs read access. Create one at: https://github.com/settings/tokens
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def get_owner_repo(repo_path):
    """Extract GitHub owner/repo from git remote."""
    result = subprocess.run(
        ["git", "-C", repo_path, "remote"],
        capture_output=True, text=True
    )
    remotes = result.stdout.strip().split("\n")
    repos = []
    for remote in remotes:
        if not remote:
            continue
        url_result = subprocess.run(
            ["git", "-C", repo_path, "remote", "get-url", remote],
            capture_output=True, text=True
        )
        url = url_result.stdout.strip()
        m = re.search(r'github\.com[:/](.+?)/(.+?)(?:\.git)?$', url)
        if m:
            repos.append(f"{m.group(1)}/{m.group(2)}")
    return repos if repos else None


def get_all_authors(repo_path):
    """Return set of "author_name|||author_email" for all commits in the repo."""
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--all", "--format=%an\t%ae"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("❌ Failed to run git log.", file=sys.stderr)
        sys.exit(1)

    authors = set()
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            authors.add(f"{parts[0]}|||{parts[1]}")
    return authors


def github_api(url, token, retries=3):
    """Call GitHub API and return parsed JSON. Retries on network errors."""
    for attempt in range(retries):
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "git-commit-stats/1.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 403 and "rate limit" in body.lower():
                raise RuntimeError("RATE_LIMIT")
            if e.code in (404, 422):
                return None
            print(f"  ⚠️  HTTP {e.code}: {body[:200]}", file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < retries - 1:
                wait = (attempt + 1) * 3
                print(f"  🔄 网络错误，{wait}s 后重试 ({attempt + 1}/{retries}): {e}", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  ⚠️  网络错误（已重试{retries}次）: {e}", file=sys.stderr)
                return None


def search_user_by_name(name, token):
    """Search GitHub for a user by display name. Returns login or None."""
    q = urllib.parse.quote(f'"{name}" type:user')
    url = f"https://api.github.com/search/users?q={q}&per_page=3"
    data = github_api(url, token)
    if data and data.get("items"):
        return data["items"][0].get("login")
    return None


def get_commit_author_via_api(owner_repo, author_name, token):
    """Find a user's GitHub login by looking at repo commits that match the name.
    Uses GET /repos/:owner/:repo/commits with ?author=NAME to find the GitHub login.
    """
    q = urllib.parse.quote(author_name)
    url = f"https://api.github.com/repos/{owner_repo}/commits?author={q}&per_page=1"
    data = github_api(url, token)
    if data and len(data) > 0:
        commit = data[0]
        author = commit.get("author")
        if author and author.get("login"):
            return author["login"]
        committer = commit.get("committer")
        if committer and committer.get("login"):
            return committer["login"]
    return None


def search_commit_by_email(email, token):
    """Find GitHub login by searching commits by author email.
    Uses GET /search/commits?q=author-email:EMAIL.
    Requires the 'commit-search' preview accept header."""
    q = urllib.parse.quote(f"author-email:{email}")
    url = f"https://api.github.com/search/commits?q={q}&per_page=1"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.cloak-preview+json")
    req.add_header("User-Agent", "git-commit-stats/1.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            items = data.get("items", [])
            if items:
                author = items[0].get("author")
                if author and author.get("login"):
                    return author["login"]
    except Exception:
        pass
    return None


def guess_from_email(email):
    """Try to guess GitHub ID from email patterns.
    - @users.noreply.github.com -> extract ID from numeric suffix
      e.g. 30970038+1092626063@users.noreply.github.com -> 1092626063
    """
    if "users.noreply.github.com" in email:
        m = re.search(r'\+(\w+)@', email)
        if m:
            return m.group(1)
        return email.split("@")[0]
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    repo_path = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GITHUB_TOKEN", "")

    if not token:
        print("❌ GitHub token required.", file=sys.stderr)
        print("   Create one at: https://github.com/settings/tokens (read-only)", file=sys.stderr)
        print("   Usage: python3 resolve_github_ids.py /path/to/repo ghp_xxxx", file=sys.stderr)
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(script_dir, "github_id_map.json")
    repo_list = get_owner_repo(repo_path)
    if not repo_list:
        print("❌ Could not detect any GitHub remotes.", file=sys.stderr)
        sys.exit(1)
    primary_repo = repo_list[0]
    print(f"📦 Repositories: {', '.join(repo_list)}")

    # Load existing cache
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            cache = json.load(f)
        print(f"📂 Loaded {len(cache)} cached mappings")

    # Get all authors
    all_authors = get_all_authors(repo_path)
    unresolved = sorted(a for a in all_authors if a not in cache)
    cached_count = len(all_authors) - len(unresolved)
    print(f"🔍 {len(all_authors)} unique authors, {cached_count} cached, {len(unresolved)} to resolve\n")

    if not unresolved:
        print("✅ All authors already resolved!")
        return

    # Step 1: Resolve via commits API
    # Query /repos/:owner/:repo/commits?author=NAME to find the GitHub login.
    # Fast (core API, 5000 req/hr). Try across all remotes (origin + upstream).
    print("─ Step 1: Commits API lookup (fast, by author name)")
    new_count = 0

    still_unresolved = []
    for author_key in unresolved:
        author_name, _ = author_key.split("|||", 1)
        login = None
        for repo in repo_list:
            login = get_commit_author_via_api(repo, author_name, token)
            if login:
                break
            time.sleep(0.1)
        if login:
            cache[author_key] = login
            new_count += 1
            print(f"  ✅ commits: {author_name} → {login}")
        else:
            still_unresolved.append(author_key)

    print(f"   Resolved: {new_count}, remaining: {len(still_unresolved)}\n")

    # Step 2: Resolve via PR commits
    # For each PR number from merge commits, query /pulls/:num/commits.
    # Try across all remotes. One API call per PR, each may resolve multiple authors.
    print("─ Step 2: PR commits lookup (fast, by PR number)")
    pr_nums = set()
    merge_result = subprocess.run(
        ["git", "-C", repo_path, "log", "--all", "--merges", "--format=%s"],
        capture_output=True, text=True
    )
    for line in merge_result.stdout.strip().split("\n"):
        m = re.search(r'#(\d+)', line)
        if m:
            pr_nums.add(int(m.group(1)))
    print(f"   Found {len(pr_nums)} unique PR numbers")

    step2_new = 0
    unresolved_set = set(still_unresolved)

    for pr_num in sorted(pr_nums, reverse=True):
        if not unresolved_set:
            break

        # Try each repo for this PR
        data = None
        for repo in repo_list:
            url = f"https://api.github.com/repos/{repo}/pulls/{pr_num}/commits?per_page=100"
            data = github_api(url, token)
            if data and isinstance(data, list):
                break
            time.sleep(0.05)

        if not data or not isinstance(data, list):
            time.sleep(0.05)
            continue

        for commit in data:
            author_info = commit.get("author") or commit.get("committer")
            if not author_info or not author_info.get("login"):
                continue
            login = author_info["login"]

            git_author = commit.get("commit", {}).get("author", {})
            git_name = git_author.get("name", "")
            git_email = git_author.get("email", "")
            author_key = f"{git_name}|||{git_email}"

            if author_key in unresolved_set:
                cache[author_key] = login
                step2_new += 1
                unresolved_set.discard(author_key)
                print(f"  ✅ PR #{pr_num}: {git_name} → {login}")
        time.sleep(0.1)

    step2_unresolved = [a for a in still_unresolved if a in unresolved_set]
    print(f"   Resolved: {step2_new}, remaining: {len(step2_unresolved)}\n")

    # Step 3: Resolve via user search API
    # Search GitHub users by display name. Slower (30 req/min for authenticated).
    print("─ Step 3: User search API (slow, 30/min)")
    step3_new = 0
    step3_unresolved = []

    for author_key in step2_unresolved:
        author_name, author_email = author_key.split("|||", 1)

        login = search_user_by_name(author_name, token)
        if login:
            cache[author_key] = login
            step3_new += 1
            new_count += 1
            print(f"  ✅ search: {author_name} → {login}")
        else:
            step3_unresolved.append(author_key)
        time.sleep(2.0)

    print(f"   Resolved: {step3_new}, remaining: {len(step3_unresolved)}\n")

    # Step 4: Commit search by email (author-email: query)
    # Slow (30 req/min) but very reliable — finds the exact GitHub user for an email.
    print("─ Step 4: Commit search by email (slow, 30/min)")
    step4_new = 0
    step4_unresolved = []

    for author_key in step3_unresolved:
        author_name, author_email = author_key.split("|||", 1)

        login = search_commit_by_email(author_email, token)
        if login:
            cache[author_key] = login
            step4_new += 1
            new_count += 1
            print(f"  ✅ email: {author_name} <{author_email}> → {login}")
        else:
            step4_unresolved.append(author_key)
        time.sleep(2.0)

    print(f"   Resolved: {step4_new}, remaining: {len(step4_unresolved)}\n")

    # Step 5: Guess from email pattern
    print("─ Step 5: Email pattern guessing")
    step5_new = 0
    final_unresolved = []

    for author_key in step4_unresolved:
        author_name, author_email = author_key.split("|||", 1)
        guessed = guess_from_email(author_email)
        if guessed:
            cache[author_key] = guessed
            step5_new += 1
            new_count += 1
            print(f"  🔶 guessed: {author_name} <{author_email}> → {guessed}")
        else:
            final_unresolved.append(author_key)
            print(f"  ❌ unresolved: {author_name} <{author_email}>")

    print(f"   Guessed: {step5_new}, unresolved: {len(final_unresolved)}\n")

    # Step 6: Merge by name similarity with already-resolved authors
    # e.g. "hw_whx" is the same person as "whx" who was resolved to "whx-sjtu"
    print("─ Step 6: Name similarity merge")
    step6_new = 0
    really_unresolved = []

    for author_key in final_unresolved:
        author_name, _ = author_key.split("|||", 1)
        merged = None
        for cached_key, cached_login in cache.items():
            cached_name = cached_key.split("|||")[0].lower()
            # Check if one name contains the other
            if cached_name and author_name.lower() and (
                cached_name in author_name.lower() or author_name.lower() in cached_name
            ):
                merged = cached_login
                break
        if merged:
            cache[author_key] = merged
            step6_new += 1
            new_count += 1
            print(f"  ✅ merged: {author_name} → {merged} (via name match)")
        else:
            really_unresolved.append(author_key)
            print(f"  ❌ unresolved: {author_name}")

    print(f"   Merged: {step6_new}, unresolved: {len(really_unresolved)}\n")

    # Save
    with open(cache_file, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    matched = sum(1 for a in all_authors if a in cache)
    pct = 100 * matched // len(all_authors)
    print(f"💾 Saved {len(cache)} mappings ({new_count} new) to {cache_file}")
    print(f"   Coverage: {matched}/{len(all_authors)} authors resolved ({pct}%)")
    if really_unresolved:
        print(f"\n❌ Still unresolved ({len(really_unresolved)}):")
        for a in really_unresolved:
            name, email = a.split("|||", 1)
            print(f"   {name} <{email}>")


if __name__ == "__main__":
    main()
