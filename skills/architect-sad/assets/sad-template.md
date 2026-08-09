<!--
  Architecture Description Standard (ADS) — Solution Architecture Document template
  Structure aligned with https://archstandard.org/v1/ and the Medwick Healthcare example:
  https://archstandard.org/v1/examples/medwick-healthcare/
  Fill every section; use "TBD" / "N/A (justify)" rather than deleting headings.
  Content may be gathered later — do not invent facts. Mark unknowns explicitly.
-->

# Solution Architecture Document — {{SOLUTION_NAME}}

#### About This Document

| Field | Value |
| --- | --- |
| Standard | Architecture Description Standard (ADS) v1 |
| Documentation depth | {{DEPTH}} <!-- minimum / recommended / comprehensive --> |
| Organisation | {{ORG_NAME}} |
| Solution | {{SOLUTION_NAME}} |
| Source / brief | {{BRIEF_OR_LINKS}} |

---

## 0. Document Control

### 0.1 Document Metadata

| Field | Value |
| --- | --- |
| Document Title | Solution Architecture Document – {{SOLUTION_NAME}} |
| Application / Solution Name | {{SOLUTION_NAME}} |
| Application ID | {{APPLICATION_ID}} |
| Author(s) | {{AUTHORS}} |
| Owner | {{OWNER}} |
| Version | {{VERSION}} |
| Status | {{STATUS}} <!-- Draft / In Review / Approved --> |
| Created Date | {{CREATED_DATE}} |
| Last Updated | {{LAST_UPDATED}} |
| Classification | {{CLASSIFICATION}} <!-- public / internal / restricted / highly-restricted (or org scheme) --> |

### 0.2 Change History

| Version | Date | Author / Editor | Description of Change |
| --- | --- | --- | --- |
| {{VERSION}} | {{LAST_UPDATED}} | {{AUTHORS}} | Initial draft from template |

### 0.3 Contributors & Approvals

| Name | Role | Contribution Type |
| --- | --- | --- |
| TBD | Solution Architect | Author |
| TBD | TBD | Reviewer / Approver |

### 0.4 Document Purpose & Scope

{{DOCUMENT_PURPOSE}}

In scope:

- TBD

Out of scope:

- TBD

Related documents:

- TBD

---

## 1. Executive Summary

### 1.1 Solution Overview

{{SOLUTION_OVERVIEW}}

### 1.2 Business Context & Drivers

| Driver | Description | Priority |
| --- | --- | --- |
| TBD | TBD | Critical / High / Medium / Low |

### 1.3 Strategic Alignment

#### Organisational Strategy Alignment

| Question | Response |
| --- | --- |
| Which organisational strategy or initiative does this solution support? | TBD |
| Has this solution been reviewed against the organisation’s capability model? | TBD |
| Does this solution duplicate any existing capability? | TBD |

#### Reuse of Shared Services & Platforms

| Capability | Shared Service / Platform | Reused? | Justification (if not reused) |
| --- | --- | --- | --- |
| TBD | TBD | Yes / No | TBD |

### 1.4 Scope

#### In Scope

- TBD

#### Out of Scope

- TBD

#### Related External Dependencies

- TBD

### 1.5 Current State / As-Is Architecture

{{AS_IS_ARCHITECTURE}}

What is being retained: TBD  
What is being replaced: TBD  
What is being decommissioned: TBD  

### 1.6 Key Decisions & Constraints

| Decision / Constraint | Rationale | Impact |
| --- | --- | --- |
| TBD | TBD | TBD |

### 1.7 Project Details

| Field | Value |
| --- | --- |
| Project Name | {{PROJECT_NAME}} |
| Project Code / ID | {{PROJECT_ID}} |
| Project Manager | TBD |
| Senior Responsible Officer (SRO) | TBD |
| Estimated Solution Cost (Capex) | TBD |
| Estimated Solution Cost (Opex) | TBD |
| Target Go-Live Date | TBD |

### 1.8 Business Criticality

