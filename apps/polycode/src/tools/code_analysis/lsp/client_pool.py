"""LSP client pool for managing language server instances.

Provides a pool of LSP clients for different languages with automatic
startup, initialization, and health management.
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pygls.client import JsonRPCClient
from pygls.protocol import JsonRPCProtocol

log = logging.getLogger(__name__)


@dataclass
class LSPServerConfig:
    """Configuration for a language server."""

    command: list[str]
    initialization_options: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0


# Language server configurations
LSP_SERVERS: dict[str, LSPServerConfig] = {
    "python": LSPServerConfig(
        command=["pyright-langserver", "--stdio"],
        initialization_options={},
    ),
    "typescript": LSPServerConfig(
        command=["typescript-language-server", "--stdio"],
        initialization_options={},
    ),
    "tsx": LSPServerConfig(
        command=["typescript-language-server", "--stdio"],
        initialization_options={},
    ),
    "javascript": LSPServerConfig(
        command=["typescript-language-server", "--stdio"],
        initialization_options={},
    ),
    "go": LSPServerConfig(
        command=["gopls", "serve"],
        initialization_options={"usePlaceholders": True},
    ),
    "rust": LSPServerConfig(
        command=["rust-analyzer"],
        initialization_options={},
    ),
}


class LSPClient:
    """Wrapper for an LSP client connection."""

    def __init__(self, config: LSPServerConfig, project_root: Path):
        self.config = config
        self.project_root = project_root
        self.client: JsonRPCClient | None = None
        self.initialized = False
        self._request_id = 0
        self._response_futures: dict[int, asyncio.Future] = {}
        self._protocol: JsonRPCProtocol | None = None

    async def start(self) -> bool:
        """Start the language server process.

        Returns:
            True if server started successfully
        """
        try:
            # Check if server command exists
            server_cmd = self.config.command[0]
            if not shutil.which(server_cmd):
                log.warning(f"⚠️ Language server not found: {server_cmd}")
                return False

            self.client = JsonRPCClient(
                protocol_cls=JsonRPCProtocol,
            )

            # Start the server process
            await self.client.start_io(*self.config.command)
            log.info(f"🏹 Started LSP server: {' '.join(self.config.command)}")
            return True

        except Exception as e:
            log.error(f"🚨 Failed to start LSP server: {e}")
            return False

    async def initialize(self) -> bool:
        """Send LSP initialize request.

        Returns:
            True if initialization succeeded
        """
        if not self.client:
            return False

        try:
            params = {
                "processId": None,
                "rootUri": self.project_root.as_uri(),
                "rootPath": str(self.project_root),
                "capabilities": {
                    "textDocument": {
                        "hover": {"contentFormat": ["markdown", "plaintext"]},
                        "definition": {"linkSupport": True},
                        "references": {},
                        "publishDiagnostics": {"relatedInformation": True},
                    },
                    "workspace": {
                        "symbol": {},
                        "configuration": True,
                    },
                },
                "initializationOptions": self.config.initialization_options,
            }

            result = await self.send_request("initialize", params)
            if result and "result" in result:
                self.initialized = True
                log.info("✓ LSP server initialized")
                # Send initialized notification
                await self.send_notification("initialized", {})
                return True

            log.error(f"🚨 LSP initialization failed: no result")
            return False

        except Exception as e:
            log.error(f"🚨 Failed to initialize LSP server: {e}")
            return False

    async def send_request(
        self, method: str, params: dict[str, Any], timeout: float | None = None
    ) -> dict[str, Any] | None:
        """Send an LSP request and wait for response.

        Args:
            method: LSP method name
            params: Request parameters
            timeout: Optional timeout override

        Returns:
            Response dict or None on timeout/error
        """
        if not self.client:
            return None

        timeout = timeout or self.config.timeout
        self._request_id += 1
        request_id = self._request_id

        try:
            # Create a future for response
            loop = asyncio.get_running_loop()
            future: asyncio.Future[dict[str, Any]] = loop.create_future()
            self._response_futures[request_id] = future

            # Send the request through the protocol
            self.client.protocol.send_request(method, params)  # type: ignore[arg-type]

            # Wait for response with timeout
            return await asyncio.wait_for(future, timeout=timeout)

        except asyncio.TimeoutError:
            log.warning(f"⏱️ LSP request timed out: {method}")
            self._response_futures.pop(request_id, None)
            return None
        except Exception as e:
            log.error(f"🚨 LSP request failed: {method}: {e}")
            self._response_futures.pop(request_id, None)
            return None

        timeout = timeout or self.config.timeout
        self._request_id += 1
        request_id = self._request_id

        try:
            # Create a future for the response
            loop = asyncio.get_running_loop()
            future: asyncio.Future[dict[str, Any]] = loop.create_future()
            self._response_futures[request_id] = future

            # Send the request
            self.client.protocol.send_request(method, params, request_id)

            # Wait for response with timeout
            return await asyncio.wait_for(future, timeout=timeout)

        except asyncio.TimeoutError:
            log.warning(f"⏱️ LSP request timed out: {method}")
            self._response_futures.pop(request_id, None)
            return None
        except Exception as e:
            log.error(f"🚨 LSP request failed: {method}: {e}")
            self._response_futures.pop(request_id, None)
            return None

    async def send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send an LSP notification (no response expected).

        Args:
            method: LSP method name
            params: Notification parameters
        """
        if not self.client:
            return

        try:
            # Send notification through the protocol
            self.client.protocol.send_notification(method, params)  # type: ignore[attr-defined]
        except Exception as e:
            log.error(f"🚨 LSP notification failed: {method}: {e}")

    def _handle_response(self, response: dict[str, Any]) -> None:
        """Handle incoming LSP response.

        Args:
            response: LSP response dict
        """
        request_id = response.get("id")
        if request_id is not None and request_id in self._response_futures:
            future = self._response_futures.pop(request_id)
            if not future.done():
                future.set_result(response)

    async def shutdown(self) -> None:
        """Shutdown the LSP server."""
        if not self.client:
            return

        try:
            await self.send_request("shutdown", {}, timeout=5.0)
            await self.send_notification("exit", {})
        except Exception as e:
            log.debug(f"Shutdown error (expected): {e}")

        try:
            _ = self.client.stop()
        except Exception as e:
            log.debug(f"Stop error: {e}")

        self.client = None
        self.initialized = False
        log.info("🛑 LSP server shutdown")

    def is_healthy(self) -> bool:
        """Check if the client is healthy and ready.

        Returns:
            True if client is initialized and connected
        """
        return self.client is not None and self.initialized


