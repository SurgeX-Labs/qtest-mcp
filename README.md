# qTest MCP Server + Token Portal

Production-ready starter scaffold for a qTest MCP server deployable on OpenShift.

See `OPERATIONS_AND_ACCESS_CONTROL.md` for environment-specific run/deploy instructions and no-DB access control design.

Access control is scope-based and enforced per MCP tool call. `tools/list` is filtered by token scopes.
Optional service-token minting endpoint: `POST /api/auth/generate-service-token` (requires `X-Admin-Token` matching `MCP_ADMIN_TOKEN`).

## What this project provides

1. A web portal where a user enters qTest username/password once.
2. The backend exchanges those credentials for a qTest bearer token.
3. The portal returns a personal MCP access token for AI tools.
4. AI clients connect to this MCP server using the personal token.
5. The MCP server exposes safe qTest tools only.
6. Guardrails block destructive operations such as deleting projects, users, releases, test cases, test runs, requirements, modules, attachments, and cycles.

## High-level architecture

```text
User Browser
   |
   | HTTPS
   v
Token Portal / FastAPI
   |
   | qTest username/password used once
   v
qTest Auth API
   |
   | qTest bearer token
   v
Encrypted token store
   |
   | personal MCP token
   v
AI Chatbot / MCP Client
   |
   | Authorization: Bearer <personal_mcp_token>
   v
qTest MCP Server
   |
   | Guardrailed qTest API calls
   v
qTest Manager
```

## Safe MCP tools included

- qtest_list_projects
- qtest_get_project
- qtest_search_test_cases
- qtest_get_test_case
- qtest_create_test_case
- qtest_update_test_case
- qtest_search_requirements
- qtest_update_requirement
- qtest_list_requirement_test_cases
- qtest_get_test_run
- qtest_list_test_runs
- qtest_get_defect
- qtest_list_defects_changed_since
- qtest_create_defect
- qtest_create_defect_from_test_run
- qtest_add_comment

## Explicitly blocked

- delete_project
- delete_user
- delete_test_case
- delete_requirement
- delete_test_run
- delete_release
- delete_cycle
- delete_module
- delete_attachment
- bulk_delete
- user/admin/permission modification

## Local development

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Portal:

```text
http://localhost:8000/
```

MCP endpoint:

```text
http://localhost:8000/mcp
```

Health:

```text
http://localhost:8000/healthz
http://localhost:8000/readyz
```

## MCP smoke test

Run a quick protocol check against the local MCP endpoint:

```bash
python scripts/mcp_smoke_test.py --base-url http://127.0.0.1:8000
```

Run authenticated checks using an existing personal MCP token:

```bash
python scripts/mcp_smoke_test.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token>
```

Mint a personal token and run authenticated checks in one command:

```bash
python scripts/mcp_smoke_test.py --base-url http://127.0.0.1:8000 --username <qtest_username> --password <qtest_password>
```

Optionally test one tool call:

```bash
python scripts/mcp_smoke_test.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token> --tool-name qtest_get_project --tool-args '{"project_id": 123}'
```

Generate a one-shot capability report (safe probes only):

```bash
python scripts/mcp_capability_report.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token> --project-id <project_id>
```

Capability report with token minting and optional IDs:

```bash
python scripts/mcp_capability_report.py --base-url http://127.0.0.1:8000 --username <qtest_username> --password <qtest_password> --project-id <project_id> --test-run-id <test_run_id> --requirement-id <requirement_id> --defect-id <defect_id> --parent-id <cycle_or_suite_id>
```

Run mutation probes (create/update/comment) as well:

```bash
python scripts/mcp_capability_report.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token> --project-id <project_id> --include-mutations
```

## OpenShift deployment

```bash
oc new-project qtest-mcp
oc apply -f openshift/secret.yaml
oc apply -f openshift/configmap.yaml
oc apply -f openshift/deployment.yaml
oc apply -f openshift/service.yaml
oc apply -f openshift/route.yaml
```

## Production hardening checklist

- Use OpenShift TLS route.
- Store encryption key in OpenShift Secret or external vault.
- Replace SQLite with PostgreSQL.
- Enable network policy to qTest domain only.
- Enable structured logs and audit logs.
- Rotate personal MCP tokens.
- Add SSO/OIDC in front of the portal if available.
- Use short-lived qTest tokens if your qTest tenant supports it.
