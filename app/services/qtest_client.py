from typing import Any
import httpx
from app.core.settings import settings
from app.core.guardrails import validate_http_request

class QTestClient:
    def __init__(self, bearer_token: str):
        self.base_url = settings.qtest_base_url.rstrip("/")
        self.bearer_token = bearer_token

    @staticmethod
    async def login(username: str, password: str) -> str:
        """
        Exchange username/password for qTest bearer token.

        qTest tenants may vary slightly. Adjust the token endpoint/payload to match
        your qTest Manager API documentation.
        """
        url = f"{settings.qtest_base_url.rstrip('/')}/oauth/token"
        headers = {
            "Authorization": f"Basic {settings.qtest_client_auth_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, data=data)
            response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                raise ValueError("qTest login response did not include access_token")
            return token

    async def request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> Any:
        guardrail = validate_http_request(method, path, json_body)
        if not guardrail.allowed:
            raise PermissionError(guardrail.reason)

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, url, headers=headers, json=json_body)
            response.raise_for_status()
            if response.content:
                return response.json()
            return {"ok": True}

    async def list_projects(self) -> Any:
        return await self.request("GET", "/api/v3/projects")

    async def get_project(self, project_id: int) -> Any:
        return await self.request("GET", f"/api/v3/projects/{project_id}")

    async def search_test_cases(self, project_id: int, query: str) -> Any:
        body = {"object_type": "test-cases", "fields": ["*"], "query": query}
        return await self.request("POST", f"/api/v3/projects/{project_id}/search", body)

    async def get_test_case(self, project_id: int, test_case_id: int) -> Any:
        return await self.request("GET", f"/api/v3/projects/{project_id}/test-cases/{test_case_id}")

    async def create_test_case(self, project_id: int, payload: dict[str, Any]) -> Any:
        return await self.request("POST", f"/api/v3/projects/{project_id}/test-cases", payload)

    async def update_test_case(self, project_id: int, test_case_id: int, payload: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/api/v3/projects/{project_id}/test-cases/{test_case_id}", payload)

    async def search_requirements(self, project_id: int, query: str) -> Any:
        body = {"object_type": "requirements", "fields": ["*"], "query": query}
        return await self.request("POST", f"/api/v3/projects/{project_id}/search", body)

    async def update_requirement(self, project_id: int, requirement_id: int, payload: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/api/v3/projects/{project_id}/requirements/{requirement_id}", payload)

    async def list_requirement_test_cases(self, project_id: int, requirement_id: int) -> Any:
        try:
            return await self.request("GET", f"/api/v3/projects/{project_id}/requirements/{requirement_id}/test-cases")
        except httpx.HTTPStatusError:
            body = {"object_type": "test-cases", "fields": ["*"], "query": f"requirementId = {requirement_id}"}
            return await self.request("POST", f"/api/v3/projects/{project_id}/search", body)

    async def get_test_run(self, project_id: int, test_run_id: int) -> Any:
        return await self.request("GET", f"/api/v3/projects/{project_id}/test-runs/{test_run_id}")

    async def list_test_runs(self, project_id: int, parent_type: str, parent_id: int) -> Any:
        if parent_type not in {"test-cycles", "test-suites"}:
            raise ValueError("parent_type must be 'test-cycles' or 'test-suites'")
        try:
            return await self.request("GET", f"/api/v3/projects/{project_id}/{parent_type}/{parent_id}/test-runs")
        except httpx.HTTPStatusError:
            body = {"object_type": "test-runs", "fields": ["*"], "query": f"parentId = {parent_id}"}
            return await self.request("POST", f"/api/v3/projects/{project_id}/search", body)

    async def get_defect(self, project_id: int, defect_id: int) -> Any:
        return await self.request("GET", f"/api/v3/projects/{project_id}/defects/{defect_id}")

    async def list_defects_changed_since(self, project_id: int, changed_since: str) -> Any:
        body = {
            "object_type": "defects",
            "fields": ["*"],
            "query": f"last_modified_date >= '{changed_since}'",
        }
        return await self.request("POST", f"/api/v3/projects/{project_id}/search", body)

    async def create_defect(self, project_id: int, payload: dict[str, Any]) -> Any:
        return await self.request("POST", f"/api/v3/projects/{project_id}/defects", payload)

    async def create_defect_from_test_run(self, project_id: int, test_run_id: int, payload: dict[str, Any]) -> Any:
        try:
            return await self.request("POST", f"/api/v3/projects/{project_id}/test-runs/{test_run_id}/defects", payload)
        except httpx.HTTPStatusError:
            payload_with_run = dict(payload)
            payload_with_run.setdefault("test_run_id", test_run_id)
            return await self.create_defect(project_id, payload_with_run)

    async def add_comment(self, project_id: int, object_type: str, object_id: int, comment: str) -> Any:
        allowed_types = {"test-cases", "requirements", "test-runs", "defects"}
        if object_type not in allowed_types:
            raise PermissionError(f"Unsupported comment object type: {object_type}")
        body = {"content": comment}
        return await self.request("POST", f"/api/v3/projects/{project_id}/{object_type}/{object_id}/comments", body)
