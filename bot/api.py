import asyncio
import logging
from typing import Optional
from urllib.parse import quote as quote_url

import aiohttp

from .constants import Keys, URLs

log = logging.getLogger(__name__)


class ResponseCodeError(ValueError):
    """Raised when a non-OK HTTP response is received."""

    def __init__(
        self,
        response: aiohttp.ClientResponse,
        response_json: Optional[dict] = None,
        response_text: str = ""
    ):
        self.status = response.status
        self.response_json = response_json or {}
        self.response_text = response_text
        self.response = response

    def __str__(self):
        response = self.response_json if self.response_json else self.response_text
        return f"Status: {self.status} Response: {response}"


class APIClient:
    """Django Site API wrapper."""

    def __init__(self, loop: asyncio.AbstractEventLoop, **kwargs):
        auth_headers = {
            'Authorization': f"Token {Keys.site_api}"
        }

        if 'headers' in kwargs:
            kwargs['headers'].update(auth_headers)
        else:
            kwargs['headers'] = auth_headers

        self.session: Optional[aiohttp.ClientSession] = None
        self.loop = loop

        self._ready = asyncio.Event(loop=loop)
        self._creation_task = None
        self._session_args = kwargs

        self.recreate()

    @staticmethod
    def _url_for(endpoint: str) -> str:
        return f"{URLs.site_schema}{URLs.site_api}/{quote_url(endpoint)}"

    async def _create_session(self) -> None:
        """Create the aiohttp session and set the ready event."""
        self.session = aiohttp.ClientSession(**self._session_args)
        self._ready.set()

    async def close(self) -> None:
        """Close the aiohttp session and unset the ready event."""
        if not self._ready.is_set():
            return

        await self.session.close()
        self._ready.clear()

    def recreate(self) -> None:
        """Schedule the aiohttp session to be created if it's been closed."""
        if self.session is None or self.session.closed:
            # Don't schedule a task if one is already in progress.
            if self._creation_task is None or self._creation_task.done():
                self._creation_task = self.loop.create_task(self._create_session())

    async def maybe_raise_for_status(self, response: aiohttp.ClientResponse, should_raise: bool) -> None:
        """Raise ResponseCodeError for non-OK response if an exception should be raised."""
        if should_raise and response.status >= 400:
            try:
                response_json = await response.json()
                raise ResponseCodeError(response=response, response_json=response_json)
            except aiohttp.ContentTypeError:
                response_text = await response.text()
                raise ResponseCodeError(response=response, response_text=response_text)

    async def get(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        """Site API GET."""
        await self._ready.wait()

        async with self.session.get(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def patch(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        """Site API PATCH."""
        await self._ready.wait()

        async with self.session.patch(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def post(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        """Site API POST."""
        await self._ready.wait()

        async with self.session.post(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def put(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        """Site API PUT."""
        await self._ready.wait()

        async with self.session.put(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def delete(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> Optional[dict]:
        """Site API DELETE."""
        await self._ready.wait()

        async with self.session.delete(self._url_for(endpoint), *args, **kwargs) as resp:
            if resp.status == 204:
                return None

            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()


def loop_is_running() -> bool:
    """
    Determine if there is a running asyncio event loop.

    This helps enable "call this when event loop is running" logic (see: Twisted's `callWhenRunning`),
    which is currently not provided by asyncio.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True
