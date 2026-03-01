import os
import re

import git
import github


def get_github_repo_from_local(local_path):
    """Auto-detect GitHub repo from local git checkout."""
    repo = git.Repo(local_path)
    origin_url = repo.remotes.origin.url

    # Parse owner/repo
    url = origin_url.rstrip("/").removesuffix(".git")
    match = re.search(r"[:/](.+)/(.+)", url)
    if not match:
        raise ValueError(f"Not a GitHub remote: {origin_url}")

    owner, repo_name = match.group(1), match.group(2)

    # Connect to GitHub
    g = github.Github(auth=github.Auth.Token(os.environ["GITHUB_TOKEN"]))
    github_repo = g.get_repo(f"{owner}/{repo_name}")

    return repo, github_repo, g


def sanitize_branch_name(name: str) -> str:
    """Convert string to valid git branch name."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9._/-]", "-", s)  # replace invalid chars with dash
    s = re.sub(r"-+", "-", s)  # collapse multiple dashes
    s = s.strip("-._/")  # strip leading/trailing junk
    s = re.sub(r"\.{2,}", ".", s)  # no consecutive dots
    s = re.sub(r"/+", "/", s)  # no consecutive slashes
    return s[:16] or "unnamed"
