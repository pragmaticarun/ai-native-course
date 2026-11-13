# Feature Specification: Human-readable bitrates

**Feature Branch**: `004-bitrate-units`

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type bitrates with units (Priority: P1)

An editor types `--bitrate 2.5M` instead of counting zeros.

**Why this priority**: Every encode command takes a bitrate.

**Independent Test**: Run the examples below through the parser.

**Acceptance Scenarios**:

1. **Given** the input `800000`, **When** it is parsed, **Then** the result is `800000`
2. **Given** the input `128k`, **When** it is parsed, **Then** the result is `128000`
3. **Given** the input `2.5M`, **When** it is parsed, **Then** the result is `2500000`

---

### User Story 2 - Reject ambiguous or impossible input (Priority: P2)

A wrong bitrate should fail before a long encode starts.

**Why this priority**: A bad encode costs minutes of compute.

**Independent Test**: Run the examples below and check each is rejected.

**Acceptance Scenarios**:

1. **Given** the input `2m`, **When** it is parsed, **Then** the result is `error`
2. **Given** the input `-5k`, **When** it is parsed, **Then** the result is `error`
3. **Given** the input `1.0005k`, **When** it is parsed, **Then** the result is `error`
4. **Given** the input ``, **When** it is parsed, **Then** the result is `error`

### Edge Cases

- Lowercase `m` is rejected because it could mean milli or mega.
- A decimal that doesn't give whole bits per second is rejected, not rounded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a whole number of bits per second, or a number followed by `k` (×1,000) or `M` (×1,000,000).
- **FR-002**: System MUST reject lowercase `m`, negative numbers, empty input and results that are not whole numbers.
- **FR-003**: Error messages MUST quote the input.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every acceptance scenario passes as an automated test.
- **SC-002**: Parsing 10,000 inputs takes under 50 ms on a CI runner.

## Assumptions

- Out of scope: `G`, binary units (`Ki`, `Mi`) and bytes per second.
