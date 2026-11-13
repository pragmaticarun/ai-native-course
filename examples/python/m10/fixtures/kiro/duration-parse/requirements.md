# Requirements Document

## Introduction

Accept durations like `1h30m` in the clip-trim CLI instead of raw seconds.

## Requirements

### Requirement 1

**User Story:** As an editor, I want to type hours, minutes and seconds, so that I don't convert to seconds by hand.

#### Acceptance Criteria

1. WHEN the input is `1h30m` THE SYSTEM SHALL return `5400`
2. WHEN the input is `45s` THE SYSTEM SHALL return `45`
3. WHEN the input is `2h` THE SYSTEM SHALL return `7200`
4. WHEN the input is `1h0m5s` THE SYSTEM SHALL return `3605`

### Requirement 2

**User Story:** As an editor, I want typos rejected, so that a render isn't wasted on the wrong trim.

#### Acceptance Criteria

1. WHEN the input is `90x` THE SYSTEM SHALL return `error`
2. WHEN the input is `` THE SYSTEM SHALL return `error`
3. WHEN the input is `1m1h` THE SYSTEM SHALL return `error`
