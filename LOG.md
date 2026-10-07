# LOG.md — Verified GridForge Command Cloud Outcomes

This file records verified outcomes only: command, PASS/FAIL status, and salient output.

## 10/07/2026 — Phase 0 foundation validation

### PASS — Focused pytest suite

Command:

```powershell
python -m pytest tests
```

Salient output:

```text
collected 15 items
15 passed in 0.30s
```

### PASS — Local CI gate

Command:

```powershell
.\scripts\runLocalCi.ps1 -SkipInstall
```

Salient output:

```text
==> Ruff format check
20 files already formatted
==> Ruff lint
All checks passed!
==> Mypy type check
Success: no issues found in 20 source files
==> Pytest with coverage
collected 15 items
15 passed in 0.13s
Required test coverage of 90% reached. Total coverage: 95.56%
Local CI checks passed.
```

### PASS — Live HTTP smoke test

Server command:

```powershell
$env:PORT = "5055"; python flaskApp.py
```

Smoke command:

```powershell
python -c "import json, urllib.request; urls=['http://127.0.0.1:5055/','http://127.0.0.1:5055/start','http://127.0.0.1:5055/health']; for url in urls: ..."
```

Salient output:

```text
http://127.0.0.1:5055/ -> 200 OK; 2466 bytes
http://127.0.0.1:5055/start -> 200 OK; 1621 bytes
http://127.0.0.1:5055/health -> 200 OK; 108 bytes
{"app": "gridforge-command-cloud", "environment": "local", "repositories": {"datastore": "memory"}, "status": "ok"}
```

## 10/07/2026 — AGENTS smoke-test guidance update

### PASS — Docs whitespace validation

Command:

```powershell
git diff --check -- AGENTS.md
```

Salient output:

```text
No whitespace errors.
```

## 10/07/2026 — Phase 1 domain and repository validation

### PASS — Focused pytest suite

Command:

```powershell
python -m pytest tests
```

Salient output:

```text
collected 20 items
20 passed in 0.33s
```

### PASS — Local CI gate

Command:

```powershell
.\scripts\runLocalCi.ps1 -SkipInstall
```

Salient output:

```text
==> Ruff format check
26 files already formatted
==> Ruff lint
All checks passed!
==> Mypy type check
Success: no issues found in 26 source files
==> Pytest with coverage
collected 20 items
20 passed in 0.21s
Required test coverage of 90% reached. Total coverage: 98.52%
Local CI checks passed.
```

### PASS — Live HTTP smoke test

Server command:

```powershell
$env:PORT = "5056"; python flaskApp.py
```

Smoke command:

```powershell
python -c "import json, urllib.request; urls=['http://127.0.0.1:5056/','http://127.0.0.1:5056/start','http://127.0.0.1:5056/health']; for url in urls: ..."
```

Salient output:

```text
http://127.0.0.1:5056/ -> 200 OK; 2466 bytes
http://127.0.0.1:5056/start -> 200 OK; 1621 bytes
http://127.0.0.1:5056/health -> 200 OK; 108 bytes
{"app": "gridforge-command-cloud", "environment": "local", "repositories": {"datastore": "memory"}, "status": "ok"}
```

## 10/07/2026 — Phase 2 intake and project creation validation

### PASS — Focused pytest suite

Command:

```powershell
python -m pytest tests
```

Salient output:

```text
collected 33 items
33 passed in 0.43s
```

### PASS — Local CI gate

Command:

```powershell
.\scripts\runLocalCi.ps1 -SkipInstall
```

Salient output:

```text
==> Ruff format check
35 files already formatted
==> Ruff lint
All checks passed!
==> Mypy type check
Success: no issues found in 35 source files
==> Pytest with coverage
collected 33 items
33 passed in 0.33s
Required test coverage of 90% reached. Total coverage: 98.39%
Local CI checks passed.
```

### PASS — Live HTTP smoke test

Server command:

```powershell
$env:PORT = "5057"; python flaskApp.py
```

Smoke command:

```powershell
Invoke-WebRequest /, /start, /health; Invoke-RestMethod POST /api/intake; Invoke-WebRequest /admin/projects with and without the temporary admin header.
```

Salient output:

```text
/ -> 200 OK; 2466 bytes
/start -> 200 OK; 4033 bytes
/health -> 200 OK; 108 bytes
/api/intake -> 201 Created; project=project_30e83619a51043929319437586f6385d; intake=intake_ea40be4afff5457da6f06ed37264037b
/admin/projects without header -> 403
/admin/projects with admin header -> 200 OK; contains Smoke Test Co=True
/admin/projects/project_30e83619a51043929319437586f6385d with admin header -> 200 OK; contains Smoke Test Co=True
```

## 10/07/2026 — Phase 3 demo auth and role guard validation

### PASS — Focused pytest suite

Command:

```powershell
python -m pytest tests
```

Salient output:

```text
collected 42 items
42 passed in 0.56s
```

### PASS — Local CI gate

Command:

```powershell
.\scripts\runLocalCi.ps1 -SkipInstall
```

Salient output:

```text
==> Ruff format check
41 files already formatted
==> Ruff lint
All checks passed!
==> Mypy type check
Success: no issues found in 41 source files
==> Pytest with coverage
collected 42 items
42 passed in 0.54s
Required test coverage of 90% reached. Total coverage: 97.23%
Local CI checks passed.
```

### PASS — Live HTTP smoke test

Server command:

```powershell
$env:PORT = "5058"; python flaskApp.py
```

Smoke command:

```powershell
Invoke-WebRequest /, /start, /auth/login, /health; Invoke-RestMethod POST /api/intake; Invoke-WebRequest /admin/projects anonymous, after demo login, and after logout.
```

Salient output:

```text
/ -> 200 OK; 2618 bytes
/start -> 200 OK; 4185 bytes
/auth/login -> 200 OK; 4830 bytes
/health -> 200 OK; 108 bytes
/admin/projects anonymous -> 403
/api/intake -> 201 Created; project=project_ab8732afacb24e1cb4bb6cd290565a2b; intake=intake_f19a1b674f984efbb46c28ef9f3d0751
/auth/demo-login workflow analyst -> final 200 OK; contains Phase 3 Clean Smoke Co=True
/admin/projects/project_ab8732afacb24e1cb4bb6cd290565a2b authenticated -> 200 OK; contains Phase 3 Clean Smoke Co=True
/auth/logout -> final 200 OK
/admin/projects after logout -> 403
```
