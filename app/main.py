"""FastAPI application entrypoint for the feature frontend service."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="Feature Frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/widget.js", include_in_schema=False)
async def get_widget_bundle() -> FileResponse:
    """Return the compiled widget bundle.

    The widget bundle lives inside the static directory so that additional
    assets can be added without modifying the application code. Returning the
    file via FileResponse ensures the correct MIME type.
    """

    bundle_path = STATIC_DIR / "widget.js"
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail="widget.js not found")

    return FileResponse(bundle_path, media_type="application/javascript")


@app.get("/embed/chat", response_class=HTMLResponse, include_in_schema=False)
async def get_embed_chat(request: Request, token: str = Query(..., alias="token")) -> HTMLResponse:
    """Serve the embedded chat experience expected by the widget."""

    if not token:
        raise HTTPException(status_code=400, detail="Missing embed token")

    return templates.TemplateResponse(
        "embed_chat.html",
        {
            "request": request,
            "token": token,
        },
    )
