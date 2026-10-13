# EFINGES - Infrastructure & Technology Stack Specification

This document defines the technology stack, system architecture, integration layers, and auxiliary engineering workflows for **EFINGES**, tailored to satisfy all evaluation criteria while maintaining a robust local containerized deployment setup with enterprise-grade observability.

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
| **Observability** | OTel, Prometheus, Loki, Tempo, Grafana | Production-grade metrics, log aggregation, and distributed tracing running locally for deep operational insights. |
| **Testing** | Vitest (Frontend) & Pytest (Backend) | Fast, modern testing frameworks with native support for coverage and integration testing. | 
| **CI/CD** | GitHub Actions | Automated linting, test execution, and Docker image build validation on push/PR. | 

## 3. Detailed Component Specifications

### 3.1 Frontend Implementation & Structure
* **Structure:** Feature-based directory organization (`/components`, `/services`, `/hooks`, `/pages`).
* **API Communication:** Centralized API client module pointing to the backend base URL, managing interceptors, auth headers, and error handling uniformly.
* **Testing:** Unit and component testing using Vitest and React Testing Library, covering core views (Dashboard, Bill checking, Incidence tracking, Voting).

### 3.2 API Contract & Backend Implementation
* **API Contract:** FastAPI auto-generates a standards-compliant **OpenAPI 3.0 specification** (`/openapi.json` and interactive Swagger UI at `/docs`). This serves as the single source of truth for frontend-backend integration.
* **Backend Structure:** Clean modular architecture (Routers, CRUD operations, Models, Schemas).
* **Backend Testing:** Pytest suite covering core workflows (manual bill creation, role-based access checks, incidence state transitions, and property voting logic).

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
      - "127.0.0.1:${POSTGRES_PORT:-5433}:5432"
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
* **AI Tool & Data Policy (`docs/ai_policy.md`):** Guidelines on prompt construction, data privacy, and code review mandates.
* **Project Instructions:** Custom markdown directives (`.cursorrules`) guiding LLM interactions for EFINGES.
* **Reusable Workflows & Subagent Profile:** Pre-configured prompt templates for bug hunting and feature generation.
* **Mock MCP Server:** A local script exposing database schema tools to LLM coding assistants.
* **Guardrails & Hooks:** Pre-commit hooks checking for hardcoded secrets and validating OpenAPI contract adherence.

## 6. Security, Audit, and DevOps Hardening
* **Deterministic Security Scans:** Output reports from Bandit (Python) and container vulnerability scanners.
* **PR Audit Template:** Standardized checklist for reviewing AI-generated pull requests.
* **Operational Diagnosis Notes:** Troubleshooting logs for container communication, healthchecks, and telemetry exporters.

## 7. Proposed folder structure

```
README.md
product-spec.md
AGENTS.md or equivalent project instructions
frontend/
backend/
openapi.yaml
docker-compose.yml
.github/workflows/
docs/
security/
ops/
```
