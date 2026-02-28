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
