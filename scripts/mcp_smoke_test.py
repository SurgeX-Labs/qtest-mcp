import argparse
import json
import sys
from typing import Any

import httpx


def rpc_call(base_url: str, method: str, params: dict[str, Any], request_id: int, token: str | None) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }

    response = httpx.post(f"{base_url.rstrip('/')}/mcp", headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def get_personal_token(base_url: str, username: str, password: str) -> str:
    payload = {"username": username, "password": password}
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/auth/generate-token",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    token = body.get("personal_mcp_token")
    if not token:
        raise RuntimeError("Auth response did not include personal_mcp_token")
    return token


def pretty(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, ensure_ascii=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the local qTest MCP server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of local server")
    parser.add_argument("--token", default=None, help="Personal MCP token (Bearer token value only)")
    parser.add_argument("--username", default=None, help="qTest username to mint personal token")
    parser.add_argument("--password", default=None, help="qTest password to mint personal token")
    parser.add_argument("--tool-name", default=None, help="Optional tool to call after tools/list")
    parser.add_argument(
        "--tool-args",
        default="{}",
        help='JSON string for tool arguments, e.g. {"project_id":123}',
    )
    args = parser.parse_args()

    token = args.token
    if not token and args.username and args.password:
        print("Minting personal MCP token via /api/auth/generate-token...")
        token = get_personal_token(args.base_url, args.username, args.password)
        print("Token minted successfully.")

    try:
        init_result = rpc_call(args.base_url, "initialize", {}, 1, token=None)
        pretty("initialize", init_result)

        if not token:
            print("\nNo --token provided, skipping authenticated checks (tools/list and tools/call).")
            print("Provide --token or --username/--password to run full smoke test.")
            return 0

        tools_result = rpc_call(args.base_url, "tools/list", {}, 2, token=token)
        pretty("tools/list", tools_result)

        if args.tool_name:
            try:
                tool_args = json.loads(args.tool_args)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON for --tool-args: {exc}") from exc

            call_result = rpc_call(
                args.base_url,
                "tools/call",
                {"name": args.tool_name, "arguments": tool_args},
                3,
                token=token,
            )
            pretty(f"tools/call ({args.tool_name})", call_result)

        return 0
    except Exception as exc:
        print(f"\nSmoke test failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
