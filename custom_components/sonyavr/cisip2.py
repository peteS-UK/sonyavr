"""Minimal Sony CIS-IP2 client (JSON over TCP, port 33336).

Used only to read Zone 2 / Zone 3 state, which the binary control protocol
cannot be asked for. Commands still use the binary protocol.

Requests are one JSON object per line:
    {"id": 1, "type": "get", "feature": "zone2.power"}
Responses and change notifications are JSON objects sent back to back with no
separator:
    {"id": 1, "type": "result", "feature": "zone2.power", "value": "on"}
    {"type": "notify", "feature": "zone2.input", "value": "bd"}
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

_LOGGER = logging.getLogger(__name__)

CISIP2_PORT = 33336
CONNECT_TIMEOUT = 3.0
REQUEST_TIMEOUT = 2.0
RECONNECT_DELAY_MIN = 5
RECONNECT_DELAY_MAX = 60


def split_messages(buffer: str) -> tuple[list[dict], str]:
    """Split concatenated JSON objects; return (messages, unparsed remainder)."""
    decoder = json.JSONDecoder()
    messages = []
    idx = 0
    while True:
        while idx < len(buffer) and buffer[idx] in " \t\r\n":
            idx += 1
        if idx >= len(buffer):
            return messages, ""
        try:
            message, idx = decoder.raw_decode(buffer, idx)
        except json.JSONDecodeError:
            # Incomplete object: keep it for the next read
            return messages, buffer[idx:]
        if isinstance(message, dict):
            messages.append(message)


class CisIp2Client:
    """Connection to the AVR's CIS-IP2 port."""

    def __init__(
        self,
        host: str,
        port: int = CISIP2_PORT,
        on_notify: Callable[[str, Any], None] | None = None,
        on_reconnect: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._on_notify = on_notify
        self._on_reconnect = on_reconnect
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 0
        self._buffer = ""
        self._task: asyncio.Task | None = None
        self._closed = False

    @property
    def connected(self) -> bool:
        return self._writer is not None

    async def connect(self) -> bool:
        """Open the connection and start reading. Returns False if unavailable."""
        if not await self._open():
            return False
        self._task = asyncio.create_task(self._run())
        return True

    async def _open(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=CONNECT_TIMEOUT,
            )
        except (OSError, TimeoutError) as err:
            _LOGGER.debug(
                "CIS-IP2 connection to %s:%d failed: %s", self._host, self._port, err
            )
            self._reader = self._writer = None
            return False
        self._buffer = ""
        return True

    async def get(self, feature: str) -> Any:
        """Return the value of a feature, or None if there is no answer."""
        if self._writer is None:
            return None
        self._next_id += 1
        request_id = self._next_id
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        request = {"id": request_id, "type": "get", "feature": feature}
        try:
            self._writer.write((json.dumps(request) + "\n").encode())
            await self._writer.drain()
            return await asyncio.wait_for(future, timeout=REQUEST_TIMEOUT)
        except (OSError, TimeoutError):
            return None
        finally:
            self._pending.pop(request_id, None)

    async def close(self) -> None:
        self._closed = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._close_writer()

    async def _close_writer(self) -> None:
        writer, self._writer, self._reader = self._writer, None, None
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except OSError:
                pass

    async def _run(self) -> None:
        """Read messages; reconnect with backoff if the AVR drops the connection."""
        while not self._closed:
            try:
                data = await self._reader.read(4096)
            except OSError:
                data = b""
            if data:
                self._buffer += data.decode(errors="replace")
                messages, self._buffer = split_messages(self._buffer)
                for message in messages:
                    self._dispatch(message)
                continue

            # Connection closed: fail outstanding requests and reconnect
            await self._close_writer()
            for future in self._pending.values():
                if not future.done():
                    future.set_result(None)
            delay = RECONNECT_DELAY_MIN
            while not self._closed and not await self._open():
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_DELAY_MAX)
            if not self._closed:
                _LOGGER.debug("CIS-IP2 reconnected")
                if self._on_reconnect is not None:
                    asyncio.create_task(self._on_reconnect())

    def _dispatch(self, message: dict) -> None:
        if message.get("type") == "result" and "id" in message:
            future = self._pending.get(message["id"])
            if future is not None and not future.done():
                future.set_result(message.get("value"))
        elif message.get("type") == "notify" and self._on_notify is not None:
            self._on_notify(message.get("feature", ""), message.get("value"))
