# Feature Specification: Human-readable bitrates

**Feature Branch**: `004-bitrate-units`

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type bitrates with units (Priority: P1)

An editor types `--bitrate 2.5M`.

**Acceptance Scenarios**:

1. **Given** the input `2.5M`, **When** it is parsed, **Then** the result is `2500000`

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept units [NEEDS CLARIFICATION: which units? binary or decimal?]
- **FR-002**: System MUST handle bad input gracefully.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parsing is fast.

## Assumptions

- Users know what a bitrate is.
