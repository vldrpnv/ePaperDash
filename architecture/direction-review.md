# Project direction review

Review date: 2026-11-06 · Repository: `35e99ca` · Discussion proposal, not an accepted ADR.

Follow-up: [interview decisions and remaining questions](direction-interview.md) clarify the requirements below, particularly fixed layout blocks and source-owned cache freshness.

The later [architecture decision revision](decision-revision.md) is the current target direction. This review preserves the initial proposals; its runtime workflow is not a decision to add background polling. The bitmap polarity mismatch noted below has since been corrected in the specifications, without changing code.

The current design supports one dashboard per publisher process. Multiple dashboards would change data ownership, scheduling, configuration, preview, and delivery. The central question is **which decisions belong to a shared source, and which belong to each use of its data?**

## Decisions worth keeping—and questioning

| Direction | Assessment |
| --- | --- |
| Generate images off-device; keep firmware simple | Keep. This supports independent content development and sleeping devices. |
| Retained MQTT images | Keep provisionally. Separate dashboard output topics and unique publisher client IDs are needed; publishing successfully does not establish that a device displayed the image. |
| Source and renderer plugins | Keep the separation, but reconsider fetching inside every panel build. Reusing a plugin currently still causes a fetch for each panel. |
| SVG layout | Keep as a practical rendering backend. Revisit ownership: SVG supplies geometry, TOML supplies styling, and renderers also position images. Establish one layout authority and validate slot bindings. |
| Fixed 800×480 bitmap | Keep for existing hardware. If other displays are in scope, move encoding constraints into explicit device capabilities. Configurable layout dimensions currently still meet a fixed-size encoder. |
| One refresh interval; blank unavailable panels | Reconsider. Transport, weather, and waste schedules have different freshness needs. Missing data should have an explicit policy: marked stale data, unavailable state, or blank content. |

## A model for multiple dashboards

Separate these concepts before extending the configuration:

- **Source instance:** provider, account/location, credential reference, acquisition parameters, and refresh policy.
- **Data snapshot:** normalized data plus acquisition time, coverage, expiry, and error state.
- **Panel view:** source reference, selection/aggregation, renderer, and presentation settings.
- **Dashboard:** panels, layout, timezone, and composition schedule. A time-of-day profile is a variant within a dashboard.
- **Device binding:** which dashboard a device receives, its output topic, and display capabilities. Several devices may receive the same dashboard.

For example, a hallway dashboard could show today's calendar agenda while a desk dashboard shows three days with more detail. Both can use one calendar snapshot. Likewise, one weather forecast can feed a compact summary and an hourly chart.

Sharing requires sufficient data: a snapshot truncated to today's first five events cannot serve the three-day view. Calendar windows/limits and weather precision currently affect source output. Separate acquisition coverage from display filtering; share only compatible requests within the same credential and access scope. Cache identity must include account, location, query, and coverage—not just the plugin name.

## Workflows to rebuild

1. **Runtime:** refresh due sources → retain timestamped snapshots → build due dashboards from compatible snapshots → publish each output independently. Separate fetch, composition, publish, and device wake schedules. One dashboard failure should leave other outputs running.
2. **Editing:** edit a draft → validate references, plugin compatibility, slots, and device format → preview through the production rendering path → atomically activate a configuration revision → reload explicitly, with rollback. Currently preview refresh saves the file, uses dummy “Preview” text, and the publisher loads configuration only at startup.
3. **Verification:** use a fixed clock and recorded snapshots for reproducible previews. Check freshness separately from image changes: the generated `last_update` timestamp, clock, and random image can change pixels even when external data is unchanged.

## First redesign step

Confirm whether “multiple dashboards” means different content on identical panels, scheduled variants, or different hardware. Then implement one vertical trial: **two dashboards, one shared calendar acquisition, different views, separate MQTT outputs, and a faithful preview**. Verify fetch reuse, sufficient coverage, failure isolation, and explicit configuration activation.

Running one process per configuration is a useful simpler alternative when independent acquisition is acceptable. Prefer shared orchestration if avoiding duplicate requests and coordinating freshness are actual requirements; this does not yet require separate network services or a general workflow engine.

Resolve documentation drift alongside that trial: editor notes describe shared sources/profiles absent from the runtime model; the repository specification and encoder disagree on bitmap polarity. These are contracts to settle before extending them.

## Review basis

Static review of [runtime models](../services/desktop_dashboard_service/src/epaper_dashboard_service/domain/models.py), [build pipeline](../services/desktop_dashboard_service/src/epaper_dashboard_service/application/service.py), [publisher loop](../services/desktop_dashboard_service/src/epaper_dashboard_service/cli.py), [editor](../services/config_editor_app/src/config_editor_app/main.py), [preview](../services/config_editor_app/src/config_editor_app/preview_generator.py), and existing ADRs/specifications. No hardware or live-source validation performed.

Engineering basis: complex architecture review completed; FPF `4260875dd8bc` (A.7/A.11.OP), protocols v2.0 `434dffd98a51` from `ansea09/agent-skills-and-protocols` cache; chunk-first reading. Sandbox networking disabled; gate used current cached copies without a GitHub refresh.
