"""Built-in locale definitions for the dashboard service.

Adding a new locale
-------------------
1. Create a ``Translations`` instance with all translated strings.
2. Register it in the ``LOCALES`` dict under its IETF language tag (e.g. ``"fr"``).
3. The locale is selected via ``service.locale`` in the TOML configuration.
"""
from __future__ import annotations

from epaper_dashboard_service.domain.i18n import ENGLISH, Translations

GERMAN = Translations(
    cancelled="Entfällt",
    tomorrow="Morgen",
    tomorrow_short="mo",
    last_update="Letzte Aktualisierung",
    condition_labels={
        "Sunny": "Sonnig",
        "Mainly clear": "Überwiegend klar",
        "Partly cloudy": "Teilweise bewölkt",
        "Cloudy": "Bewölkt",
        "Foggy": "Neblig",
        "Fog": "Neblig",
        "Light drizzle": "Leichter Nieselregen",
        "Drizzle": "Nieselregen",
        "Dense drizzle": "Dichter Nieselregen",
        "Rainy": "Regnerisch",
        "Rain": "Regen",
        "Heavy rain": "Starkregen",
        "Light snow": "Leichter Schnee",
        "Snow": "Schnee",
        "Heavy snow": "Starker Schnee",
        "Rain showers": "Regenschauer",
        "Heavy showers": "Starke Schauer",
        "Thunderstorm": "Gewitter",
        "Unknown": "Unbekannt",
    },
    day_names=(
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag",
    ),
    month_names=(
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
)

#: All built-in locales keyed by IETF language tag.
LOCALES: dict[str, Translations] = {
    "en": ENGLISH,
    "de": GERMAN,
}


def get_translations(locale: str) -> Translations:
    """Return the ``Translations`` for *locale*.

    Falls back to English when *locale* is not recognised so the dashboard
    always renders rather than failing with a configuration error.
    """
    return LOCALES.get(locale, ENGLISH)
