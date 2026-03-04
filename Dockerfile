FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir "crewai[litellm]>=1.10.0b1" && crewai install

COPY . .

COPY entrypooint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
