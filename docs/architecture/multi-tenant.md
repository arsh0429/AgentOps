# Multi-tenant deployment architecture

> **Status:** design note. Not built. Documents the production-shaped path
> AgentOps would take if it grew from a single-developer dev tool into a
> platform that hosts the AgentOps platform UI for AI-company SREs while
> customers run their own agents and consumer surfaces on-premises.

## The problem

A real distributed deployment of an AI-agent observability platform has two
audiences with conflicting access requirements:

- **Customers** (end-users of the agent's *output*) — want to read research
  digests, ask follow-up questions, never see traces or evals.
- **AI-company providers** (operators of the *platform*) — want telemetry,
  drift detection, eval scores, regression signals. **Should not see raw
  customer prompts, raw model outputs, or retrieved documents** unless the
  customer explicitly opts content in.

Multi-tenancy compounds this: a single provider supports many customers,
each with their own data, tools, evals, and policy. Tenants must be
isolated at the data layer with strong guarantees, not just at the URL.

## Recommended pattern

**Edge agent + sanitised egress + multi-tenant control plane.**

- The **agent runtime** and **consumer UI** run in the customer's
  infrastructure (on-prem, customer cloud, customer VPC).
- A small **redactor** in the AgentOps SDK filters every outbound OTel
  span before it leaves the customer perimeter. Default policy: ship
  *structural signal* (timings, tool names, eval scores, drift values),
  block *content* (prompts, model outputs, tool I/O, retrievals).
- The **AgentOps control plane** (multi-tenant) lives in the provider's
  cloud. It ingests redacted spans over mTLS, routes by tenant, and runs
  drift / eval orchestration per tenant.
- **Eval LLM judges** that need raw I/O run *on customer side*; only the
  numeric `EvalResult` egresses.

```
─── Customer A premises ─────────────         ─── Provider cloud (multi-tenant) ───

  Researcher                                   Provider SRE
     │                                            │
     ▼                                            ▼
  Consumer UI ◀── reads ── Customer-side        Tenant-aware platform UI
  (agentops-research-web)        digest store          │ (filtered to tenant A)
     ▲                       ▲                    ▼
     │                       │                  ┌────────────────────────┐
     │ runs locally          │                  │  Per-tenant data plane │
  Agent runtime ─────────────┘                  │  Tenant A: schema A    │
  (agentops-research-agent)                             │  Tenant B: schema B    │
     │                                          │  Tenant C: schema C    │
     │ otel/genai spans                         └──────────▲─────────────┘
     ▼                                                     │
  SDK Redactor ─── mTLS + scoped API key ────▶  Multi-tenant ingestion
  (egress policy)                                (auth, tenant routing,
     │  ships:                                    rate limit per tenant)
     │   - tool names + timings                            │
     │   - eval scores (no rationales)                     ▼
     │   - cost/token usage                       Drift / eval workers
     │   - explicitly-allowlisted attrs           (per-tenant pods)

─── Customer B premises ─────────────
  (same shape, different policy)  ─── mTLS ──▶  ingestion → tenant B schema
```

## Boundaries in detail

### Network and identity

- **mTLS** between customer SDK and provider ingestion. Mutual auth — the
  provider trusts the cert chain, not just an API key.
- **Per-customer API keys**, scoped (`write:spans`, `read:own-runs`,
  `trigger:regression`), short-lived, rotatable. Tenant ID is enforced
  server-side from the cert / key, never trusted from the request body.
- Customer-side auth (SSO/OIDC, customer's identity provider) gates the
  consumer UI. The provider never sees customer end-users.

### Data isolation (multi-tenancy models)

| Model | Isolation | Cost | When |
|---|---|---|---|
| Tenant column on shared schema | Logical only — bug = leak | Lowest | Internal tools |
| **Schema per tenant** in shared DB | Strong via `SET search_path` per connection | Moderate | **Default for SaaS** |
| DB per tenant | Physical | High | Regulated industries, BYOK customers |

Default to schema-per-tenant on Postgres, with DB-per-tenant available as
an enterprise tier. Tenant routing is a thin middleware that reads the
tenant from the auth context and switches the connection's search_path
before any application query runs.

### What egresses, what doesn't

The redaction policy is configured **per customer** and lives **on the
customer side**. Provider can ship a default policy template; customer
applies it. Default allowlist:

| Allowed (default) | Blocked (default) |
|---|---|
| Span structure (parent / child, timings, status) | Raw user prompts |
| `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.*` | Raw model outputs |
| `gen_ai.tool.name` (which tool fired) | Tool inputs / outputs |
| `agentops.role`, `agentops.run_id` | Retrieved documents (RAG context) |
| Eval scores (numeric, label) | Eval rationales (free text) |
| Drift values | Anything tagged `pii.*` / `confidential.*` |

Provider can detect that quality is drifting and on which tool path —
without seeing what the user asked or what the model said. That's the
contract that makes this enterprise-saleable.

### Tools and data separation

- **Tools are customer code**, executed in customer infrastructure. They
  never cross the boundary. Provider sees only that *a tool named X fired
  and took Y ms* — not what X did or with what data.
- **Custom tools and custom evals** are versioned and registered per
  tenant. Provider serves a registry but never sees the bodies.
- **Eval LLM judges** that need raw I/O execute in the customer's
  environment using the customer's Anthropic key. Only the numeric
  `EvalResult` ships up.

### Drift detection across the boundary

ADWIN, MMD, and PSI all work on aggregates, not content:

- **ADWIN on numeric eval scores** — no leakage.
- **PSI on tool-name distributions** — no leakage.
- **MMD on input embeddings** — needs care. Two paths:
  - (a) embeddings computed customer-side; only embedding vectors egress.
    Small leak surface (an attacker with significant resources could
    invert short embeddings), defensible for most threat models.
  - (b) only the drift signal egresses (`is_drifted=true`), no values.
    Hides too much for diagnosis.

  Default to (a); offer (b) as a stricter mode.

### Provider's view (two consoles)

- **Provider SRE console** — cross-tenant operational health (SLOs,
  ingestion lag, error rates). Cannot access tenant-specific content
  without a break-glass audit trail.
- **Tenant-scoped platform UI** — what `agentops-console` is today. Each
  tenant's customer admin sees only their tenant's data. Provider can
  impersonate a tenant for support, with full audit logging.

### Compliance niceties

- **Audit log** of every cross-tenant access (impersonation, exports,
  bulk reads). Reviewable by tenant.
- **Customer-managed keys** — envelope-encrypt per-tenant data at rest
  with keys the customer controls in their own KMS. Provider has no
  cleartext key access by design.
- **Data residency** — for EU / regulated tenants, the ingestion endpoint
  and data plane are regionalised. Routing-by-tenant happens at the load
  balancer.
- **DSAR / right-to-deletion** — deletes scoped to a single tenant's
  data. Eval history retained per the tenant's retention policy.

## What AgentOps already has vs. what would change

The current single-developer code already has the right *seams* for this
pattern. None of the work below requires architectural rewrites — the
contract on the wire stays the same.

| Surface | Current | Needs for distributed |
|---|---|---|
| OTel/GenAI ingestion | ✓ already framework-agnostic | mTLS termination + per-tenant routing |
| SDK exporter | ✓ clean POST hook (`AgentOpsSpanExporter`) | Add a `redactor: Callable[[Span], Span \| None]` plugin |
| Server data model | Run / Span / EvalResult / DriftStateRow / Dataset / RegressionRun | `tenant_id` column on every table; `SET search_path` middleware |
| API auth | None (single-developer dev tool) | mTLS + scoped API keys + tenant context |
| Eval orchestrator | Server-side LLM judge | Split: customer-side judge for content evals, server-side for invariants and aggregates |
| Drift workers | Server-side | OK as-is — they consume aggregates only |
| Platform UI (`agentops-console`) | Single-tenant | Tenant context in routes (`/t/:tenant/...`); break-glass for provider-side |
| Consumer UI (`agentops-research-web`) | Customer-side, single-tenant by definition | Stays as-is — no tenancy concept needed |
| Repo shape | Two TS apps + Python SDK + server | Add `agentops-redactor/` (customer-side OTel filter), `agentops-control-plane/` (multi-tenant routing layer) |

The biggest design lever: **the redactor plugin in the SDK is the seam
that makes this whole pattern tractable.** Customers ship spans through
it; the existing platform code ingests as before. The wire format
doesn't change.

## Buildout, in priority order

If AgentOps were to evolve toward this:

1. **Customer-side redaction policy** — build on the existing `SpanRedactor`
   protocol and opt-in allowlist, and require it before any customer data
   crosses a tenant boundary.
2. **Tenant column on all server tables** + session-layer enforcement.
   *~1 day.*
3. **API key auth with scopes on `/ingest`.** *~½ day.*
4. **Tenant-scoped routing in the platform UI** (`/t/:tenant/...`).
   *~½ day.*
5. **mTLS + ingestion gateway** as a small forward-proxy service that
   terminates customer TLS, validates certs, injects tenant context,
   forwards to internal ingestion. *~1 day.*
6. **Customer-side eval runner** as a separate package — same
   `@agentops/sdk` evaluation surface, but execution stays local; only
   `EvalResult` (no rationale) goes upstream. *~1 day.*
7. **Documentation** — customer deployment guide + tenant onboarding
   runbook. *~½ day.*

Total: ~5 focused days to a real distributed-ready posture.

## Why this is documented but not built

This portfolio is for an **AI Agent Software Engineer** role. The signal
that role hires for is "can you build agents and the platforms that
support them." The signal demonstrated by *implementing* multi-tenancy
(versus *designing* for it) doesn't move the needle for that role —
it's more relevant for a Platform Engineer or Distributed Systems role.

This document exists so a reviewer can see the architectural reasoning,
the seam choices, and the migration path — without reading 5 days of
incidental implementation work that would crowd the agent-engineering
story.
