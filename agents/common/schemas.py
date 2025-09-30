# D:\projects\helddigital\projects\agentic-webrenewal\agents\common\schemas.py
from typing import Dict, Any
from jsonschema import validate

TOOL_CATALOG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "tools": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "category", "homepage", "runtime", "score", "total"],
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "homepage": {"type": "string"},
                    "runtime": {"type": "string"},
                    "summary": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "score": {
                        "type": "object",
                        "properties": {
                            "fit": {"type": "number"},
                            "maturity": {"type": "number"},
                            "license": {"type": "number"},
                            "compliance": {"type": "number"},
                            "performance": {"type": "number"},
                            "docs": {"type": "number"},
                            "interop": {"type": "number"},
                            "observability": {"type": "number"},
                        },
                        "required": ["fit","maturity","license","compliance","performance","docs","interop","observability"]
                    },
                    "total": {"type": "number"}
                }
            }
        }
    },
    "required": ["tools"]
}

def validate_tool_catalog(doc: dict) -> None:
    validate(instance=doc, schema=TOOL_CATALOG_SCHEMA)