| Field | Value |
| --- | --- |
| Criticality tier | TBD <!-- e.g. Tier 1 Critical / Business Important / Standard --> |
| RTO | TBD |
| RPO | TBD |
| Impact of prolonged outage | TBD |

---

## 2. Stakeholders & Concerns

### 2.1 Stakeholder Register

| Stakeholder / Group | Role | Interest / Concern | Influence |
| --- | --- | --- | --- |
| TBD | TBD | TBD | High / Medium / Low |

### 2.2 Concerns Matrix

| Concern | Stakeholder(s) | Addressed in section(s) | Status |
| --- | --- | --- | --- |
| TBD | TBD | TBD | Open / Addressed |

### 2.3 Compliance & Regulatory Context

#### Regulatory Requirements

| Regulation / Obligation | Applicability | Evidence / Control owner |
| --- | --- | --- |
| TBD | TBD | TBD |

#### Regulated Activities

- TBD

#### Compliance Standards

| Standard / Framework | Version | How applied |
| --- | --- | --- |
| TBD | TBD | TBD |

---

## 3. Architecture Views

### 3.1 Logical View

#### 3.1.1 Application Architecture Diagram

```text
[Place logical / application architecture diagram here — mermaid or linked image]
```

#### 3.1.2 Component Decomposition

| Component | Responsibility | Technology | Owner |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### 3.1.3 Service & Capability Mapping

| Business capability | Application service / component | Notes |
| --- | --- | --- |
| TBD | TBD | TBD |

#### 3.1.4 Application Impact

| Impacted system | Impact type | Description |
| --- | --- | --- |
| TBD | New / Modified / Retired / Consumed | TBD |

#### 3.1.5 Key Design Patterns

| Pattern | Where applied | Rationale |
| --- | --- | --- |
| TBD | TBD | TBD |

#### 3.1.6 Technology & Vendor Lock-in Assessment

| Technology / Vendor | Lock-in risk | Mitigation |
| --- | --- | --- |
| TBD | High / Medium / Low | TBD |

#### 3.1.7 Sustainability Considerations

{{LOGICAL_SUSTAINABILITY}}

### 3.2 Integration & Data Flow View

#### 3.2.1 Data Flow Diagrams

```text
[Place data-flow diagram(s) here]
```

#### 3.2.2 Internal Component Connectivity

| From | To | Protocol / pattern | Data classification | Sync / Async |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

#### 3.2.3 External Integration Architecture

| External system | Direction | Interface | AuthN/Z | Owner |
| --- | --- | --- | --- | --- |
| TBD | In / Out / Bi | TBD | TBD | TBD |

##### End User Access

| Channel | Users | Entry point | Notes |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### 3.2.4 API & Interface Contracts

| Interface | Style | Versioning | Consumer(s) | Contract location |
| --- | --- | --- | --- | --- |
| TBD | REST / Events / … | TBD | TBD | TBD |

### 3.3 Physical View

#### 3.3.1 Deployment Architecture Diagram

```text
[Place deployment / infrastructure diagram here]
```

#### 3.3.2 Hosting & Infrastructure

##### Hosting Venues

| Venue / region | Role | Provider |
| --- | --- | --- |
| TBD | Primary / DR / Edge | TBD |

##### Compute

| Workload | Platform | Sizing notes |
| --- | --- | --- |
| TBD | TBD | TBD |

##### Security Agents

| Agent / control | Scope | Purpose |
| --- | --- | --- |
| TBD | TBD | TBD |

#### 3.3.3 Network Topology & Connectivity

##### Connectivity Summary

{{NETWORK_SUMMARY}}

##### User & Administrator Access

| Persona | Path | Controls |
| --- | --- | --- |
| End user | TBD | TBD |
| Administrator | TBD | TBD |

##### Transport Protocols

| Path | Protocol | Encryption |
| --- | --- | --- |
| TBD | TBD | TBD |

##### Network Bandwidth

| Link / path | Expected load | Notes |
| --- | --- | --- |
| TBD | TBD | TBD |

##### Internet Perimeter Protection

