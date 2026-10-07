# AGENTS.md — Master Operational Guide for the GridForge Agent
Version: 0.1
Last Updated: 10/07/2026

## 1) Purpose and Scope
This document defines how contributors and automation agents should work in this repository: mission, process, boundaries, and coordination with other project files.

- Audience: contributors and automation agents working on the GridForge project.
- Goal: deliver a cloud-first, role-based workflow operating system that helps GridForge Systems turn messy customer workflows into structured blueprints, developer-ready plans, implementation slices, QA validation, client handoff, and ongoing support.

## 2) Relationship to Other Project Docs
- README.md: Project overview, setup notes, and current product direction.
- projectGuide.md, when created: Product requirements and intended architecture for the GridForge Command Cloud.
- LOG.md, when created: Chronological record of verified outcomes only (PASS/FAIL), with commands and salient outputs.

How to use these together:
1. Read README.md and projectGuide.md, when available, to understand what to build.
2. Propose one logical operation at a time (complete functional increment).
3. Validate with explicit commands and record verified outcomes in LOG.md.

## 3) Project Mission (GridForge)
Deliver GridForge Command Cloud: a private workflow operating system for GridForge Systems.

The system should help GridForge repeatedly convert messy customer workflow descriptions into:

- Structured customer intake records.
- Customer-facing workflow blueprints.
- Human-reviewed scope baselines.
- Internal developer-ready implementation plans.
- Entity, route, permission, state-machine, validation, dashboard, export, and test specifications.
- Implementation slices and build tasks.
- QA/validation records.
- Client review and handoff records.
- Support, retainer, and enhancement workflows.
- Role-scoped dashboards, reports, exports, and audit history.

Required product capabilities (POC/MVP scope):
- Public or internal guided intake for messy workflow descriptions.
- AI-assisted customer blueprint generation with validation guardrails.
- Human review before blueprint approval.
- Role-based access for GridForge internal users and customer-side users.
- Customer Workflow Project lifecycle from lead captured through support/retainer.
- Developer plan storage/generation for build-ready technical planning.
- Implementation slice tracking.
- QA/validation tracking.
- Customer-safe summaries and exports.
- Internal notes, AI logs, prompt versions, validation errors, and developer plans kept internal-only.
- Audit events for approvals, exports, status changes, role changes, prompt changes, and overrides.

Non-goals unless explicitly approved:
- Native-mobile-first implementation.
- Guaranteed offline-first behavior.
- Enterprise real-time collaboration complexity in the first MVP.
- Compliance certification promises.
- Autonomous AI decision-making without human review.
- Public publishing of customer examples without explicit sanitization and admin approval.

## 4) Operating Cycle
The agent follows an incremental, test-driven loop:
1. Implement one cohesive, testable unit of work per cycle.
   - A "logical unit" encompasses the full slice needed to verify a behavior (e.g., Service + Route + Template + Test). Avoid artificially fragmenting work into tiny steps that cannot be run or tested in isolation.
2. Run validation commands and analyze outputs.
3. Record verified outcomes in LOG.md (PASS/FAIL with commands and salient outputs), once LOG.md exists.
4. On failure, apply a focused fix and re-validate. Never bundle unrelated operations.

A key part of this cycle is the **Iterative Synthesis** approach to code generation: when multiple inputs exist, synthesize the best coverage, clarity, and edge-case handling into one cohesive solution.

## 5) Change Management
- One logical operation per proposal cycle.
- Prefer incremental modifications; avoid sweeping refactors.
- Do not move/rename/delete files or restructure without explicit approval.
- When a source file grows beyond healthy working size, an approved refactor pattern is to keep the primary file as a thin pass-through/orchestration module and move cohesive responsibilities into focused secondary files within a nearby subdirectory.
- Keep product requirements anchored to README.md and projectGuide.md, when available; if requirements conflict with implementation reality, propose a small correction.
- Controlled files (require explicit approval before modifying): AGENTS.md.
- Maintain originality: do not copy code, prose, prompts, UI copy, or architecture text from external sources unless the license explicitly permits reuse and attribution is preserved.
- Keep reusable examples generic; avoid embedding repository-specific or client-specific identifiers in templates unless they are required for this repository.

## 6) Coding Standards (Repository-Level)
Follow existing repository conventions.

