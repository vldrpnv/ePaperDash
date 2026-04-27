# ADR-007 — Locale-based internationalization for dashboard text

## Status

Accepted

## Context

The ePaperDash system renders a dashboard that includes several user-visible
text strings: calendar day and month names, weather condition labels, a
"Tomorrow" section header, train departure status labels, and a "Last update"
timestamp line.  All of these were previously hard-coded in English.

The dashboard is deployed in Germany and the operator requested German text by
default while keeping English available and the system open to other locales.

## Decision

A lightweight, explicit i18n mechanism is introduced in the desktop dashboard
service (the only component that renders text).  Firmware, MQTT payload format,
and the bitmap contract are unchanged.

The mechanism is described fully in the service-level record:
`services/desktop_dashboard_service/architecture/adr-0007-i18n-locale-translations.md`.

### Repository-level impact summary

- The desktop service introduces a `Translations` value object in `domain/i18n.py`
  and a built-in locale registry in `adapters/i18n.py`.
- Locale is selected via `service.locale` in the operator TOML config (default
  `"de"` for German; `"en"` for English).
- No changes to the firmware, MQTT topic, payload format, or the 800 × 480 1-bit
  bitmap contract.
- No new external dependencies are introduced; the feature uses only the Python
  standard library and existing service infrastructure.

## Consequences

- German is the default language for all user-visible dashboard text.
- English is available by setting `service.locale = "en"`.
- New locales are added solely in `adapters/i18n.py`; no firmware changes are
  needed.
- The service specification and service-level ADR are updated in the same change.