{{PERIMETER_PROTECTION}}

#### 3.3.4 Environments

| Environment | Purpose | Data profile | Promotion path |
| --- | --- | --- | --- |
| Dev | TBD | Non-prod | TBD |
| Test / UAT | TBD | TBD | TBD |
| Prod | TBD | Production | TBD |

##### Connectivity Between Environments

{{ENV_CONNECTIVITY}}

#### 3.3.5 End User Compute & IoT

##### End User Compute

| Device / platform | Supported? | Notes |
| --- | --- | --- |
| TBD | Yes / No | TBD |

##### IoT Devices

| Device class | In scope? | Notes |
| --- | --- | --- |
| TBD | Yes / No / N/A | TBD |

#### 3.3.6 Sustainability Considerations

{{PHYSICAL_SUSTAINABILITY}}

### 3.4 Data View

#### 3.4.1 Data Architecture & Storage

##### Data Footprint

| Dataset | Source of truth | Volume / growth | Retention |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

##### Storage Systems

| Store | Technology | What is stored | Encryption |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### 3.4.2 Data Classification

| Data category | Classification | Examples | Handling notes |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### 3.4.3 Data Lifecycle

| Stage | Process | Owner | Notes |
| --- | --- | --- | --- |
| Create | TBD | TBD | TBD |
| Store | TBD | TBD | TBD |
| Use / Share | TBD | TBD | TBD |
| Archive | TBD | TBD | TBD |
| Destroy | TBD | TBD | TBD |

#### 3.4.4 Data Privacy & Protection

##### Privacy Assessments

| Assessment | Status | Reference |
| --- | --- | --- |
| DPIA / equivalent | TBD | TBD |

##### Use of Production Data for Testing

{{PROD_DATA_IN_TEST}}

##### Data Integrity

{{DATA_INTEGRITY}}

##### Data on End User Devices

{{DATA_ON_DEVICES}}

#### 3.4.5 Data Transfers & Sovereignty

##### Data Transfers to Third Parties

| Recipient | Data | Legal basis / controls | Location |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

##### Data Sovereignty

{{DATA_SOVEREIGNTY}}

#### 3.4.6 Sustainability Considerations

{{DATA_SUSTAINABILITY}}

### 3.5 Security View

#### 3.5.1 Security Overview & Threat Model

##### Security Context

{{SECURITY_CONTEXT}}

##### Business Impact Assessment

| Impact dimension | Rating | Notes |
| --- | --- | --- |
| Confidentiality | TBD | TBD |
| Integrity | TBD | TBD |
| Availability | TBD | TBD |

##### Threat Model

| Threat | Impact | Likelihood | Mitigations |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### 3.5.2 Identity & Access Management

##### Authentication Model – External / Customers

{{AUTHN_EXTERNAL}}

##### Authentication Model – Internal Users

{{AUTHN_INTERNAL}}

##### Authentication Details

| Flow | IdP | Factors | Notes |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

##### Session Management

{{SESSION_MANAGEMENT}}

##### Authorisation Model

{{AUTHZ_MODEL}}

##### Authorisation Details

| Role / persona | Permissions summary | Source of truth |
| --- | --- | --- |
| TBD | TBD | TBD |

##### Privileged Access

{{PRIVILEGED_ACCESS}}

#### 3.5.3 Network Security & Perimeter Protection

{{NETWORK_SECURITY}}

#### 3.5.4 Data Protection

##### Encryption at Rest

| Store / volume | Algorithm / KMS | Notes |
| --- | --- | --- |
| TBD | TBD | TBD |

##### Secret & Password Protection

{{SECRETS_PROTECTION}}

#### 3.5.5 Security Monitoring & Threat Detection

| Control | Tool | Coverage |
| --- | --- | --- |
| SIEM / detections | TBD | TBD |
| Runtime / app security | TBD | TBD |

### 3.6 Scenarios

#### 3.6.1 Key Use Cases

| ID | Use case | Actors | Architecture touchpoints |
| --- | --- | --- | --- |
| UC-01 | TBD | TBD | TBD |

