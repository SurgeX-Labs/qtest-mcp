import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.settings import settings

TOOL_SCOPE_MAP: dict[str, str] = {
    "qtest_list_projects": "projects:read",
    "qtest_get_project": "projects:read",
    "qtest_search_requirements": "requirements:read",
    "qtest_update_requirement": "requirements:write",
    "qtest_list_requirement_test_cases": "requirements:read",
    "qtest_search_test_cases": "testcases:read",
    "qtest_get_test_case": "testcases:read",
    "qtest_create_test_case": "testcases:write",
    "qtest_update_test_case": "testcases:write",
    "qtest_get_test_run": "testruns:read",
    "qtest_list_test_runs": "testruns:read",
    "qtest_get_defect": "defects:read",
    "qtest_list_defects_changed_since": "defects:read",
    "qtest_create_defect": "defects:write",
    "qtest_create_defect_from_test_run": "defects:write",
    "qtest_add_comment": "testcases:write",
}


DEFAULT_POLICY: dict[str, Any] = {
    "default_deny": True,
    "roles": {
        "bot_reader": [
            "projects:read",
            "requirements:read",
            "testcases:read",
            "testruns:read",
            "defects:read",
        ],
        "user_editor": [
            "projects:read",
            "requirements:read",
            "requirements:write",
            "testcases:read",
            "testcases:write",
            "testruns:read",
            "defects:read",
            "defects:write",
        ],
    },
    "subjects": {},
}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _coerce_scope_values(raw: Any) -> set[str]:
    if isinstance(raw, str):
        return set(_split_csv(raw))
    if isinstance(raw, list):
        return {str(item).strip() for item in raw if str(item).strip()}
    return set()


@lru_cache(maxsize=1)
def load_policy() -> dict[str, Any]:
    policy = dict(DEFAULT_POLICY)
    policy["roles"] = dict(DEFAULT_POLICY["roles"])
    policy["subjects"] = dict(DEFAULT_POLICY["subjects"])

    if settings.mcp_policy_file:
        path = Path(settings.mcp_policy_file)
        if path.exists() and path.is_file():
            with path.open("r", encoding="utf-8") as f:
                parsed = json.load(f)
                if isinstance(parsed, dict):
                    policy.update(parsed)

    if settings.mcp_policy_json:
        parsed = json.loads(settings.mcp_policy_json)
        if isinstance(parsed, dict):
            policy.update(parsed)

    return policy


def _subject_policy_scopes(subject: str) -> set[str]:
    policy = load_policy()
    subjects = policy.get("subjects", {})
    roles = policy.get("roles", {})
    role = subjects.get(subject)
    if not role:
        return set()
    role_scopes = roles.get(role, [])
    return _coerce_scope_values(role_scopes)


def effective_scopes(claims: dict[str, Any]) -> set[str]:
    subject = str(claims.get("sub", "")).strip()
    token_type = str(claims.get("token_type", "user")).strip().lower()
    explicit = _coerce_scope_values(claims.get("scopes"))

    # Backward compatibility for previously issued tokens.
    if claims.get("scope") == "qtest:mcp:safe":
        explicit.update(_split_csv(settings.default_user_scopes))

    defaults = set(_split_csv(settings.default_user_scopes))
    if token_type == "bot":
        defaults = set(_split_csv(settings.default_bot_scopes))

    by_subject = _subject_policy_scopes(subject)
    return defaults.union(by_subject).union(explicit)


def can_access_tool(claims: dict[str, Any], tool_name: str) -> tuple[bool, str]:
    required_scope = TOOL_SCOPE_MAP.get(tool_name)
    if not required_scope:
        return False, f"No scope mapping defined for tool: {tool_name}"

    token_type = str(claims.get("token_type", "user")).strip().lower()
    if token_type == "bot" and required_scope.endswith(":write") and not settings.allow_bot_writes:
        return False, "Bot tokens are not permitted to execute write operations."

    scopes = effective_scopes(claims)
    if "*" in scopes or required_scope in scopes:
        return True, ""

    default_deny = bool(load_policy().get("default_deny", True))
    if default_deny:
        return False, f"Missing required scope '{required_scope}' for tool '{tool_name}'."
    return True, ""


def assert_tool_access(claims: dict[str, Any], tool_name: str) -> None:
    allowed, reason = can_access_tool(claims, tool_name)
    if not allowed:
        raise PermissionError(reason)
