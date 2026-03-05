import re


def sanitize_branch_name(name: str) -> str:
    """Convert string to valid git branch name."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9._/-]", "-", s)  # replace invalid chars with dash
    s = re.sub(r"-+", "-", s)  # collapse multiple dashes
    s = s.strip("-._/")  # strip leading/trailing junk
    s = re.sub(r"\.{2,}", ".", s)  # no consecutive dots
    s = re.sub(r"/+", "/", s)  # no consecutive slashes
    return s[:16] or "unnamed"
