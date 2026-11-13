# Feature Specification: Duration display

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See clip length (Priority: P1)

An editor sees how long a clip is in the clip list.

**Acceptance Scenarios**:

1. **Given** a clip of `3723` seconds, **When** the list renders, **Then** it shows `1:02:03`
2. **Given** a clip of `59` seconds, **When** the list renders, **Then** it shows `0:00:59`

## Requirements *(mandatory)*

- **FR-001**: Hours are not zero-padded; minutes and seconds are always two digits.
- **FR-002**: Durations typed as `1h2m3s` are parsed to seconds; anything else is rejected.

## Success Criteria *(mandatory)*

- **SC-001**: Both scenarios above pass as tests in `py/tests/test_durations.py`.

## Assumptions

- Out of scope: durations over 99 hours and fractional seconds.
