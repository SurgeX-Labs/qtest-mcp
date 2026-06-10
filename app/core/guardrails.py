from dataclasses import dataclass
from typing import Any

BLOCKED_OPERATION_KEYWORDS = [
    "delete",
    "remove_user",
    "remove_project",
    "purge",
    "drop",
    "destroy",
    "deactivate_user",
    "modify_permission",
    "grant_admin",
    "revoke_admin",
    "bulk_delete",
]

BLOCKED_QTEST_PATH_PARTS = [
    "/users",
    "/site-admin",
    "/permissions",
]

@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""

def validate_tool_name(tool_name: str) -> GuardrailResult:
    lowered = tool_name.lower()
    for word in BLOCKED_OPERATION_KEYWORDS:
        if word in lowered:
            return GuardrailResult(False, f"Blocked destructive or administrative operation: {tool_name}")
    return GuardrailResult(True)

def validate_http_request(method: str, path: str, body: dict[str, Any] | None = None) -> GuardrailResult:
    method_upper = method.upper()
    path_lower = path.lower()

    if method_upper == "DELETE":
        return GuardrailResult(False, "DELETE requests are not allowed by this MCP server.")

    for part in BLOCKED_QTEST_PATH_PARTS:
        if part in path_lower and method_upper in ["POST", "PUT", "PATCH", "DELETE"]:
            return GuardrailResult(False, f"Administrative path is read-only/blocked: {path}")

    dangerous_body_keys = {"deleted", "is_deleted", "active", "admin", "role", "permission"}
    if body:
        overlap = dangerous_body_keys.intersection(set(k.lower() for k in body.keys()))
        if overlap:
            return GuardrailResult(False, f"Request contains restricted administrative fields: {sorted(overlap)}")

    return GuardrailResult(True)
