# ADR-0007 — Locale-based i18n with a `Translations` value object

## Status

Accepted

## Context

All user-visible text on the dashboard was previously hard-coded in English (e.g.
`"Cancelled"`, `"Tomorrow"`, `"tmrw"`, `"Last update"`).  Calendar day and
month names were produced by Python's `strftime("%A")` / `strftime("%B")`, which
returns English names on the C locale used in this environment.

The dashboard is deployed in Germany, and the operator requested German text by
default while keeping English available and the system open to other languages in
the future.

## Decision

A lightweight, explicit translation mechanism is introduced without bringing in a
third-party i18n library:

1. **`domain/i18n.py`** defines a `Translations` dataclass that carries every
   user-visible string as a typed field with English defaults.  A `condition(label)`
   helper performs condition-label lookups with a passthrough fallback.

2. **`adapters/i18n.py`** provides the two built-in locale instances (`ENGLISH`,
   `GERMAN`) and a `LOCALES` registry.  `get_translations(locale)` resolves a
   locale tag (e.g. `"de"`) to a `Translations` instance, falling back to English
   for unknown tags.  Adding a new locale only requires a new entry in `LOCALES`.

3. **`ServiceConfig.locale`** (default `"de"`) is the single configuration
   surface: set `service.locale = "en"` in the TOML file to switch to English.

4. **Constructor injection** wires translations into the components that render
   text — `TrainDepartureTextRenderer`, `WeatherBlockRenderer`,
   `CalendarSourcePlugin`, and `DashboardApplicationService` — following the
   same pattern already used for `WeatherIconProvider`.  All accepting components
   default to `ENGLISH` when no `Translations` is supplied, keeping unit tests
   that construct them in isolation green.

5. **`bootstrap.build_application`** now accepts an optional `ServiceConfig`
   parameter.  It calls `get_translations(service_config.locale)` and injects the
   result into every component that needs it.  The CLI passes
   `configuration.service` to `build_application`.

## Affected strings

| Component | English | German |
|---|---|---|
| `TrainDepartureTextRenderer` | `"Cancelled"` | `"Entfällt"` |
| `WeatherBlockRenderer` row 3 | `"Tomorrow: "` | `"Morgen: "` |
| `WeatherBlockRenderer` block label | `"tmrw "` | `"mo "` |
| `WeatherBlockRenderer` row 1 & 3 conditions | (as received) | translated via `condition_labels` mapping |
| `DashboardApplicationService` | `"Last update: "` | `"Letzte Aktualisierung: "` |
| `CalendarSourcePlugin` day names | strftime `%A` | `GERMAN.day_names[weekday]` |
| `CalendarSourcePlugin` month names | strftime `%B` | `GERMAN.month_names[month-1]` |

## Trade-offs

- **No runtime locale switching** — translations are resolved once at bootstrap
  and remain fixed for the service lifetime.  This keeps the implementation
  simple and consistent with the single-cycle render model.

- **English condition labels in the domain model** — `WeatherPeriod.condition_label`
  continues to store English strings from the weather sources.  Translation
  happens in the renderer, keeping the domain model language-neutral.

- **No translation file on disk** — strings live in code (`adapters/i18n.py`).
  This is appropriate for a small, bounded string set; an external resource file
  would add file-system coupling without benefit at this scale.

- **Calendar custom format strings bypass translation** — when
  `day_of_week_format` is set to a value other than `"%A"` (e.g. `"%a"`), the
  strftime path is used unchanged.  This preserves backward compatibility with
  custom format configurations.

## Consequences

- German text is shown by default for all new deployments (`locale = "de"`).
- English is available by setting `service.locale = "en"` in the TOML config.
- New locales are added solely by appending an entry to `adapters/i18n.LOCALES`.
- All existing unit tests that construct renderers or the application service
  without a `Translations` argument continue to pass because defaults are English.
