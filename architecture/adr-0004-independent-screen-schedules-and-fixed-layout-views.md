# ADR-0004: Give each screen an independent schedule of fixed-layout views

## Status

Accepted target direction, 2026-11-06. Not implemented. Based on the [direction interview](direction-interview.md).

## Context

The current publisher has one layout, panel list, and MQTT destination. The required system supports screens in different places and scheduled views on each screen. Treating all screens as copies of one global profile would prevent independent weekday/weekend and time-of-day behavior.

## Decision

- A **screen** identifies a physical display and its configured output binding. Each screen has its own schedule.
- A **view** defines a layout and assignments of source-backed presentations to its blocks. Views can be reused by screen configurations; reusing one does not force schedules to be shared.
- A screen's schedule selects its active view using weekday/weekend and time-of-day rules. A scheduled change can select a different layout, data subset, and presentation.
- Within the active view, block geometry and assignments remain fixed. Source values, completion state, and availability can change rendered content within a block; they do not remove the block, reassign it, or reflow surrounding blocks.
- Acquisition and rendering stay off-device. Existing devices continue consuming complete retained bitmap images. Screen wake intervals do not define source freshness.
- Distinct simultaneously displayed outputs need distinct retained image topics. Connections must have non-conflicting MQTT client IDs. Topic naming and deployment topology remain implementation choices.

For example, both floor screens can read one all-room temperature source. Each normally selects its own floor. One screen can switch at a scheduled time to an all-room view with a different layout while the other keeps its own schedule.

Marking trash collection as done changes the content rendered in the existing waste block. It does not select a new layout or change panel assignments.

## Alternatives

- **One global profile schedule:** rejected because screens require independent schedules.
- **Data-driven block expansion/reflow:** excluded from this direction; the interview requires stable blocks within a view.
- **One process per screen:** remains a deployment option, but separate processes do not by themselves provide shared source acquisition/cache ownership.

## Consequences and boundaries

Configuration must distinguish screens, schedules, views, source references, and output bindings. This is a conceptual boundary, not a finalized TOML schema or a requirement for separate network services.

Keep the existing 800×480 bitmap contract for existing hardware. Whether other resolutions/formats are required remains open. MQTT publish completion does not establish physical display completion.

## Acceptance criteria for implementation

1. Two screens can select different views at the same instant.
2. Each screen can select different views by weekday/weekend and time of day.
3. A scheduled view can change both layout and the selected subset of shared data.
4. Data changes, unavailable data, and marking a collection done leave active-view block geometry and assignments unchanged.
5. Distinct outputs do not overwrite one another's retained image topics.

## Open decisions

Timezone ownership, daylight-saving transitions, overlapping rules, midnight behavior, and a missing-rule default must be specified before scheduler implementation. Dashboard composition/publish triggers and device wake timing are separate decisions still open.
