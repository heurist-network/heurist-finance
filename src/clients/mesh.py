"""REST client for selected Heurist Mesh agents and tools.

Mesh agents are exposed here as a collection of API tools. This module uses
the Mesh `/mesh_request` API directly instead of the MCP JSON-RPC transport.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from src.config import (
    HEURIST_API_KEY,
    HEURIST_MESH_API_ENDPOINT,
    HEURIST_MESH_SCHEMA_ENDPOINT,
    require_env,
)

DEFAULT_TIMEOUT_SECONDS = 60.0

# A 502/503/504 comes from the Mesh gateway, not from the tool: the request
# never reached a healthy worker, so the same call a moment later usually
# succeeds. Read timeouts behave the same way. Retrying here matters most for
# batch callers — the trending lane fires one request per symbol back to back,
# and an unretried gateway flap burns its whole remaining symbol list in the
# seconds the flap lasts.
RETRY_STATUSES = frozenset({502, 503, 504})
RETRY_BACKOFF_S: tuple[float, ...] = (0.5, 2.0)

YAHOO_FINANCE_AGENT = "YahooFinanceAgent"
FRED_MACRO_AGENT = "FredMacroAgent"
SEC_EDGAR_AGENT = "SecEdgarAgent"
EXA_SEARCH_DIGEST_AGENT = "ExaSearchDigestAgent"
TOKEN_RESOLVER_AGENT = "TokenResolverAgent"

SELECTED_MESH_TOOLS: dict[str, tuple[str, ...]] = {
    TOKEN_RESOLVER_AGENT: ("token_search",),
    YAHOO_FINANCE_AGENT: (
        "resolve_symbol",
        "quote_snapshot",
        "price_history",
        "technical_snapshot",
        "options_chain",
        "news_search",
        "market_overview",
        "equity_overview",
        "fund_snapshot",
        "equity_screen",
    ),
    FRED_MACRO_AGENT: (
        "macro_series_snapshot",
        "macro_series_history",
        "macro_regime_context",
        "macro_release_calendar",
        "macro_release_context",
        "macro_vintage_history",
    ),
    SEC_EDGAR_AGENT: (
        "resolve_company",
        "filing_timeline",
        "filing_diff",
        "xbrl_fact_trends",
        "insider_activity",
        "activist_watch",
        "institutional_holders",
    ),
    EXA_SEARCH_DIGEST_AGENT: (
        "exa_web_search",
        "exa_scrape_url",
    ),
}


class MeshApiError(RuntimeError):
    """Raised when the Mesh API or a Mesh tool returns an error."""


@dataclass(frozen=True)
class MeshTool:
    agent_id: str
    name: str
    description: str
    parameters: dict[str, Any]
    price: float | None = None


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _api_key(value: str | None) -> str:
    return require_env("HEURIST_API_KEY", value or HEURIST_API_KEY)


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-HEURIST-API-KEY": api_key,
    }


def _tool_enabled(agent_id: str, tool_name: str, selected_tools: dict[str, tuple[str, ...]]) -> bool:
    tools = selected_tools.get(agent_id)
    return tools is not None and (not tools or tool_name in tools)


def _mesh_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error")
        if detail:
            return str(detail)
    return str(payload)


def _mesh_payload(response: httpx.Response) -> dict[str, Any]:
    """Validated body of a `/mesh_request` response, or `MeshApiError`."""
    if response.is_error:
        raise MeshApiError(f"Mesh request failed with status {response.status_code}: {_mesh_error(response)}")
    data = response.json() if response.content else {}
    if isinstance(data, dict) and data.get("error"):
        raise MeshApiError(str(data["error"]))
    return data


def _unwrap_tool_response(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload

    data = payload.get("data", payload)
    if isinstance(data, dict):
        error = data.get("error")
        if error:
            raise MeshApiError(str(error))
        if data.get("status") == "error":
            raise MeshApiError(str(data.get("error") or data))
    return data


def _schema_tools(payload: dict[str, Any], selected_tools: dict[str, tuple[str, ...]]) -> list[MeshTool]:
    agents = payload.get("agents") or {}
    if not isinstance(agents, dict):
        raise MeshApiError("Mesh schema response did not include an agents object.")

    out: list[MeshTool] = []
    for agent_id, agent_payload in agents.items():
        if not isinstance(agent_payload, dict):
            continue
        for tool in agent_payload.get("tools") or []:
            if not isinstance(tool, dict):
                continue
            name = str(tool.get("name") or "")
            if not name or not _tool_enabled(agent_id, name, selected_tools):
                continue
            params = tool.get("parameters")
            out.append(
                MeshTool(
                    agent_id=agent_id,
                    name=name,
                    description=str(tool.get("description") or ""),
                    parameters=params if isinstance(params, dict) else {},
                    price=tool.get("price") if isinstance(tool.get("price"), (int, float)) else None,
                )
            )
    return out


class MeshClient:
    """Synchronous Heurist Mesh REST client."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_endpoint: str = HEURIST_MESH_API_ENDPOINT,
        schema_endpoint: str = HEURIST_MESH_SCHEMA_ENDPOINT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = _api_key(api_key)
        self.api_endpoint = api_endpoint.rstrip("/")
        self.schema_endpoint = schema_endpoint
        self.timeout = timeout

    def call_agent(self, agent_id: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        url = _join_url(self.api_endpoint, "mesh_request")
        body = {
            "agent_id": agent_id,
            "input": dict(input_payload),
            "api_key": self.api_key,
        }
        headers = _headers(self.api_key)
        response: httpx.Response | None = None
        transport_error: Exception | None = None
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(len(RETRY_BACKOFF_S) + 1):
                if attempt:
                    time.sleep(RETRY_BACKOFF_S[attempt - 1])
                try:
                    response = client.post(url, json=body, headers=headers)
                except httpx.TransportError as exc:
                    response, transport_error = None, exc
                    continue
                transport_error = None
                if response.status_code not in RETRY_STATUSES:
                    break
        if response is None:
            raise transport_error
        return _mesh_payload(response)

    def call_tool(
        self,
        agent_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        raw_data_only: bool = True,
    ) -> Any:
        payload = {
            "tool": tool_name,
            "tool_arguments": arguments or {},
            "raw_data_only": raw_data_only,
        }
        return _unwrap_tool_response(self.call_agent(agent_id, payload))

    def schema(
        self,
        agent_ids: list[str] | None = None,
        *,
        pricing: str = "credits",
    ) -> dict[str, Any]:
        agent_ids = agent_ids or list(SELECTED_MESH_TOOLS)
        params: list[tuple[str, str]] = [("pricing", pricing)]
        params.extend(("agent_id", agent_id) for agent_id in agent_ids)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(self.schema_endpoint, params=params, headers=_headers(self.api_key))
        if response.is_error:
            raise MeshApiError(f"Mesh schema failed with status {response.status_code}: {_mesh_error(response)}")
        return response.json() if response.content else {}

    def selected_tools(self, agent_ids: list[str] | None = None) -> list[MeshTool]:
        return _schema_tools(self.schema(agent_ids), SELECTED_MESH_TOOLS)


class AsyncMeshClient:
    """Async Heurist Mesh REST client for service code."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_endpoint: str = HEURIST_MESH_API_ENDPOINT,
        schema_endpoint: str = HEURIST_MESH_SCHEMA_ENDPOINT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = _api_key(api_key)
        self.api_endpoint = api_endpoint.rstrip("/")
        self.schema_endpoint = schema_endpoint
        self.timeout = timeout

    async def call_agent(self, agent_id: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        url = _join_url(self.api_endpoint, "mesh_request")
        body = {
            "agent_id": agent_id,
            "input": dict(input_payload),
            "api_key": self.api_key,
        }
        headers = _headers(self.api_key)
        response: httpx.Response | None = None
        transport_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(len(RETRY_BACKOFF_S) + 1):
                if attempt:
                    await asyncio.sleep(RETRY_BACKOFF_S[attempt - 1])
                try:
                    response = await client.post(url, json=body, headers=headers)
                except httpx.TransportError as exc:
                    response, transport_error = None, exc
                    continue
                transport_error = None
                if response.status_code not in RETRY_STATUSES:
                    break
        if response is None:
            raise transport_error
        return _mesh_payload(response)

    async def call_tool(
        self,
        agent_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        raw_data_only: bool = True,
    ) -> Any:
        payload = {
            "tool": tool_name,
            "tool_arguments": arguments or {},
            "raw_data_only": raw_data_only,
        }
        return _unwrap_tool_response(await self.call_agent(agent_id, payload))

    async def schema(
        self,
        agent_ids: list[str] | None = None,
        *,
        pricing: str = "credits",
    ) -> dict[str, Any]:
        agent_ids = agent_ids or list(SELECTED_MESH_TOOLS)
        params: list[tuple[str, str]] = [("pricing", pricing)]
        params.extend(("agent_id", agent_id) for agent_id in agent_ids)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.schema_endpoint, params=params, headers=_headers(self.api_key))
        if response.is_error:
            raise MeshApiError(f"Mesh schema failed with status {response.status_code}: {_mesh_error(response)}")
        return response.json() if response.content else {}

    async def selected_tools(self, agent_ids: list[str] | None = None) -> list[MeshTool]:
        return _schema_tools(await self.schema(agent_ids), SELECTED_MESH_TOOLS)


def call_mesh_tool(
    agent_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    client: MeshClient | None = None,
) -> Any:
    return (client or MeshClient()).call_tool(agent_id, tool_name, arguments or {})


async def call_mesh_tool_async(
    agent_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    client: AsyncMeshClient | None = None,
) -> Any:
    c = client or AsyncMeshClient()
    return await c.call_tool(agent_id, tool_name, arguments or {})


def yahoo_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    client: MeshClient | None = None,
) -> Any:
    return call_mesh_tool(YAHOO_FINANCE_AGENT, tool_name, arguments or {}, client=client)


async def yahoo_tool_async(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    client: AsyncMeshClient | None = None,
) -> Any:
    return await call_mesh_tool_async(YAHOO_FINANCE_AGENT, tool_name, arguments or {}, client=client)


def unwrap_results(payload: Any) -> dict[str, Any]:
    """Peel the second-layer Mesh `{status: 'success', data: {...}}` envelope.

    `MeshClient.call_tool` already strips the outer `data` wrapper, but Yahoo
    tools wrap their actual payload in a second `{status, data}` pair. Most
    callers care about the inner dict. Returns `{}` for non-dict input or
    non-success envelopes so caller code stays flat.
    """
    if not isinstance(payload, dict):
        return {}
    if payload.get("status") == "success" and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def yahoo_quote_snapshot(
    symbols: list[str] | str,
    *,
    include_history: bool = False,
    interval: str = "1d",
    period: str = "1mo",
    limit_bars: int = 10,
    client: MeshClient | None = None,
) -> Any:
    return yahoo_tool(
        "quote_snapshot",
        {
            "symbols": symbols,
            "include_history": include_history,
            "interval": interval,
            "period": period,
            "limit_bars": limit_bars,
        },
        client=client,
    )


def yahoo_price_history(
    symbols: list[str] | str,
    *,
    interval: str = "1d",
    period: str | None = "1mo",
    limit_bars: int = 50,
    client: MeshClient | None = None,
) -> Any:
    args: dict[str, Any] = {
        "symbols": symbols,
        "interval": interval,
        "limit_bars": limit_bars,
    }
    if period is not None:
        args["period"] = period
    return yahoo_tool("price_history", args, client=client)


def fred_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    client: MeshClient | None = None,
) -> Any:
    return call_mesh_tool(FRED_MACRO_AGENT, tool_name, arguments or {}, client=client)


def sec_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    client: MeshClient | None = None,
) -> Any:
    return call_mesh_tool(SEC_EDGAR_AGENT, tool_name, arguments or {}, client=client)


def exa_digest_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    client: MeshClient | None = None,
) -> Any:
    return call_mesh_tool(EXA_SEARCH_DIGEST_AGENT, tool_name, arguments or {}, client=client)


def token_search(
    query: str, *, chain: str | None = None, type_hint: str | None = None,
    client: MeshClient | None = None,
) -> Any:
    arguments = {"query": query}
    if chain:
        arguments["chain"] = chain
    if type_hint:
        arguments["type_hint"] = type_hint
    return call_mesh_tool(TOKEN_RESOLVER_AGENT, "token_search", arguments, client=client)


def run_async(coro: Any) -> Any:
    """Run a Mesh coroutine from script code that is not already in an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("run_async cannot be called from a running event loop; await the coroutine instead.")


__all__ = [
    "AsyncMeshClient",
    "DEFAULT_TIMEOUT_SECONDS",
    "EXA_SEARCH_DIGEST_AGENT",
    "FRED_MACRO_AGENT",
    "MeshApiError",
    "MeshClient",
    "MeshTool",
    "SEC_EDGAR_AGENT",
    "TOKEN_RESOLVER_AGENT",
    "SELECTED_MESH_TOOLS",
    "YAHOO_FINANCE_AGENT",
    "call_mesh_tool",
    "call_mesh_tool_async",
    "exa_digest_tool",
    "fred_tool",
    "run_async",
    "sec_tool",
    "token_search",
    "unwrap_results",
    "yahoo_price_history",
    "yahoo_quote_snapshot",
    "yahoo_tool",
    "yahoo_tool_async",
]
