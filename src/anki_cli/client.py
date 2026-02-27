"""AnkiConnect v6 API client."""

from __future__ import annotations

from typing import Any

import httpx

ANKICONNECT_URL = "http://localhost:8765"
ANKICONNECT_VERSION = 6


class AnkiError(Exception):
    pass


class AnkiConnectionError(AnkiError):
    pass


class AnkiClient:
    def __init__(self, url: str = ANKICONNECT_URL) -> None:
        self._url = url

    def _invoke(self, action: str, **params: Any) -> Any:
        payload: dict[str, Any] = {"action": action, "version": ANKICONNECT_VERSION}
        if params:
            payload["params"] = params
        try:
            resp = httpx.post(self._url, json=payload, timeout=10)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise AnkiConnectionError("Cannot reach AnkiConnect – is Anki running?") from exc
        except httpx.HTTPError as exc:
            raise AnkiConnectionError(str(exc)) from exc
        body = resp.json()
        if body.get("error"):
            raise AnkiError(body["error"])
        return body.get("result")

    def deck_names(self) -> list[str]:
        return self._invoke("deckNames")

    def deck_stats(self) -> dict[str, dict[str, int]]:
        raw: dict[str, dict] = self._invoke("getDeckStats", decks=self.deck_names())
        return {v["name"]: v for v in raw.values()}

    def model_names(self) -> list[str]:
        return self._invoke("modelNames")

    def model_field_names(self, model: str) -> list[str]:
        return self._invoke("modelFieldNames", modelName=model)

    def find_notes(self, query: str) -> list[int]:
        return self._invoke("findNotes", query=query)

    def notes_info(self, ids: list[int]) -> list[dict[str, Any]]:
        return self._invoke("notesInfo", notes=ids)

    def add_note(
        self,
        deck: str,
        model: str,
        fields: dict[str, str],
        tags: list[str] | None = None,
    ) -> int:
        note: dict[str, Any] = {
            "deckName": deck,
            "modelName": model,
            "fields": fields,
        }
        if tags:
            note["tags"] = tags
        return self._invoke("addNote", note=note)

    def update_note_fields(self, note_id: int, fields: dict[str, str]) -> None:
        self._invoke("updateNoteFields", note={"id": note_id, "fields": fields})

    def delete_notes(self, ids: list[int]) -> None:
        self._invoke("deleteNotes", notes=ids)

    def add_tags(self, ids: list[int], tags: str) -> None:
        self._invoke("addTags", notes=ids, tags=tags)

    def remove_tags(self, ids: list[int], tags: str) -> None:
        self._invoke("removeTags", notes=ids, tags=tags)

    def cards_reviewed_today(self) -> int:
        return len(self._invoke("findCards", query="rated:1"))

    def find_cards(self, query: str) -> list[int]:
        return self._invoke("findCards", query=query)

    def suspend(self, card_ids: list[int]) -> None:
        self._invoke("suspend", cards=card_ids)

    def unsuspend(self, card_ids: list[int]) -> None:
        self._invoke("unsuspend", cards=card_ids)

    def sync(self) -> None:
        self._invoke("sync")

    def create_deck(self, name: str) -> int:
        return self._invoke("createDeck", deck=name)

    def delete_decks(self, names: list[str], cards_too: bool = True) -> None:
        self._invoke("deleteDecks", decks=names, cardsToo=cards_too)

    def change_deck(self, card_ids: list[int], deck: str) -> None:
        self._invoke("changeDeck", cards=card_ids, deck=deck)

    def store_media_file(self, filename: str, path: str) -> str:
        return self._invoke("storeMediaFile", filename=filename, path=path)

    def add_notes(self, notes: list[dict[str, Any]]) -> list[int | None]:
        return self._invoke("addNotes", notes=notes)

    def cards_reviewed_by_day(self) -> list[list]:
        return self._invoke("getNumCardsReviewedByDay")

    def export_package(self, deck: str, path: str, include_sched: bool = False) -> None:
        self._invoke("exportPackage", deck=deck, path=path, includeSched=include_sched)

    def import_package(self, path: str) -> None:
        self._invoke("importPackage", path=path)
