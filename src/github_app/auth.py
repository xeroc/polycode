import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, cast

import jwt
import requests
from redis import Redis

logger = logging.getLogger(__name__)


class GitHubAppAuth:
    def __init__(
        self,
        app_id: str,
        private_key: str,
        redis_client: Optional[Redis] = None,
        cache_prefix: str = "github_app_auth",
    ):
        self.app_id = app_id
        self.private_key = private_key
        self.redis_client = redis_client
        self.cache_prefix = cache_prefix
        self.base_url = "https://api.github.com"

    def generate_jwt(self, expiration_minutes: int = 10) -> str:
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + (expiration_minutes * 60),
            "iss": self.app_id,
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        logger.debug(f"Generated JWT for app {self.app_id}")
        return token

    def get_installation_token(self, installation_id: int) -> Optional[str]:
        if self.redis_client:
            cached_token = self._get_cached_token(installation_id)
            if cached_token:
                logger.debug(
                    f"Using cached installation token for installation {installation_id}"
                )
                return cached_token

        jwt_token = self.generate_jwt()
        url = f"{self.base_url}/app/installations/{installation_id}/access_tokens"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            token = data.get("token")
            expires_at = data.get("expires_at")

            if token and self.redis_client and expires_at:
                self._cache_token(installation_id, token, expires_at)

            logger.info(
                f"Obtained installation token for installation {installation_id}"
            )
            return token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get installation token: {e}")
            return None

    def _get_cached_token(self, installation_id: int) -> Optional[str]:
        if not self.redis_client:
            return None

        cache_key = f"{self.cache_prefix}:installation:{installation_id}:token"
        cached_data = cast(Optional[bytes], self.redis_client.get(cache_key))

        if not cached_data:
            return None

        try:
            data_str: str
            if isinstance(cached_data, bytes):
                data_str = cached_data.decode("utf-8")
            else:
                data_str = cached_data

            data = json.loads(data_str)
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.now(timezone.utc) < expires_at - timedelta(minutes=5):
                return data["token"]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse cached token: {e}")

        return None

    def _cache_token(self, installation_id: int, token: str, expires_at: str):
        if not self.redis_client:
            return

        cache_key = f"{self.cache_prefix}:installation:{installation_id}:token"
        cache_data = {"token": token, "expires_at": expires_at}

        expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        ttl = int((expires_at_dt - datetime.now(timezone.utc)).total_seconds() - 300)

        if ttl > 0:
            self.redis_client.setex(cache_key, ttl, json.dumps(cache_data))
            logger.debug(f"Cached installation token for {ttl} seconds")

    def get_installation(self, installation_id: int) -> Optional[Dict[str, Any]]:
        jwt_token = self.generate_jwt()
        url = f"{self.base_url}/app/installations/{installation_id}"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get installation {installation_id}: {e}")
            return None

    def list_installations(self) -> Optional[list]:
        jwt_token = self.generate_jwt()
        url = f"{self.base_url}/app/installations"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list installations: {e}")
            return None

    def get_installation_repos(self, installation_id: int) -> Optional[list]:
        token = self.get_installation_token(installation_id)
        if not token:
            return None

        url = f"{self.base_url}/installation/repositories"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return [repo["full_name"] for repo in data.get("repositories", [])]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get installation repos: {e}")
            return None

    def verify_webhook_payload(self, payload: str, signature: str, secret: str) -> bool:
        import hashlib
        import hmac

        expected_signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)
