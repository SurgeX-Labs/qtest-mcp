from app.core.guardrails import validate_tool_name, validate_http_request

def test_delete_tool_is_blocked():
    result = validate_tool_name("qtest_delete_project")
    assert result.allowed is False

def test_delete_http_is_blocked():
    result = validate_http_request("DELETE", "/api/v3/projects/1")
    assert result.allowed is False

def test_admin_field_is_blocked():
    result = validate_http_request("PUT", "/api/v3/projects/1/test-cases/10", {"admin": True})
    assert result.allowed is False

def test_get_is_allowed():
    result = validate_http_request("GET", "/api/v3/projects")
    assert result.allowed is True
