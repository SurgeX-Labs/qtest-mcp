from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.mcp.router import router as mcp_router
from app.core.settings import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def portal():
    return FileResponse("app/static/index.html")
