# AMI Risk Domain Specification

## 1. Mission & Scope
- Deliver a first-class risk management domain under `domains/risk` that operationalises the lifecycle required by EU AI Act Article 9, ISO/IEC 42001 Clause 8, ISO/IEC 23894, and the consolidated compliance backlog (see `compliance/docs/research/COMPLIANCE_GAP_ANALYSIS.md`, GAP-AI-001).
- Treat Base DataOps artefacts (BPMN relational models, UnifiedCRUD, storage backends) as the authoritative substrate for storing, querying, and orchestrating all risk entities.
- Supply the risk lifecycle services and data contracts expected by the forthcoming compliance backend (`compliance/docs/research/COMPLIANCE_BACKEND_SPEC.md`) so that `risk_service.py` can rely on this domain without duplicating business logic.
- Provide reusable BPMN-driven workflows and telemetry that downstream orchestrators (`backend/scheduling`, `backend/agents`) can invoke for risk identification, assessment, mitigation, incident response, and post-market monitoring.

## 2. Guiding Principles
- **Base Alignment:** All persistence uses `StorageModel` + `UnifiedCRUD` (`base/backend/dataops/models/base_model.py`, `base/backend/dataops/core/unified_crud.py`). Risk models declare storage targets via `StorageConfig` rather than custom DAOs.
- **BPMN-Native Execution:** Workflow definitions live in `base.backend.dataops.models.bpmn_relational.Process` and are executed through the shared scheduling service (`backend/scheduling/SPEC-SCHEDULING.md`). The risk domain only owns the domain semantics, not a bespoke engine.
- **Evidence & Audit Ready:** Every mutating action emits audit entries through `base.backend.dataops.security.audit_trail` and attaches evidence pointers compatible with the compliance service contract.
- **Data Classification First:** Reuse `base.backend.dataops.models.security.DataClassification` and ACL utilities to protect sensitive risk content (hazards, incidents, regulator correspondence).
- **Continuous Feedback Loop:** Post-market monitoring (Article 73) and Key Risk Indicator telemetry feed back into BPMN loops that re-open assessments when thresholds are breached.

## 3. Core Capabilities
- **Risk Register Service:** CRUD + search for risks, hazards, and control mappings exposed over an internal service API (`domains/risk/services/risk_registry.py`) and surfaced to the compliance MCP.
- **Lifecycle Workflows:** Managed BPMN processes for identification, assessment, treatment, monitoring, and acceptance, seeded from `/base` DataOps models (`Process`, `Task`, `Gateway`, `Event`). Includes reusable sub-processes for residual risk reviews and Article 73 incident handling.
- **Control Alignment:** Link risks to controls defined in the compliance module (`compliance/backend/models/controls.py`) and ISO 27001/NIST controls tracked in Base. Surface coverage gaps and compensating controls.
- **KRI & Metrics Engine:** Collect quantitative indicators (timeseries) such as likelihood drift, incident frequency, and mitigation SLAs, persisting snapshots in the TimeSeries backend (`StorageType.TIMESERIES`).
- **Incident & Escalation Handling:** Provide domain services for Article 73 notifications, SLA countdown tracking, regulator response logging, and auto-reopening of BPMN incidents when evidence is incomplete.
- **Reporting & Exports:** Generate structured packets (JSON/CSV) summarising risk posture, mitigation status, and outstanding actions for regulators, feeding the compliance evidence workflow.
- **Generic Assessment Toolkit:** Ship reusable scoring templates, probability/impact matrices, and scenario simulators that support non-AI risk categories (operational, vendor, security) while reusing the shared persistence, BPMN hooks, and telemetry pipelines.

