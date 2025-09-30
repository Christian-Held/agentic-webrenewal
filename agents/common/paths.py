# D:\projects\helddigital\projects\agentic-webrenewal\agents\common\paths.py
from pathlib import Path

ROOT = Path(r"D:\projects\helddigital\projects\agentic-webrenewal").resolve()
SANDBOX = ROOT / "sandbox"
SANDBOX_TOOLS = SANDBOX / "tools"
MCPS_DIR = ROOT / "mcps"
CONFIGS = ROOT / "configs"

def ensure_dirs() -> None:
    SANDBOX.mkdir(exist_ok=True)
    SANDBOX_TOOLS.mkdir(parents=True, exist_ok=True)
    MCPS_DIR.mkdir(exist_ok=True)
