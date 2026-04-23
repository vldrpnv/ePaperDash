# Copilot instructions for ePaperDash

Before making changes, read:

1. `docs/architecture/README.md`
2. Relevant files in `docs/architecture/adr/`
3. Relevant files in `docs/architecture/design_decisions/`

## Required working style

- Capture the expected specification first.
  - Write or update acceptance criteria before changing behavior.
  - If the behavior is not yet clear, stop and clarify the contract instead of guessing.
- Prefer test-first development.
  - Add or update tests before implementation whenever the code can be tested.
  - If a change is hard to test because logic is embedded in hardware-facing code, first look for a small seam that can be extracted into testable logic.
  - If automated tests are still not practical, document the missing test seam and provide a concrete manual verification plan.
- Preserve architectural intent.
  - Keep the wake → connect → receive → compare → render → sleep lifecycle intact unless the change intentionally revises an ADR.
  - Treat battery use, bounded active time, and fail-safe recovery as primary constraints.
- Preserve the existing data contract.
  - The dashboard payload is a raw 800 × 480 1-bit bitmap unless the specification and decision records are updated together.
- Update the decision records when design intent changes.
  - Add or amend an ADR for architectural changes.
  - Add or amend a design decision record for implementation-level changes.

## Harness state

- `docs/architecture/README.md` is the canonical navigation index for architecture context.
- Use the summary tables in that file to decide which ADRs and design decisions must be loaded for the current task.
- There is currently no committed automated test or CI harness in this repository.
- Until a harness exists, changes should include explicit acceptance criteria first and either:
  - tests added first when a seam exists, or
  - a documented missing test seam plus a concrete manual verification plan.

## Intended agent workflow

1. Load `docs/architecture/README.md`.
2. Load only the ADRs and design-decision records whose scope matches the requested change.
3. Capture or refine the specification before editing behavior.
4. Prefer test-first changes; if not practical, document the missing seam and manual verification.
5. Keep changes small and update the relevant decision records whenever design intent changes.

## Repository-specific notes

- Favor small, explicit changes over broad abstraction.
- Keep configuration in `config.h` unless a documented decision changes that boundary.
