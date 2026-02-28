import os
import re

import git
import github


def get_github_repo_from_local(local_path, token=None):
    """Auto-detect GitHub repo from local git checkout."""
    repo = git.Repo(local_path)
    origin_url = repo.remotes.origin.url

    # Parse owner/repo
    url = origin_url.rstrip("/").removesuffix(".git")
    match = re.search(r"github\.com[:/](.+)/(.+)", url)
    if not match:
        raise ValueError(f"Not a GitHub remote: {origin_url}")

    owner, repo_name = match.group(1), match.group(2)

    # Connect to GitHub
    g = github.Github(token or os.environ["GITHUB_TOKEN"])
    return repo, g.get_repo(f"{owner}/{repo_name}")