#### 3.6.2 Architecture Decision Records (ADRs)

| ADR ID | Title | Status | Summary | Link |
| --- | --- | --- | --- | --- |
| ADR-001 | TBD | Proposed / Accepted / Superseded | TBD | TBD |

---

## 4. Quality Attributes

### 4.1 Operational Excellence

#### 4.1.1 Observability – Logging

##### Log Architecture

| Log source | Destination | Retention | PII handling |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### 4.1.2 Observability – Monitoring & Alerting

##### Operational Alerts

| Alert | Condition | Severity | Route |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

##### Monitoring Tools

| Concern | Tool |
| --- | --- |
| APM / metrics | TBD |
| Synthetic / uptime | TBD |

#### 4.1.3 Capacity Monitoring

{{CAPACITY_MONITORING}}

#### 4.1.4 Operational Procedures

| Procedure | Runbook / owner | Notes |
| --- | --- | --- |
| Incident response | TBD | TBD |
| Change / release | TBD | TBD |

### 4.2 Reliability & Resilience

#### 4.2.1 Geographic Footprint & Disaster Recovery

| Site / region | Role | Failover model |
| --- | --- | --- |
| TBD | Primary / DR | TBD |

#### 4.2.2 Scalability

{{SCALABILITY}}

#### 4.2.3 Fault Tolerance

{{FAULT_TOLERANCE}}

#### 4.2.4 Failure Modes & Recovery Behaviour

| Failure mode | Detection | Recovery | User impact |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### 4.2.5 Backup & Recovery

##### Backup Design

| Dataset | Method | Frequency | Retention | Test cadence |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

#### 4.2.6 Recovery Scenarios

| Scenario | Steps summary | RTO/RPO met? |
| --- | --- | --- |
| TBD | TBD | TBD |

### 4.3 Performance Efficiency

#### 4.3.1 Performance Requirements

##### Key Performance Indicators

| KPI | Target | Measurement |
| --- | --- | --- |
| TBD | TBD | TBD |

##### Performance Testing

{{PERF_TESTING}}

##### Capacity & Growth Projections

{{CAPACITY_GROWTH}}

#### 4.3.2 Resource Optimisation

{{RESOURCE_OPTIMISATION}}

#### 4.3.3 Network Performance

{{NETWORK_PERFORMANCE}}

### 4.4 Cost Optimisation

#### 4.4.1 Cost Influence & Analysis

##### Design Cost Decisions

| Decision | Cost influence | Alternatives considered |
| --- | --- | --- |
| TBD | TBD | TBD |

##### Cost Analysis

{{COST_ANALYSIS}}

##### Monthly Cost Breakdown (Production)

| Cost category | Estimate | Notes |
| --- | --- | --- |
| Compute | TBD | TBD |
| Data / storage | TBD | TBD |
| Networking | TBD | TBD |
| Licences / SaaS | TBD | TBD |
| Support / ops | TBD | TBD |
| **Total** | TBD | TBD |

#### 4.4.2 Cost Implications

{{COST_IMPLICATIONS}}

#### 4.4.3 FinOps Practices

{{FINOPS}}

### 4.5 Sustainability

#### 4.5.1 Hosting Efficiency

##### Hosting Location

{{HOSTING_LOCATION_SUSTAINABILITY}}

##### On-Demand Availability

{{ON_DEMAND_AVAILABILITY}}

##### Resource Efficiency

{{RESOURCE_EFFICIENCY}}

#### 4.5.2 Code Efficiency

{{CODE_EFFICIENCY}}

#### 4.5.3 Data Efficiency

{{DATA_EFFICIENCY}}

---

## 5. Lifecycle Management

### 5.1 Software Development & CI/CD

{{CICD_OVERVIEW}}

#### Application Security in Development

| Control | Tool / practice | Stage |
| --- | --- | --- |
| SAST / dependency scan | TBD | TBD |
| Secret scanning | TBD | TBD |
| IaC / image scan | TBD | TBD |

### 5.2 Service Transition & Migration

#### Migration Classification (6 R’s)

| Workload / component | 6R choice | Notes |
| --- | --- | --- |
| TBD | Rehost / Replatform / Refactor / Repurchase / Retire / Retain | TBD |

#### Transition Plan

{{TRANSITION_PLAN}}

### 5.3 Test & Release

#### Release Management

| Cadence | Environments | Approval gates |
| --- | --- | --- |
| TBD | TBD | TBD |

### 5.4 Operations

{{OPERATIONS_MODEL}}

#### Sustainability in Operation

{{OPS_SUSTAINABILITY}}

### 5.5 Resourcing & Skills

#### Team Capability Assessment

| Skill area | Current | Gap | Plan |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### Operational Readiness

{{OPERATIONAL_READINESS}}

#### Service Start

{{SERVICE_START}}

#### Maintainability

{{MAINTAINABILITY}}

### 5.6 Decommissioning & Exit

#### Exit Planning

{{EXIT_PLANNING}}

---

## 6. Decision Making & Governance

### 6.1 CRAIDS Log

#### Constraints

| ID | Constraint | Source | Impact |
| --- | --- | --- | --- |
| C-01 | TBD | TBD | TBD |

#### Assumptions

| ID | Assumption | Validation plan | Status |
| --- | --- | --- | --- |
| A-01 | TBD | TBD | Open / Validated |

#### Risks

##### Risk Identification

| ID | Risk | Likelihood | Impact | Score |
| --- | --- | --- | --- | --- |
| R-01 | TBD | TBD | TBD | TBD |

##### Risk Response

| ID | Response | Owner | Status |
| --- | --- | --- | --- |
| R-01 | Mitigate / Accept / Transfer / Avoid | TBD | TBD |

#### Dependencies

| ID | Dependency | Type | Owner | Status |
| --- | --- | --- | --- | --- |
| D-01 | TBD | Internal / External | TBD | TBD |

#### Issues

| ID | Issue | Owner | Status | Resolution |
| --- | --- | --- | --- | --- |
| I-01 | TBD | TBD | Open / Closed | TBD |

### 6.3 Guardrail Exceptions

#### Policy Exceptions

| Policy | Exception requested | Compensating control | Approver |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

#### Process Exceptions

| Process | Exception | Justification |
| --- | --- | --- |
| TBD | TBD | TBD |

#### Risk Profile Impact

{{GUARDRAIL_RISK_IMPACT}}

### 6.4 Architectural Decisions Log

| ADR ID | Title | Status | Date | Link |
| --- | --- | --- | --- | --- |
| ADR-001 | TBD | TBD | TBD | TBD |

### 6.5 Compliance Traceability

| Requirement / control | SAD section | Evidence |
| --- | --- | --- |
| TBD | TBD | TBD |

---

## 7. Appendices

### 7.1 Glossary

| Term | Definition |
| --- | --- |
| TBD | TBD |

### 7.2 Reference Documents

| Document | Version / date | Location |
| --- | --- | --- |
| TBD | TBD | TBD |

### 7.3 Standards & Patterns Referenced

| Standard / pattern | How used |
| --- | --- |
| ADS v1 | Document structure |
| TBD | TBD |

### 7.4 Approval Sign-Off

| Role | Name | Date | Signature / status |
| --- | --- | --- | --- |
| Solution Architect | TBD | TBD | TBD |
| Design Authority / ARB | TBD | TBD | TBD |
| Security | TBD | TBD | TBD |
| SRO | TBD | TBD | TBD |

---

## Compliance Scoring

> Optional ADS governance aid. Score each major section 0–5; leave blank until review.

#### Assessment Summary

| Section | Score (0–5) | Notes |
| --- | --- | --- |
| 0 Document Control | | |
| 1 Executive Summary | | |
| 2 Stakeholders & Concerns | | |
| 3 Architecture Views | | |
| 4 Quality Attributes | | |
| 5 Lifecycle Management | | |
| 6 Decision Making & Governance | | |
| 7 Appendices | | |
| **Overall** | | |
