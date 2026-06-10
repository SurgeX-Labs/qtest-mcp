from typing import Any
from fastapi import APIRouter, Header, HTTPException, Request
from app.core.security import verify_personal_token, decrypt_secret
from app.services.qtest_client import QTestClient
from app.mcp.tools import TOOL_DEFINITIONS, call_tool

router = APIRouter()

def _get_client_from_auth(authorization: str | None) -> QTestClient:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    personal_token = authorization.replace("Bearer ", "", 1)
    try:
        claims = verify_personal_token(personal_token)
        qtest_token = decrypt_secret(claims["qtest_token"])
        return QTestClient(qtest_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid MCP token: {str(exc)}")

@router.post("")
async def mcp_endpoint(request: Request, authorization: str | None = Header(default=None)):
    """
    Minimal HTTP JSON-RPC endpoint compatible with MCP-style clients.

    For production, you can replace this minimal router with the official MCP SDK
    transport once your selected client stack is finalized.
    """
    body: dict[str, Any] = await request.json()
    method = body.get("method")
    request_id = body.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": "qtest-mcp-server", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "tools/list":
        _get_client_from_auth(authorization)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOL_DEFINITIONS}}

    if method == "tools/call":
        client = _get_client_from_auth(authorization)
        params = body.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            result = await call_tool(client, tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": "text", "text": str(result)}
                    ]
                },
            }
        except PermissionError as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32001, "message": str(exc)},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }
