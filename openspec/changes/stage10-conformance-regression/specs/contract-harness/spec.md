# contract-harness Specification

## MODIFIED Requirements

### Requirement: Bounded-context conformance and regression verification

The system SHALL provide an automated, local operational mechanism to verify conformance and regression across both Legal Knowledge and Judicial Process bounded-context flows, proving that the canonical Legal bundle remains strictly isolated and that all Stage 1–9 contracts and invariants are satisfied.

#### Scenario: End-to-end pipeline flows run conformantly

- **WHEN** the conformance runner executes both the Legal Knowledge and Judicial Process pipeline flows end-to-end using controlled, deterministic synthetic fixtures
- **THEN** all individual stages (Ingress, Preflight, SHA validation, Preservation, Conversion, Critical-data validation, Quality Gate, Domain Routing, Semantic Review, and Producer publication) execute successfully
- **AND** all shared and domain-specific contract schemas are satisfied
- **AND** the Judicial Process conformance flow ends strictly at the authorized Judicial Process producer and canonical process-storage boundary, never implying or invoking Judicial Process Retrieval (which remains out of scope)

#### Scenario: Bounded-context storage is strictly isolated

- **WHEN** the Judicial Process pipeline flow runs end-to-end and publishes process candidates
- **THEN** all resulting process artifacts are written exclusively to isolated process storage
- **AND** the canonical Legal bundle remains completely untouched (zero writes under the Legal bundle root)

#### Scenario: Legal Knowledge Retrieval remains Zero-Write and isolated

- **WHEN** the retrieval sync, rebuild, and search paths are executed
- **THEN** they operate strictly in read-only mode over the canonical Legal bundle (Zero-Write)
- **AND** they never access, index, or reference Judicial Process storage, symbols, or retrieval mechanisms

#### Scenario: Real-corpus regression tests are executed successfully

- **WHEN** the regression test runner executes the test suite over frozen real-corpus PDF fixtures (such as `AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, and `L10.406_CC_2002.pdf`)
- **THEN** all assertions on reading order preservation, repetitive header/footer removal, signature blocks, and legal citations pass against lightweight git-tracked goldens in `tests/test_conformance/golden/`
- **AND** the default acceptance gate runs offline and deterministically, never depending on live nondeterministic external OCR/LLM output
- **AND** no existing functional capabilities are broken

#### Scenario: Source-inspection validates domain-schema independence

- **WHEN** static source-inspection checks are executed over the codebase
- **THEN** no prohibited coupling or import of domain-specific schemas is found in the common contract layer
- **AND** the core conversion package remains completely independent of domain-specific producers

#### Scenario: Conformance CLI command executes successfully

- **WHEN** the operator invokes the local CLI command `repo-jur test conformance`
- **THEN** the runner invokes pytest through the active Python interpreter using `sys.executable -m pytest` with two explicit bounded executions over `tests/test_conformance/` (one for conformance, one for regression)
- **AND** a structured non-canonical derived report is produced at `var/conformance/report.json` (or overridden location) distinguishing `CONFORMANCE_FAILURE`, `REGRESSION_FAILURE`, and `ENVIRONMENT_CONFIGURATION_ERROR`
- **AND** returns exit code 0 on success, or a deterministic non-zero exit code on failure
