# D:\projects\helddigital\projects\agentic-webrenewal\scripts\run_a0.py
import asyncio
from agents.a0-tool-discovery.agent_a0 import ToolDiscoveryAgent
from agents.common.paths import CONFIGS

"""
Entry point to run A0 Tool-Discovery.
"""

async def main() -> None:
    cfg = str((CONFIGS / "sources.mcp.yaml").resolve())
    agent = ToolDiscoveryAgent(config_path=cfg)
    out = await agent.run()
    print(f"A0 completed. Catalog: {out}")

if __name__ == "__main__":
    asyncio.run(main())
