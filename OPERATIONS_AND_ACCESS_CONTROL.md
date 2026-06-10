# qTest MCP Operations and Access Control Guide

This document defines how to run and test qTest MCP in two modes:
- Developer: local run and local testing
- QA/Prod: OpenShift deployment and real usage

It also explains how users provide runtime values (`qTest URL`, `qTest token`, `MCP URL`) and how to implement MCP server access control without using a database.

## 1. Runtime Inputs Users Must Provide

For all environments, these values are required:

1. qTest URL
- Example: `https://your-company.qtestnet.com`
- Maps to `QTEST_BASE_URL`

2. qTest Personal Access Token (API token / SDK token depending on tenant setup)
- Used by qTest auth or direct API access flows
- In this project, client credential is mapped to `QTEST_CLIENT_AUTH_TOKEN`

3. MCP URL
- Local: `http://127.0.0.1:8000/mcp`
- OCP: `https://<route-host>/mcp`

4. MCP Authorization token
- Header format: `Authorization: Bearer <token>`
- Token can be user-specific (recommended) or generic chatbot token (restricted)

## 2. Developer Flow (Local Run + Local Test)

### 2.1 Configure environment

Create `.env` from template and set required values.

Windows PowerShell:

```powershell
Set-Location "C:/path/to/Qtest-MCP"
Copy-Item .env.example .env
$fernet = python generate_fernet_key.py
(Get-Content .env) -replace '^FERNET_KEY=.*$',("FERNET_KEY=" + $fernet.Trim()) | Set-Content .env
```

macOS/Linux:

```bash
cd /path/to/Qtest-MCP
cp .env.example .env
FERNET_KEY_VALUE="$(python3 generate_fernet_key.py)"
sed -i.bak "s|^FERNET_KEY=.*|FERNET_KEY=${FERNET_KEY_VALUE}|" .env
```

Set these values in `.env`:
- `QTEST_BASE_URL`
- `QTEST_CLIENT_AUTH_TOKEN`
- `JWT_SECRET`
- `FERNET_KEY`

### 2.2 Start server

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2.3 Verify endpoints

- Portal: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/healthz`
- Ready: `http://127.0.0.1:8000/readyz`
- MCP: `http://127.0.0.1:8000/mcp`

### 2.4 Generate personal MCP token for local tools

- Use portal at `/`
- Or call `POST /api/auth/generate-token`

Then configure MCP client header:

```text
Authorization: Bearer <personal_mcp_token>
```

### 2.5 Local testing commands

```bash
python scripts/mcp_smoke_test.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token>
python scripts/mcp_capability_report.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token> --project-id <project_id>
```

## 3. QA/Prod Flow (OCP Deploy + Usage)

### 3.1 Build image in OCP

```bash
oc login <ocp-api-url>
oc project qtest-mcp || oc new-project qtest-mcp
oc new-build --name qtest-mcp-server --binary --strategy=docker
oc start-build qtest-mcp-server --from-dir=. --follow
```

### 3.2 Configure runtime values

Set qTest and security values in:
- `openshift/configmap.yaml`
- `openshift/secret.yaml`

Minimum required:
- `QTEST_BASE_URL`
- `QTEST_CLIENT_AUTH_TOKEN`
- `JWT_SECRET`
- `FERNET_KEY`
- `ALLOWED_ORIGINS` (set to your route origin)

### 3.3 Deploy manifests

```bash
oc apply -f openshift/secret.yaml
oc apply -f openshift/configmap.yaml
oc apply -f openshift/deployment.yaml
oc apply -f openshift/service.yaml
oc apply -f openshift/route.yaml
```

### 3.4 Verify rollout and route

```bash
oc rollout status deployment/qtest-mcp-server
oc get route qtest-mcp-route
```

Expected runtime URLs:
- Portal: `https://<route-host>/`
- MCP: `https://<route-host>/mcp`

### 3.5 Actual usage in QA/Prod

1. User gets/creates a personal MCP token from portal (`/api/auth/generate-token`).
2. User configures assistant MCP server with:
- URL: `https://<route-host>/mcp`
- Header: `Authorization: Bearer <personal_mcp_token>`
3. User runs commands through MCP tools.

## 4. How User-Provided qTest Token, qTest URL, and MCP URL Should Be Handled

Use one of these patterns:

### Pattern A: Current model (recommended with your existing code)

- Server stores global qTest integration settings in env (`QTEST_BASE_URL`, `QTEST_CLIENT_AUTH_TOKEN`).
- User provides qTest username/password once to mint personal MCP token.
- Personal MCP token is then used with MCP URL.

### Pattern B: Direct user token model

- User provides qTest personal token + qTest URL to the UI.
- Server encrypts and embeds that token into a user-scoped MCP token.
- MCP requests use user-scoped token and call qTest directly with the embedded token.

Pattern B is better for user-level separation when different users should have different qTest permissions.

## 5. Access Control for qTest MCP Without a Database

You can implement robust access control with signed tokens and static policy files/env vars.

### 5.1 Goals

- Support generic chatbot tokens (shared service principals)
- Support user-specific tokens (GitHub Copilot user sessions)
- Enforce scopes and tenant restrictions
- No DB dependency

### 5.2 Token types