## 4. Architecture Overview
1. **Risk Domain API Layer** – Pydantic-forward service module (`domains/risk/services/`) exposing orchestrator-friendly functions (register risk, schedule assessment, record mitigation, export risk report).
2. **BPMN Orchestration Hooks** – Templates and utilities that create/update `Process` definitions, register with the scheduler, and launch `ProcessInstance` runs tied to risk IDs. Aligns with `backend/scheduling` event gateway for external triggers.
3. **Persistence Layer** – Data models living under `domains/risk/models/` built on `StorageModel` with storage configs for graph, document, timeseries, and vector stores as required. Use `UnifiedCRUD` helpers for operations.
4. **Metrics & Telemetry** – Integration with Base metrics collectors (`base/backend/utils/metrics`) to emit Prometheus-compatible metrics; optionally push structured logs to audit trails.
5. **Assessment Engine** – Pluggable `AssessmentEngine` service providing generic scoring templates, risk taxonomies, and scenario simulations that produce `RiskAssessment` artefacts regardless of domain context.
6. **Compliance Bridge** – Sync layer that packages risk data for consumption by `compliance/backend/services/risk_service.py` and ensures evidence attachments resolve to compliance evidence entries.
7. **Agent & MCP Integrations** – Tooling loaders that let `backend/agents` and MCP clients query/update risk state via typed interfaces, enforcing role-based access control (RBAC) from Base security models.

## 5. Data Model Blueprint
| Model | Purpose | Key Fields | Storage Targets |
| --- | --- | --- | --- |
| `RiskRegisterEntry` | Canonical risk/hazard record. | `risk_id`, `title`, `description`, `category` (taxonomy aligned with ISO/IEC 23894), `likelihood`, `impact`, `risk_owner`, `status`, `data_classification`, `related_process_ids`, `control_links` | `document`, `graph` |
| `RiskAssessment` | Outcome of a lifecycle evaluation. | `assessment_id`, `risk_id`, `trigger_source` (e.g. BPMN, incident, model drift), `assessment_method`, `initial_rating`, `residual_rating`, `assessor`, `assessment_date`, `review_due`, `evidence_refs` | `document` |
| `MitigationPlan` | Treatments and follow-up actions. | `plan_id`, `risk_id`, `treatment_strategy`, `tasks` (linked BPMN task IDs), `owner`, `start_date`, `target_completion`, `status`, `dependencies` | `graph`, `document` |
| `ControlCoverage` | Mapping to compliance controls. | `link_id`, `risk_id`, `control_id` (from `compliance/backend/models/controls.py`), `coverage_level`, `residual_gap`, `last_verified_at`, `evidence_refs` | `graph` |
| `IncidentReport` | Article 73 / breach log. | `incident_id`, `risk_id`, `severity`, `detected_at`, `reported_at`, `authority_notifications`, `corrective_actions`, `regulator_feedback`, `sla_deadline`, `closure_state` | `document`, `timeseries` |
| `KRISnapshot` | Quantitative monitoring sample. | `risk_id`, `timestamp`, `metric` (enum), `value`, `threshold`, `breach_state`, `source_system` | `timeseries` |
| `RiskEvidence` | Evidence pointers for audit trail. | `evidence_id`, `risk_id`, `source_type`, `location`, `hash`, `submitted_by`, `submitted_at`, `validation_state`, `linked_control_ids` | `document`, reuse compliance evidence schema |
| `RiskVectorEmbedding` | Optional semantic index for similar risks. | `risk_id`, `embedding`, `model_ref`, `last_refreshed` | `vector` |

### Model Conventions
- Extend `StorageModel` directly or via mixins such as `SecuredModelMixin` to inherit ACL enforcement.
- Use Base enumerations where available (`DataClassification`, `Permission`, `ComplianceStatus`). Introduce new enums only when not present in Base/Compliance.
- Register CRUD helpers with `get_crud()` (`base/backend/dataops/services/unified_crud.py`) to ensure per-model caching and connection pooling.
- Maintain forward references to BPMN artefacts (`Process`, `Task`, `ProcessInstance`) using their graph IDs for traceability.

## 6. BPMN Lifecycle Alignment
- **Process Library:** Maintain a catalogue of BPMN XML definitions (stored alongside domain code or in DataOps) covering: Risk Intake, Periodic Assessment, Mitigation Execution, Residual Risk Review, Incident Response, Post-Market Monitoring. Each process should map to predefined lanes (Risk Owner, Compliance, Engineering, Regulator Liaison) via `WorkerBinding` metadata from the scheduling spec.
- **Instance Synchronicity:** When a `RiskRegisterEntry` is created/updated, spawn or update `ProcessInstance` records to reflect active treatments. Use correlation keys equal to `risk_id` and maintain business keys grouping by product/service.
- **Gateway Policies:** Encode decision logic (e.g. accept residual risk vs escalate) in BPMN gateways using data from assessments and compliance statuses. Gateways should call into the risk service for scoring calculations, including generic risk categories provided by the Assessment Engine.
- **Event Handling:** Integrate with the scheduling Event Gateway to react to: KPI breaches (timeseries alerts), compliance evidence submissions, or external regulator notifications. Intermediate events must translate into `RiskAssessment` or `IncidentReport` updates.
- **Audit Integration:** Each BPMN task completion logs to the audit trail, including references to evidence and controls, satisfying traceability required by Article 12 logging expectations.

