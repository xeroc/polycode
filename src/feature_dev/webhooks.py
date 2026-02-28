import logging
import os
from typing import Any

import httpx

from .persistence import get_active_webhooks

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "10"))


def trigger_webhooks(
    phase: str, state: dict[str, Any]
) -> list[dict[str, Any]]:
    results = []
    webhooks = get_active_webhooks()

    for webhook in webhooks:
        try:
            events = webhook.events if isinstance(webhook.events, list) else []
            if phase not in events and "*" not in events:
                continue

            payload = {
                "phase": phase,
                "state": state,
                "webhook_name": webhook.name,
            }

            response = httpx.post(
                webhook.url, json=payload, timeout=WEBHOOK_TIMEOUT
            )
            results.append(
                {
                    "webhook": webhook.name,
                    "status_code": response.status_code,
                    "success": response.is_success,
                }
            )

            if not response.is_success:
                logger.warning(
                    f"Webhook {webhook.name} failed: {response.status_code} - {response.text}"
                )

        except httpx.TimeoutException:
            logger.error(f"Webhook {webhook.name} timed out")
            results.append({"webhook": webhook.name, "error": "timeout"})
        except Exception as e:
            logger.error(f"Webhook {webhook.name} error: {e}")
            results.append({"webhook": webhook.name, "error": str(e)})

    return results
