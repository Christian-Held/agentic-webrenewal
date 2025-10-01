"""Model Context Protocol server exposing LLM functionality."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple
from urllib.parse import unquote, urlparse

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from . import LLMService, create_llm_service, default_model_for, get_tracer, list_available_providers

LOGGER = logging.getLogger("llm.mcp")


server = Server(name="webrenewal-llm", instructions="Agentic WebRenewal LLM bridge")


def _tool_definition(name: str, description: str, properties: Dict[str, Any]) -> types.Tool:
    return types.Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": ["provider", "model", "prompt"],
        },
    )


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        _tool_definition(
            "llm.complete_text",
            "Generate text using the configured provider.",
            {
                "provider": {"type": "string", "description": "LLM provider identifier"},
                "model": {"type": "string", "description": "Model name"},
                "prompt": {"type": "string", "description": "User prompt"},
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (optional)",
                },
            },
        ),
        types.Tool(
            name="llm.complete_json",
            description="Generate structured JSON via the configured provider.",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {"type": "string"},
                    "model": {"type": "string"},
                    "prompt": {"type": "string"},
                    "schema": {
                        "type": "string",
                        "description": "JSON schema definition or instructions",
                    },
                    "temperature": {"type": "number"},
                },
                "required": ["provider", "model", "prompt"],
            },
        ),
    ]


async def _resolve_service(provider: str) -> Tuple[LLMService, str]:
    service = create_llm_service(provider, tracer=get_tracer())
    if service is None:
        raise RuntimeError(f"No credentials configured for provider '{provider}'")
    return service, default_model_for(provider)


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]):
    provider = arguments.get("provider")
    model = arguments.get("model")
    prompt = arguments.get("prompt")
    temperature = arguments.get("temperature")
    schema = arguments.get("schema")

    if not provider or not model or not prompt:
        return server._make_error_result("provider, model and prompt are required")

    try:
        service, default_model = await _resolve_service(str(provider))
        model_name = model or default_model
        if name == "llm.complete_text":
            completion = await service.complete_text(
                prompt,
                model=model_name,
                temperature=temperature,
            )
            structured = completion.model_dump(mode="json", exclude={"raw"})
            content = [types.TextContent(type="text", text=completion.text)]
            return content, structured

        if name == "llm.complete_json":
            completion = await service.complete_json(
                prompt,
                model=model_name,
                schema=schema,
                temperature=temperature,
            )
            structured = completion.model_dump(mode="json", exclude={"raw"})
            content = [
                types.TextContent(
                    type="text",
                    text=json.dumps(completion.data, indent=2, ensure_ascii=False),
                )
            ]
            return content, structured

        return server._make_error_result(f"Unknown tool {name}")
    except Exception as exc:  # pragma: no cover - exercised via integration
        LOGGER.exception("Tool execution failed")
        return server._make_error_result(str(exc))


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    tracer = get_tracer()
    resources: list[types.Resource] = [
        types.Resource(
            uri="llm://providers",
            mimeType="application/json",
            description="Available providers and default models",
        )
    ]

    seen_last: set[tuple[str, str]] = set()
    for entry in tracer.list_traces():
        resources.append(
            types.Resource(
                uri=f"llm://trace/{entry.id}",
                mimeType="application/json",
                description=f"Trace for {entry.provider}:{entry.model}",
            )
        )
        key = (entry.provider, entry.model)
        if key not in seen_last:
            resources.append(
                types.Resource(
                    uri=f"llm://last/{entry.provider}/{entry.model}",
                    mimeType="application/json",
                    description="Last response for provider/model",
                )
            )
            seen_last.add(key)
    return resources


@server.read_resource()
async def read_resource(request: types.ReadResourceRequest):
    uri = request.params.uri
    tracer = get_tracer()

    if uri == "llm://providers":
        data = list_available_providers()
    elif uri.startswith("llm://trace/"):
        parsed = urlparse(uri)
        if parsed.netloc != "trace":
            return server._make_error_result(f"Unsupported resource {uri}")
        trace_id = unquote(parsed.path.lstrip("/"))
        if not trace_id:
            return server._make_error_result("Trace id missing")
        entry = tracer.get_trace(trace_id)
        if entry is None:
            return server._make_error_result(f"Trace {trace_id} not found")
        data = entry.model_dump(mode="json")
    elif uri.startswith("llm://last/"):
        parsed = urlparse(uri)
        if parsed.netloc != "last":
            return server._make_error_result(f"Unsupported resource {uri}")
        remainder = parsed.path.lstrip("/")
        if not remainder or "/" not in remainder:
            return server._make_error_result("Invalid last trace URI")
        provider_raw, model_raw = remainder.split("/", 1)
        provider = unquote(provider_raw)
        model = unquote(model_raw)
        if not provider or not model:
            return server._make_error_result("Invalid last trace URI")
        entry = tracer.get_last_trace(provider, model)
        if entry is None:
            return server._make_error_result("No trace for provider/model")
        data = entry.model_dump(mode="json")
    else:
        return server._make_error_result(f"Unsupported resource {uri}")

    content = [
        types.TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(data, indent=2, ensure_ascii=False),
        )
    ]
    return types.ServerResult(types.ReadResourceResult(contents=content))


async def run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        options = server.create_initialization_options()
        await server.run(read_stream, write_stream, options)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    anyio.run(run)


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()

