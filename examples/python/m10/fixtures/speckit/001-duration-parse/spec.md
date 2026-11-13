# Feature Specification: Parse human-readable durations

**Feature Branch**: `001-duration-parse`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Accept durations like 1h30m in the clip-trim CLI instead of raw seconds"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trim with hours, minutes and seconds (Priority: P1)

An editor types `--start 1h30m` instead of working out 5400 seconds.

**Why this priority**: Every trim command takes a duration; it's the whole feature.

**Independent Test**: Call the parser with the examples below and compare the number of seconds.

**Acceptance Scenarios**:

1. **Given** the input `1h30m`, **When** it is parsed, **Then** the result is `5400`
2. **Given** the input `45s`, **When** it is parsed, **Then** the result is `45`
3. **Given** the input `2h`, **When** it is parsed, **Then** the result is `7200`
4. **Given** the input `1h0m5s`, **When** it is parsed, **Then** the result is `3605`

---

### User Story 2 - Clear errors for bad input (Priority: P2)

A typo should fail loudly instead of trimming at the wrong place.

**Why this priority**: A silent wrong trim wastes a render.

**Independent Test**: Call the parser with malformed input and check that it is rejected.

**Acceptance Scenarios**:

1. **Given** the input `90x`, **When** it is parsed, **Then** the result is `error`
2. **Given** the input ``, **When** it is parsed, **Then** the result is `error`
3. **Given** the input `1m1h`, **When** it is parsed, **Then** the result is `error`

---

### Edge Cases

- Units out of order (`1m1h`) are rejected rather than reordered.
- A bare number without a unit is rejected (ambiguous: seconds or frames?).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept the units `h`, `m` and `s`, each at most once, in that order.
- **FR-002**: System MUST return the total as a whole number of seconds.
- **FR-003**: System MUST reject empty input, unknown units and out-of-order units with an error that names the input.

### Key Entities

- **Duration**: a whole number of seconds, zero or more.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every acceptance scenario above passes as an automated test.
- **SC-002**: Parsing 10,000 inputs takes under 100 ms on a CI runner.

## Assumptions

- Out of scope: fractional values (`1.5h`), days, and frame counts.
- The CLI keeps accepting raw seconds through a separate `--start-seconds` flag.
