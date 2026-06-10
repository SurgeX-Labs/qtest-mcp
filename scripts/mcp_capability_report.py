import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


@dataclass
class ProbeResult:
    tool_name: str
    status: str
    reason: str


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
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/auth/generate-token",
        headers={"Content-Type": "application/json"},
        json={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    token = body.get("personal_mcp_token")
    if not token:
        raise RuntimeError("Auth response did not include personal_mcp_token")
    return token


def infer_tool_args(tool_name: str, required: list[str], values: dict[str, Any], include_mutations: bool) -> tuple[dict[str, Any] | None, str | None]:
    mutation_tools = {
        "qtest_create_test_case",
        "qtest_update_test_case",
        "qtest_update_requirement",
        "qtest_create_defect",
        "qtest_create_defect_from_test_run",
        "qtest_add_comment",
    }
    if tool_name in mutation_tools and not include_mutations:
        return None, "skipped mutation tool (use --include-mutations to run)"

    arg_map: dict[str, Any] = {}
    for field in required:
        if field in values and values[field] is not None:
            arg_map[field] = values[field]
            continue

        if field == "payload":
            # Minimal payload only used when mutation probes are explicitly enabled.
            if tool_name == "qtest_update_requirement":
                arg_map[field] = {"name": "MCP probe update", "description": "Probe update payload"}
            elif tool_name in {"qtest_create_test_case", "qtest_update_test_case"}:
                arg_map[field] = {"name": "MCP probe test case"}
            elif tool_name in {"qtest_create_defect", "qtest_create_defect_from_test_run"}:
                arg_map[field] = {"name": "MCP probe defect", "description": "Probe defect payload"}
            else:
                arg_map[field] = {}
            continue

        if field == "parent_type":
            arg_map[field] = values.get("parent_type") or "test-cycles"
            continue

        if field == "changed_since":
            arg_map[field] = values.get("changed_since") or (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            continue

        if field == "query":
            arg_map[field] = values.get("query") or "name ~ 'a'"
            continue

        if field == "object_type":
            arg_map[field] = "test-cases"
            continue

        if field == "comment":
            arg_map[field] = "MCP capability probe comment"
            continue

        return None, f"missing required argument: {field}"

    return arg_map, None


def print_summary(results: list[ProbeResult]) -> None:
    print("\n=== MCP Capability Report ===")
    print(f"Total tools: {len(results)}")
    print(f"passed: {sum(1 for r in results if r.status == 'passed')}")
    print(f"failed: {sum(1 for r in results if r.status == 'failed')}")
    print(f"skipped: {sum(1 for r in results if r.status == 'skipped')}")

    print("\n=== Details ===")
    for item in results:
        print(f"- {item.tool_name}: {item.status} ({item.reason})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot MCP capability report by probing available tools.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of local server")
    parser.add_argument("--token", default=None, help="Personal MCP token")
    parser.add_argument("--username", default=None, help="qTest username to mint personal token")
    parser.add_argument("--password", default=None, help="qTest password to mint personal token")
    parser.add_argument("--project-id", type=int, default=None)
    parser.add_argument("--requirement-id", type=int, default=None)
    parser.add_argument("--test-case-id", type=int, default=None)
    parser.add_argument("--test-run-id", type=int, default=None)
    parser.add_argument("--defect-id", type=int, default=None)
    parser.add_argument("--parent-id", type=int, default=None)
    parser.add_argument("--parent-type", default="test-cycles", choices=["test-cycles", "test-suites"])
    parser.add_argument("--query", default=None)
    parser.add_argument("--changed-since", default=None, help="ISO 8601 timestamp for defect change filter")
    parser.add_argument("--include-mutations", action="store_true", help="Run create/update/comment tools as probes")
    args = parser.parse_args()

    token = args.token
    if not token and args.username and args.password:
        print("Minting personal MCP token via /api/auth/generate-token...")
        token = get_personal_token(args.base_url, args.username, args.password)
        print("Token minted successfully.")

    if not token:
        print("A token is required for capability report. Use --token or --username/--password.")
        return 1

    try:
        init_result = rpc_call(args.base_url, "initialize", {}, 1, token=None)
        if "error" in init_result:
            print("initialize returned error:")
            print(json.dumps(init_result, indent=2, ensure_ascii=True))
            return 1

        list_result = rpc_call(args.base_url, "tools/list", {}, 2, token=token)
        if "error" in list_result:
            print("tools/list returned error:")
            print(json.dumps(list_result, indent=2, ensure_ascii=True))
            return 1

        tools = list_result.get("result", {}).get("tools", [])
        if not isinstance(tools, list):
            print("tools/list result did not include a tools array")
            return 1

        values = {
            "project_id": args.project_id,
            "requirement_id": args.requirement_id,
            "test_case_id": args.test_case_id,
            "test_run_id": args.test_run_id,
            "defect_id": args.defect_id,
            "parent_id": args.parent_id,
            "parent_type": args.parent_type,
            "query": args.query,
            "changed_since": args.changed_since,
        }

        results: list[ProbeResult] = []
        request_id = 100
        for tool in tools:
            name = tool.get("name", "<unknown>")
            required = tool.get("inputSchema", {}).get("required", [])
            if not isinstance(required, list):
                required = []

            arg_map, skip_reason = infer_tool_args(name, required, values, args.include_mutations)
            if arg_map is None:
                results.append(ProbeResult(name, "skipped", skip_reason or "unable to infer arguments"))
                continue

            probe_result = rpc_call(
                args.base_url,
                "tools/call",
                {"name": name, "arguments": arg_map},
                request_id,
                token=token,
            )
            request_id += 1

            if "error" in probe_result:
                msg = probe_result.get("error", {}).get("message", "unknown tool error")
                results.append(ProbeResult(name, "failed", msg))
            else:
                results.append(ProbeResult(name, "passed", "ok"))

        print_summary(results)
        return 0
    except Exception as exc:
        print(f"Capability report failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
