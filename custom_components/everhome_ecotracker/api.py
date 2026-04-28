"""Client for the everHome cloud API."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import time
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession

from .const import API_BASE_URL, AUTHORIZE_URL, TOKEN_URL

TokenUpdater = Callable[[dict[str, Any]], Awaitable[None]]


class EverHomeApiError(Exception):
    """Base exception for everHome API errors."""


class EverHomeApiAuthError(EverHomeApiError):
    """Authentication failed or token refresh failed."""


class EverHomeApi:
    """Small async everHome cloud API wrapper."""

    def __init__(
        self,
        session: ClientSession,
        client_id: str,
        client_secret: str,
        token: dict[str, Any],
        token_updater: TokenUpdater | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = token
        self._token_updater = token_updater

    @property
    def token(self) -> dict[str, Any]:
        """Return the current OAuth token."""
        return self._token

    @staticmethod
    def authorization_url(client_id: str, redirect_uri: str, state: str) -> str:
        """Build the everHome OAuth authorization URL."""
        from urllib.parse import urlencode

        return f"{AUTHORIZE_URL}?{urlencode({
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state,
        })}"

    @classmethod
    async def async_exchange_code(
        cls,
        session: ClientSession,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange an OAuth authorization code for a token."""
        return await cls._async_post_token(
            session,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return devices for the authenticated account."""
        return await self._async_request_json("GET", "/device", params={"include": "properties"})

    async def _async_request_json(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Send an authenticated API request and decode JSON."""
        await self._async_ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token['access_token']}"
        headers["Accept"] = "application/json"

        try:
            response = await self._session.request(
                method,
                f"{API_BASE_URL}{path}",
                headers=headers,
                **kwargs,
            )
        except ClientError as err:
            raise EverHomeApiError("Could not connect to everHome cloud") from err

        async with response:
            await self._raise_for_status(response)
            return await response.json(content_type=None)

    async def _async_ensure_token(self) -> None:
        """Refresh the OAuth token if needed."""
        expires_at = self._token.get("expires_at")
        if expires_at is None and "expires_in" in self._token:
            expires_at = time.time() + int(self._token["expires_in"])
            self._token["expires_at"] = expires_at

        if expires_at is None or float(expires_at) > time.time() + 60:
            return

        refresh_token = self._token.get("refresh_token")
        if not refresh_token:
            raise EverHomeApiAuthError("OAuth token expired and no refresh token is available")

        token = await self._async_post_token(
            self._session,
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if "refresh_token" not in token:
            token["refresh_token"] = refresh_token
        self._token = token
        if self._token_updater is not None:
            await self._token_updater(token)

    @staticmethod
    async def _async_post_token(
        session: ClientSession,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Post to the everHome OAuth token endpoint."""
        try:
            response = await session.post(
                TOKEN_URL,
                data=data,
                headers={"Accept": "application/json"},
            )
        except ClientError as err:
            raise EverHomeApiError("Could not connect to everHome OAuth endpoint") from err

        async with response:
            await EverHomeApi._raise_for_status(response)
            token = await response.json(content_type=None)

        if "access_token" not in token:
            raise EverHomeApiAuthError("OAuth response did not include an access token")

        token["expires_at"] = time.time() + int(token.get("expires_in", 86400))
        return token

    @staticmethod
    async def _raise_for_status(response: ClientResponse) -> None:
        """Translate HTTP errors to integration exceptions."""
        if response.status < 400:
            return

        text = await response.text()
        if response.status in (400, 401, 403):
            raise EverHomeApiAuthError(text)
        raise EverHomeApiError(f"everHome API returned HTTP {response.status}: {text}")
