from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from igscraper.constants import (
    SEARCH_PAGE,
    SEARCH_RESULTS_IMG_TEXT,
    SEARCH_SEL_INPUT_CANDIDATES,
    SEARCH_SEL_RESULTS_IMG,
    SEARCH_SEL_RESULTS_NAMES,
    SEARCH_SEL_RESULTS_URL,
    SEARCH_TO_RESULTS,
    TYPE_PAUSE_CHANCE,
    TYPE_PAUSE_MS,
    TYPE_SLEEP_MAX_MS,
    TYPE_SLEEP_MIN_MS,
    debug,
    error,
    info,
    success,
)
from igscraper.errors import guard
from igscraper.navigation import goto_page, type_text
from igscraper.scripts import script


class Search:
    def __init__(self, page):
        self._page = page

    @guard
    async def search(self, query):
        query = (query or "").strip()

        if not query:
            error("Requête de recherche vide.")

            return None

        await goto_page(self._page, SEARCH_PAGE)

        success("Page de recherche ouverte.")

        field = await self._find_input()

        if field is None:
            error("Barre de recherche introuvable.")

            return None

        try:
            await field.focus(timeout=SEARCH_TO_RESULTS)
        except PlaywrightTimeoutError:
            error("Barre de recherche non focalisable (page non chargée ?).")

            return None

        await field.fill("")
        await type_text(
            field,
            query,
            min_ms=TYPE_SLEEP_MIN_MS,
            max_ms=TYPE_SLEEP_MAX_MS,
            pause_ms=TYPE_PAUSE_MS,
            pause_chance=TYPE_PAUSE_CHANCE,
        )
        await field.press("Enter")

        await self._wait_results()

        accounts = await self._collect()

        info(f"Résultats pour « {query} » : {len(accounts)} compte(s).")

        return accounts

    @property
    def page(self):
        return self._page

    async def _find_input(self):
        for selector in SEARCH_SEL_INPUT_CANDIDATES:
            locator = self._page.locator(selector)

            if await locator.count():
                return locator.first

        return None

    async def _wait_results(self):
        try:
            await self._page.locator(SEARCH_SEL_RESULTS_IMG).first.wait_for(state="visible", timeout=SEARCH_TO_RESULTS)
        except PlaywrightTimeoutError:
            debug("Aucun résultat visible dans le délai imparti.")

    async def _collect(self):
        return await self._page.evaluate(
            script("search_results"),
            {
                "prefix": SEARCH_RESULTS_IMG_TEXT,
                "imgSelector": SEARCH_SEL_RESULTS_IMG,
                "namesSelector": SEARCH_SEL_RESULTS_NAMES,
                "linkSelector": SEARCH_SEL_RESULTS_URL,
            },
        )


__all__ = ["Search"]
