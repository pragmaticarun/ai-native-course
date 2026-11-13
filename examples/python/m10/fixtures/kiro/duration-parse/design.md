# Design Document

## Overview

A pure function `parse_duration(text) -> int` in `src/duration.py`, called by the trim CLI.

## Components and Interfaces

- `parse_duration(text: str) -> int` — raises `ValueError` naming the input on bad input.

## Error Handling

One regular expression, `^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$`, plus a check that at least one unit matched.

## Testing Strategy

Acceptance criteria from requirements.md become table-driven tests.
