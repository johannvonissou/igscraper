import re
import time

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from igscraper.constants import (
    POLL_DELAY_GROWTH,
    POLL_DELAY_MAX,
    POLL_DELAY_START,
    SEARCH_DETAIL_SEPARATOR,
    SEARCH_FOLLOWERS_SUFFIXES,
    SEARCH_NONPERSONALIZED_PATTERN,
    SEARCH_NONPERSONALIZED_TEXT,
    SEARCH_PAGE,
    SEARCH_PERSONALIZED_TEXT,
    SEARCH_RESULTS_IMG_TEXT,
    SEARCH_SEL_INPUT_CANDIDATES,
    SEARCH_SEL_RESULTS_IMG,
    SEARCH_SEL_RESULTS_LINK,
    SEARCH_SEL_RESULTS_SCOPE,
    SEARCH_SEL_TAB,
    SEARCH_STABLE_DELAY,
    SEARCH_TO_RESULTS,
    SEARCH_TO_SWITCH,
    SEARCH_TO_TAB,
    TYPE_PAUSE_CHANCE,
    TYPE_PAUSE_MS,
    TYPE_SLEEP_MAX_MS,
    TYPE_SLEEP_MIN_MS,
    asleep,
    debug,
    error,
    info,
    success,
    warn,
)
from igscraper.errors import guard
from igscraper.navigation import goto_page, parse_count, type_text
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

        accounts = await self._combined_results()

        if accounts is None:
            error("Panneau de résultats introuvable.")

            return None

        info(f"Résultats pour « {query} » : {len(accounts)} compte(s).")

        return accounts

    @property
    def page(self):
        return self._page

    @staticmethod
    def _normalize(accounts):
        if accounts is None:
            return None

        return [
            {
                "profilePictureUrl": account["profilePictureUrl"],
                "username": account["username"],
                "name": account["name"],
                "followersCount": parse_count(Search._strip_followers(account["followers"])),
                "url": account["url"],
            }
            for account in accounts
        ]

    @staticmethod
    def _strip_followers(text):
        if not text:
            return None

        lowered = text.lower()

        for suffix in SEARCH_FOLLOWERS_SUFFIXES:
            if lowered.endswith(suffix):
                return text[: -len(suffix)].strip()

        return text

    async def _find_input(self):
        field = self._page.locator(", ".join(SEARCH_SEL_INPUT_CANDIDATES)).first

        try:
            await field.wait_for(state="attached", timeout=SEARCH_TO_RESULTS)
        except PlaywrightTimeoutError:
            return None

        return field

    async def _combined_results(self):
        tab = self._page.locator(SEARCH_SEL_TAB).filter(has_text=re.compile(SEARCH_NONPERSONALIZED_PATTERN))

        try:
            await tab.first.wait_for(state="visible", timeout=SEARCH_TO_TAB)
        except PlaywrightTimeoutError:
            warn(f"Onglet « {SEARCH_NONPERSONALIZED_TEXT} » introuvable : résultats personnalisés seuls.")

            return await self._stable_results(None)

        if await tab.first.get_attribute("aria-selected") == "true":
            return await self._stable_results(None)

        personalized = await self._stable_results(None)

        if personalized is None:
            return None

        info(f"Onglet « {SEARCH_PERSONALIZED_TEXT} » : {len(personalized)} compte(s).")

        try:
            await tab.first.click(timeout=SEARCH_TO_TAB)
        except PlaywrightError:
            warn(f"Clic sur l'onglet « {SEARCH_NONPERSONALIZED_TEXT} » impossible : résultats personnalisés seuls.")

            return personalized

        previous = tuple(account["username"] for account in personalized)
        nonpersonalized = await self._stable_results(previous) or []

        info(f"Onglet « {SEARCH_NONPERSONALIZED_TEXT} » : {len(nonpersonalized)} compte(s).")

        return self._union(personalized, nonpersonalized)

    @staticmethod
    def _union(*groups):
        merged = {}

        for accounts in groups:
            for account in accounts:
                known = merged.setdefault(account["username"], dict(account))

                for key, value in account.items():
                    if known.get(key) is None and value is not None:
                        known[key] = value

        return list(merged.values())

    async def _signature(self):
        accounts = await self._collect()

        return None if accounts is None else tuple(account["username"] for account in accounts)

    async def _stable_results(self, previous):
        deadline = time.monotonic() + SEARCH_TO_SWITCH
        delay = POLL_DELAY_START
        accounts = await self._collect()
        signature = None
        stable_since = None

        while True:
            current = None if accounts is None else tuple(account["username"] for account in accounts)
            changed = previous is None or current != previous

            if current and changed:
                if current != signature:
                    signature = current
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= SEARCH_STABLE_DELAY:
                    return self._normalize(accounts)

            if time.monotonic() >= deadline:
                debug("Résultats non stabilisés dans le délai imparti.")

                return self._normalize(accounts)

            await asleep(delay)

            delay = min(delay * POLL_DELAY_GROWTH, POLL_DELAY_MAX)
            accounts = await self._collect()

    async def _collect(self):
        return await self._page.evaluate(
            script("search_results"),
            {
                "scopeSelector": SEARCH_SEL_RESULTS_SCOPE,
                "tabSelector": SEARCH_SEL_TAB,
                "prefix": SEARCH_RESULTS_IMG_TEXT,
                "imgSelector": SEARCH_SEL_RESULTS_IMG,
                "linkSelector": SEARCH_SEL_RESULTS_LINK,
                "separator": SEARCH_DETAIL_SEPARATOR,
                "followerSuffixes": list(SEARCH_FOLLOWERS_SUFFIXES),
            },
        )


__all__ = ["Search"]
