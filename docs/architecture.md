# EFINGES - Infrastructure & Technology Stack Specification

This document defines the technology stack, system architecture, integration layers, and auxiliary engineering workflows for **EFINGES**. It describes the system as it is actually built and run (local Docker Compose with a full observability pipeline); where it drifts from the code, the code and the root `README.md` win.

## 1. High-Level System Architecture

EFINGES follows a modern three-tier decoupled architecture integrated with a local observability pipeline:

1. **Presentation Layer (Frontend):** A responsive Single Page Application (SPA) providing user interfaces for Residents, Managers, and Administrators.
2. **Application Layer (Backend):** A RESTful API server handling business logic, user authorization, bill creation, incidence lifecycles, and voting computations. Emits OpenTelemetry traces and metrics.
3. **Data Layer (Database):** A relational database managing multi-tier property hierarchies, resident records, bills, maintenance threads, and voting logs.
4. **Observability Pipeline:** OpenTelemetry Collector collecting telemetry from the backend, backed by Prometheus (metrics), Loki (logs), Tempo (traces), and visualized via Grafana.

All components run locally via **Docker Compose** to guarantee environment parity and seamless execution.

## 2. Technology Stack Selection

| Tier / Component | Technology Choice | Rationale | 
| ----- | ----- | ----- | 
| **Frontend** | React (Vite) + TypeScript + Tailwind CSS | Component-driven, highly maintainable, strong typing, rapid UI development with clean utility styling. | 
| **Backend** | Python (FastAPI) | Automatically generates an **OpenAPI specification**, supports asynchronous requests, and ensures strict data validation via Pydantic. | 
| **Database** | PostgreSQL (runtime) / SQLite (unit tests) | Relational data integrity required for complex property hierarchies (Communities -> Buildings -> Units -> Residents) and tagging relations. | 
| **Containerization** | Docker & Docker Compose | Orchestrates frontend, backend, database, and observability services into a single local execution environment. | 
| **Observability** | OTel Collector, Prometheus, Loki, Tempo, Grafana | Traces, metrics, and logs exported over OTLP from the backend; collected once and fanned out to three storage backends and a provisioned dashboard. |
| **Testing** | Pytest (backend unit + integration) & Vitest + React Testing Library (frontend) | Unit tests run on in-memory SQLite; the three key workflows run against a dedicated PostgreSQL; the frontend tests cover components and pure logic. |
| **Linting** | Ruff (backend) & ESLint 9 flat config (frontend) | One fast formatter + linter per language, run identically locally (`make lint`) and in CI. |
| **CI/CD** | GitHub Actions | Runs lint, both test suites, and the frontend build, then builds both Docker images once the other jobs pass. Deployment is intentionally out of scope (local Compose only). |

## 3. Detailed Component Specifications