class LSPClientPool:
    """Pool of LSP clients for different languages.

    Manages client lifecycle and provides access to language-specific clients.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._clients: dict[str, LSPClient] = {}
        self._lock = asyncio.Lock()

    async def get_client(self, language: str) -> LSPClient | None:
        """Get or create an LSP client for a language.

        Args:
            language: Language name (e.g., 'python', 'typescript')

        Returns:
            LSPClient instance or None if language not supported
        """
        async with self._lock:
            # Return existing client if healthy
            if language in self._clients:
                client = self._clients[language]
                if client.is_healthy():
                    return client
                # Remove unhealthy client
                del self._clients[language]

            # Check if language is supported
            if language not in LSP_SERVERS:
                log.warning(f"⚠️ No LSP server configured for: {language}")
                return None

            # Create new client
            config = LSP_SERVERS[language]
            client = LSPClient(config, self.project_root)

            # Start server
            if not await client.start():
                return None

            # Initialize
            if not await client.initialize():
                await client.shutdown()
                return None

            self._clients[language] = client
            return client

    async def shutdown_all(self) -> None:
        """Shutdown all LSP clients."""
        async with self._lock:
            for client in self._clients.values():
                try:
                    await client.shutdown()
                except Exception as e:
                    log.debug(f"Shutdown error: {e}")
            self._clients.clear()

    def get_active_languages(self) -> list[str]:
        """Get list of languages with active clients.

        Returns:
            List of language names with healthy clients
        """
        return [lang for lang, client in self._clients.items() if client.is_healthy()]


# Global client pool instance
_client_pool: LSPClientPool | None = None


def get_client_pool(project_root: Path | None = None) -> LSPClientPool:
    """Get or create the global client pool.

    Args:
        project_root: Project root path (required for first call)

    Returns:
        LSPClientPool instance
    """
    global _client_pool
    if _client_pool is None:
        if project_root is None:
            project_root = Path.cwd()
        _client_pool = LSPClientPool(Path(project_root).resolve())
    return _client_pool


async def close_client_pool() -> None:
    """Close the global client pool."""
    global _client_pool
    if _client_pool:
        await _client_pool.shutdown_all()
        _client_pool = None
