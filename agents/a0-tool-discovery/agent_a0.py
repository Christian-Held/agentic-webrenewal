# D:\projects\helddigital\projects\agentic-webrenewal\agents\a0-tool-discovery\agent_a0.py
import os
import re
import json
import time
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import httpx
import yaml
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents.common.logger import get_logger
from agents.common.paths import ensure_dirs, SANDBOX_TOOLS, MCPS_DIR, CONFIGS
from agents.common.schemas import validate_tool_catalog

load_dotenv(override=True)
logger = get_logger("A0.ToolDiscovery")

# --- OpenAI setup (direct, no orchestration framework) ---
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
client = AsyncOpenAI()

@dataclass
class Source:
    url: str
    label: str

@dataclass
class ToolCandidate:
    name: str
    homepage: str
    summary: str
    runtime: str  # "Node.js" | "Python" | "Java" | "Other"
    sources: List[str]

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))

MCP_NAME_RE = re.compile(r'\b(mcp[-_/][a-z0-9][a-z0-9-_/\.@]*|@playwright/mcp|@modelcontextprotocol/server-filesystem)\b', re.IGNORECASE)
GITHUB_RE = re.compile(r'https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', re.IGNORECASE)
NPM_RE = re.compile(r'https?://www\.npmjs\.com/package/[A-Za-z0-9_.@/-]+', re.IGNORECASE)
PYPI_RE = re.compile(r'https?://pypi\.org/project/[A-Za-z0-9_.@/-]+', re.IGNORECASE)

RUNTIME_HINTS = [
    (re.compile(r'\bnpx\b|\bnpm\b|\bnode\b', re.IGNORECASE), "Node.js"),
    (re.compile(r'\bpip\b|\bpython\b|\buvx\b', re.IGNORECASE), "Python"),
    (re.compile(r'\bgradle\b|\bmaven\b|\bjava\b', re.IGNORECASE), "Java"),
]

# ---------------- I/O helpers ----------------

def _write_json(rel_name: str, data: dict) -> str:
    path = SANDBOX_TOOLS / rel_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Wrote JSON: {path}")
    return str(path)

def _write_md(name: str, content: str) -> str:
    path = MCPS_DIR / name
    path.write_text(content, encoding="utf-8")
    logger.info(f"Wrote MD: {path}")
    return str(path)

# ---------------- HTTP fetch ----------------

class FetchError(Exception):
    pass

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.8, min=1, max=6),
       retry=retry_if_exception_type(FetchError))
async def fetch_text(client_http: httpx.AsyncClient, url: str) -> Tuple[str, str]:
    try:
        r = await client_http.get(url, timeout=HTTP_TIMEOUT, follow_redirects=True, headers={
            "User-Agent": "AgenticWebRenewal/1.0 (+https://github.com/helddigital)"
        })
        if r.status_code >= 400:
            raise FetchError(f"HTTP {r.status_code} for {url}")
        ctype = r.headers.get("content-type", "")
        return r.text, ctype
    except Exception as e:
        raise FetchError(str(e))

# ---------------- Extraction ----------------

def extract_candidates(html: str, base_url: str) -> List[ToolCandidate]:
    """
    Heuristic extraction: find MCP names and nearby descriptions/links.
    """
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    chunks = set()

    # Names from text by regex
    for m in MCP_NAME_RE.finditer(text):
        chunks.add(m.group(0))

    # Also inspect code blocks and links
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "mcp" in href.lower() or "modelcontextprotocol" in href.lower():
            chunks.add(a.get_text(strip=True) or href)
            chunks.add(href)

    # Build candidates
    cands: List[ToolCandidate] = []
    for ch in sorted(chunks):
        name = ch.strip().split("/")[-1] if ch.startswith("http") else ch.strip()
        # Try to find a nearby homepage (prefer GitHub/NPM/PyPI)
        homepage = None
        near_text = ""
        for link_pat in (GITHUB_RE, NPM_RE, PYPI_RE):
            m2 = link_pat.search(html)
            if m2:
                homepage = m2.group(0)
                break
        if not homepage:
            homepage = base_url

        # Summary heuristics
        near_text = text[:2000]  # crude context slice
        runtime = "Other"
        for pat, rt in RUNTIME_HINTS:
            if pat.search(near_text):
                runtime = rt
                break

        cand = ToolCandidate(
            name=name,
            homepage=homepage,
            summary=f"Discovered on {base_url}. Heuristic summary window collected.",
            runtime=runtime,
            sources=[base_url]
        )
        cands.append(cand)

    return cands

# ---------------- LLM Classification & Scoring ----------------

async def llm_classify_and_score(candidates: List[ToolCandidate], weights: Dict[str, int]) -> List[Dict[str, Any]]:
    """
    Use OpenAI to classify each candidate into a single category and assign 1–5 scores per rubric dimension.
    """
    tools_payload = [
        {
            "name": c.name,
            "homepage": c.homepage,
            "runtime": c.runtime,
            "summary": c.summary,
            "sources": c.sources,
        } for c in candidates
    ]

    prompt = {
        "role": "user",
        "content": (
            "You are a strict JSON generator. For each tool, return a JSON array where each item is:\n"
            "{name, category(one of: browser, fetch, filesystem, memory, rag, search, codegen, qa, other), "
            "homepage, runtime, summary, sources, score:{fit,maturity,license,compliance,performance,docs,interop,observability (1-5 each)}, total}\n"
            "Scoring rubric weights: fit(3), maturity(2), license(2), compliance(2), performance(2), docs(1), interop(1), observability(1).\n"
            "Total = weighted sum. Be conservative. Output JSON only."
        )
    }

    try:
        resp = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[prompt, {"role": "user", "content": json.dumps(tools_payload)}],
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        # Expect { "tools": [ ... ] } or [ ... ]
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "tools" in data:
            return data["tools"]
        # Fallback: wrap best-effort
        return data.get("tools", [])
    except Exception as e:
        logger.error(f"LLM classification failed: {e}")
        return []

