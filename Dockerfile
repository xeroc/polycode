FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./

RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "crewai[litellm]>=1.10.0b1" && uv sync

COPY . .

COPY entrypooint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Creates a non-root user and adds permission to access the /app folder
RUN    useradd --create-home appuser \
    && chown -R appuser /app
USER appuser

VOLUME [ "/data" ]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
