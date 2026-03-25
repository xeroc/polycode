# Use the official Python 3.13 slim image as the base
FROM python:3.13-slim AS base

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies, Node.js (from NodeSource), and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ssh \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && curl -fsSL https://bun.sh/install | bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add Bun to PATH and verify installations
ENV PATH="/root/.bun/bin:$PATH"
RUN node --version && npm --version && npm install -g pnpm && pnpm --version && bun --version

# Install Context+ globally ( bun install -g contextplus)
RUN bun install -g contextplus

FROM base
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir "crewai[litellm]>=1.10.0b1" && uv sync

COPY entrypooint.sh /entrypooint.sh /entrypoint.sh
RUN chmod +x /entrypooint.sh
# Creates a non-root user and adds permission to access the /app folder
RUN    useradd --create-home appuser \
    && chown -R appuser /app
USER appuser

# Need to whitelist fingerprint of github
RUN mkdir /home/appuser/.ssh && ssh-keyscan github.com >> /home/appuser/.ssh/known_hosts

VOLUME [ "/data" ]
COPY . .

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