### 3.1 Frontend Implementation & Structure
* **Structure:** Split by concern under `frontend/src/`: `pages/` (one file per role's home plus `pages/<role>/` sections), `services/` (the API layer), `auth/` (context, provider, route guard, navigation model), `hooks/`, `types/`, and `test/` helpers.
* **API Communication:** Every call goes through one centralized client, `frontend/src/services/apiClient.ts`, which owns the base URL, attaches the Bearer token, and normalizes errors. The typed service modules (`property`, `billing`, `maintenance`, `governance`, `auth`, `users`, `assignments`) are thin wrappers over it; no component calls `fetch` directly.
* **Testing:** Vitest + React Testing Library cover the login/navigation flow, each role's screens, and the pure logic seams (bill filtering, ballot handling, incidence transitions, initiative scoping, user-form validation), with a documented `npm test` / `npm run test:watch`.

### 3.2 API Contract & Backend Implementation
* **API Contract:** FastAPI generates the OpenAPI schema served at `/openapi.json` and Swagger UI at `/docs`, and the same schema is exported to `openapi.yaml` at the repository root. That committed file is the single source of truth for frontend-backend integration; `backend/tests/test_openapi_contract.py` fails if it drifts, and `make openapi` regenerates it.
* **Backend Structure:** Routers under `app/routers/`, Pydantic schemas in `app/schemas/` (split by area), SQLAlchemy models in `app/models/`, dependencies in `app/dependencies.py`, and all access rules centralized in `app/access.py`.
* **Backend Testing:** The unit suite (`backend/tests/`, in-memory SQLite) covers CRUD, role boundaries, bill status, incidence transitions, and voting; the integration suite (`backend/tests/integration/`, dedicated PostgreSQL) drives the three key workflows over HTTP.

### 3.3 Database Integration
* **ORM:** SQLAlchemy with Alembic for database migrations.
* **Environments:** Supports environment-based configuration separating local development from testing databases.

### 3.4 Containerization & Local Deployment (`docker-compose.yml`)
The full system runs via Docker Compose, including the application services and the complete monitoring pipeline:

```yaml
name: efinges

services:
  backend:
    image: efinges-backend:${EFINGES_TAG:-local}
    build: 
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "127.0.0.1:${BACKEND_PORT:-8000}:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://efinges:efinges@postgres:5432/efinges
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: efinges-backend
    depends_on:
      postgres:
        condition: service_healthy
      otel-collector:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]
      interval: 5s
      timeout: 3s
      retries: 12

  frontend:
    image: efinges-frontend:${EFINGES_TAG:-local}
    build: 
      context: .
      dockerfile: Dockerfile.frontend
      args:
        VITE_API_URL: http://localhost:8000
    ports:
      - "127.0.0.1:${FRONTEND_PORT:-3000}:3000"
    depends_on:
      - backend
    restart: unless-stopped

  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: efinges
      POSTGRES_PASSWORD: efinges
      POSTGRES_DB: efinges
    ports:
      - "127.0.0.1:${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U efinges -d efinges"]
      interval: 5s
      timeout: 3s
      retries: 12

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.123.0
    command: ["--config=/etc/otelcol-contrib/config.yaml"]
    volumes:
      - ./observability/otel-collector.yaml:/etc/otelcol-contrib/config.yaml:ro
    depends_on:
      prometheus:
        condition: service_started
      loki:
        condition: service_started
      tempo:
        condition: service_started
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v3.2.1
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --web.enable-lifecycle
    ports:
      - "127.0.0.1:${PROMETHEUS_PORT:-9090}:9090"
    volumes:
      - ./observability/prometheus.yaml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    restart: unless-stopped

  loki:
    image: grafana/loki:3.5.0
    command: ["-config.file=/etc/loki/config.yaml"]
    ports:
      - "127.0.0.1:${LOKI_PORT:-3100}:3100"
    volumes:
      - ./observability/loki.yaml:/etc/loki/config.yaml:ro
      - loki_data:/loki
    restart: unless-stopped

  tempo:
    image: grafana/tempo:2.7.2
    command: ["-config.file=/etc/tempo/config.yaml"]
    ports:
      - "127.0.0.1:${TEMPO_PORT:-3200}:3200"
    volumes:
      - ./observability/tempo.yaml:/etc/tempo/config.yaml:ro
      - tempo_data:/var/tempo
    restart: unless-stopped

  grafana:
    image: grafana/grafana:11.5.2
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
    ports:
      - "127.0.0.1:${GRAFANA_PORT:-3001}:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./observability/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./observability/grafana/dashboards:/var/lib/grafana/dashboards:ro
    depends_on:
      prometheus:
        condition: service_started
      loki:
        condition: service_started
      tempo:
        condition: service_started
    restart: unless-stopped

volumes:
  postgres_data:
  prometheus_data:
  loki_data:
  tempo_data:
  grafana_data:

networks:
  default:
    ipam:
    config:
      - subnet: ${EFINGES_SUBNET:-10.215.25.0/24}
```

### 3.5 Metrics, Logs, and Alerts Architecture (Observability)
The `./observability/` directory structures the monitoring tools:
* **`otel-collector.yaml`**: Receives telemetry data from the backend and routes metrics to Prometheus, logs to Loki, and traces to Tempo.
* **`prometheus.yaml`**: Scrapes backend and system metrics for monitoring service health.
* **`loki.yaml`**: Aggregates structured JSON logs for error tracking and auditability.
* **`tempo.yaml`**: Captures distributed traces for performance bottleneck analysis.
* **Grafana Dashboards**: Pre-provisioned dashboards provide real-time visualization of HTTP request rates, error codes, and container resource usage at `http://localhost:3001`.

## 4. Integration Testing Strategy
* **Separation:** Unit tests run in-memory or mocked. Integration tests run against a spinning test database container.
* **Key Workflows Tested:**
  1. Resident submits an incidence -> Manager updates status -> Comment thread exchange.
  2. Manager creates an initiative -> Resident casts a property-weighted vote -> Vote aggregation.
  3. Manager creates a manual bill -> Resident checks status (Pending/Paid/Overdue).

## 5. Agent Extension Pack & AI Workflow Documentation
* **Project Instructions:** `AGENTS.md` (context, required behavior, validation commands) with `.github/copilot-instructions.md` as the entry point and `.cursorrules` pointing back at `AGENTS.md`.
* **Reusable Prompts & Subagent:** `.github/prompts/` (implement a backlog task, diagnose a failing check, review an API change) and a read-only `.github/agents/bug-hunter.agent.md` profile.
* **Mock MCP Server:** `backend/scripts/mock_mcp_server.py` — a read-only, metadata-only stdio server exposing the SQLAlchemy table and column schema to LLM coding assistants (never a database connection or row data).
* **Guardrails & Hooks:** `.pre-commit-config.yaml` blocks staged hard-coded secrets (`backend/scripts/check_staged_secrets.py`) and verifies the OpenAPI contract (`make openapi-check`).
* **AI Tool & Data Policy (`docs/ai_policy.md`):** prompt construction, data privacy, permitted agent actions, and mandatory human review; the allow/deny list is in `docs/agent-permissions.md`.
* **Workflow record (`docs/ai_workflow.md`):** the prompts, context files, review, and verification for the project's tasks, with completed audits in `docs/pr_audits/`.

## 6. Security, Audit, and DevOps Hardening
* **Deterministic Security Scans:** Committed reports under `security/` — Bandit static analysis of the backend Python, plus Trivy vulnerability scans of both images — with a full triage in `security/README.md`; regenerate with `make security`.
* **PR Audit:** `.github/pull_request_template.md` is the checklist every change is reviewed against; `docs/pr_audits/` holds completed examples of it applied to real tasks, including reviews that caught defects.
* **Operational Diagnosis Notes:** `docs/operations.md` records real troubleshooting sessions with the containers and telemetry (symptom, evidence, root cause, fix, verification).

## 7. Repository layout (as built)

```
README.md
AGENTS.md               # project instructions (and .cursorrules, .github/copilot-instructions.md)
.github/                # workflows/ci.yml, prompts/, agents/, pull_request_template.md
backend/                # FastAPI app/ (routers, models, schemas, access), tests/, alembic/, scripts/
frontend/               # React + Vite SPA (src/pages, services, auth, hooks, types)
openapi.yaml            # exported API contract (single source of truth)
docker-compose.yml      # backend, frontend, postgres + observability pipeline
Dockerfile.backend
Dockerfile.frontend
observability/          # otel-collector, prometheus, loki, tempo, grafana config
security/               # Bandit + Trivy reports and their triage
Makefile                # install/run/test/lint/build/up/seed/security/...
docs/                   # specs, architecture, backlog, ai_policy, ai_workflow, pr_audits, operations
```
