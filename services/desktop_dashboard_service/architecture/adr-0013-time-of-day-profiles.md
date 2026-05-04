# ADR-0013: Time of Day Layout Profiles and DRY Sources

## Status

Accepted

## Context

The initial dashboard layout implementation defined a single `template.svg` layout and a flat `[[panels]]` array that hardcoded a 1:1 mapping between a data source, a visual renderer, and a layout slot. As the display requirements evolved, it became desirable to change the layout over the course of the day: showing different sets of panels (e.g. commuting info in the morning, tasks during the day, relaxation info in the evening) and applying different renderer settings (e.g. widening the clock validity window during low-activity periods).

Duplicating source configuration (like API URLs, coordinates, board IDs, timezone settings) across multiple time-bound profiles would create a maintenance burden and violate the DRY (Don't Repeat Yourself) principle.

## Decision

We will split the monolithic `[[panels]]` array into two separate concerns in the configuration:

1. **Shared Sources (`[[sources]]`)**: Define data sources once with a unique `id`. These blocks carry the connection, location, and authentication parameters needed to fetch data, but no presentation rules.
2. **Time-based Profiles (`[[profiles]]`)**: Define multiple daily phases. Each profile carries:
   - A `start_time` (e.g. "09:00").
   - A `template` (SVG layout specific to that phase).
   - An array of `[[profiles.panels]]` that map a `source_id` to a specific `renderer`, `slot`, and `renderer_config`.

The application service will resolve the active profile based on the current local time (falling back to the profile with the latest `start_time` before the current time, wrapping around midnight) and construct ephemeral `PanelDefinition` instances by joining the shared source configuration with the profile-specific renderer configuration.

To ensure backward compatibility, the configuration parser will still accept the legacy `[[panels]]` array if no profiles are defined.

## Consequences

- **Positive:** Layouts can now change dynamically throughout the day without restarting the service.
- **Positive:** Data source credentials and settings are defined exactly once.
- **Positive:** Renderer settings (like font sizes or clock validity windows) can be tuned per time-of-day.
- **Negative:** The TOML configuration file is longer and slightly more complex, utilizing references (`source_id`).
- **Negative:** Evaluating the active profile adds a small amount of logic to the dashboard rendering loop.