import re
import time
from urllib.parse import urlparse

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from igscraper.constants import (
    SEARCH_DETAIL_SEPARATOR,
    SEARCH_EMPTY_DELAY,
    SEARCH_EMPTY_MARKERS,
    SEARCH_EMPTY_UNMARKED_DELAY,
    SEARCH_FOLLOWERS_SUFFIXES,
    SEARCH_NONPERSONALIZED_PATTERN,
    SEARCH_NONPERSONALIZED_TEXT,
    SEARCH_PAGE,
    SEARCH_PERSONALIZED_TEXT,
    SEARCH_POLL_DELAY,
    SEARCH_RESULTS_IMG_TEXT,
    SEARCH_SEL_BUSY,
    SEARCH_SEL_INPUT_CANDIDATES,
    SEARCH_SEL_RESULTS_IMG,
    SEARCH_SEL_RESULTS_LINK,
    SEARCH_SEL_RESULTS_SCOPE,
    SEARCH_SEL_TAB,
    SEARCH_STABLE_DELAY,
    SEARCH_TO_CLEAR,
    SEARCH_TO_RESULTS,
    SEARCH_TO_REUSE,
    SEARCH_TO_SWITCH,
    SEARCH_TO_TAB,
    SEARCH_UNCHANGED_DELAY,
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
from igscraper.navigation import goto_page, parse_count, poll_for, type_text
from igscraper.scripts import script


class Search:
    def __init__(self, page, *, reuse_page=True):
        self._page = page
        self._reuse_page = reuse_page

    @guard
    async def search(self, query):
        query = (query or "").strip()

        if not query:
            error("Requête de recherche vide.")

            return None

        field = await self._open_search()

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

    async def _open_search(self):
        if self._reuse_page and self._on_search_page():
            field = await self._find_input(SEARCH_TO_REUSE)

            if field is not None and await self._clear(field):
                info("Page de recherche déjà ouverte.")

                return field

            debug("Recherche précédente encore affichée : page rechargée.")

        await goto_page(self._page, SEARCH_PAGE)

        success("Page de recherche ouverte.")

        return await self._find_input(SEARCH_TO_RESULTS)

    def _on_search_page(self):
        return urlparse(self._page.url).path.rstrip("/") == urlparse(SEARCH_PAGE).path.rstrip("/")

    async def _find_input(self, wait_ms):
        field = self._page.locator(", ".join(SEARCH_SEL_INPUT_CANDIDATES)).first

        try:
            await field.wait_for(state="attached", timeout=wait_ms)
        except PlaywrightTimeoutError:
            return None

        return field

    async def _clear(self, field):
        try:
            await field.fill("", timeout=SEARCH_TO_REUSE)
        except PlaywrightError:
            return False

        async def cleared():
            return await self._collect() is None

        return await poll_for(cleared, timeout_s=SEARCH_TO_CLEAR / 1000)

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

        before = self._snapshot(await self._collect())

        try:
            await tab.first.click(timeout=SEARCH_TO_TAB)
        except PlaywrightError:
            warn(f"Clic sur l'onglet « {SEARCH_NONPERSONALIZED_TEXT} » impossible : résultats personnalisés seuls.")

            return personalized

        nonpersonalized = await self._stable_results(before) or []

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

    @staticmethod
    def _snapshot(state):
        if state is None:
            return None

        return tuple(account["username"] for account in state["accounts"]), state["empty"]

    async def _stable_results(self, previous):
        deadline = time.monotonic() + SEARCH_TO_SWITCH
        signature = None
        stable_since = None
        refreshed = previous is None

        while True:
            state = await self._collect()
            accounts = None if state is None else state["accounts"]
            current = tuple(account["username"] for account in accounts or ())
            busy = state is not None and state["busy"]
            now = time.monotonic()

            if state is not None and not refreshed:
                refreshed = busy or self._snapshot(state) != previous

            if state is None or busy:
                signature = None
            elif current != signature:
                signature = current
                stable_since = now
            elif now - stable_since >= self._settle_delay(state, refreshed=refreshed):
                return self._normalize(accounts)

            if now >= deadline:
                debug("Résultats non stabilisés dans le délai imparti.")

                return self._normalize(accounts)

            await asleep(SEARCH_POLL_DELAY)

    @staticmethod
    def _settle_delay(state, *, refreshed):
        if not refreshed:
            return SEARCH_UNCHANGED_DELAY

        if state["accounts"]:
            return SEARCH_STABLE_DELAY

        return SEARCH_EMPTY_DELAY if state["empty"] else SEARCH_EMPTY_UNMARKED_DELAY

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
                "emptyMarkers": list(SEARCH_EMPTY_MARKERS),
                "busySelector": SEARCH_SEL_BUSY,
            },
        )


__all__ = ["Search"]
