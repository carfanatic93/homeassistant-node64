from typing import Any

import aiohttp


class Node64AuthError(Exception):
    """Der API-Key wird abgelehnt."""


class Node64ConnectError(Exception):
    """Die Node ist nicht erreichbar."""


class Node64Client:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def _get(self, path: str) -> Any:
        try:
            async with self._session.get(
                f"{self._base_url}{path}",
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise Node64AuthError
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise Node64ConnectError from err
        except TimeoutError as err:
            raise Node64ConnectError from err

    async def version(self) -> dict[str, Any]:
        return await self._get("/api/version")

    async def status(self) -> dict[str, Any]:
        return await self._get("/api/status")

    async def checks(self) -> list[dict[str, Any]]:
        return await self._get("/api/checks")

    async def stats(self, token: str, rng: str) -> dict[str, Any]:
        return await self._get(f"/api/checks/{token}/stats?range={rng}")

    async def cdn_hosts(self) -> list[dict[str, Any]]:
        return await self._get("/api/cdn64/hosts")

    async def cdn_status(self) -> dict[str, Any]:
        return await self._get("/api/cdn64/status")

    async def cdn_stats(self) -> dict[str, Any]:
        return await self._get("/api/cdn64/stats?hours=24")

    async def m64_overview(self) -> dict[str, Any]:
        return await self._get("/api/monitor64/overview")

    async def hp_status(self) -> dict[str, Any]:
        return await self._get("/api/honeypot/status")

    async def hp_stats(self) -> dict[str, Any]:
        return await self._get("/api/honeypot/stats?since=24h&top=5")
