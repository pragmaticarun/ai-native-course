---
description: "Task list for parsing human-readable durations"
---

# Tasks: Parse human-readable durations

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Create the module skeleton in src/duration.py

## Phase 3: User Story 1 - Trim with hours, minutes and seconds (Priority: P1)

### Tests for User Story 1

- [x] T002 [P] [US1] Acceptance tests from spec.md scenarios in tests/test_duration.py
- [x] T003 [P] [US1] Property test: parse(format(n)) == n in tests/test_roundtrip.py

### Implementation for User Story 1

- [x] T004 [US1] Implement the h/m/s parser in src/duration.py (depends on T002)

## Phase 4: User Story 2 - Clear errors for bad input (Priority: P2)

### Tests for User Story 2

- [ ] T005 [US2] Error-case tests in tests/test_duration.py (depends on T002)

### Implementation for User Story 2

- [ ] T006 [US2] Reject empty, unknown and out-of-order units in src/duration.py (depends on T004, T005)
- [ ] T007 [P] [US2] Wire the parser into the trim CLI in src/cli.py (depends on T006)