## 7. Integrations & Dependencies
- **Base Module:**
  - Persistence via `UnifiedCRUD`, `StorageConfig`, and existing connection providers.
  - BPMN models (`base/backend/dataops/models/bpmn_relational.py`) for process definitions and runtime state.
  - Security primitives (`base/backend/dataops/models/security.py`) for ACLs, roles, and data classification.
  - Compliance reporting helpers (`base/backend/dataops/security/compliance_reporting.py`) for severity vocabularies and SOC2 alignment.
- **Compliance Module:**
  - Share risk/control linkage data and incident status with `compliance/backend/services/risk_service.py` once implemented.
  - Honor evidence contracts defined in `compliance/docs/research/COMPLIANCE_BACKEND_SPEC.md` and surface GAP-AI-001 remediation progress.
  - Provide MCP tools or adapters so compliance clients can query risk posture without duplicating queries.
- **Backend Scheduling:**
  - Register all risk BPMN definitions and schedule recurrences through the scheduler MCP (see `backend/scheduling/SPEC-SCHEDULING.md`).
  - Subscribe to scheduler events for task readiness and worker dispatch (risk reviews may require human-in-the-loop tasks).
- **Backend Agents:**
  - Offer LangChain tools or MCP adapters so agents can fetch risk profiles, update mitigation tasks, or summarise incidents.
- **Nodes & External Services:**
  - Use Node setup automation for provisioning dependencies (databases, message brokers) before launching intensive workflows.

## 8. Compliance Traceability
| Obligation | Source | Risk Domain Fulfilment |
| --- | --- | --- |
| Lifecycle risk management | EU AI Act Article 9 (`compliance/docs/research/consolidated/.../risk_management_system.md`) | BPMN processes covering identification → mitigation → monitoring, risk register persistence, continuous reviews triggered by telemetry. |
| Post-market monitoring & incident reporting | EU AI Act Articles 61 & 73 | `IncidentReport` models + Article 73 SLA tracking, regulator notification workflows, audit trail linkage. |
| AIMS risk assessment & treatment | ISO/IEC 42001 Clauses 6.1, 8.2, 8.3 | Structured assessments, mitigation plans, residual risk acceptance BPMN gateways, linkage to AIMS controls. |
| Risk management guidance alignment | ISO/IEC 23894:2023 | Taxonomy fields and evaluation steps follow ISO 23894 categories, scenario analysis, and risk treatment heuristics. |
| Information security risk integration | ISO/IEC 27001 Clause 6.1.2 | Shared controls and classification with Base security models ensure AI risks feed the organisation-wide ISMS register. |
| Governance-Measure-Manage functions | NIST AI RMF | Governance via role ownership & audit logs, Measure via KRI metrics and generic assessments, Manage through mitigation workflows and residual risk approvals. |
| Compliance backlog closure | `COMPLIANCE_GAP_ANALYSIS.md` GAP-AI-001 | Risk service + DAO delivered here so compliance backend can expose Article 9 coverage; provide API hooks documented in this spec. |

## 11. Risk MCP Contract
- **Server:** `domains/risk/mcp/risk_server.py`, extending `base.backend.mcp.fastmcp_server_base.FastMCPServerBase` and registering under namespace `risk`.
- **Authentication & RBAC:** Reuse Base security contexts; enforce that mutating tools require `Permission.WRITE` or `Permission.ADMIN` and classification-aware checks (e.g. `DataClassification.RESTRICTED`).