- Python files should retain the existing module header style used in this repository once established.
- Keep imports at the top of the file and organized.
- Prefer explicit types where helpful; keep functions small and testable.
- Keep route handlers thin; move business logic into services and persistence into repository classes.
- Use server-side route guards for ownership/admin checks; never rely on frontend hiding for authorization.
- Prefer fake repositories and fake AI clients in tests.
- Keep customer-facing text, internal notes, raw AI output, and developer-only records clearly separated.
- Avoid rendering unsanitized customer or AI-generated text.

## 7) Current Focus (POC Milestones)
Based on the GridForge product direction, prioritize:

1. Project foundation
   - Flask app factory or equivalent app entry point.
   - Health route.
   - Configuration loading.
   - Repository/service/route/test structure.
   - Basic layout and visual system.

2. Customer Workflow Project lifecycle
   - Lead captured.
   - Intake in progress.
   - Intake ready for blueprint.
   - Blueprint generated.
   - Human review.
   - Customer review.
   - Blueprint approved.
   - Developer plan drafted/approved.
   - Build active.
   - QA/validation.
   - Demo ready.
   - Handoff/accepted.
   - Support/retainer.

3. Role-based access
   - GridForge Owner / Platform Admin.
   - Workflow Analyst / Blueprint Reviewer.
   - Developer / Builder.
   - QA / Validation Reviewer.
   - Support / Account Manager.
   - Customer Contact.
   - Client Stakeholder / Approver.
   - Read-only Executive / Advisor.
   - Public Visitor / Prospect.

4. Blueprint and developer-plan workflow
   - Intake answers.
   - Missing-detail tracking.
   - AI consent.
   - Customer-facing blueprint.
   - Human review notes.
   - Internal developer plan.
   - Prompt version and validation status.
   - Retry/repair path for invalid AI output.

5. Implementation and QA workflow
   - Implementation slices.
   - Build tasks.
   - Acceptance criteria.
   - QA items.
   - Demo links/screenshots.
   - Test command summaries.
   - Handoff readiness.

6. Reports and exports
   - Customer-safe project summary.
   - Blueprint export.
   - Developer-plan internal export.
   - QA/handoff summary.
   - Support/enhancement summary.
   - Export audit events.

## 8) Commands & Validation (Typical)
Use explicit commands and paste full output for verification. Examples:

- **Install development dependencies**:
  ```powershell
  python -m pip install -e ".[dev]"
  ```

- **Standard pytest**:
  ```powershell
  python -m pytest tests
  ```

- **Focused pytest**:
  ```powershell
  python -m pytest tests/test_<area>.py
  ```

- **Run local app**:
  ```powershell
  python flaskApp.py
  ```

- **Live HTTP smoke test for runnable web changes**:
  ```powershell
  $env:PORT = "5055"; python flaskApp.py
  python -c "import json, urllib.request; urls=['http://127.0.0.1:5055/','http://127.0.0.1:5055/start','http://127.0.0.1:5055/health']; [print(f'{url} -> {urllib.request.urlopen(url, timeout=5).status}') for url in urls]"
  ```

- **Local CI gate, once `scripts/runLocalCi.ps1` exists**:
  ```powershell
  .\scripts\runLocalCi.ps1
  .\scripts\runLocalCi.ps1 -SkipInstall
  ```

If a command requires environment setup that is not yet documented, propose adding that documentation in a focused follow-up change.

## 8.1) Testing and CI Expectations

GridForge should follow the same testing discipline as the swobodaWare Blueprint Portal setup: local CI must mirror GitHub CI, and quality gates should block completion rather than be treated as optional.

### Required quality gate

When the tooling exists, the local CI gate must run these checks in this order:

1. Install development dependencies unless `-SkipInstall` is passed.
2. `python -m ruff format --check .`
3. `python -m ruff check .`
4. `python -m mypy <source packages> tests main.py flaskApp.py`
5. `python -m pytest -p pytest_cov --cov=<source package> --cov-report=term-missing --cov-fail-under=90 tests`

The expected GridForge source package should be used once it exists. If multiple first-party packages are added, include all first-party source packages in both mypy and coverage. Do not lower the coverage threshold to make a failing build pass without explicit owner approval.

### Tooling expectations

