"""Trello source plugin.

Fetches open cards from a configured Trello board, optionally filtered to a
subset of lists/columns by name.

Configuration keys
------------------
``api_key`` (required)
    Trello API key.  Obtain from https://trello.com/power-ups/admin.
    Use a ``${trello_api_key}`` placeholder and supply the value via secrets.toml.

``token`` (required)
    Trello API token with *read-only* scope.
    Use a ``${trello_token}`` placeholder and supply the value via secrets.toml.

``board_id`` (required)
    The 24-character board ID or the short name from the board URL.

``list_names`` (optional)
    List of column names to include (case-insensitive substring match).
    When omitted, cards from all open lists are returned.

``max_cards`` (optional, default 20)
    Maximum number of cards to return across all included lists.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import TrelloCard, TrelloCards
from epaper_dashboard_service.domain.ports import SourcePlugin

_LOGGER = logging.getLogger(__name__)
_BASE_URL = "https://api.trello.com/1"
_FETCH_TIMEOUT_SECONDS = 10
_DEFAULT_MAX_CARDS = 20


class TrelloSourcePlugin(SourcePlugin):
    name = "trello_cards"

    def fetch(self, config: dict[str, Any]) -> TrelloCards:
        api_key = str(config.get("api_key", "")).strip()
        token = str(config.get("token", "")).strip()
        board_id = str(config.get("board_id", "")).strip()

        if not api_key:
            raise ValueError("trello_cards source requires config value: api_key")
        if not token:
            raise ValueError("trello_cards source requires config value: token")
        if not board_id:
            raise ValueError("trello_cards source requires config value: board_id")

        max_cards = int(config.get("max_cards", _DEFAULT_MAX_CARDS))
        list_name_filters = tuple(
            name.strip().lower() for name in config.get("list_names", [])
        )
        base_url = str(config.get("base_url", _BASE_URL)).rstrip("/")
        auth = {"key": api_key, "token": token}

        try:
            board_data = _fetch_json(f"{base_url}/boards/{board_id}", {**auth, "fields": "name"})
            board_name = str(board_data.get("name", board_id))

            lists_data = _fetch_json(
                f"{base_url}/boards/{board_id}/lists",
                {**auth, "fields": "id,name", "filter": "open"},
            )
            list_id_to_name: dict[str, str] = {item["id"]: item["name"] for item in lists_data}

            if list_name_filters:
                included_ids = {
                    list_id
                    for list_id, list_name in list_id_to_name.items()
                    if list_name.strip().lower() in list_name_filters
                }
            else:
                included_ids = set(list_id_to_name)

            cards_data = _fetch_json(
                f"{base_url}/boards/{board_id}/cards",
                {**auth, "filter": "open", "fields": "name,idList"},
            )
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise SourceUnavailableError("trello_cards source unavailable") from error

        cards = tuple(
            TrelloCard(name=card["name"], list_name=list_id_to_name[card["idList"]])
            for card in cards_data
            if card.get("idList") in included_ids
        )[:max_cards]

        _LOGGER.info("Trello board=%r cards=%d", board_name, len(cards))
        return TrelloCards(board_name=board_name, cards=cards)


def _fetch_json(url: str, params: dict[str, str]) -> Any:
    full_url = f"{url}?{urlencode(params)}"
    req = Request(full_url, headers={"Accept": "application/json", "User-Agent": "ePaperDash/1.0"})
    try:
        with urlopen(req, timeout=_FETCH_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except HTTPError as error:
        _LOGGER.error("Trello HTTPError url=%s status=%s", url, error.code)
        raise
    except URLError as error:
        _LOGGER.error("Trello URLError url=%s reason=%s", url, error.reason)
        raise