### Tool Catalogue
| Tool | Purpose | Inputs | Outputs |
| --- | --- | --- | --- |
| `risk.create_entry` | Register a new `RiskRegisterEntry` and kick off the relevant BPMN intake process. | `risk_payload` (matches `RiskRegisterEntry` schema minus server-generated IDs). | Created entry snapshot + correlation IDs (`risk_id`, BPMN `process_instance_id`). |
| `risk.run_assessment` | Launch a generic or AI-specific assessment using the Assessment Engine templates. | `risk_id`, `assessment_template_id`, optional `parameters` (scenario modifiers, probability overrides). | `RiskAssessment` record, BPMN task identifiers, residual risk score. |
| `risk.get_dashboard` | Retrieve aggregated metrics and KRIs for one or more risks. | Filter object (`risk_ids`, `category`, `owner`, `time_window`). | Structured dashboard payload containing summaries, trend data, outstanding actions. |
| `risk.submit_evidence` | Attach audit evidence or regulatory correspondence. | `risk_id`, `evidence_payload` (shared schema with compliance evidence). | Updated `RiskEvidence` list, audit reference, optional compliance control updates. |
| `risk.export_report` | Produce a regulator-ready package (JSON/CSV) covering register entries, assessments, incidents, and control coverage. | `format`, `scope` (single risk, portfolio, standard), optional `include_incidents`. | Report artefact metadata (`uri`, `hash`, `generated_at`) plus summary counts. |
| `risk.stream_updates` | Optional SSE tool to subscribe to risk lifecycle events (assessment progress, incident escalations). | `risk_id` or `category`, subscription token. | Event stream conforming to MCP streaming contract with payloads referencing BPMN task IDs and audit hashes. |

### Transport Expectations
- Support synchronous REST and optional SSE/WebSocket transports following FastMCP conventions.
- All responses include `audit_ref` metadata so downstream consumers (compliance backend, agents) can link activity to immutable logs.
- Clients must set `risk_compute_profile` headers/environment variables when requesting heavy simulations; the server respects `AMI_COMPUTE_PROFILE` to launch appropriate workers.

### Implementation Notes
- Implement MCP adapters on top of the existing services (`RiskRegistryService`, `AssessmentEngine`, `IncidentService`) to avoid duplicating business logic.
- Provide integration tests that hit the MCP tools using module-level test runners (per repo guardrails) and validate BPMN process launches and audit logging side effects.
- Document CLI usage in `domains/risk/README.md` once the server ships; include examples for both AI-specific and generic operational risk assessments.

## 9. Operational Considerations
- **Configuration:** Define `.env` keys (`RISK_STORAGE_GRAPH_URI`, `RISK_DEFAULT_REVIEW_DAYS`, `RISK_KRI_SOURCE`) that mirror Base settings patterns. Honour `AMI_HOST` overrides for external services.
- **Access Control:** Enforce RBAC using Base roles. High-severity risks default to `DataClassification.RESTRICTED`; exposures require explicit audit logging.
- **Testing:** Provide pytest suites covering models, service APIs, BPMN workflow happy paths, failure scenarios, and compliance mappings. Reuse module-level scripts per repository standards.
- **Observability:** Emit structured logs (JSON) with risk IDs, process instance IDs, and correlation keys. Publish Prometheus metrics for SLA countdowns and threshold breaches.
- **Versioning:** Maintain migration helpers to update BPMN versions and risk taxonomies without breaking running process instances.
- **Documentation Sync:** Keep this spec aligned with updates in `/compliance/docs/research` and `/base` so that risk and compliance roadmaps remain in lockstep.

## 10. Implementation Roadmap (Draft)
1. **Phase 0 – Foundations:** Define Pydantic models, storage configs, and CRUD scaffolding. Import/normalise risk taxonomy from consolidated compliance docs.
2. **Phase 1 – BPMN & Services:** Author BPMN definitions, integrate with scheduler, and implement registry/assessment services with audit logging.
3. **Phase 2 – Compliance Bridge:** Build control linkage, evidence export, and MCP adapters, enabling compliance backend integration.
4. **Phase 3 – Telemetry & Incidents:** Add KRI ingestion, Article 73 workflows, and Prometheus metrics with alert routing.
5. **Phase 4 – Automation & AI Assistants:** Expose risk tooling to agents, implement automated risk summarisation, and refine feedback loops based on production monitoring.

---

This specification is the authoritative blueprint for the `domains/risk` module. Update it alongside major architecture or compliance changes to keep Base, Compliance, and Orchestrator modules synchronised.
