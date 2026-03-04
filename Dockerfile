FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "crewai[litellm]>=1.10.0b1" && crewai install

COPY . .

RUN crewai install

COPY entrypooint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
