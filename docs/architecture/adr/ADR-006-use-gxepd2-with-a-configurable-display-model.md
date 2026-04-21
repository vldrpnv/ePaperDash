# ADR-006: Use GxEPD2 with a configurable display model

- Status: Accepted
- Date: 2026-04-21

## Context

Driving the 7.5 inch ePaper panel directly would require low-level timing and driver knowledge. The code also needs a practical fallback for closely related display variants.

## Decision

The firmware uses the GxEPD2 abstraction and defaults to `GxEPD2_750_T7`, while keeping an alternate `GxEPD2_750_M07` configuration in the source as a documented fallback.

## Consequences

- Rendering logic stays focused on application behavior rather than controller details.
- Display compatibility is managed at compile time.
- Changing the panel model remains a source-level configuration decision.

## Evidence

- `ePaperDash.ino` defines the display object with the default model and comments the fallback option.
- `README.md` lists GxEPD2 as a required dependency.