- Python target: 3.11+ unless the repo owner explicitly changes it.
- Development dependencies should include Ruff, mypy, pytest, and pytest-cov.
- Pytest should use strict config and strict markers.
- Coverage should measure branch coverage, show missing lines, and fail under 90% total coverage.
- Ruff should enforce formatting and lint checks before tests are considered complete.
- Mypy should check source packages, tests, and app entry points with strict enough settings to catch untyped or incomplete definitions.
- Set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` in the local CI script for deterministic pytest behavior unless a documented plugin requires otherwise.

### GitHub Actions expectations

When GitHub Actions is added, CI should:

- Run on `push`, `pull_request`, and `workflow_dispatch`.
- Use read-only repository permissions by default (`contents: read`).
- Set up Python 3.11 with pip caching.
- Install development dependencies with `python -m pip install -e ".[dev]"`.
- Run the same local CI gate script, e.g. `./scripts/runLocalCi.ps1 -SkipInstall` under PowerShell.
- Treat GitHub CI as parity with local CI, not as a separate weaker check.

### Test suite shape

Default tests must run fully offline and deterministically. Do not make live AI, email, billing, cloud, or network calls in the default suite.

Use test doubles for external or expensive dependencies:

- Fake repositories for route, service, and dashboard tests.
- Fake AI clients with queued deterministic responses.
- Fake email/notification clients.
- Temporary databases or temporary paths for persistence tests.
- Seeded fictional data for demos and examples.

The expected test coverage includes:

- Route tests for every public, customer, internal, admin, export, and API route.
- Service tests for blueprint generation, developer-plan generation, validation, scoring, state transitions, exports, and notifications.
- Repository tests for each persistence implementation, including ownership and tenant scoping.
- Role/permission tests for every sensitive surface and cross-tenant boundary.
- AI validation tests for malformed JSON, missing keys, forbidden claims, unsafe promises, retry/repair paths, and human-review gates.
- Export tests proving customer-safe exports exclude internal notes, raw AI output, developer-only details, and other customer data.
- Security negative tests for auth/session, file upload, prompt/AI logs, role changes, public-example publishing, and data leakage risks.
- Template/static asset smoke tests for dashboard, wizard, result, admin, and error surfaces.

### Smoke testing expectations

Automated route tests are necessary, but they are not a substitute for a live-server smoke test when a change affects the runnable web app.

Run a live HTTP smoke test before marking work complete when a change affects any of these surfaces:

- Flask app startup, app factory wiring, configuration loading, entry points, or repository injection.
- Public, customer, internal, admin, developer, QA, support, export, or health routes.
- Jinja templates, static assets, navigation, forms, dashboards, result pages, or error pages.
- Authentication/session behavior, role guards, redirects, or permission-denied flows.
- Runtime dependencies, packaging, CI scripts, or anything that could prevent `python flaskApp.py` from starting.

A proper live smoke test means:

1. Start the app in a real local process using `python flaskApp.py` with a non-default test port when practical.
2. Request `/health` over HTTP and confirm `200 OK` plus a non-sensitive JSON payload.
3. Request `/` and every newly added or materially changed page route over HTTP and confirm the expected status code and key page text.
4. For protected routes, smoke at least one allowed access path and one denied/redirect path when local auth fixtures make that practical.
5. Stop the local server after the smoke test.
6. Record the server command, smoke command, status codes, and salient payload/page checks in `LOG.md` when it exists.

If the app cannot start or a route cannot be smoke-tested, do not claim the web change is complete. State the blocker, fix it if possible, and rerun the smoke test. For docs-only or pure service/repository changes that do not affect runtime startup or routes, a live smoke test is optional; run the strongest relevant tests instead.

### Change-specific validation rules

- New routes require route tests, permission tests, and live HTTP smoke tests for the new or changed route surface.
- New services require service tests with edge cases and failure cases.
- New repositories or schema changes require repository tests and migration/seed tests when applicable.
- New AI prompts or schemas require validation tests, fake-client tests, and forbidden-claim tests.
- New export behavior requires export shape tests, role-access tests, and audit-event tests.
- New dashboard metrics require service tests for calculations and route/template tests for visibility.
- Security-sensitive changes require both positive and negative tests.
- Bug fixes require regression tests that fail before the fix when practical.
- Docs-only changes require at least whitespace validation, such as `git diff --check -- <changed docs>`.

### Completion standard

Before marking work complete:

1. Run the most focused tests that prove the changed behavior.
2. Run a live HTTP smoke test when the change affects app startup, routes, templates, static assets, navigation, forms, dashboards, auth/session, or runtime configuration.
3. Run the full local CI gate when tooling exists and the change affects code, tests, security, exports, AI, auth, persistence, or templates.
4. If full CI or live smoke testing cannot be run, state why and run the strongest narrower validation available.
5. Record verified PASS/FAIL outcomes in LOG.md once that file exists, including smoke-test commands and status codes when smoke testing applies.
6. Never weaken tests, linting, typing, coverage, security checks, smoke-test requirements, or CI settings just to make a build pass.

## 8.2) Deployment Policy (Cloud Run)

- Deployments, if added later, should use the approved project workflow.
- Do not propose, instruct, or run `gcloud run deploy`, Cloud Build YAML deployments, or other CLI-based Cloud Run deployment flows unless explicitly requested by the repo owner.
- Do not paste secrets (API keys, SMTP passwords, OAuth client secrets, webhook secrets, etc.) into chat, logs, prompts, command lines, client-side JavaScript, or committed files.
  - Secrets must be stored in environment variables or Secret Manager and mapped safely into runtime configuration.

## 8.3) Security Baseline

- Treat all external input as untrusted; validate, normalize, and escape it before use or display.
- Never introduce hardcoded credentials, API keys, tokens, private certificates, or secret URLs.
- Use least privilege for files, services, and credentials; avoid broad access when narrower access works.
- Review dependencies and third-party assets before adding them; avoid unverified packages, scripts, or downloads.
- Do not execute unreviewed code or shell scripts from external sources.
- Do not weaken authentication, permission checks, encryption, audit trails, or session controls.
- Avoid logging sensitive data, personally identifiable information, or secrets.
- For auth/session, file upload, export, AI, prompt, role, billing/proposal, or audit features, include a security impact review and tests.
- If a change could enable injection, XSS, CSRF, path traversal, SSRF, privilege escalation, prompt leakage, raw AI leakage, or data leakage, treat it as high risk and address it explicitly.
- Customer records must be tenant/project-scoped.
- Internal notes, developer plans, raw AI prompts, raw AI responses, validation errors, prompt versions, and AI usage/cost logs are internal-only unless explicitly converted into customer-facing content.
- Public examples require sanitization and explicit Platform Admin approval.

## 8.4) Software Integrity and Supply Chain Safety

- Keep dependency versions pinned where practical, and review lockfile changes carefully before accepting them.
- Verify checksums, signatures, and provenance for external artifacts and downloads when those details are available.
- Do not bypass tests, linting, code review, or validation gates for changes that affect integrity-sensitive behavior.
- Treat build outputs, caches, migrations, generated assets, generated blueprints, and generated developer plans as derived artifacts; regenerate them instead of hand-editing unless documented.
- Preserve audit logs, timestamps, prompt versions, AI request records, validation records, approvals, export histories, and event histories; do not alter records without a traceable reason and approval.
- For update, install, import, export, sync, publishing, and AI-generation flows, validate hashes, versions, identifiers, ownership, and permissions before accepting data.
- Do not add runtime code loading, remote script execution, or unsigned plugin mechanisms without explicit approval.
- Prefer deterministic, reproducible behavior so changes can be verified and tampering is easier to detect.

## 8.5) XML and Markup Processing

- When working with XML or XML-like documents, use DOM for tree-based inspection and editing, SAX for streaming or large-document processing, and DTD or schema validation when the format requires it.
- Treat DTDs and external entities as untrusted by default; disable unsafe entity resolution and related expansion features unless a documented use case requires them.
- Prefer the smallest parsing model that satisfies the task, and preserve document structure, namespaces, and encoding rules when transforming markup.
- Do not assume HTML, XML, SVG, or other markup is safe to render or inject without sanitization and context-appropriate escaping.

## 9) Allocation of Content Across Files
- AGENTS.md: How we work (process, scope boundaries, validation habits).
- README.md: Project overview, setup, and current direction.
- projectGuide.md, when created: Product requirements and architecture intent.
- LOG.md, when created: Verified run history (commands + outcomes only).
- RUNBOOK.md, when created: Operational procedures, deployment notes, environment setup, and recovery guidance.

## 10) Maintenance Checklist
- Before proposing a change: re-read the relevant sections of README.md and projectGuide.md, when available.
- During proposal: ensure scope is a complete, testable logical operation (or a pre-approved ACS).
- Before editing security-sensitive behavior: identify the affected roles, records, ownership rules, and audit events.
- Before rendering AI/customer text: confirm validation, escaping, and customer/internal visibility rules.
- After validation: record verified facts only in LOG.md, when available.

## 11) Example Header (for Python Files)
Use this exact structure for all new or modified Python files. The "Last Updated" date must always be the current date of the modification (e.g., today's date).
# -*- coding: utf-8 -*-
# gridForge/path/to/your/file.py
"""
One-sentence module purpose.

Detailed explanation of the module's role within the application and key
dependencies/interactions.

Author: @seanl
Version: 0001
Creation Date: 08/27/2025
Last Updated: 10/07/2026
"""

from __future__ import annotations
# 1) Standard library imports (alphabetized)

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
# from package.moduleX import Y

def exampleInternalFunction(arg1: int) -> int:
    """
    Demonstrates the required docstring and naming format.

    Args:
        arg1: Example integer argument.

    Returns:
        The incremented integer value.
    """
    return arg1 + 1

## 12) Coding & Documentation Standards (Summary)
Follow these technical standards when editing or adding Python modules:

- Required file header (see Example Header above).
- Imports grouped/alphabetized: standard library, third-party, then application-specific.
- Public modules/classes/functions require docstrings with purpose, Args, Returns.
- File size: start decomposing a source file once it reaches about `1500` lines of code; the primary file should begin shifting into a thin pass-through/orchestration module with focused secondary files in a nearby subdirectory.
- File size maximum: source files may go up to `2500` lines of code as an upper bound, but they should not grow beyond that size; if additional code is needed, split the file instead of extending it further.
- Naming:
  - Classes: PascalCase
  - Functions & Methods (Internal): camelCase
  - Variables, Instances, Parameters: snake_case
  - Constants (Module-level): UPPER_SNAKE_CASE
  - Overridden Methods (e.g., PyQt, Python): snake_case
  - File names: camelCase for source files; tests use test_sourceFileName.py
  - Test function names: camelCase
- Formatting: lines under ~100 chars where feasible; clarity over novelty.
- Keep customer-facing blueprint data separate from internal developer-plan data.
- Keep public-example records separate from private customer workflow records.
- Keep generated AI output behind validation before rendering or storing as successful output.
- Prefer compact, explicit, testable logic over hidden framework magic.

## 13) Decision Analysis
If multiple options are given to the user, then do the following:

- Criteria for Evaluation: Define "better" in the context of the user’s project as primarily focusing on healthiness rather than speed or efficiency. Consider other factors such as sustainability, maintainability, security, privacy, testability, cost, and overall well-being.
- Decision-Making Framework: Utilize multi-criteria decision analysis (MCDA) to evaluate the options based on the defined criteria.
- Output: Suggest the most suitable option for the user’s project, providing a rationale for why this option is considered healthier and better aligned with their goals.
- User Engagement: Encourage the user to specify any additional criteria or preferences that may influence the decision-making process.

## 14) GridForge Product Guardrails

- GridForge is cloud-first and web-first by default.
- Do not introduce native mobile, offline-first behavior, or complex real-time collaboration unless explicitly requested.
- AI assists with planning but does not approve scope, replace human review, or make final business decisions.
- Human review is required before:
  - A generated blueprint becomes customer-approved scope.
  - A developer plan becomes build-ready.
  - A public example is published.
  - A final handoff is marked accepted without customer approval.
- Customer-facing records must not expose:
  - Internal notes.
  - Raw AI prompts.
  - Raw AI responses.
  - Developer-only implementation details.
  - Prompt versions unless intentionally surfaced.
  - Validation errors unless converted into customer-safe language.
  - Other customer data.
- Customer-safe exports must exclude restricted/internal fields.
- Sensitive actions should be fail-closed: if the system is unsure whether a user can see something, it should hide it.
