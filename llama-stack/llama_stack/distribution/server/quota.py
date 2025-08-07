# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import json
import time
from datetime import UTC, datetime, timedelta

from starlette.types import ASGIApp, Receive, Scope, Send

from llama_stack.log import get_logger
from llama_stack.providers.utils.kvstore.api import KVStore
from llama_stack.providers.utils.kvstore.config import KVStoreConfig, SqliteKVStoreConfig
from llama_stack.providers.utils.kvstore.kvstore import kvstore_impl

logger = get_logger(name=__name__, category="quota")


class QuotaMiddleware:
    """
    ASGI middleware that enforces separate quotas for authenticated and anonymous clients
    within a configurable time window.

    - For authenticated requests, it reads the client ID from the
      `Authorization: Bearer <client_id>` header.
    - For anonymous requests, it falls back to the IP address of the client.
    Requests are counted in a KV store (e.g., SQLite), and HTTP 429 is returned
    once a client exceeds its quota.
    """

    def __init__(
        self,
        app: ASGIApp,
        kv_config: KVStoreConfig,
        anonymous_max_requests: int,
        authenticated_max_requests: int,
        window_seconds: int = 86400,
    ):
        self.app = app
        self.kv_config = kv_config
        self.kv: KVStore | None = None
        self.anonymous_max_requests = anonymous_max_requests
        self.authenticated_max_requests = authenticated_max_requests
        self.window_seconds = window_seconds

        if isinstance(self.kv_config, SqliteKVStoreConfig):
            logger.warning(
                "QuotaMiddleware: Using SQLite backend. Expiry/TTL is not enforced; cleanup is manual. "
                f"window_seconds={self.window_seconds}"
            )

    async def _get_kv(self) -> KVStore:
        if self.kv is None:
            self.kv = await kvstore_impl(self.kv_config)
        return self.kv

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            # pick key & limit based on auth
            auth_id = scope.get("authenticated_client_id")
            if auth_id:
                key_id = auth_id
                limit = self.authenticated_max_requests
            else:
                # fallback to IP
                client = scope.get("client")
                key_id = client[0] if client else "anonymous"
                limit = self.anonymous_max_requests

            current_window = int(time.time() // self.window_seconds)
            key = f"quota:{key_id}:{current_window}"

            try:
                kv = await self._get_kv()
                prev = await kv.get(key) or "0"
                count = int(prev) + 1

                if int(prev) == 0:
                    # Set with expiration datetime when it is the first request in the window.
                    expiration = datetime.now(UTC) + timedelta(seconds=self.window_seconds)
                    await kv.set(key, str(count), expiration=expiration)
                else:
                    await kv.set(key, str(count))
            except Exception:
                logger.exception("Failed to access KV store for quota")
                return await self._send_error(send, 500, "Quota service error")

            if count > limit:
                logger.warning(
                    "Quota exceeded for client %s: %d/%d",
                    key_id,
                    count,
                    limit,
                )
                return await self._send_error(send, 429, "Quota exceeded")

        return await self.app(scope, receive, send)

    async def _send_error(self, send: Send, status: int, message: str):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [[b"content-type", b"application/json"]],
            }
        )
        body = json.dumps({"error": {"message": message}}).encode()
        await send({"type": "http.response.body", "body": body})