1. Generic chatbot token
- Claims example:
  - `sub=bot:team-chatbot`
  - `token_type=bot`
  - `scopes=["projects:read","testcases:read"]`
  - short expiry (`exp`)
- Restricted to read-only or narrow write scopes.

2. User-specific token
- Claims example:
  - `sub=user:<email_or_id>`
  - `token_type=user`
  - `scopes=["projects:read","testcases:write","requirements:write"]`
  - optional `qtest_user=<id>`
- Can permit broader actions depending on role.

### 5.3 No-DB policy storage

Store policy in ConfigMap or local file loaded at startup.

Example policy JSON:

```json
{
  "default_deny": true,
  "roles": {
    "bot_reader": ["projects:read", "requirements:read", "testcases:read", "testruns:read", "defects:read"],
    "user_editor": ["projects:read", "requirements:read", "requirements:write", "testcases:read", "testcases:write", "testruns:read", "defects:read", "defects:write"]
  },
  "subjects": {
    "bot:qa-assistant": "bot_reader",
    "user:alice@example.com": "user_editor"
  }
}
```

### 5.4 Enforcement model

At request time:

1. Verify JWT signature and expiry.
2. Read `sub`, `token_type`, and requested `tool_name`.
3. Map tool to required scope.
4. Resolve role from static policy.
5. Allow or deny.

Tool-to-scope mapping example:

- `qtest_list_projects` -> `projects:read`
- `qtest_get_project` -> `projects:read`
- `qtest_search_requirements` -> `requirements:read`
- `qtest_update_requirement` -> `requirements:write`
- `qtest_search_test_cases` -> `testcases:read`
- `qtest_create_test_case` -> `testcases:write`
- `qtest_update_test_case` -> `testcases:write`
- `qtest_get_test_run` -> `testruns:read`
- `qtest_list_test_runs` -> `testruns:read`
- `qtest_get_defect` -> `defects:read`
- `qtest_list_defects_changed_since` -> `defects:read`
- `qtest_create_defect` -> `defects:write`
- `qtest_create_defect_from_test_run` -> `defects:write`

### 5.5 Token issuance without DB

Issue tokens from an admin script or endpoint that uses only:
- static subject allowlist
- static role map
- `JWT_SECRET`

Implemented endpoint:

- `POST /api/auth/generate-service-token`
- Header: `X-Admin-Token: <MCP_ADMIN_TOKEN>`
- Body:

```json
{
  "subject": "bot:qa-assistant",
  "qtest_bearer_token": "<qtest-bearer-token>",
  "token_type": "bot",
  "scopes": ["projects:read", "testcases:read"],
  "ttl_minutes": 60
}
```

Concrete example 1: generic chatbot token

Use this for a shared assistant such as a team chatbot or background automation that should stay read-only.

```json
{
  "sub": "bot:qa-assistant",
  "token_type": "bot",
  "iss": "qtest-mcp-server",
  "aud": "qtest-mcp-clients",
  "scopes": [
    "projects:read",
    "requirements:read",
    "testcases:read",
    "testruns:read",
    "defects:read"
  ],
  "exp": 1710003600
}
```

Expected behavior:
- `tools/list` shows only read tools.
- `tools/call` blocks write operations such as `qtest_create_test_case` and `qtest_update_requirement`.
- Best fit for shared bots, summarizers, and non-human automation.

Concrete example 2: GitHub Copilot user token

Use this for an individual developer signing into GitHub Copilot or a similar assistant where actions should be tied to one person.

```json
{
  "sub": "user:alice@example.com",
  "token_type": "user",
  "iss": "qtest-mcp-server",
  "aud": "qtest-mcp-clients",
  "scopes": [
    "projects:read",
    "requirements:read",
    "requirements:write",
    "testcases:read",
    "testcases:write",
    "testruns:read",
    "defects:read",
    "defects:write"
  ],
  "exp": 1710003600
}
```

Expected behavior:
- `tools/list` shows read and write tools allowed for that user.
- `tools/call` allows writes only when the subject and static policy permit them.
- Best fit for per-developer Copilot use where permissions should follow the person, not the chatbot.

Revocation without DB options:
- very short token TTL (recommended)
- key rotation (invalidates all tokens)
- denylist file in ConfigMap (for emergency block of specific `sub` values)

### 5.6 Recommended security defaults

- Use separate signing secrets per environment (dev/qa/prod).
- Keep bot tokens short-lived and read-only.
- Require user-specific tokens for write operations.
- Add `aud` and `iss` claims and validate both.
- Pin `QTEST_BASE_URL` by environment; do not allow arbitrary override from request body.

## 6. Suggested MCP Client Config Inputs

When onboarding users, ask for:
- qTest URL
- qTest personal token or username/password (per your chosen auth pattern)
- MCP URL

Example MCP entry:

```json
{
  "servers": {
    "qtest-local": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer <personal_mcp_token>"
      }
    }
  }
}
```

For QA/Prod, replace URL with `https://<route-host>/mcp`.

## 7. Acceptance Checklist

Developer local:
- server runs on `127.0.0.1:8000`
- smoke test passes
- capability report returns expected pass/skip/fail

QA/Prod OCP:
- deployment healthy with ready and live probes
- route serves portal and `/mcp`
- user-specific MCP token can call read tools
- generic chatbot token is restricted by scope
- write tools blocked for bot token and allowed for authorized user tokens