# ---------------- Catalog Consolidation ----------------

def dedupe_merge(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for t in tools:
        key = (t.get("name","").lower(), t.get("homepage","").lower())
        if key in by_key:
            # merge sources
            old = by_key[key]
            old_sources = set(old.get("sources", []))
            new_sources = set(t.get("sources", []))
            old["sources"] = sorted(old_sources | new_sources)
            # keep higher total
            if t.get("total", 0) > old.get("total", 0):
                by_key[key] = t
                by_key[key]["sources"] = sorted(old_sources | new_sources)
        else:
            by_key[key] = t
    return list(by_key.values())

def generate_usage_markdowns(selected: List[Dict[str, Any]]) -> None:
    """
    For core categories, emit usage .md snippets consistent with our runtime assumptions.
    """
    for t in selected:
        cat = t.get("category", "other").lower()
        name = t.get("name", "tool")
        if cat == "filesystem":
            content = f"""```python
# Filesystem MCP usage
from agents.mcp import MCPServerStdio  # placeholder for your MCP client
import os

sandbox_path = os.path.abspath(os.path.join(os.getcwd(), "sandbox"))
files_params = {{"command": "npx","args": ["-y", "@modelcontextprotocol/server-filesystem", sandbox_path]}}

async with MCPServerStdio(params=files_params, client_session_timeout_seconds=60) as server:
    file_tools = await server.list_tools()
print(file_tools)
```"""
            _write_md("file-tools.md", content)

        elif cat == "browser":
            content = """```python
# Playwright MCP usage
from agents.mcp import MCPServerStdio  # placeholder for your MCP client

playwright_params = {"command": "npx","args": ["@playwright/mcp@latest"]}

async with MCPServerStdio(params=playwright_params, client_session_timeout_seconds=60) as server:
    playwright_tools = await server.list_tools()
print(playwright_tools)
```"""
            _write_md("web-browsing.md", content)

        elif cat == "fetch":
            content = """```python
# Fetch MCP usage
from agents.mcp import MCPServerStdio  # placeholder for your MCP client

fetch_params = {"command": "uvx","args": ["mcp-server-fetch"]}

async with MCPServerStdio(params=fetch_params, client_session_timeout_seconds=60) as server:
    fetch_tools = await server.list_tools()
print(fetch_tools)
```"""
            _write_md("web-fetch.md", content)

        elif cat == "memory":
            content = """```python
# Memory MCP (LibSQL) usage
from agents.mcp import MCPServerStdio  # placeholder for your MCP client

memory_params = {"command": "npx","args": ["-y", "mcp-memory-libsql"],"env": {"LIBSQL_URL": "file:./memory/ed.db"}}

async with MCPServerStdio(params=memory_params, client_session_timeout_seconds=60) as server:
    memory_tools = await server.list_tools()
print(memory_tools)
```"""
            _write_md("memory-libsql.md", content)

# ---------------- Public API ----------------

class ToolDiscoveryAgent:
    """
    A0 Tool Discovery – scans known directories, extracts MCP tool candidates,
    classifies & scores with LLM, consolidates a catalog, emits usage snippets.
    """

    def __init__(self, config_path: str):
        self.config_path = config_path

    async def run(self) -> str:
        ensure_dirs()
        cfg = yaml.safe_load(open(self.config_path, "r", encoding="utf-8"))
        sources = [Source(**s) for s in cfg.get("sources", [])]
        weights = cfg.get("rubric", {}).get("weights", {})

        logger.info(f"Loaded {len(sources)} sources")
        all_candidates: List[ToolCandidate] = []

        async with httpx.AsyncClient() as http:
            for src in sources:
                try:
                    html, ctype = await fetch_text(http, src.url)
                    logger.info(f"Fetched {src.label} ({ctype})")
                    cands = extract_candidates(html, src.url)
                    # tag source per candidate
                    for c in cands:
                        if src.url not in c.sources:
                            c.sources.append(src.url)
                    logger.info(f"Extracted {len(cands)} candidates from {src.label}")
                    all_candidates.extend(cands)
                except Exception as e:
                    logger.error(f"Fetch/Extract failed for {src.label}: {e}")

        # Deduplicate early (by name+homepage) at candidate level
        seen = {}
        unique_candidates: List[ToolCandidate] = []
        for c in all_candidates:
            key = (c.name.lower(), c.homepage.lower())
            if key in seen:
                # merge sources
                seen[key].sources = sorted(set(seen[key].sources) | set(c.sources))
            else:
                seen[key] = c
                unique_candidates.append(c)

        logger.info(f"{len(unique_candidates)} unique candidates before LLM classification")

        # LLM classify + score
        classified = await llm_classify_and_score(unique_candidates, weights)
        merged = dedupe_merge(classified)

        # Sort by total desc
        merged.sort(key=lambda x: x.get("total", 0), reverse=True)

        catalog = {"tools": merged}
        validate_tool_catalog(catalog)

        # Persist
        out_path = _write_json("ToolCatalog.json", catalog)

        # Emit usage snippets for top tools in core categories
        # pick the highest total per category among known core categories
        best_by_cat: Dict[str, Dict[str, Any]] = {}
        for t in merged:
            cat = t.get("category", "other").lower()
            if cat not in best_by_cat:
                best_by_cat[cat] = t

        generate_usage_markdowns(list(best_by_cat.values()))
        return out_path
