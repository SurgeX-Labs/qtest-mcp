# qTest MCP Developer Runbook

This guide covers:
- local development on Windows, macOS, and Linux
- smoke testing the MCP endpoint
- deployment to OpenShift Container Platform (OCP)

## 1. Prerequisites

- Python 3.11+
- pip
- Git
- Optional for container build: Docker or Podman
- For OCP deploy: `oc` CLI with cluster access

## 2. Local Setup (All Platforms)

1. Clone and open the repository.
2. Create a local environment file from the template.
3. Generate and set a valid Fernet key.
4. Install dependencies.
5. Start the server.

Required environment values in `.env`:
- `QTEST_BASE_URL`
- `QTEST_CLIENT_AUTH_TOKEN`
- `JWT_SECRET`
- `FERNET_KEY`

## 3. Windows (PowerShell)

```powershell
Set-Location "C:/Users/<you>/path/to/Qtest-MCP"

python -m venv .venv
.\.venv\Scripts\Activate.ps1

Copy-Item .env.example .env
$fernet = python generate_fernet_key.py
(Get-Content .env) -replace '^FERNET_KEY=.*$',("FERNET_KEY=" + $fernet.Trim()) | Set-Content .env

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 4. macOS/Linux (bash/zsh)

```bash
cd /path/to/Qtest-MCP

python3 -m venv .venv
source .venv/bin/activate

cp .env.example .env
FERNET_KEY_VALUE="$(python3 generate_fernet_key.py)"
sed -i.bak "s|^FERNET_KEY=.*|FERNET_KEY=${FERNET_KEY_VALUE}|" .env

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 5. Verify Local Server

With the server running, verify:

- Portal: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/healthz
- Ready: http://127.0.0.1:8000/readyz
- MCP endpoint: http://127.0.0.1:8000/mcp

Run smoke test:

```bash
python scripts/mcp_smoke_test.py --base-url http://127.0.0.1:8000
```

Run authenticated smoke test:

```bash
python scripts/mcp_smoke_test.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token>
```

Generate full capability report:

```bash
python scripts/mcp_capability_report.py --base-url http://127.0.0.1:8000 --token <personal_mcp_token> --project-id <project_id>
```

## 6. OCP Deployment Overview

This repo already includes manifests in `openshift/`:
- `configmap.yaml`
- `secret.yaml`
- `deployment.yaml`
- `service.yaml`
- `route.yaml`

The deployment expects image:
- `image-registry.openshift-image-registry.svc:5000/qtest-mcp/qtest-mcp-server:latest`

If your OCP project is not `qtest-mcp`, update the image path in `openshift/deployment.yaml`.

## 7. OCP Deploy (Step by Step)

### 7.1 Login and select project

```bash
oc login <your-ocp-api-url>
oc new-project qtest-mcp
oc project qtest-mcp
```

If the project already exists:

```bash
oc project qtest-mcp
```

### 7.2 Build the container image inside OCP

Create build config once:

```bash
oc new-build --name qtest-mcp-server --binary --strategy=docker
```

Start a build from this repo directory:

```bash
oc start-build qtest-mcp-server --from-dir=. --follow
```

This produces the `qtest-mcp-server:latest` image in the `qtest-mcp` project image stream.

### 7.3 Configure runtime settings

Edit these files before applying:

- `openshift/configmap.yaml`
  - set `QTEST_BASE_URL`
  - set `ALLOWED_ORIGINS` to your route URL once known
- `openshift/secret.yaml`
  - set `QTEST_CLIENT_AUTH_TOKEN`
  - set `JWT_SECRET`
  - set `FERNET_KEY`

Generate Fernet key locally:

```bash
python generate_fernet_key.py
```

### 7.4 Apply manifests

```bash
oc apply -f openshift/secret.yaml
oc apply -f openshift/configmap.yaml
oc apply -f openshift/deployment.yaml
oc apply -f openshift/service.yaml
oc apply -f openshift/route.yaml
```

### 7.5 Verify rollout and route

```bash
oc rollout status deployment/qtest-mcp-server
oc get pods -l app=qtest-mcp-server
oc get route qtest-mcp-route
```

Get route host only:

```bash
oc get route qtest-mcp-route -o jsonpath='{.spec.host}'
```

Test health over route:

```bash
curl -k https://<route-host>/healthz
curl -k https://<route-host>/readyz
```

## 8. Post-Deploy Checks

- Open `https://<route-host>/` and verify the portal loads.
- Confirm token generation via `POST /api/auth/generate-token`.
- Configure your MCP client to call `https://<route-host>/mcp` with:
  - `Authorization: Bearer <personal_mcp_token>`

## 9. Common Issues

1. `Fernet key must be 32 url-safe base64-encoded bytes`
- Regenerate key using `python generate_fernet_key.py` and update `FERNET_KEY`.

2. `401 Missing Bearer token` on `/mcp`
- MCP client is not sending `Authorization: Bearer <token>`.

3. qTest auth errors in token generation
- Check `QTEST_BASE_URL` and `QTEST_CLIENT_AUTH_TOKEN`.

4. OCP pods crash on startup
- Check logs:

```bash
oc logs deployment/qtest-mcp-server
```

5. Route works but browser app cannot call API (CORS)
- Ensure `ALLOWED_ORIGINS` includes your route origin.

## 10. Useful Commands

Restart rollout:

```bash
oc rollout restart deployment/qtest-mcp-server
```

Show deployment env source refs:

```bash
oc get deployment qtest-mcp-server -o yaml | grep -n "envFrom\|configMapRef\|secretRef"
```

Delete and redeploy all app resources:

```bash
oc delete -f openshift/route.yaml -f openshift/service.yaml -f openshift/deployment.yaml -f openshift/configmap.yaml -f openshift/secret.yaml
oc apply -f openshift/secret.yaml
oc apply -f openshift/configmap.yaml
oc apply -f openshift/deployment.yaml
oc apply -f openshift/service.yaml
oc apply -f openshift/route.yaml
```
