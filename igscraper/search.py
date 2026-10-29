from urllib.parse import urljoin

from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from igscraper.constants import (
    SEARCH_PAGE,
    SEARCH_RESULTS_IMG_TEXT,
    SEARCH_SEL_INPUT_CANDIDATES,
    SEARCH_SEL_RESULTS_CONTAINER,
    SEARCH_SEL_RESULTS_IMG,
    SEARCH_SEL_RESULTS_NAMES,
    SEARCH_SEL_RESULTS_URL,
    SEARCH_SLEEP_INTER,
    SEARCH_TO_RESULTS,
    asleep,
    debug,
    error,
    info,
    success,
)
from igscraper.errors import guard
from igscraper.navigation import goto_page


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
        await field.press_sequentially(query)
        await field.press("Enter")

        await asleep(SEARCH_SLEEP_INTER)
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
        images = self._page.locator(SEARCH_SEL_RESULTS_IMG)

        accounts = []
        seen = set()

        for img in await images.all():
            alt = await img.get_attribute("alt") or ""
            username = alt.removeprefix(SEARCH_RESULTS_IMG_TEXT).strip()

            if not username or username in seen:
                continue

            container = img.locator(SEARCH_SEL_RESULTS_CONTAINER)
            names = await container.locator(SEARCH_SEL_RESULTS_NAMES).all_inner_texts()

            labels = list(dict.fromkeys(name.strip() for name in names if name.strip()))
            name = next((label for label in labels if label != username), username)

            url = await self._result_url(container, username)

            if url is None:
                continue

            accounts.append(
                {
                    "profilePictureUrl": await img.get_attribute("src"),
                    "username": username,
                    "name": name,
                    "url": url,
                },
            )

            seen.add(username)

        return accounts

    async def _result_url(self, container, username):
        for link in await container.locator(SEARCH_SEL_RESULTS_URL).all():
            href = await link.get_attribute("href")

            if not href:
                continue

            if href.strip("/").split("/", 1)[0] != username:
                continue

            return urljoin(self._page.url, href)

        return None


__all__ = ["Search"]
