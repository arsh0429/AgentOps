# AgentOps roadmap

This roadmap describes future work beyond the current local-first release. Ordering may change as deployment and user feedback clarify priorities.

## Production service foundation

- Add PostgreSQL support with versioned schema migrations.
- Move evaluation, regression, digest, and drift work to durable queues.
- Add authentication, role-based access control, tenant isolation, and audit logs.
- Publish container images and deployment manifests with health, readiness, and graceful-shutdown behavior.
- Add retention policies, archival, backups, and disaster-recovery guidance.

## Telemetry and interoperability

- Accept standard OTLP/HTTP and OTLP/gRPC alongside the compact ingestion endpoint.
- Add sampling controls, exporter compression, batching policies, and delivery metrics.
- Expand GenAI semantic-convention coverage as the upstream standard evolves.
- Publish signed Python and npm releases with compatibility matrices.
- Add integrations for popular agent frameworks while keeping the core contract framework-neutral.

## Evaluation operations

- Add dataset versioning, annotations, review queues, and approval workflows.
- Support configurable evaluation graphs, scheduled regressions, and baseline promotion.
- Add judge calibration, inter-rater analysis, confidence intervals, and score explanations.
- Integrate experiment tracking and pull-request quality gates.

## Drift intelligence

- Add configurable windows, thresholds, minimum sample sizes, and detector ensembles.
- Segment drift by tenant, agent, model, prompt revision, and deployment.
- Add alert routing, acknowledgement, suppression, and incident timelines.
- Connect detected shifts to representative traces and likely contributing changes.

## Console and research experience

- Add streaming trace updates, advanced filtering, saved views, and shareable links.
- Add accessible chart alternatives, keyboard navigation, and responsive layouts.
- Add research-job cancellation, retry controls, provenance export, and richer citation review.
- Add configurable dashboards and organization-level usage views.

## Reliability and governance

- Establish load, soak, chaos, and upgrade test suites.
- Add service-level objectives and self-observability dashboards.
- Document threat models, data classification, and privacy deployment patterns.
- Add automated dependency, license, and supply-chain checks.
