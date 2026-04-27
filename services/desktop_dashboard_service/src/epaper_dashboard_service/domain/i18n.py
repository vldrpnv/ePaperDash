from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Translations:
    """All user-visible strings rendered onto the dashboard.

    Defaults are the English strings that were hard-coded before i18n was
    introduced.  Each field may be overridden by a locale-specific instance.

    ``condition_labels`` maps English condition labels produced by the weather
    sources (e.g. ``"Sunny"``, ``"Partly cloudy"``) to their localized
    equivalents.  Any label not found in the mapping is passed through
    unchanged, so a partial mapping is safe.

    ``day_names`` provides localized weekday names ordered Monday=0 … Sunday=6.
    When the tuple is non-empty it replaces Python's locale-dependent
    ``strftime("%A")`` output for the calendar day-of-week field.

    ``month_names`` provides localized month names ordered January=0 … December=11.
    When the tuple is non-empty it replaces Python's locale-dependent
    ``strftime("%B")`` output for the calendar month field.
    """

    cancelled: str = "Cancelled"
    tomorrow: str = "Tomorrow"
    tomorrow_short: str = "tmrw"
    last_update: str = "Last update"
    condition_labels: dict[str, str] = field(default_factory=dict)
    day_names: tuple[str, ...] = ()
    month_names: tuple[str, ...] = ()

    def condition(self, label: str) -> str:
        """Return the localized equivalent of *label*, falling back to *label* itself."""
        return self.condition_labels.get(label, label)


# Singleton English instance used as the default throughout the codebase.
ENGLISH = Translations()
