from typing import Any
from app.core.guardrails import validate_tool_name
from app.services.qtest_client import QTestClient

TOOL_DEFINITIONS = [
    {
        "name": "qtest_list_projects",
        "description": "List qTest projects visible to the authenticated user.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "qtest_get_project",
        "description": "Get qTest project details by project ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"project_id": {"type": "integer"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "qtest_search_test_cases",
        "description": "Search test cases in a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "query": {"type": "string"},
            },
            "required": ["project_id", "query"],
        },
    },
    {
        "name": "qtest_get_test_case",
        "description": "Get a test case by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "test_case_id": {"type": "integer"},
            },
            "required": ["project_id", "test_case_id"],
        },
    },
    {
        "name": "qtest_create_test_case",
        "description": "Create a qTest test case. Destructive fields are blocked.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "payload": {"type": "object"},
            },
            "required": ["project_id", "payload"],
        },
    },
    {
        "name": "qtest_update_test_case",
        "description": "Update a qTest test case. Deletion/admin fields are blocked.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "test_case_id": {"type": "integer"},
                "payload": {"type": "object"},
            },
            "required": ["project_id", "test_case_id", "payload"],
        },
    },
    {
        "name": "qtest_search_requirements",
        "description": "Search qTest requirements in a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "query": {"type": "string"},
            },
            "required": ["project_id", "query"],
        },
    },
    {
        "name": "qtest_update_requirement",
        "description": "Update basic fields on an existing requirement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "requirement_id": {"type": "integer"},
                "payload": {"type": "object"},
            },
            "required": ["project_id", "requirement_id", "payload"],
        },
    },
    {
        "name": "qtest_list_requirement_test_cases",
        "description": "List test cases linked to a requirement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "requirement_id": {"type": "integer"},
            },
            "required": ["project_id", "requirement_id"],
        },
    },
    {
        "name": "qtest_get_test_run",
        "description": "Get a qTest test run by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "test_run_id": {"type": "integer"},
            },
            "required": ["project_id", "test_run_id"],
        },
    },
    {
        "name": "qtest_list_test_runs",
        "description": "List test runs under a test cycle or test suite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "parent_type": {"type": "string", "enum": ["test-cycles", "test-suites"]},
                "parent_id": {"type": "integer"},
            },
            "required": ["project_id", "parent_type", "parent_id"],
        },
    },
    {
        "name": "qtest_get_defect",
        "description": "Get defect details by defect ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "defect_id": {"type": "integer"},
            },
            "required": ["project_id", "defect_id"],
        },
    },
    {
        "name": "qtest_list_defects_changed_since",
        "description": "List defects changed since a timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "changed_since": {"type": "string", "description": "ISO 8601 timestamp"},
            },
            "required": ["project_id", "changed_since"],
        },
    },
    {
        "name": "qtest_create_defect",
        "description": "Create a defect in a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "payload": {"type": "object"},
            },
            "required": ["project_id", "payload"],
        },
    },
    {
        "name": "qtest_create_defect_from_test_run",
        "description": "Create and link a defect from a test run execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "test_run_id": {"type": "integer"},
                "payload": {"type": "object"},
            },
            "required": ["project_id", "test_run_id", "payload"],
        },
    },
    {
        "name": "qtest_add_comment",
        "description": "Add a non-destructive comment to a qTest object.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "object_type": {"type": "string", "enum": ["test-cases", "requirements", "test-runs", "defects"]},
                "object_id": {"type": "integer"},
                "comment": {"type": "string"},
            },
            "required": ["project_id", "object_type", "object_id", "comment"],
        },
    },
]

async def call_tool(client: QTestClient, tool_name: str, args: dict[str, Any]) -> Any:
    guardrail = validate_tool_name(tool_name)
    if not guardrail.allowed:
        raise PermissionError(guardrail.reason)

    if tool_name == "qtest_list_projects":
        return await client.list_projects()
    if tool_name == "qtest_get_project":
        return await client.get_project(args["project_id"])
    if tool_name == "qtest_search_test_cases":
        return await client.search_test_cases(args["project_id"], args["query"])
    if tool_name == "qtest_get_test_case":
        return await client.get_test_case(args["project_id"], args["test_case_id"])
    if tool_name == "qtest_create_test_case":
        return await client.create_test_case(args["project_id"], args["payload"])
    if tool_name == "qtest_update_test_case":
        return await client.update_test_case(args["project_id"], args["test_case_id"], args["payload"])
    if tool_name == "qtest_search_requirements":
        return await client.search_requirements(args["project_id"], args["query"])
    if tool_name == "qtest_update_requirement":
        return await client.update_requirement(args["project_id"], args["requirement_id"], args["payload"])
    if tool_name == "qtest_list_requirement_test_cases":
        return await client.list_requirement_test_cases(args["project_id"], args["requirement_id"])
    if tool_name == "qtest_get_test_run":
        return await client.get_test_run(args["project_id"], args["test_run_id"])
    if tool_name == "qtest_list_test_runs":
        return await client.list_test_runs(args["project_id"], args["parent_type"], args["parent_id"])
    if tool_name == "qtest_get_defect":
        return await client.get_defect(args["project_id"], args["defect_id"])
    if tool_name == "qtest_list_defects_changed_since":
        return await client.list_defects_changed_since(args["project_id"], args["changed_since"])
    if tool_name == "qtest_create_defect":
        return await client.create_defect(args["project_id"], args["payload"])
    if tool_name == "qtest_create_defect_from_test_run":
        return await client.create_defect_from_test_run(args["project_id"], args["test_run_id"], args["payload"])
    if tool_name == "qtest_add_comment":
        return await client.add_comment(args["project_id"], args["object_type"], args["object_id"], args["comment"])

    raise ValueError(f"Unknown tool: {tool_name}")
